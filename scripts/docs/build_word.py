"""Build the Word deliverables in docs/word/ from the Markdown-like sources in docs/word/src/.

Supported source syntax (deliberately small):
  front matter   key: value lines up to the first '---' (title, subtitle, header, meta, toc, style)
  # / ## / ###   headings 1-3; with "numbered: yes" they get 1, 1.1, 1.1.1 unless the text starts with "!"
  - item         bullet list;  1. item  numbered paragraph (number kept as written)
  ![caption](path)   figure, numbered "Gambar N."
  Tabel: caption     caption for the next pipe table, numbered "Tabel N."
  | a | b |          pipe table, first row is the header
  > text             note box
  ```                code block
  [pagebreak]        page break
  **bold**, *italic*, `code` inline

Usage: python scripts/docs/build_word.py [name ...]
"""
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "docs" / "word" / "src"
OUT = ROOT / "docs" / "word"
ACCENT = RGBColor(0x0D, 0x4F, 0x5C)
INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)")


def set_cell_shading(cell, hex_fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tc_pr.append(shd)


def paragraph_border(paragraph, side="left", color="0D4F5C", size=18):
    p_pr = paragraph._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    edge = OxmlElement(f"w:{side}")
    edge.set(qn("w:val"), "single")
    edge.set(qn("w:sz"), str(size))
    edge.set(qn("w:space"), "8")
    edge.set(qn("w:color"), color)
    borders.append(edge)
    p_pr.append(borders)


def paragraph_shading(paragraph, hex_fill):
    p_pr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    p_pr.append(shd)


def add_field(run, instr):
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    text = OxmlElement("w:instrText")
    text.set(qn("xml:space"), "preserve")
    text.text = instr
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    placeholder = OxmlElement("w:t")
    placeholder.text = "Klik kanan lalu pilih Update Field untuk memperbarui daftar isi."
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for el in (begin, text, sep, placeholder, end):
        run._r.append(el)


def add_inline(paragraph, text, size=None):
    for part in INLINE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = "Consolas"
            run._r.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "Consolas")
            run.font.size = Pt((size or 11) - 1.5)
            run.font.color.rgb = RGBColor(0x3A, 0x3A, 0x3A)
            continue
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            run = paragraph.add_run(part[1:-1])
            run.italic = True
        else:
            run = paragraph.add_run(part)
        if size:
            run.font.size = Pt(size)


class Builder:
    def __init__(self, meta):
        self.meta = meta
        self.doc = Document()
        self.fig = 0
        self.tab = 0
        self.pending_table_caption = None
        self.numbered_headings = meta.get("numbered") == "yes"
        self.counters = [0, 0, 0]
        self.body_font = meta.get("font", "Cambria")
        self.body_size = float(meta.get("size", "11.5"))
        self.spacing = float(meta.get("spacing", "1.3"))
        self._styles()
        self._page()

    def _styles(self):
        st = self.doc.styles
        normal = st["Normal"]
        normal.font.name = self.body_font
        normal.element.rPr.rFonts.set(qn("w:eastAsia"), self.body_font)
        normal.font.size = Pt(self.body_size)
        pf = normal.paragraph_format
        pf.line_spacing = self.spacing
        pf.space_after = Pt(6)
        for level, size in ((1, 16), (2, 13.5), (3, 12)):
            h = st[f"Heading {level}"]
            h.font.name = "Calibri"
            h.element.rPr.rFonts.set(qn("w:asciiTheme"), "")
            h.element.rPr.rFonts.set(qn("w:hAnsiTheme"), "")
            h.font.size = Pt(size)
            h.font.bold = True
            h.font.color.rgb = ACCENT if level < 3 else RGBColor(0x22, 0x22, 0x22)
            h.paragraph_format.space_before = Pt(18 if level == 1 else 12)
            h.paragraph_format.space_after = Pt(6)
            h.paragraph_format.keep_with_next = True
        for name in ("List Bullet", "List Number"):
            st[name].font.name = self.body_font
            st[name].font.size = Pt(self.body_size)

    def _page(self):
        s = self.doc.sections[0]
        s.page_height, s.page_width = Cm(29.7), Cm(21.0)
        s.top_margin = s.bottom_margin = Cm(2.5)
        s.left_margin, s.right_margin = Cm(3.0), Cm(2.5)

    def cover(self):
        d, m = self.doc, self.meta
        for _ in range(5):
            d.add_paragraph()
        p = d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r = p.add_run(m.get("kicker", "").upper())
        r.font.size, r.font.bold, r.font.color.rgb = Pt(10.5), True, ACCENT
        p = d.add_paragraph()
        r = p.add_run(m["title"])
        r.font.size, r.font.bold, r.font.name = Pt(26), True, "Calibri"
        p.paragraph_format.line_spacing = 1.05
        paragraph_border(p, "bottom", size=12)
        if m.get("subtitle"):
            p = d.add_paragraph()
            r = p.add_run(m["subtitle"])
            r.font.size, r.font.color.rgb = Pt(13), RGBColor(0x44, 0x44, 0x44)
        for _ in range(6):
            d.add_paragraph()
        for line in m.get("meta", []):
            p = d.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            add_inline(p, line, size=10.5)
        p = d.add_paragraph()
        p.add_run().add_break(WD_BREAK.PAGE)

    def title_block(self):
        d, m = self.doc, self.meta
        p = d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(m["title"])
        r.font.size, r.font.bold, r.font.name = Pt(15), True, "Calibri"
        p.paragraph_format.line_spacing = 1.1
        for line in m.get("meta", []):
            p = d.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(0)
            add_inline(p, line.split(":**", 1)[-1].strip(), size=10.5)
        rule = d.add_paragraph()
        paragraph_border(rule, "bottom", size=6)

    def toc(self):
        p = self.doc.add_paragraph()
        r = p.add_run("Daftar Isi")
        r.font.name, r.font.size, r.font.bold, r.font.color.rgb = "Calibri", Pt(16), True, ACCENT
        add_field(self.doc.add_paragraph().add_run(), 'TOC \\o "1-3" \\h \\z \\u')
        p = self.doc.add_paragraph()
        p.add_run().add_break(WD_BREAK.PAGE)

    def header_footer(self):
        for i, s in enumerate(self.doc.sections):
            s.different_first_page_header_footer = True
            hp = s.header.paragraphs[0]
            hp.text = ""
            r = hp.add_run(self.meta.get("header", self.meta["title"]))
            r.font.size, r.font.color.rgb = Pt(8.5), RGBColor(0x66, 0x66, 0x66)
            hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            fp = s.footer.paragraphs[0]
            fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = fp.add_run()
            r.font.size = Pt(9)
            add_field_simple(r, "PAGE")

    def heading(self, level, text):
        if text.startswith("!"):
            text = text[1:].strip()
        elif self.numbered_headings:
            self.counters[level - 1] += 1
            for k in range(level, 3):
                self.counters[k] = 0
            text = ".".join(str(c) for c in self.counters[:level]) + ("." if level == 1 else "") + "  " + text
        self.doc.add_paragraph(text, style=f"Heading {level}")

    def para(self, text):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        add_inline(p, text)

    def bullet(self, text, level=0):
        p = self.doc.add_paragraph(style="List Bullet" if level == 0 else "List Bullet 2")
        p.paragraph_format.space_after = Pt(3)
        add_inline(p, text)

    def numbered(self, num, text):
        p = self.doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.9)
        p.paragraph_format.first_line_indent = Cm(-0.6)
        p.paragraph_format.space_after = Pt(3)
        p.add_run(f"{num}\t")
        p.paragraph_format.tab_stops.add_tab_stop(Cm(0.9))
        add_inline(p, text)

    def note(self, text):
        p = self.doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.4)
        p.paragraph_format.right_indent = Cm(0.2)
        paragraph_border(p)
        paragraph_shading(p, "EEF5F5")
        add_inline(p, text, size=self.body_size - 0.5)

    def code(self, lines):
        for i, line in enumerate(lines):
            p = self.doc.add_paragraph()
            pf = p.paragraph_format
            pf.space_after = Pt(0) if i < len(lines) - 1 else Pt(8)
            pf.space_before = Pt(0)
            pf.line_spacing = 1.0
            pf.left_indent = Cm(0.3)
            paragraph_shading(p, "F3F4F4")
            r = p.add_run(line or " ")
            r.font.name = "Consolas"
            r._r.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "Consolas")
            r.font.size = Pt(8.5)

    def figure(self, caption, path, width_cm=None):
        img = ROOT / path
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.line_spacing = 1.0
        from PIL import Image

        with Image.open(img) as im:
            w, h = im.size
        width = width_cm or 15.5
        if h / w > 1.25:  # tall images such as phone screenshots
            width = min(width, 7.5)
        p.add_run().add_picture(str(img), width=Cm(width))
        self.fig += 1
        c = self.doc.add_paragraph()
        c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = c.add_run(f"Gambar {self.fig}. ")
        r.bold, r.font.size = True, Pt(9.5)
        add_inline(c, caption, size=9.5)

    def table(self, rows):
        if self.pending_table_caption:
            self.tab += 1
            c = self.doc.add_paragraph()
            c.paragraph_format.keep_with_next = True
            c.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = c.add_run(f"Tabel {self.tab}. ")
            r.bold, r.font.size = True, Pt(9.5)
            add_inline(c, self.pending_table_caption, size=9.5)
            self.pending_table_caption = None
        ncol = len(rows[0])
        t = self.doc.add_table(rows=0, cols=ncol)
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        # column widths follow content length (square root damps very long cells), within 15.5 cm
        weights = []
        for ci in range(ncol):
            lengths = sorted(len(r[ci]) if ci < len(r) else 0 for r in rows)
            typical = lengths[int(len(lengths) * 0.8)] if lengths else 1
            weights.append(max(typical, 6) ** 0.6)
        widths = [Cm(15.5 * w / sum(weights)) for w in weights]
        for ci, col in enumerate(t.columns):  # Word lays out from tblGrid, so set it as well as each cell
            col.width = widths[ci]
        for ri, row in enumerate(rows):
            cells = t.add_row().cells
            for ci in range(ncol):
                val = row[ci] if ci < len(row) else ""
                cell = cells[ci]
                cell.width = widths[ci]
                cell.paragraphs[0].paragraph_format.line_spacing = 1.0
                cell.paragraphs[0].paragraph_format.space_after = Pt(2)
                add_inline(cell.paragraphs[0], val.replace("**", "") if ri == 0 else val, size=9.5)
                if ri == 0:
                    for r in cell.paragraphs[0].runs:
                        r.bold = True
                        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                    set_cell_shading(cell, "0D4F5C")
                elif ri % 2 == 0:
                    set_cell_shading(cell, "F2F6F6")
        # repeat header row on each page
        tr_pr = t.rows[0]._tr.get_or_add_trPr()
        el = OxmlElement("w:tblHeader")
        el.set(qn("w:val"), "true")
        tr_pr.append(el)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def page_break(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def save(self, path):
        settings = self.doc.settings.element
        upd = OxmlElement("w:updateFields")
        upd.set(qn("w:val"), "true")
        settings.append(upd)
        self.doc.core_properties.title = self.meta["title"]
        self.doc.core_properties.author = self.meta.get("author", "")
        self.doc.core_properties.language = "id-ID"
        self.doc.save(path)


def add_field_simple(run, instr):
    for typ, val in (("begin", None), ("instr", instr), ("separate", None), ("text", "1"), ("end", None)):
        if typ == "instr":
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = val
        elif typ == "text":
            el = OxmlElement("w:t")
            el.text = val
        else:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), typ)
        run._r.append(el)


def parse_front_matter(lines):
    meta, i = {"meta": []}, 0
    while i < len(lines) and lines[i].strip() != "---":
        key, _, val = lines[i].partition(":")
        if key.strip() == "meta":
            meta["meta"].append(val.strip())
        elif key.strip():
            meta[key.strip()] = val.strip()
        i += 1
    return meta, lines[i + 1:]


def split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def build(name):
    lines = (SRC / f"{name}.md").read_text(encoding="utf-8").splitlines()
    meta, body = parse_front_matter(lines)
    b = Builder(meta)
    if meta.get("cover") == "compact":
        b.title_block()
    else:
        b.cover()
    if meta.get("toc", "yes") == "yes":
        b.toc()
    i, para_buf = 0, []

    def flush():
        if para_buf:
            b.para(" ".join(s.strip() for s in para_buf))
            para_buf.clear()

    while i < len(body):
        line = body[i]
        s = line.strip()
        if not s:
            flush()
        elif s.startswith("```"):
            flush()
            j = i + 1
            block = []
            while not body[j].strip().startswith("```"):
                block.append(body[j].rstrip())
                j += 1
            b.code(block)
            i = j
        elif s.startswith("#"):
            flush()
            level = len(s) - len(s.lstrip("#"))
            b.heading(level, s[level:].strip())
        elif s == "[pagebreak]":
            flush()
            b.page_break()
        elif m := re.match(r"!\[(.*)\]\(([^)\s]+)(?:\s+(\d+(?:\.\d+)?))?\)$", s):
            flush()
            b.figure(m.group(1), m.group(2), float(m.group(3)) if m.group(3) else None)
        elif s.startswith("Tabel:"):
            flush()
            b.pending_table_caption = s[len("Tabel:"):].strip()
        elif s.startswith("|"):
            flush()
            rows = []
            while i < len(body) and body[i].strip().startswith("|"):
                if not re.match(r"^\|[\s:|-]+\|$", body[i].strip()):
                    rows.append(split_row(body[i]))
                i += 1
            b.table(rows)
            continue
        elif s.startswith("> "):
            flush()
            text = [s[2:]]
            while i + 1 < len(body) and body[i + 1].strip().startswith(">"):
                i += 1
                text.append(body[i].strip()[1:].strip())
            b.note(" ".join(text))
        elif re.match(r"^\s*- ", line):
            flush()
            b.bullet(s[2:], level=1 if line.startswith("  ") else 0)
        elif m := re.match(r"^(\d+[.)]|[a-z][.)])\s+(.*)", s):
            flush()
            b.numbered(m.group(1), m.group(2))
        else:
            para_buf.append(s)
        i += 1
    flush()
    b.header_footer()
    out = OUT / f"{meta.get('file', name)}.docx"
    b.save(out)
    print(f"{out.relative_to(ROOT)}  figures={b.fig} tables={b.tab}")


if __name__ == "__main__":
    names = sys.argv[1:] or sorted(p.stem for p in SRC.glob("*.md"))
    for n in names:
        build(n)
