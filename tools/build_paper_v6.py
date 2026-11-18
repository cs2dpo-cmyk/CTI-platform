# -*- coding: utf-8 -*-
"""v6: AMITAC typography rules.
Title 16pt bold; authors/section headings 12pt bold; level-2 headings 11pt bold;
body, abstract and references 10pt regular; captions bold 10pt; single spacing;
no page numbers; headings left-aligned with one blank line before and after."""
import sys
from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

SRC = r"C:/dev/cti-platform/docs/paper/content.txt"
OUT = r"C:/dev/cti-platform/docs/AMITAC2026_CTI專題論文_v6.docx"
CN, EN = "標楷體", "Times New Roman"
BODY, TITLE, H1, H2, CAP = 10, 16, 12, 11, 10
TEXT_W = 15.5

def set_run(run, size=BODY, bold=False):
    run.font.name = EN
    run.font.size = Pt(size)
    run.font.bold = bold
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts"); rPr.append(rFonts)
    for a in ("w:ascii", "w:hAnsi"):
        rFonts.set(qn(a), EN)
    rFonts.set(qn("w:eastAsia"), CN)

def para(doc, text="", size=BODY, bold=False, align=None, before=0, after=0, line=1.0):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(before); pf.space_after = Pt(after); pf.line_spacing = line
    if text:
        set_run(p.add_run(text), size, bold)
    return p

def heading(doc, level, text):
    if level == 1:
        para(doc, text, size=H1, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, before=H1, after=H1)
    else:
        para(doc, text, size=H2, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, before=H2, after=H2)

def cell_text(cell, text, size=BODY, bold=False):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(1); p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.line_spacing = 1.0
    set_run(p.add_run(text), size, bold)

def add_table(doc, caption, rows):
    para(doc, caption, size=CAP, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, before=CAP, after=CAP / 2)
    n_rows, n_cols = len(rows), len(rows[0])
    table = doc.add_table(rows=n_rows, cols=n_cols)
    table.style = "Table Grid"; table.alignment = WD_TABLE_ALIGNMENT.CENTER; table.autofit = False
    tblPr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for side, val in (("top", 20), ("left", 60), ("bottom", 20), ("right", 60)):
        el = OxmlElement("w:" + side); el.set(qn("w:w"), str(val)); el.set(qn("w:type"), "dxa"); mar.append(el)
    tblPr.append(mar)
    if n_cols == 1: col_w = [TEXT_W]
    elif n_cols == 2: col_w = [5.0, TEXT_W - 5.0]
    elif n_cols == 3: col_w = [6.2, 5.4, TEXT_W - 11.6]
    elif n_cols == 5: col_w = [2.1, 2.9, 2.9, 3.3, TEXT_W - 11.2]
    else: col_w = [TEXT_W / n_cols] * n_cols
    grid = table._tbl.find(qn("w:tblGrid"))
    if grid is not None:
        for j, gc in enumerate(grid.findall(qn("w:gridCol"))):
            gc.set(qn("w:w"), str(int(col_w[j] / 2.54 * 1440)))
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = table.cell(i, j); c.width = Cm(col_w[j])
            cell_text(c, val, size=BODY, bold=(i == 0))
    para(doc, "", size=BODY, after=CAP)

lines = open(SRC, encoding="utf-8").read().split("\n")
meta, title = {}, None
for ln in lines:
    if ln.startswith("@TITLE "): title = ln[7:]
    elif ln.startswith("@SCHOOL "): meta["school"] = ln[8:]
    elif ln.startswith("@AUTHORS "): meta["authors"] = ln[9:]
    elif ln.startswith("@ADVISOR "): meta["advisor"] = ln[9:]
    elif ln.startswith("@ABSTRACT "): meta["abstract"] = ln[10:]
    elif ln.startswith("@KEYWORDS "): meta["keywords"] = ln[10:]

doc = Document()
sec = doc.sections[0]
for side in ("top", "bottom", "left", "right"):
    setattr(sec, side + "_margin", Cm(2.5))
cols = sec._sectPr.find(qn("w:cols"))
if cols is None:
    cols = OxmlElement("w:cols"); sec._sectPr.append(cols)
cols.set(qn("w:num"), "1")

para(doc, "", size=BODY)
para(doc, title, size=TITLE, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=TITLE)
para(doc, meta.get("school", ""), size=H1, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
para(doc, meta.get("authors", ""), size=H1, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
para(doc, meta.get("advisor", ""), size=H1, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=H1)
heading(doc, 1, "摘要")
para(doc, meta.get("abstract", ""), size=BODY, after=BODY)
p = para(doc, "", size=BODY, after=0)
set_run(p.add_run("關鍵詞："), BODY, True)
set_run(p.add_run(meta.get("keywords", "")), BODY, False)

i = 0
while i < len(lines):
    ln = lines[i].rstrip()
    if not ln.strip():
        i += 1; continue
    if ln.startswith(("@TITLE ", "@SCHOOL ", "@AUTHORS ", "@ADVISOR ", "@ABSTRACT ", "@KEYWORDS ")):
        i += 1; continue
    if ln.startswith("#1 "):
        text = ln[3:]
        if text.startswith("參考文獻"):
            h = para(doc, text, size=H1, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, before=0, after=H1)
            h.paragraph_format.page_break_before = True
            i += 1; continue
        heading(doc, 1, text); i += 1; continue
    if ln.startswith("#2 "):
        heading(doc, 2, ln[3:]); i += 1; continue
    if ln.startswith("@EQ "):
        para(doc, ln[4:], size=BODY, align=WD_ALIGN_PARAGRAPH.CENTER, before=BODY, after=BODY); i += 1; continue
    if ln.startswith("@TCAP "):
        caption = ln[6:].strip(); rows = []; i += 1
        while i < len(lines) and lines[i].strip().startswith("|"):
            rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")]); i += 1
        add_table(doc, caption, rows)
        continue
    if ln.startswith("@IMG "):
        spec = ln[5:].strip(); i += 1; cap = ""
        width_cm = 15.0
        if "|" in spec:
            path, w = spec.split("|", 1)
            try: width_cm = float(w)
            except ValueError: width_cm = 15.0
        else:
            path = spec
        if i < len(lines) and lines[i].startswith("@ICAP "):
            cap = lines[i][6:].strip(); i += 1
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(CAP)
        p.add_run().add_picture(path, width=Cm(width_cm))
        para(doc, cap, size=CAP, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, before=CAP / 2, after=CAP)
        continue
    para(doc, ln, size=BODY, after=0)
    i += 1

doc.save(OUT)
d2 = Document(OUT)
print("saved", OUT)
print("tables:", len(d2.tables), "images:", len(d2.inline_shapes), "chars:", sum(len(p.text) for p in d2.paragraphs))
