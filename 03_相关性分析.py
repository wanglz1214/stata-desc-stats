# -*- coding: utf-8 -*-
"""
============================================================
03_相关性分析.py
============================================================
目的：算变量之间的相关系数矩阵，并做多重共线性初检。

为什么描述统计之后要做这一步？
    ① 看"解释变量和被解释变量"的关系方向和强弱——这是回归结果的前奏。
    ② 看"控制变量之间"是否高度相关。两个控制变量相关系数 0.9，
       说明它们在讲同一件事，同时放进回归会打架（多重共线性），
       导致系数估计不稳定、标准误膨胀。
    ③ 论文里几乎都要放一张 correlation matrix（相关性分析表）。

输出文件（在"输出结果"文件夹）：
    03_相关系数矩阵.xlsx  —— 三个工作表：Pearson、Spearman、VIF
    03_相关系数_带星号.csv —— 论文格式（* p<0.1, ** p<0.05, *** p<0.01）

运行方式：python 03_相关性分析.py
============================================================
"""

import os
import numpy as np
import pandas as pd
from scipy import stats

import config as cfg

print("=" * 70)
print("第 1 步：读取数据并挑出要做相关分析的变量")
print("=" * 70)
df, meta = cfg.load_data()
cfg.ensure_out_dir()

vars_use = [v for v in cfg.CONT_VARS if v in df.columns]
# 去掉完全重复的变量（Mfee 与 AgC1_1 数值完全相同、Occupy 与 AgC2 相同）
# 【原理】完全共线的两个变量相关系数 = 1，会让相关矩阵奇异、VIF 变成无穷大
DROP_DUP = ["AgC1_1", "AgC2"]
vars_use = [v for v in vars_use if v not in DROP_DUP]

# 只保留数值列，并转成纯数值矩阵
mat = df[vars_use].apply(pd.to_numeric, errors="coerce")
print(f"参与分析的变量数：{len(vars_use)}")
print(f"已剔除重复变量：{DROP_DUP}（与 Mfee / Occupy 数值完全一致）")


# ============================================================
# 第 2 步：Pearson 相关系数
# ============================================================
# 【在干嘛】两两计算线性相关系数。
# 【原理】Pearson r 衡量"两个变量是否沿一条直线同向/反向变动"：
#        r 的取值永远在 [-1, 1]：
#           r > 0  正相关（一个涨另一个也涨）
#           r < 0  负相关
#           |r| 越接近 1，线性关系越强；接近 0 说明没有线性关系
#        【注意】r 只捕捉"线性"关系。r≈0 不代表没关系，
#        可能是有 U 型关系。所以相关分析只是初步的，不能代替回归。
#
#        【重要】算相关之前，每一对变量只在"两者都不缺失"的样本上计算
#        （pandas 默认 pairwise 删除），所以不同格的样本量可能略有差别。
print("\n" + "=" * 70)
print("第 2 步：计算 Pearson 相关系数")
print("=" * 70)

corr = mat.corr(method="pearson")

# 打印一小块看看（前 8 个变量）——全表 30 个变量在屏幕上没法看
print("相关系数矩阵（前 8 个变量的局部）：")
print(corr.iloc[:8, :8].round(3).to_string())


# ============================================================
# 第 3 步：显著性检验 + 打星号
# ============================================================
# 【在干嘛】给每个相关系数算一个 p 值，显著的标上 *。
# 【原理】r 是从样本算出来的，样本有随机性，r 不等于 0 可能只是巧合。
#        检验的原假设是"H0：总体相关系数 = 0"（也就是真的没关系）。
#        p 值 = "如果真没关系，出现这么强的相关（或更强）的概率"。
#        p < 0.05  → 我们拒绝原假设，认为关系是真实存在的（** ）
#        p < 0.01  → 更强的证据（***）
#        统计量 t = r * sqrt(n-2) / sqrt(1-r²)，服从自由度 n-2 的 t 分布。
#        （n 是这一对变量的有效样本量，所以每格的 n 是单独算的）
print("\n" + "=" * 70)
print("第 3 步：显著性检验（t 检验）与星号标记")
print("=" * 70)

cols = vars_use
n_var = len(cols)
r_mat = np.full((n_var, n_var), np.nan)   # 存 r
p_mat = np.full((n_var, n_var), np.nan)   # 存 p
n_mat = np.full((n_var, n_var), np.nan)   # 存每对的有效样本量

for i in range(n_var):
    for j in range(i, n_var):
        a, b = mat[cols[i]], mat[cols[j]]
        ok = a.notna() & b.notna()          # 两个都不缺的样本
        n = int(ok.sum())
        n_mat[i, j] = n_mat[j, i] = n
        if n > 3:
            r, p = stats.pearsonr(a[ok], b[ok])
        else:
            r, p = np.nan, np.nan
        r_mat[i, j] = r_mat[j, i] = r
        p_mat[i, j] = p_mat[j, i] = p

def star(p):
    """把 p 值转成星号：*** p<0.01, ** p<0.05, * p<0.1"""
    if pd.isna(p):
        return ""
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "**"
    if p < 0.1:
        return "*"
    return ""

# 论文格式：数值 + 星号，例如 0.253***
star_mat = pd.DataFrame(index=cols, columns=cols, dtype=object)
for i in range(n_var):
    for j in range(n_var):
        if i == j:
            star_mat.iloc[i, j] = "1"
        else:
            r, p = r_mat[i, j], p_mat[i, j]
            star_mat.iloc[i, j] = "" if pd.isna(r) else f"{r:.3f}{star(p)}"

print("带星号矩阵（前 8 个变量的局部）：")
print(star_mat.iloc[:8, :8].to_string())

# 【在干嘛】找出相关系数绝对值最大的几对——这是最需要警惕的共线性嫌疑
print("\n相关性最强的 10 对变量（|r| 从大到小）：")
pairs = []
for i in range(n_var):
    for j in range(i + 1, n_var):
        pairs.append((cols[i], cols[j], r_mat[i, j]))
pair_df = pd.DataFrame(pairs, columns=["变量1", "变量2", "相关系数"])
print(pair_df.reindex(pair_df["相关系数"].abs().sort_values(ascending=False).index)
      .head(10).round(3).to_string(index=False))


# ============================================================
# 第 4 步：Spearman 秩相关（稳健性对照）
# ============================================================
# 【在干嘛】再算一套"秩相关"，跟 Pearson 对照着看。
# 【原理】Spearman 不看具体数值，只看"排序"：
#        先把每个变量换成名次，再算名次的 Pearson 相关。
#        好处是对极端值不敏感，也能捕捉"单调但非线性"的关系。
#        如果 Pearson 显著但 Spearman 不显著，说明关系可能被少数极端值撑起来的。
print("\n" + "=" * 70)
print("第 4 步：Spearman 秩相关")
print("=" * 70)
corr_s = mat.corr(method="spearman")
print("Spearman 矩阵（前 5 个变量）：")
print(corr_s.iloc[:5, :5].round(3).to_string())


# ============================================================
# 第 5 步：VIF 多重共线性检验（进阶，但很有用）
# ============================================================
# 【在干嘛】算每个变量的方差膨胀因子（VIF）。
# 【原理】VIF 衡量"这个变量能被其他所有变量解释多少"。
#        数学上：VIF_j = 1 / (1 - R²_j)，R²_j 是用其他变量回归该变量得到的拟合优度。
#        所以：R²=0 → VIF=1（完全独立）；R²=0.9 → VIF=10（危险）。
#        经验标准：VIF > 10 → 严重共线性，该变量要考虑剔除或换指标；
#                  5~10   → 需要留意；
#                  <5     → 基本没问题。
#        这里用相关矩阵的逆矩阵对角元来快速算（相关系数的 VIF 等价形式），
#        不用跑一个个回归，速度快很多。
print("\n" + "=" * 70)
print("第 5 步：VIF 多重共线性检验")
print("=" * 70)

# 用"完整样本"（所有变量都不缺的行）算，否则相关矩阵不完整无法求逆
complete = mat.dropna()
print(f"完整样本量：{len(complete):,} 行（{len(complete)/len(mat)*100:.1f}% 的观测）")

R = complete.corr().values
try:
    inv_R = np.linalg.inv(R)
    vif_vals = np.diag(inv_R)
    vif = pd.DataFrame({"变量": cols, "VIF": np.round(vif_vals, 2)})
    vif = vif.sort_values("VIF", ascending=False).reset_index(drop=True)

    def vif_flag(x):
        if x > 10:
            return "严重共线性"
        if x > 5:
            return "需要留意"
        return "可接受"

    vif["判断"] = vif["VIF"].apply(vif_flag)
    print(vif.head(12).to_string(index=False))
    print("\n【解读】VIF>10 的变量之间高度冗余，同时放进回归会让系数不稳定。")
except np.linalg.LinAlgError:
    vif = pd.DataFrame({"变量": cols, "VIF": np.nan, "判断": "矩阵奇异，无法计算"})
    print("相关矩阵不可逆（存在完全共线的变量），请先删除重复变量。")


# ============================================================
# 第 6 步：导出
# ============================================================
print("\n" + "=" * 70)
print("第 6 步：导出结果")
print("=" * 70)

xlsx_path = os.path.join(cfg.OUT_DIR, "03_相关系数矩阵.xlsx")
with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
    corr.round(4).to_excel(writer, sheet_name="Pearson系数")
    pd.DataFrame(p_mat, index=cols, columns=cols).round(4).to_excel(writer, sheet_name="p值")
    star_mat.to_excel(writer, sheet_name="带星号矩阵")
    corr_s.round(4).to_excel(writer, sheet_name="Spearman系数")
    vif.to_excel(writer, sheet_name="VIF", index=False)

# 论文格式 csv：行列都用中文变量名，方便直接复制进 Word 表格
star_paper = star_mat.copy()
star_paper.index = [cfg.cn(c) for c in star_paper.index]
star_paper.columns = [cfg.cn(c) for c in star_paper.columns]
csv_path = os.path.join(cfg.OUT_DIR, "03_相关系数_带星号.csv")
star_paper.to_csv(csv_path, encoding="utf-8-sig")

print("  已保存：", xlsx_path)
print("  已保存：", csv_path)
print("\n【第 03 步完成】")
print("下一步：运行 04_可视化.py")
