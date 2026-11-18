# -*- coding: utf-8 -*-
"""Build the AMITAC paper in the required layout:
A4, TWO columns (7.75cm each, 0.5cm gap), margins 2.5cm, single spacing,
title 16pt bold, headings 12/11pt bold, body 10pt DFKai + Times New Roman,
last page balanced across both columns, no page numbers."""
import sys
from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

SRC = r"C:/dev/cti-platform/docs/paper/content.txt"
OUT = r"C:/dev/cti-platform/docs/AMITAC2026_CTI專題論文_v4.docx"
CN, EN = "標楷體", "Times New Roman"
COL_SPACE_TWIPS = 284   # 0.5cm

def set_run(run, size=10, bold=False):
    run.font.name = EN
    run.font.size = Pt(size)
    run.font.bold = bold
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts"); rPr.append(rFonts)
    for attr in ("w:ascii", "w:hAnsi"):
        rFonts.set(qn(attr), EN)
    rFonts.set(qn("w:eastAsia"), CN)

def para(doc, text="", size=10, bold=False, align=None, before=0, after=0, line=1.0):
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
        para(doc, text, size=12, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, before=8, after=6)
    else:
        para(doc, text, size=11, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, before=6, after=4)

def set_cols(section, num):
    sectPr = section._sectPr
    cols = sectPr.find(qn("w:cols"))
    if cols is None:
        cols = OxmlElement("w:cols"); sectPr.append(cols)
    cols.set(qn("w:num"), str(num))
    cols.set(qn("w:space"), str(COL_SPACE_TWIPS))

def set_margins(section):
    for side in ("top", "bottom", "left", "right"):
        setattr(section, side + "_margin", Cm(2.5))

def cell_text(cell, text, size=10, bold=False):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(1); p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.line_spacing = 1.0
    set_run(p.add_run(text), size, bold)

def add_table(doc, caption, rows):
    full = (len(rows[0]) in (1, 3, 5))
    if full:
        s = doc.add_section(WD_SECTION.CONTINUOUS); set_cols(s, 1); set_margins(s)
    para(doc, caption, size=10, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, before=6, after=4)
    n_rows, n_cols = len(rows), len(rows[0])
    table = doc.add_table(rows=n_rows, cols=n_cols)
    table.style = "Table Grid"; table.alignment = WD_TABLE_ALIGNMENT.CENTER; table.autofit = False
    tblPr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for side, val in (("top", 20), ("left", 60), ("bottom", 20), ("right", 60)):
        el = OxmlElement("w:" + side); el.set(qn("w:w"), str(val)); el.set(qn("w:type"), "dxa"); mar.append(el)
    tblPr.append(mar)
    if n_cols == 1: col_w = [15.5]
    elif n_cols == 2: col_w = [2.8, 4.7]
    elif n_cols == 3: col_w = [6.2, 5.4, 3.9]
    elif n_cols == 5: col_w = [2.1, 2.9, 2.9, 3.3, 4.3]
    else: col_w = [15.5 / n_cols] * n_cols
    grid = table._tbl.find(qn("w:tblGrid"))
    if grid is not None:
        for j, gc in enumerate(grid.findall(qn("w:gridCol"))):
            gc.set(qn("w:w"), str(int(col_w[j] / 2.54 * 1440)))
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = table.cell(i, j); c.width = Cm(col_w[j])
            cell_text(c, val, size=10, bold=(i == 0))
    if full:
        s2 = doc.add_section(WD_SECTION.CONTINUOUS); set_cols(s2, 2); set_margins(s2)

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
sec0 = doc.sections[0]; set_margins(sec0); set_cols(sec0, 1)
para(doc, "", size=10)
para(doc, title, size=16, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=10)
para(doc, meta.get("school", ""), size=12, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
para(doc, meta.get("authors", ""), size=12, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
para(doc, meta.get("advisor", ""), size=12, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=10)
para(doc, "摘要", size=12, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, before=4, after=4)
para(doc, meta.get("abstract", ""), size=10, after=4)
p = para(doc, "", size=10, after=6)
set_run(p.add_run("關鍵詞："), 10, True)
set_run(p.add_run(meta.get("keywords", "")), 10, False)

sec1 = doc.add_section(WD_SECTION.CONTINUOUS); set_margins(sec1); set_cols(sec1, 2)

i = 0
while i < len(lines):
    ln = lines[i].rstrip()
    if not ln.strip():
        i += 1; continue
    if ln.startswith(("@TITLE ", "@SCHOOL ", "@AUTHORS ", "@ADVISOR ", "@ABSTRACT ", "@KEYWORDS ")):
        i += 1; continue
    if ln.startswith("#1 "):
        heading(doc, 1, ln[3:]); i += 1; continue
    if ln.startswith("#2 "):
        heading(doc, 2, ln[3:]); i += 1; continue
    if ln.startswith("@EQ "):
        para(doc, ln[4:], size=10, align=WD_ALIGN_PARAGRAPH.CENTER, before=3, after=3); i += 1; continue
    if ln.startswith("@TCAP "):
        caption = ln[6:].strip(); rows = []; i += 1
        while i < len(lines) and lines[i].strip().startswith("|"):
            rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")]); i += 1
        add_table(doc, caption, rows)
        continue
    if ln.startswith("@IMG "):
        path = ln[5:].strip(); i += 1; cap = ""
        if i < len(lines) and lines[i].startswith("@ICAP "):
            cap = lines[i][6:].strip(); i += 1
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(4)
        p.add_run().add_picture(path, width=Cm(7.75))
        para(doc, cap, size=10, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, before=2, after=6)
        continue
    para(doc, ln, size=10, after=0)
    i += 1

tail = doc.add_section(WD_SECTION.CONTINUOUS); set_margins(tail); set_cols(tail, 1)
para(doc, "", size=10)

doc.save(OUT)
d2 = Document(OUT)
print("saved", OUT)
print("sections:", len(d2.sections), "| cols:", [s._sectPr.find(qn("w:cols")).get(qn("w:num")) for s in d2.sections])
print("tables:", len(d2.tables), "| images:", len(d2.inline_shapes), "| chars:", sum(len(p.text) for p in d2.paragraphs))
