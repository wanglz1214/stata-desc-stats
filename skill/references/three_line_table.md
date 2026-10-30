# 学术论文三线表：实现细节与两条技术路线

## 一、三线表规范

| 元素 | 规格 | OOXML 值 |
|---|---|---|
| 顶线 | 1.5 磅实线 | `w:sz="12"`（单位是 1/8 磅） |
| 底线 | 1.5 磅实线 | `w:sz="12"` |
| 栏目线（表头下那条） | 0.75 磅实线 | `w:sz="6"` |
| 左右边线 | 无 | `w:val="none"` |
| 内部横线 | 无 | `w:val="none"` |
| 内部竖线 | 无 | `w:val="none"` |

字体：楷体。表名 12 磅加粗居中，表体 10.5 磅（五号），表注 9 磅（小五）左对齐。

## 二、路线 A：python-docx（推荐，自包含，可移植）

依赖 `pip install python-docx`。核心是 python-docx 没封装边框接口，要直接操作 OOXML。

### 整表边框

`w:tblBorders` 的子元素**必须按 top → left → bottom → right → insideH → insideV 顺序**插入，
顺序错了 Word 会判定 XML 不合法。

```python
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def _table_borders(table, top_sz=12, bottom_sz=12):
    tblPr = table._tbl.tblPr
    old = tblPr.find(qn("w:tblBorders"))
    if old is not None:
        tblPr.remove(old)
    borders = OxmlElement("w:tblBorders")
    for edge, sz in [("top", top_sz), ("left", 0), ("bottom", bottom_sz),
                     ("right", 0), ("insideH", 0), ("insideV", 0)]:
        el = OxmlElement("w:" + edge)
        el.set(qn("w:val"), "single" if sz else "none")
        el.set(qn("w:sz"), str(sz))
        el.set(qn("w:color"), "000000")
        borders.append(el)
    tblPr.append(borders)
```

### 单元格下框线（栏目线）

```python
def _cell_border(cell, bottom):   # bottom={"sz":6,"val":"single","color":"000000"}
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
```

**顺序很重要**：先设整表 `tblBorders`，再设表头的 `tcBorders`。
反过来会被覆盖掉。

### 中文字体

只设 `run.font.name` 对中文无效，必须写 `w:eastAsia`：

```python
def _set_run_font(run, font_name, size_pt, bold=False):
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.bold = bold
    rFonts = run._element.get_or_add_rPr().get_or_add_rFonts()
    rFonts.set(qn("w:ascii"), font_name)
    rFonts.set(qn("w:hAnsi"), font_name)
    rFonts.set(qn("w:eastAsia"), font_name)   # 中文靠这个
```

文档默认样式（Normal）也要设，否则表格外的段落会掉回 Calibri。

## 三、路线 B：腾讯 editor_sdk（本机可用，但依赖平台）

技能 `tencent-local-office-edit`，SDK 目录：

```
D:\workbuddy\resources\app.asar.unpacked\resources\plugins\workbuddy-builtin\skills\tencent-local-office-edit
```

调用方式：

```bash
python.exe edsdk.py call create_doc
python.exe edsdk.py call doc_insert_paragraph_with_text file_id=<id> idx=-1 text="表名"
python.exe edsdk.py call doc_insert_table file_id=<id> idx=10 row_count=22 col_count=7
python.exe edsdk.py call doc_set_table_cells --json-file cells.json
python.exe edsdk.py call doc_set_table_properties --json '{"file_id":..., "borders":{...}}'
python.exe edsdk.py call save_file --json '{"file_id":..., "file_path":"D:\\...\\x.docx"}'
```

### 踩过的坑（都已验证）

1. **borders 不能整包传**：一次传多个边框字段会报 `ToCommands returned empty`，
   必须拆成多次调用，每次只传一类字段。
2. **单元格边框会被 `tblBorders` 覆盖**：表头下面那条栏目线要**最后**再补一次。
3. **`paragraph_id` 会漂移**：删除段落后 id 会变，改段落属性前先跑
   `doc_resolve_document_structure` 取最新 id。
4. **`mode:"auto"` 自适应列宽无效**：不报错但没效果。
5. 参数含中文时用 `--json-file` 传（先写 UTF-8 JSON 文件），比命令行直接拼 JSON 稳。

**选型建议**：路线 A 优先——脚本化、可复现、能放进 GitHub 给别人用。
路线 B 只在需要「用户能在 Word/WPS 里实时看到编辑过程」时才用。
