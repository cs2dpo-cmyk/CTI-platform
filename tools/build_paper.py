# -*- coding: utf-8 -*-
"""Build the AMITAC 2026 paper docx from content.txt markup."""
import re, sys
from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

SRC = r"C:/dev/cti-platform/docs/paper/content.txt"
OUT = r"C:/dev/cti-platform/docs/AMITAC2026_CTI專題論文.docx"

CN = "標楷體"
EN = "Times New Roman"

def set_run(run, size=10, bold=False):
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

def para(doc, text="", size=10, bold=False, align=None, before=0, after=0, line=1.0):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    if text:
        r = p.add_run(text)
        set_run(r, size, bold)
    return p

def heading(doc, level, text):
    size = 12 if level == 1 else 11
    para(doc, text, size=size, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, before=8, after=8)

def set_cols(section, num, space_twips=284):
    sectPr = section._sectPr
    cols = sectPr.find(qn("w:cols"))
    if cols is None:
        cols = OxmlElement("w:cols")
        sectPr.append(cols)
    cols.set(qn("w:num"), str(num))
    cols.set(qn("w:space"), str(space_twips))

def set_margins(section):
    for side in ("top", "bottom", "left", "right"):
        setattr(section, side + "_margin", Cm(2.5))

def cell_text(cell, text, size=10, bold=False):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.line_spacing = 1.0
    r = p.add_run(text)
    set_run(r, size, bold)

def add_table(doc, caption, rows, full_width=False):
    if full_width:
        # swap into a single-column continuous section, then back to two columns
        s1 = doc.add_section(WD_SECTION.CONTINUOUS)
        set_cols(s1, 1)
        set_margins(s1)
    para(doc, caption, size=10, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, before=6, after=4)
    n_rows, n_cols = len(rows), len(rows[0])
    table = doc.add_table(rows=n_rows, cols=n_cols)
    table.style = "Table Grid"
    table.autofit = False
    width_cm = 16.0 if full_width else 7.75
    col_w = [width_cm / n_cols] * n_cols
    if full_width and n_cols == 5:
        col_w = [2.2, 3.0, 3.0, 3.4, 4.4]
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = table.cell(i, j)
            c.width = Cm(col_w[j])
            cell_text(c, val, size=10, bold=(i == 0))
    if full_width:
        s2 = doc.add_section(WD_SECTION.CONTINUOUS)
        set_cols(s2, 2)
        set_margins(s2)

# ---------------- parse ----------------
lines = open(SRC, encoding="utf-8").read().split("\n")

doc = Document()
# front-matter section: single column
sec0 = doc.sections[0]
set_margins(sec0)
set_cols(sec0, 1)
para(doc, "", size=10)
title = None
meta = {}
for ln in lines:
    if ln.startswith("@TITLE "): title = ln[7:]
    elif ln.startswith("@SCHOOL "): meta["school"] = ln[8:]
    elif ln.startswith("@AUTHORS "): meta["authors"] = ln[9:]
    elif ln.startswith("@ADVISOR "): meta["advisor"] = ln[9:]
    elif ln.startswith("@ABSTRACT "): meta["abstract"] = ln[10:]
    elif ln.startswith("@KEYWORDS "): meta["keywords"] = ln[10:]

para(doc, title, size=16, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=10)
para(doc, meta.get("school", ""), size=12, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
para(doc, meta.get("authors", ""), size=12, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
para(doc, meta.get("advisor", ""), size=12, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=10)
para(doc, "摘要", size=12, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, before=6, after=6)
para(doc, meta.get("abstract", ""), size=10, after=6)
p = para(doc, "", size=10, after=6)
r = p.add_run("關鍵詞：")
set_run(r, 10, True)
r2 = p.add_run(meta.get("keywords", ""))
set_run(r2, 10, False)

# body section: two columns
sec1 = doc.add_section(WD_SECTION.CONTINUOUS)
set_margins(sec1)
set_cols(sec1, 2)

i = 0
lines = lines
while i < len(lines):
    ln = lines[i].rstrip()
    if not ln.strip():
        i += 1
        continue
    if ln.startswith("#1 "):
        heading(doc, 1, ln[3:]); i += 1; continue
    if ln.startswith("#2 "):
        heading(doc, 2, ln[3:]); i += 1; continue
    if ln.startswith("@EQ "):
        para(doc, ln[4:], size=10, align=WD_ALIGN_PARAGRAPH.CENTER, before=4, after=4); i += 1; continue
    if ln.startswith("@TCAP "):
        caption = ln[6:].strip()
        rows = []
        i += 1
        while i < len(lines) and lines[i].strip().startswith("|"):
            cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            rows.append(cells)
            i += 1
        full = len(rows[0]) >= 5 if rows else False
        add_table(doc, caption, rows, full_width=full)
        para(doc, "", size=10)
        continue
    if ln.startswith("@IMG "):
        path = ln[5:].strip()
        i += 1
        cap = ""
        if i < len(lines) and lines[i].startswith("@ICAP "):
            cap = lines[i][6:].strip()
            i += 1
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(6)
        p.add_run().add_picture(path, width=Cm(7.75))
        para(doc, cap, size=10, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, before=2, after=6)
        continue
    # normal paragraph
    para(doc, ln, size=10, after=0)
    i += 1

# balance the last page's columns: a trailing continuous single-column section
tail = doc.add_section(WD_SECTION.CONTINUOUS)
set_margins(tail)
set_cols(tail, 1)
para(doc, "", size=10)

doc.save(OUT)
print("saved", OUT)

# verification pass: reopen and report stats
doc2 = Document(OUT)
print("sections:", len(doc2.sections))
print("paragraphs:", len(doc2.paragraphs))
print("tables:", len(doc2.tables))
body_chars = 0
for p in doc2.paragraphs:
    body_chars += len(p.text)
print("total chars:", body_chars)
for s in doc2.sections:
    cols = s._sectPr.find(qn("w:cols"))
    print("cols:", cols.get(qn("w:num")) if cols is not None else "?", "space:", cols.get(qn("w:space")) if cols is not None else "?")
