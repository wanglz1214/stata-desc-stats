# -*- coding: utf-8 -*-
"""
从描述统计 CSV 生成「学术论文三线表」Word 文档（.docx）。

用法（双击运行或在命令行）：
    python make_three_line_docx.py --input 02_描述统计_论文格式.csv --output 主要变量描述性统计.docx
    python make_three_line_docx.py -i in.csv -o out.docx --title "主要变量描述性统计" --font 楷体 --size 10.5

输入 CSV 要求：第一列是变量名称，其余列是统计量（样本量/均值/标准差/最小值/中位数/最大值…）。
表头行（第一行）会加粗并加栏目线。

依赖：pip install python-docx
"""
import sys, os, csv, argparse

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
except ImportError:
    print("缺少 python-docx，请先安装：")
    print("  python -m pip install -i https://pypi.org/simple python-docx")
    sys.exit(1)


# ---------------------------------------------------------------
# 低层工具：直接操作 OOXML，因为 python-docx 没有封装边框接口
# ---------------------------------------------------------------
def _set_run_font(run, font_name, size_pt, bold=False):
    """设置一个文字块的中文字体。
    关键点：中文必须同时写 w:eastAsia，只写 font.name 对中文无效。"""
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.bold = bold
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    rFonts.set(qn("w:ascii"), font_name)
    rFonts.set(qn("w:hAnsi"), font_name)
    rFonts.set(qn("w:eastAsia"), font_name)   # 中文靠这个


def _fmt_cell(cell, font_name, size_pt, bold=False, align="center"):
    cell.vertical_alignment = 1  # 垂直居中
    for p in cell.paragraphs:
        p.alignment = {"center": WD_ALIGN_PARAGRAPH.CENTER,
                       "left": WD_ALIGN_PARAGRAPH.LEFT,
                       "right": WD_ALIGN_PARAGRAPH.RIGHT}[align]
        p.paragraph_format.space_before = Pt(1.5)
        p.paragraph_format.space_after = Pt(1.5)
        for r in p.runs:
            _set_run_font(r, font_name, size_pt, bold)


def _cell_border(cell, bottom=None):
    """给单个单元格加边框。bottom={'sz':6,'val':'single','color':'000000'}
    sz 单位是 1/8 磅：12 = 1.5pt（粗线），6 = 0.75pt（细线）。"""
    if bottom is None:
        return
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = tcPr.find(qn("w:tcBorders"))
    if tcBorders is None:
        tcBorders = OxmlElement("w:tcBorders")
        tcPr.append(tcBorders)
    el = tcBorders.find(qn("w:bottom"))
    if el is None:
        el = OxmlElement("w:bottom")
        tcBorders.append(el)
    for k, v in bottom.items():
        el.set(qn("w:" + k), str(v))


def _table_borders(table, top_sz=12, bottom_sz=12):
    """设置整表边框：只留顶线和底线，左右与内部线全部去掉——这就是三线表的骨架。
    注意：w:tblBorders 里的子元素必须按 top/left/bottom/right/insideH/insideV 顺序插入，
    顺序错了 Word 会认为 XML 不合法。"""
    tblPr = table._tbl.tblPr
    old = tblPr.find(qn("w:tblBorders"))
    if old is not None:
        tblPr.remove(old)
    borders = OxmlElement("w:tblBorders")
    spec = [("top", top_sz), ("left", 0), ("bottom", bottom_sz),
            ("right", 0), ("insideH", 0), ("insideV", 0)]
    for edge, sz in spec:
        el = OxmlElement("w:" + edge)
        el.set(qn("w:val"), "single" if sz else "none")
        el.set(qn("w:sz"), str(sz))
        el.set(qn("w:color"), "000000")
        borders.append(el)
    tblPr.append(borders)


def build(csv_path, docx_path, title="主要变量描述性统计", note="",
          font="楷体", size=10.5, title_size=12, note_size=9):
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.reader(f) if any(c.strip() for c in r)]
    if not rows:
        raise ValueError("CSV 是空的")
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]

    doc = Document()
    # 让西文默认字体也跟随，避免英文数字掉回 Calibri
    normal = doc.styles["Normal"]
    normal.font.name = font
    normal.font.size = Pt(size)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), font)

    # 表名
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    _set_run_font(p.add_run(title), font, title_size, bold=True)

    # 表格
    table = doc.add_table(rows=len(rows), cols=ncol)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    _table_borders(table, top_sz=12, bottom_sz=12)

    for ri, row in enumerate(rows):
        for ci, txt in enumerate(row):
            cell = table.cell(ri, ci)
            cell.text = txt
            is_header = (ri == 0)
            _fmt_cell(cell, font, size, bold=is_header, align="center")
            if is_header:
                # 栏目线（表头下的细线）——必须在整表边框之后设置，否则会被覆盖
                _cell_border(cell, bottom={"sz": 6, "val": "single", "color": "000000"})

    # 表注
    if note:
        pn = doc.add_paragraph()
        pn.alignment = WD_ALIGN_PARAGRAPH.LEFT
        pn.paragraph_format.space_before = Pt(3)
        pn.paragraph_format.space_after = Pt(3)
        _set_run_font(pn.add_run(note), font, note_size, bold=False)

    doc.save(docx_path)
    return len(rows), ncol


def main():
    ap = argparse.ArgumentParser(description="生成三线表 Word 文档")
    ap.add_argument("-i", "--input", required=True, help="输入 CSV 路径")
    ap.add_argument("-o", "--output", required=True, help="输出 docx 路径")
    ap.add_argument("--title", default="主要变量描述性统计", help="表名")
    ap.add_argument("--note", default="", help="表下注释文字")
    ap.add_argument("--font", default="楷体", help="字体，默认楷体")
    ap.add_argument("--size", type=float, default=10.5, help="表格字号（磅），默认10.5（五号）")
    ap.add_argument("--title-size", type=float, default=12, help="表名字号（磅）")
    ap.add_argument("--note-size", type=float, default=9, help="注释字号（磅）")
    a = ap.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(a.output)) or ".", exist_ok=True)
    nrow, ncol = build(a.input, a.output, a.title, a.note,
                       a.font, a.size, a.title_size, a.note_size)
    print("已生成：%s" % os.path.abspath(a.output))
    print("  规格：%d 行 × %d 列，字体 %s %.1f 磅，顶/底线 1.5 磅，栏目线 0.75 磅" %
          (nrow, ncol, a.font, a.size))


if __name__ == "__main__":
    main()
