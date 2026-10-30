# -*- coding: utf-8 -*-
"""
============================================================
config.py —— 全局配置文件（所有脚本共用）
============================================================

【这是什么】
    这是一个"设置文件"，不是要单独运行的程序。
    后面 01/02/03/04 每个脚本开头都会 import 它，
    这样"数据在哪、结果存哪、哪些变量算什么类型、图里用中文字体"
    这些设置就只用写一遍，改的时候也只改这一个文件。

【原理】
    Python 的 import 机制：脚本运行时，Python 会把"当前脚本所在的文件夹"
    加入搜索路径（sys.path[0]），所以同目录下的 config.py 可以直接 import。
    这也是为什么这些文件必须放在同一个文件夹里。

【你需要改的地方】
    基本不用改。除非你换了一个新的数据文件，
    那就只改下面 DATA_FILE 这一行。
============================================================
"""

import os
import sys
import glob

# ------------------------------------------------------------
# 第 0 步：让控制台能正常显示中文
# ------------------------------------------------------------
# 【原理】Windows 控制台默认用 GBK 编码（cp936），而 Python 3 内部字符串是
#        Unicode。打印中文时如果编码对不上就会抛 UnicodeEncodeError 或乱码。
#        reconfigure 把输出流强制改成 UTF-8，再配合运行脚本里的 chcp 65001
#        就能正常显示。这一步纯粹是"防乱码"，对数据分析结果没有任何影响。
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


# ------------------------------------------------------------
# 第 1 步：路径设置
# ------------------------------------------------------------
# 【原理】__file__ 是"当前这个 py 文件自己的路径"。
#        os.path.dirname() 取出它所在的文件夹。
#        这样写的好处：不管你从哪个目录运行脚本，路径都指向正确位置，
#        不会出现"在 A 文件夹运行就找不到文件"的问题（这叫"绝对路径"，比相对路径稳）。
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 原始数据文件名（如果换数据，只改这里）
DATA_FILE = os.path.join(BASE_DIR, "上市公司 控制变量_剔除金融剔除ST或PT已缩尾.dta")

# 所有结果（表格、图、日志）统一放在这个子文件夹里，不跟代码混在一起
OUT_DIR = os.path.join(BASE_DIR, "输出结果")


def ensure_out_dir():
    """确保输出文件夹存在；不存在就新建（exist_ok=True 表示已存在也不报错）。"""
    os.makedirs(OUT_DIR, exist_ok=True)
    return OUT_DIR


def find_data_file():
    """
    找到数据文件。
    如果 config 里写死的文件名不存在，就在同目录下自动找第一个 .dta 文件。
    【为什么加这个】文件名里带空格和中文，容易手误；自动兜底更省事。
    """
    if os.path.exists(DATA_FILE):
        return DATA_FILE
    candidates = sorted(glob.glob(os.path.join(BASE_DIR, "*.dta")))
    if not candidates:
        raise FileNotFoundError(
            f"在 {BASE_DIR} 里没找到 .dta 数据文件，请检查数据是否放在这个文件夹。"
        )
    return candidates[0]


# ------------------------------------------------------------
# 第 2 步：变量分组
# ------------------------------------------------------------
# 【为什么要分组】
#    描述统计里，连续变量算"均值/标准差/分位数"，分类变量算"频数和占比"，
#    两者方法完全不同。先把变量分好类，后面的代码才能自动处理，
#    不用每加一个变量就改一次代码。

# 标识类：不是用来统计的，是"谁、哪一年、哪个行业"
ID_VARS = ["stkcd", "year", "证券代码", "行业代码", "省份", "所属城市", "Industry"]

# 垃圾列：这是数据商（淘宝店）打广告塞进来的文字列，不是真实变量。
# 留着会污染统计分析，所以读取时直接删掉。
JUNK_COLS = ["知行数据分析"]

# 连续变量（控制变量 + 主要变量），描述统计的主战场
CONT_VARS = [
    "Size",       # 公司规模（总资产取自然对数）
    "Lev",        # 资产负债率
    "ROA",        # 总资产净利润率
    "ROE",        # 净资产收益率
    "ATO",        # 总资产周转率
    "Cashflow",   # 现金流比率
    "INV",        # 存货占比
    "FIXED",      # 固定资产占比
    "Growth",     # 营业收入增长率
    "TobinQ",     # 托宾Q值
    "Board",      # 董事人数
    "Indep",      # 独立董事占比
    "Top1",       # 第一大股东持股比例
    "Top5",       # 前五大股东持股比例
    "Top10",      # 前十大股东持股比例
    "Balance1",   # 股权制衡度（第2-5大股东/第1大股东）
    "Balance2",   # 股权制衡度（第2-10大股东/第1大股东）
    "ListAge",    # 上市年限（取对数）
    "FirmAge",    # 公司成立年限（取对数）
    "INST",       # 机构投资者持股比例
    "Mshare",     # 管理层持股比例
    "Mfee",       # 管理费用率
    "Occupy",     # 大股东资金占用
    "AgC1_1",     # 第一类代理成本：管理费用率
    "AgC1_2",     # 第一类代理成本：经营费用率
    "AgC1_3",     # 第一类代理成本：总资产周转率
    "AgC2",       # 第二类代理成本
    "Employ",     # 员工总人数
    "Cap1",       # 人均资产
    "Cap2",       # 单位营收资产
    "Pay",        # 薪酬（数据里没给标签，名称原样保留）
]

# 0/1 虚拟变量与有序分类变量：算频数、占比
CAT_VARS = [
    "Loss",             # 是否亏损（1=亏损）
    "Dual",             # 两职合一（董事长兼总经理=1）
    "SOE",              # 股权性质（1=国企）
    "Big4",             # 是否四大审计（1=是）
    "企业区域",         # 东部=2 / 中部=1 / 西部=0
    "管制行业",         # 是否管制行业
    "是否发生ST或ST或PT",  # 是否被 ST/*ST/PT
]

# 分组统计用的维度变量（按行业/省份/年份看样本分布）
GROUP_VARS = ["Industry", "省份", "year"]

# 画图时重点看分布的 8 个核心变量（子图太多会看不清）
PLOT_VARS = ["Size", "Lev", "ROA", "Growth", "TobinQ", "Top1", "INST", "Mfee"]

# 变量中文名对照表：让输出的表格和论文里一样是中文
VAR_LABELS = {
    "Size": "公司规模", "Lev": "资产负债率", "ROA": "总资产净利润率",
    "ROE": "净资产收益率", "ATO": "总资产周转率", "Cashflow": "现金流比率",
    "INV": "存货占比", "FIXED": "固定资产占比", "Growth": "营业收入增长率",
    "TobinQ": "托宾Q值", "Board": "董事人数", "Indep": "独立董事占比",
    "Top1": "第一大股东持股比例", "Top5": "前五大股东持股比例",
    "Top10": "前十大股东持股比例", "Balance1": "股权制衡度1",
    "Balance2": "股权制衡度2", "ListAge": "上市年限", "FirmAge": "公司成立年限",
    "INST": "机构投资者持股比例", "Mshare": "管理层持股比例",
    "Mfee": "管理费用率", "Occupy": "大股东资金占用",
    "AgC1_1": "第一类代理成本(管理费用率)", "AgC1_2": "第一类代理成本(经营费用率)",
    "AgC1_3": "第一类代理成本(总资产周转率)", "AgC2": "第二类代理成本",
    "Employ": "员工总人数", "Cap1": "人均资产", "Cap2": "单位营收资产",
    "Pay": "薪酬", "Loss": "是否亏损", "Dual": "两职合一", "SOE": "股权性质",
    "Big4": "是否四大审计", "企业区域": "企业区域", "管制行业": "管制行业",
    "是否发生ST或ST或PT": "是否ST/PT",
}


# ------------------------------------------------------------
# 第 3 步：读取数据的统一入口
# ------------------------------------------------------------
def load_data(drop_junk=True, verbose=True):
    """
    读取 Stata 的 .dta 文件，返回 (DataFrame, meta)。

    【原理】
      1. .dta 是 Stata 的二进制格式，不是文本，用记事本打开是乱码。
         pandas 虽然能直接 read_stata，但 pyreadstat 更稳，
         而且能顺便把"变量标签（中文注释）"一起读出来。
      2. 返回值 df 是 pandas 的 DataFrame —— 本质上就是一张 Excel 表：
         行 = 观测值（公司-年度），列 = 变量。
      3. meta 里存着变量的中文标签、文件说明等"元信息"。

    【参数】
      drop_junk=True  自动删掉数据商塞的广告列
      verbose=True    读的时候打印一点信息，方便确认没读错
    """
    import pyreadstat

    path = find_data_file()
    df, meta = pyreadstat.read_dta(path)

    if verbose:
        print(f"已读取数据：{os.path.basename(path)}")
        print(f"  观测值（行）数：{df.shape[0]:,}")
        print(f"  变量（列）数  ：{df.shape[1]}")

    if drop_junk:
        junk = [c for c in JUNK_COLS if c in df.columns]
        if junk:
            df = df.drop(columns=junk)
            if verbose:
                print(f"  已删除广告列：{junk}")

    return df, meta


# ------------------------------------------------------------
# 第 4 步：matplotlib 中文字体设置
# ------------------------------------------------------------
def setup_matplotlib():
    """
    让 matplotlib 画图时能显示中文、负号不变成方块。

    【原理】matplotlib 默认字体 DejaVu Sans 里没有汉字，
           所以中文会显示成一个个小方框。
           指定成 Windows 自带的"微软雅黑/黑体"就好了。
    """
    import matplotlib
    matplotlib.use("Agg")          # 用不弹窗的后端，直接把图存成文件
    import matplotlib.pyplot as plt

    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei", "SimHei", "SimSun", "DejaVu Sans"
    ]
    plt.rcParams["axes.unicode_minus"] = False   # 正常显示负号
    plt.rcParams["figure.dpi"] = 120
    plt.rcParams["savefig.bbox"] = "tight"       # 保存时自动裁掉多余白边
    plt.rcParams["axes.grid"] = True
    plt.rcParams["grid.alpha"] = 0.3
    return plt


def cn(var):
    """变量名 -> 中文名，查不到就返回原名。"""
    return VAR_LABELS.get(var, var)
