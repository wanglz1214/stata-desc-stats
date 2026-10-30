# -*- coding: utf-8 -*-
"""
============================================================
02_描述统计.py
============================================================
目的：算出论文里那张"描述性统计表（Descriptive Statistics）"。

这是实证论文的标配表格，也是你判断数据质量最直接的窗口。
它一般包含这几列：
    N（样本量）、Mean（均值）、SD（标准差）、Min（最小值）、
    P25（25 分位）、Median（中位数）、P75（75 分位）、Max（最大值）

我们额外加了三列，帮你判断数据是否需要处理：
    Skew（偏度）、Kurt（峰度）、缺失率

输出文件（在"输出结果"文件夹）：
    02_描述统计.xlsx    —— 多个工作表：连续变量、分类变量、分年度均值
    02_描述统计_论文格式.csv —— 只有核心 8 列，可直接贴进论文

运行方式：python 02_描述统计.py
============================================================
"""

import os
import numpy as np
import pandas as pd

import config as cfg

print("=" * 70)
print("第 1 步：读取数据")
print("=" * 70)
df, meta = cfg.load_data()
cfg.ensure_out_dir()


# ============================================================
# 第 2 步：连续变量的描述统计
# ============================================================
# 【在干嘛】对 cfg.CONT_VARS 里的每个连续变量，算它的集中趋势、离散程度、分布形状。
# 【原理】每个指标在回答什么问题：
#   N       —— 有效样本量（去掉缺失后的数目）。N 不一致说明变量缺失程度不同。
#   Mean    —— 均值，平均值。对极端值敏感（一个 1 亿的离群点能把它拉飞）。
#   SD      —— 标准差，数据"散得有多开"。SD 太小说明变量几乎不变，解释力弱。
#   Min/Max —— 极值。用来发现离谱数据（比如资产负债率 15 这种不可能的值）。
#   P25/P50/P75 —— 分位数。P50 就是中位数，比均值更抗极端值。
#               "均值 vs 中位数"差很多，说明分布偏斜严重。
#   Skew    —— 偏度。0 = 对称；>0 右偏（长尾在右边）；<0 左偏。
#   Kurt    —— 峰度（超额峰度，正态分布=0）。>0 说明尾部很厚，极端值多。
#
# 【实证里的经验判断】
#   偏度绝对值 > 1 或峰度 > 3，通常要考虑"缩尾（winsorize）"或取对数。
#   你这份数据文件名写了"已缩尾"，所以后面看到极值应该在合理范围内。
print("\n" + "=" * 70)
print("第 2 步：计算连续变量描述统计")
print("=" * 70)

rows = []
for v in cfg.CONT_VARS:
    if v not in df.columns:
        print(f"  [跳过] 变量 {v} 不在数据里")
        continue
    s = pd.to_numeric(df[v], errors="coerce")   # 强制转数值，转不了的变缺失
    s_valid = s.dropna()
    rows.append({
        "变量": v,
        "变量名": cfg.cn(v),
        "N": int(s_valid.shape[0]),
        "均值": s_valid.mean(),
        "标准差": s_valid.std(),
        "最小值": s_valid.min(),
        "P25": s_valid.quantile(0.25),
        "中位数": s_valid.median(),
        "P75": s_valid.quantile(0.75),
        "最大值": s_valid.max(),
        "偏度": s_valid.skew(),
        "峰度": s_valid.kurt(),
        "缺失率(%)": round(s.isna().mean() * 100, 2),
    })

desc = pd.DataFrame(rows)

# 【在干嘛】判断每个变量的偏度和峰度是否超出"可接受范围"，打个标记
# 【原理】abs(偏度)>1 或 峰度>3 算是明显非正态，回归前一般要处理
desc["分布提示"] = np.where(
    (desc["偏度"].abs() > 1) | (desc["峰度"] > 3),
    "偏态明显，注意",
    "接近正态"
)

# 打印时只保留 3 位小数，看起来清爽
pretty = desc.copy()
for c in ["均值", "标准差", "最小值", "P25", "中位数", "P75", "最大值", "偏度", "峰度"]:
    pretty[c] = pretty[c].round(3)

print(f"共统计 {len(desc)} 个连续变量\n")
print(pretty[["变量", "N", "均值", "标准差", "最小值", "最大值", "偏度", "峰度"]]
      .to_string(index=False))


# ============================================================
# 第 3 步：分类/虚拟变量的频数统计
# ============================================================
# 【在干嘛】统计每个 0/1 变量里"1 占多少比例"。
# 【原理】对虚拟变量，均值 = 取 1 的比例（因为 0 不影响求和）。
#        例如 SOE 的均值 0.35，意思是"35% 的观测是国有企业"。
#        这一步能立刻看出样本结构：
#        SOE 接近 0 或 1，说明样本几乎全是民企或全是国企，
#        那这个变量在回归里就没有对比组，解释不了任何东西。
print("\n" + "=" * 70)
print("第 3 步：分类变量频数")
print("=" * 70)

cat_rows = []
for v in cfg.CAT_VARS:
    if v not in df.columns:
        continue
    vc = df[v].value_counts(dropna=False).sort_index()
    total = len(df)
    for val, cnt in vc.items():
        cat_rows.append({
            "变量": v,
            "变量名": cfg.cn(v),
            "取值": "缺失" if pd.isna(val) else val,
            "频数": int(cnt),
            "占比(%)": round(cnt / total * 100, 2),
        })
cat_freq = pd.DataFrame(cat_rows)
print(cat_freq.to_string(index=False))


# ============================================================
# 第 4 步：数据质量警报——比率型变量里不该出现的值
# ============================================================
# 【在干嘛】检查一批"按定义就该落在 0~1 之间"的比率变量，
#          看有多少观测超过 1，并判断是哪种问题。
# 【原理】比率型变量是"分子/分母"，比如 负债合计/资产总计。
#        这类值数学上不可能超过 1。如果出现 7.8、17.3，
#        几乎只有一个解释：量纲错了 —— 把 7.8% 写成了 7.8 而不是 0.078。
#        这种混杂单位不处理，会直接毁掉均值、标准差和回归系数。
#
#        【要小心假警报】不是所有"百分比"变量都该落在 0~1：
#        独立董事占比(Indep)、管理层持股比例(Mshare)这两列
#        整列都用"33.33 表示 33.33%"的写法，是统一口径不是错误。
#        所以下面只检查"有界比率"变量，
#        把 Mshare / Indep 单独作为"百分数口径"提示，不报错。
print("\n" + "=" * 70)
print("第 4 步：数据质量警报（比率变量是否超过 1）")
print("=" * 70)

# 这些变量的含义决定了它们必须在 0~1 之间（极少数可为负）
bounded_ratio = ["Lev", "INV", "FIXED", "Cashflow", "Mfee", "AgC1_1",
                 "AgC1_2", "Occupy", "AgC2", "INST", "Top1"]
bounded_ratio = [v for v in bounded_ratio if v in df.columns]

alert_rows = []
for v in bounded_ratio:
    s = pd.to_numeric(df[v], errors="coerce").dropna()
    n_big = int((s > 1).sum())
    alert_rows.append({
        "变量": v,
        "变量名": cfg.cn(v),
        "中位数": round(s.median(), 4),
        "超过1的观测数": n_big,
        "占比(%)": round(n_big / len(s) * 100, 2),
        "最大值": round(s.max(), 3),
    })
alert = pd.DataFrame(alert_rows).sort_values("超过1的观测数", ascending=False)
print(alert.to_string(index=False))

bad = alert[alert["超过1的观测数"] > 0]
if len(bad):
    print("\n【发现】以下'有界比率'变量出现了不可能的值，属于量纲混杂：")
    for _, r in bad.iterrows():
        print(f"  · {r['变量']}（{r['变量名']}）：{r['超过1的观测数']:,} 条"
              f"（{r['占比(%)']}%），中位数 {r['中位数']}，最大 {r['最大值']}")
    print("\n  判断依据：中位数只有百分之几（正常的小数写法），")
    print("  但最大值几十 —— 典型的'把 7.8% 写成 7.8'。")
    print("  后果：均值、标准差被严重拉高，回归系数也会偏。")
    print("  处理建议：先跟数据商核对原始定义；若确认是百分数，")
    print("  只对 >1 的那部分除以 100（不要整列除，否则把对的也改错）。")
else:
    print("\n所有有界比率变量都在 1 以内，量纲正常。")

# 单独提示：这两列是"百分数口径"，属于正常但要注意尺度
print("\n【口径提示】以下变量整列用百分数记录（不是错误，但别和 0~1 的变量混着比）：")
for v in ["Indep", "Mshare"]:
    if v in df.columns:
        s = pd.to_numeric(df[v], errors="coerce").dropna()
        print(f"  · {v}（{cfg.cn(v)}）：中位数 {s.median():.2f}，"
              f"最大 {s.max():.2f} —— 1 个单位 = 1 个百分点")


# ============================================================
# 第 5 步：分年度的均值（看趋势）
# ============================================================
# 【在干嘛】把核心变量按年份求平均，看它们随时间怎么变。
# 【原理】这一步是给"平行趋势/时间趋势"做初步判断：
#        如果某个控制变量的均值逐年单调上升（比如 Size），
#        说明样本在扩张，回归里就必须控制年份固定效应，
#        否则时间趋势会被误当成你解释变量的效应。
print("\n" + "=" * 70)
print("第 5 步：核心变量分年度均值")
print("=" * 70)

core = ["Size", "Lev", "ROA", "Growth", "TobinQ", "Top1", "INST", "SOE"]
core = [v for v in core if v in df.columns]
year_mean = df.groupby("year")[core].mean().round(4).reset_index()
print(year_mean.to_string(index=False))


# ============================================================
# 第 6 步：导出结果
# ============================================================
# 【在干嘛】把这几张表写进一个 Excel 文件的不同工作表（sheet）。
# 【原理】ExcelWriter 相当于在内存里建一个工作簿，
#        to_excel(..., sheet_name=...) 每调一次就新建一个 sheet，
#        最后 with 语句块结束时自动保存。
#        好处：一个文件装下全部结果，不会满地都是 csv。
print("\n" + "=" * 70)
print("第 6 步：导出 Excel")
print("=" * 70)

xlsx_path = os.path.join(cfg.OUT_DIR, "02_描述统计.xlsx")

# 导出前把数值列统一保留 4 位小数，Excel 里看起来清爽（不影响任何计算）
desc_out = desc.copy()
num_cols = ["均值", "标准差", "最小值", "P25", "中位数", "P75", "最大值", "偏度", "峰度"]
desc_out[num_cols] = desc_out[num_cols].round(4)

with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
    desc_out.to_excel(writer, sheet_name="连续变量描述统计", index=False)
    cat_freq.to_excel(writer, sheet_name="分类变量频数", index=False)
    alert.to_excel(writer, sheet_name="数据质量警报", index=False)
    year_mean.to_excel(writer, sheet_name="分年度均值", index=False)

# 论文格式：只要 8 列，变量名换中文，方便直接复制进 Word
paper = desc[["变量名", "N", "均值", "标准差", "最小值", "P25", "中位数", "P75", "最大值"]].copy()
for c in paper.columns[1:]:
    paper[c] = paper[c].round(4)
paper_path = os.path.join(cfg.OUT_DIR, "02_描述统计_论文格式.csv")
paper.to_csv(paper_path, index=False, encoding="utf-8-sig")

print("  已保存：", xlsx_path)
print("  已保存：", paper_path)

print("\n【第 02 步完成】")
print("下一步：运行 03_相关性分析.py")
