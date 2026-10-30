---
name: stata-panel-desc-stats
description: 上市公司面板数据（.dta/.csv）描述性统计全套流水线——读数据、体检、描述统计表、相关性/VIF 共线性、画图，并生成学术论文格式的「中文三线表」Word 文档。当用户提到"描述统计/描述性统计/变量统计表/论文表格/三线表/相关系数矩阵/VIF/共线性/数据体检/面板数据"且数据是 Stata 的 .dta 或其他表格文件时启用。面向无 Python 基础的用户，脚本内含【在干嘛】【原理】中文注释。
agent_created: true
---

# 上市公司面板数据描述性统计流水线

## 1. 目的

把「一份 .dta 面板数据 → 论文里那张描述统计表」做成一条可重复执行、可交接的流水线。
产出：变量清单、缺失报告、描述统计表、相关系数矩阵、VIF 诊断、5 张图、以及**中文三线表 Word 文档**。

## 2. 何时启用

- 用户要做「描述统计 / 描述性统计 / 变量统计表」。
- 用户要「三线表」「论文表格」「Word 表」，内容是统计结果。
- 用户拿到一份 .dta / .xlsx / .csv 的面板或截面数据，想先摸清底数。
- 用户提到 VIF、共线性、相关系数矩阵、缩尾、量纲这些词。

不适用：回归分析本身（那是下一步，本 skill 只做回归前的摸底）。

## 3. 环境前提（本机 Windows，已验证）

Python 用绝对路径调用，不要依赖 `python` 在 PATH 里：

```
C:\Users\14568\.workbuddy\binaries\python\versions\3.13.12\python.exe
```

必需包：pandas、numpy、pyreadstat、matplotlib、openpyxl、scipy、python-docx

**装包必须加官方源**，默认清华源在这台机器上取不到包：

```
python.exe -m pip install -i https://pypi.org/simple --no-warn-script-location <包名>
```

**不要浪费时间建 venv**：`python -m venv` 在本机会静默失败（退出码 0 但目录不生成），
直接装进托管 Python 即可。

## 4. 标准流程

### 第 1 步：跑流水线

```bash
PY="C:/Users/14568/.workbuddy/binaries/python/versions/3.13.12/python.exe"
"$PY" scripts/stata_desc_pipeline.py "D:/路径/数据.dta"
```

可选参数：
- `--out 输出目录`（默认：数据同级的 `输出结果/`）
- `--id stkcd --year year`（公司代码列、年份列；不传会自动识别）
- `--core Size Lev ROA`（指定画哪些变量的图，默认取缺失最少的 9 个）

产出文件（都在输出目录里）：

| 文件 | 内容 |
|---|---|
| `01_变量清单.csv` | 每个变量的类型、缺失率、唯一值数、中文标签 |
| `01_重复检查.txt` | 公司-年度是否重复、公司数、年份跨度 |
| `02_描述统计.xlsx` | 描述统计 / 论文格式 / 虚拟变量频数 / 分年度均值 / 量纲警报 |
| `02_描述统计_论文格式.csv` | **三线表的输入**，7 列中文表头 |
| `03_相关系数矩阵.xlsx` | Pearson、Spearman、长表带星号、VIF |
| `04_图*.png` | 变量分布直方图、相关系数热力图、年度趋势图 |

### 第 2 步：生成 Word 三线表

```bash
"$PY" scripts/make_three_line_docx.py \
  -i "输出目录/02_描述统计_论文格式.csv" \
  -o "输出目录/主要变量描述性统计.docx" \
  --title "主要变量描述性统计" \
  --note "注：样本为……连续变量均经 1% 和 99% 分位缩尾处理。"
```

可选：`--font 楷体`（默认）、`--size 10.5`（五号）、`--title-size 12`、`--note-size 9`。

### 第 3 步：把体检发现的问题告诉用户

不要只交表格。**必须在回复里点名**流水线报警的问题，详见 `references/data_quality.md`：
完全重复的变量对、量纲混杂、VIF>10 的变量组、常数列、缩尾是否真的做过。

## 5. 三线表规范（已固化在脚本里）

| 元素 | 规格 |
|---|---|
| 顶线 / 底线 | 1.5 磅实线（`w:sz=12`，单位是 1/8 磅） |
| 栏目线（表头下） | 0.75 磅实线（`w:sz=6`） |
| 左右边线、内部横竖线 | 全部 `val="none"` |
| 字体 | 楷体（必须写 `w:eastAsia`，只设 `font.name` 对中文无效） |
| 表头 | 加粗、水平垂直居中 |
| 表名 | 楷体 12 磅加粗居中 |
| 表注 | 楷体 9 磅左对齐 |

关键实现细节见 `references/three_line_table.md`，里面有 python-docx 直接操作
OOXML 的写法和腾讯 editor_sdk 方案的踩坑记录。

## 6. 交付给无 Python 基础的用户

- 提供一个 `运行全部.bat`（**内容必须纯 ASCII**，中文注释在 .bat 里会乱码），双击即可跑全流程。
- Python 脚本内三件套：`sys.stdout.reconfigure(encoding="utf-8")`、CSV 用 `utf-8-sig` 编码、
  matplotlib 中文字体用 `Microsoft YaHei`。
- 每个步骤脚本里写【在干嘛】【原理】两段注释，解释这一步在算什么、为什么这么算。

## 7. 参考文件

- `references/windows_env.md` — 本机环境踩坑（venv 失败、pip 源、编码、字体）
- `references/three_line_table.md` — 三线表实现细节与两条技术路线的对比
- `references/data_quality.md` — 数据体检清单与各类问题的判断标准
