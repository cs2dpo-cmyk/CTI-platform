# -*- coding: utf-8 -*-
"""Build the competition paper docx in the reference layout:
A4, single column, 3 cm margins, 12 pt DFKai + Times New Roman."""
import re, sys
from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

SRC = r"C:/dev/cti-platform/docs/paper/content.txt"
OUT = r"C:/dev/cti-platform/docs/AMITAC2026_CTI專題論文_v3.docx"

CN = "標楷體"
EN = "Times New Roman"
TEXT_W_CM = 16.0   # A4 21cm - 2*2.5cm

def set_run(run, size=11, bold=False):
    run.font.name = EN
    run.font.size = Pt(size)
    run.font.bold = bold
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), EN)
    rFonts.set(qn("w:hAnsi"), EN)
    rFonts.set(qn("w:eastAsia"), CN)

def para(doc, text="", size=11, bold=False, align=None, before=0, after=0, line=1.0):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    if text:
        set_run(p.add_run(text), size, bold)
    return p

def heading(doc, level, text):
    if level == 1:
        para(doc, text, size=13, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, before=8, after=4)
    else:
        para(doc, text, size=11.5, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, before=6, after=2)

def cell_text(cell, text, size=10, bold=False, align=None):
    cell.text = ""
    p = cell.paragraphs[0]
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.line_spacing = 1.0
    set_run(p.add_run(text), size, bold)

def add_table(doc, caption, rows):
    para(doc, caption, size=10.5, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, before=8, after=4)
    n_rows, n_cols = len(rows), len(rows[0])
    table = doc.add_table(rows=n_rows, cols=n_cols)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    if n_cols == 1:
        col_w = [TEXT_W_CM]
    elif n_cols == 2:
        col_w = [5.0, TEXT_W_CM - 5.0]
    elif n_cols == 3:
        col_w = [6.4, 5.6, 3.0]
    elif n_cols == 5:
        col_w = [3.1, 3.0, 2.9, 2.9, 3.1]
    else:
        col_w = [TEXT_W_CM / n_cols] * n_cols
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = table.cell(i, j)
            c.width = Cm(col_w[j])
            cell_text(c, val, size=10, bold=(i == 0))


# ---- parse ----
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

para(doc, "", size=10)
para(doc, title, size=16, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=12)
para(doc, meta.get("school", ""), size=12, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
para(doc, meta.get("authors", ""), size=12, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
para(doc, meta.get("advisor", ""), size=12, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=12)
para(doc, "摘要", size=13, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, before=6, after=4)
para(doc, meta.get("abstract", ""), size=11, after=4)
p = para(doc, "", size=11, after=8)
set_run(p.add_run("關鍵詞："), 11, True)
set_run(p.add_run(meta.get("keywords", "")), 11, False)

i = 0
while i < len(lines):
    ln = lines[i].rstrip()
    if not ln.strip():
        i += 1; continue
    if ln.startswith("#1 "):
        heading(doc, 1, ln[3:]); i += 1; continue
    if ln.startswith("#2 "):
        heading(doc, 2, ln[3:]); i += 1; continue
    if ln.startswith("@EQ "):
        para(doc, ln[4:], size=11, align=WD_ALIGN_PARAGRAPH.CENTER, before=4, after=4); i += 1; continue
    if ln.startswith("@TCAP "):
        caption = ln[6:].strip()
        rows = []
        i += 1
        while i < len(lines) and lines[i].strip().startswith("|"):
            rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
            i += 1
        add_table(doc, caption, rows)
        continue
    if ln.startswith("@IMG "):
        path = ln[5:].strip(); i += 1
        cap = ""
        if i < len(lines) and lines[i].startswith("@ICAP "):
            cap = lines[i][6:].strip(); i += 1
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(6)
        p.add_run().add_picture(path, width=Cm(9.6))
        para(doc, cap, size=10.5, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, before=2, after=8)
        continue
    para(doc, ln, size=11, after=0)
    i += 1

doc.save(OUT)
print("saved", OUT)
d2 = Document(OUT)
print("paragraphs:", len(d2.paragraphs), "tables:", len(d2.tables), "images:", len(d2.inline_shapes))
print("chars:", sum(len(p.text) for p in d2.paragraphs))
