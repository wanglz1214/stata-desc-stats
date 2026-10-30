# -*- coding: utf-8 -*-
"""
============================================================
01_读取与数据体检.py
============================================================
目的：把数据读进来，做一次"全面体检"，确认这份数据能不能用来做分析。

做实证研究，第一步永远是体检，而不是急着算均值。
体检要看四件事：
    ① 数据规模对不对（多少公司、多少年）
    ② 面板结构完不完美（公司-年度有没有重复、有没有缺年份）
    ③ 每个变量的缺失情况（缺失太多说明这个变量不可靠）
    ④ 有没有脏数据（异常值、类型错误、全是同一个值的废列）

输出文件（都在"输出结果"文件夹里）：
    01_变量清单.csv      —— 每个变量的类型、标签、缺失率
    01_缺失情况.csv      —— 缺失率排序
    01_年度分布.csv      —— 每年多少观测值、多少家公司
    01_重复检查.txt      —— 面板唯一性检查结果

运行方式：双击"运行全部.bat"，或者命令行 python 01_读取与数据体检.py
============================================================
"""

import os
import pandas as pd

import config as cfg


# ============================================================
# 第 1 步：读取数据
# ============================================================
# 【在干嘛】调用 config 里写好的读取函数，把 .dta 变成 pandas 表格。
# 【原理】.dta 是 Stata 的二进制文件；pyreadstat 把它解析成
#        DataFrame（行=观测，列=变量）。meta 里带中文标签。
print("=" * 70)
print("第 1 步：读取数据")
print("=" * 70)

df, meta = cfg.load_data()
cfg.ensure_out_dir()

# 变量标签 = 变量的中文说明。没写标签的变量返回 None
label_map = dict(zip(meta.column_names, meta.column_labels))


# ============================================================
# 第 2 步：看数据长什么样
# ============================================================
# 【在干嘛】打印行列数、前 5 行、后 5 行。
# 【原理】df.shape 返回 (行数, 列数)；
#        df.head() 看前几行是为了确认"列名对齐了没有、数值是不是乱码"，
#        这一步相当于打开 Excel 扫一眼，能发现 90% 的读取出错。
print("\n" + "=" * 70)
print("第 2 步：数据概览")
print("=" * 70)

print(f"数据规模：{df.shape[0]:,} 行 × {df.shape[1]} 列")
print("\n前 5 行（只看前 8 列）：")
print(df.iloc[:5, :8].to_string())

print("\n数据的时间跨度：", end="")
print(f"{int(df['year'].min())} — {int(df['year'].max())} 年"
      f"（共 {df['year'].nunique()} 个年度）")
print(f"公司数量  ：{df['stkcd'].nunique():,} 家（按 stkcd 证券代码去重）")


# ============================================================
# 第 3 步：面板结构检查（这一步最关键）
# ============================================================
# 【在干嘛】检查"同一个公司 + 同一年"是不是只出现一次。
# 【原理】实证论文用的基本都是"面板数据（panel data）"：
#        每个公司每年一条记录，"公司-年度"应该是唯一的。
#        如果出现重复，说明数据有合并错误，后面跑回归会翻车。
#        duplicated() 会标记出重复行；sum() 数出一共有多少条重复。
print("\n" + "=" * 70)
print("第 3 步：面板唯一性检查（公司-年度是否重复）")
print("=" * 70)

dup_mask = df.duplicated(subset=["stkcd", "year"], keep=False)
n_dup = int(dup_mask.sum())
print(f"重复的'公司-年度'记录数：{n_dup} 条")

# 检查年份是否连续：非平衡面板是正常的（公司会上市/退市），但要有记录
year_span = df.groupby("stkcd")["year"].agg(["min", "max", "count"])
year_span["应有年数"] = year_span["max"] - year_span["min"] + 1
year_span["缺少年数"] = year_span["应有年数"] - year_span["count"]
print(f"平均每家公司的观测年数：{year_span['count'].mean():.1f} 年")
print(f"最长观测跨度：{year_span['应有年数'].max()} 年"
      f"（说明面板不平衡是正常的：公司有上市早晚、有退市）")

# 每家公司至少要有 2 年才能做"公司固定效应"，检查一下
n_single = int((year_span["count"] == 1).sum())
print(f"只有 1 年观测的公司：{n_single} 家"
      f"（占比 {n_single / len(year_span) * 100:.1f}%）")


# ============================================================
# 第 4 步：变量清单（类型 + 标签 + 缺失率）
# ============================================================
# 【在干嘛】把每个变量的名字、类型、中文标签、缺失率、唯一值个数整理成一张表。
# 【原理】dtype 决定能做什么运算：
#        float64 = 连续数值，能做加减乘除；
#        object/str = 文本，只能做分类统计；
#        int64 = 整数（年份、代码）。
#        缺失率 = 空值数 / 总行数。经验规则：缺失超过 30% 的变量要慎重使用。
print("\n" + "=" * 70)
print("第 4 步：变量清单与缺失情况")
print("=" * 70)

info = pd.DataFrame({
    "变量名": df.columns,
    "中文标签": [label_map.get(c) for c in df.columns],
    "数据类型": [str(t) for t in df.dtypes],
    "非空值数": [int(df[c].notna().sum()) for c in df.columns],
    "缺失数": [int(df[c].isna().sum()) for c in df.columns],
    "缺失率(%)": [round(df[c].isna().mean() * 100, 2) for c in df.columns],
    "唯一值个数": [int(df[c].nunique(dropna=True)) for c in df.columns],
})
info["是否数值型"] = info["数据类型"].str.startswith(("float", "int"))

print(f"数值型变量 {int(info['是否数值型'].sum())} 个，"
      f"文本型变量 {int((~info['是否数值型']).sum())} 个")
print("\n缺失最严重的 10 个变量：")
print(info.nlargest(10, "缺失率(%)")[["变量名", "中文标签", "缺失率(%)"]]
      .to_string(index=False))


# ============================================================
# 第 5 步：找出"废列"（全样本取值都一样，没有信息量）
# ============================================================
# 【在干嘛】检查哪些变量的所有观测值完全相同。
# 【原理】如果一个变量在所有样本里都是 0（或都是同一个值），
#        它的方差为 0，无法解释任何差异，放进回归会被自动剔除。
#        这种列往往是"筛选样本时已经做过处理"的痕迹。
#        比如这份数据文件名写了"剔除 ST 或 PT"，那么"是否发生 ST"这一列
#        就应该是全 0 —— 这正是数据已经筛过的证据。
print("\n" + "=" * 70)
print("第 5 步：识别无信息量的废列")
print("=" * 70)

waste = []
for c in df.columns:
    if df[c].nunique(dropna=True) <= 1:
        vals = df[c].dropna().unique()
        waste.append((c, label_map.get(c), vals[:3] if len(vals) else "全是空值"))

if waste:
    for c, lab, v in waste:
        print(f"  · {c}（{lab}）：全部取值 = {v}")
    print("\n【解读】这些变量在样本里没有变化，回归时没有意义。")
    print("  其中'是否发生ST或ST或PT'全为 0，说明这份数据确实已经剔除了 ST/PT 样本，")
    print("  跟文件名描述一致，可以放心使用；但这一列本身在模型里就没用了。")
else:
    print("  没有发现取值恒定的列。")


# ============================================================
# 第 6 步：分组看样本分布（年度 / 行业 / 省份）
# ============================================================
# 【在干嘛】统计每年、每行业、每省各有多少观测值。
# 【原理】样本分布能暴露"结构性偏差"：
#        比如某一年观测突然暴增，可能是数据源换了；
#        某行业只有 3 家公司，做行业固定效应就会有问题。
print("\n" + "=" * 70)
print("第 6 步：样本分布")
print("=" * 70)

year_dist = (df.groupby("year")
               .agg(观测值数=("stkcd", "size"), 公司数=("stkcd", "nunique"))
               .reset_index())
print("年度分布（前 5 年 / 后 5 年）：")
print(pd.concat([year_dist.head(5), year_dist.tail(5)]).to_string(index=False))

ind_dist = (df.groupby("Industry").size()
              .sort_values(ascending=False).reset_index(name="观测值数"))
print(f"\n行业数：{len(ind_dist)} 个；观测最多的 5 个行业：")
print(ind_dist.head(5).to_string(index=False))

prov_dist = (df.groupby("省份").size()
               .sort_values(ascending=False).reset_index(name="观测值数"))
print(f"\n省份数：{len(prov_dist)} 个；观测最多的 5 个省份：")
print(prov_dist.head(5).to_string(index=False))


# ============================================================
# 第 7 步：保存体检结果
# ============================================================
# 【在干嘛】把上面几张表存成 CSV，方便用 Excel 打开检查。
# 【原理】to_csv 的 encoding="utf-8-sig" 很关键：
#        普通 utf-8 用 Excel 打开中文会乱码，加 sig 会写入 BOM 标记，
#        Excel 才能正确识别编码。
print("\n" + "=" * 70)
print("第 7 步：保存体检结果")
print("=" * 70)

f1 = os.path.join(cfg.OUT_DIR, "01_变量清单.csv")
f2 = os.path.join(cfg.OUT_DIR, "01_缺失情况.csv")
f3 = os.path.join(cfg.OUT_DIR, "01_年度分布.csv")
f4 = os.path.join(cfg.OUT_DIR, "01_重复检查.txt")

info.to_csv(f1, index=False, encoding="utf-8-sig")
info.sort_values("缺失率(%)", ascending=False).to_csv(f2, index=False, encoding="utf-8-sig")
year_dist.to_csv(f3, index=False, encoding="utf-8-sig")
ind_dist.to_csv(os.path.join(cfg.OUT_DIR, "01_行业分布.csv"), index=False, encoding="utf-8-sig")
prov_dist.to_csv(os.path.join(cfg.OUT_DIR, "01_省份分布.csv"), index=False, encoding="utf-8-sig")

with open(f4, "w", encoding="utf-8") as fh:
    fh.write("面板唯一性检查\n")
    fh.write(f"总观测值：{len(df)}\n")
    fh.write(f"公司数：{df['stkcd'].nunique()}\n")
    fh.write(f"重复的公司-年度记录：{n_dup}\n")
    fh.write(f"只有 1 年观测的公司：{n_single}\n")
    fh.write(f"年份范围：{int(df['year'].min())}-{int(df['year'].max())}\n")

for p in [f1, f2, f3, f4]:
    print("  已保存：", p)

print("\n【第 01 步完成】体检结论见控制台输出和 01_*.csv 文件。")
print("下一步：运行 02_描述统计.py")
