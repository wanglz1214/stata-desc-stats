# -*- coding: utf-8 -*-
"""
============================================================
04_可视化.py
============================================================
目的：把前面的数字画成图。数字看趋势，图看形状。

描述统计最容易漏掉的一件事：只看均值和标准差，看不出"分布长什么样"。
同样是均值 0.04、标准差 0.07，可能是漂亮的正态分布，
也可能是 90% 的公司挤在 0 附近、另外 10% 拖出一条长尾巴。
而"分布形状"直接决定了你要不要缩尾、要不要取对数。

输出 5 张图（都在"输出结果"文件夹）：
    04_图1_核心变量分布.png     —— 8 个核心变量的直方图
    04_图2_相关系数热力图.png   —— 变量相关性的可视化
    04_图3_样本年度分布.png     —— 每年多少观测值
    04_图4_虚拟变量构成.png     —— 0/1 变量的样本结构
    04_图5_核心变量年度趋势.png —— 关键变量的时间趋势

运行方式：python 04_可视化.py
============================================================
"""

import os
import numpy as np
import pandas as pd

import config as cfg

plt = cfg.setup_matplotlib()   # 设置中文字体，返回 pyplot 模块
print("=" * 70)
print("第 1 步：读取数据")
print("=" * 70)
df, meta = cfg.load_data()
cfg.ensure_out_dir()


# ============================================================
# 第 2 步：核心变量的分布图（直方图）
# ============================================================
# 【在干嘛】给 8 个核心变量各画一张直方图，拼成 2 行 4 列的大图。
# 【原理】直方图把取值范围切成若干"区间（bin）"，
#        数一数有多少观测落进每个区间，再用柱子的高度表示。
#        它告诉你三件事：中心在哪、散得多开、有没有长尾（偏态）。
#        【看图要点】
#          · 柱子大致对称像钟形 → 接近正态，可以直接用
#          · 右边拖出长长的尾巴   → 右偏，通常要取对数或缩尾
#          · 单独一根柱子特别高   → 大量观测堆在同一个值（比如 0）
#        我在每个子图上标了均值和标准差，方便跟描述统计表对照。
print("\n" + "=" * 70)
print("第 2 步：绘制核心变量分布直方图")
print("=" * 70)

plot_vars = [v for v in cfg.PLOT_VARS if v in df.columns]
n = len(plot_vars)
fig, axes = plt.subplots(2, 4, figsize=(16, 7.5))
axes = axes.ravel()

for ax, v in zip(axes, plot_vars):
    s = pd.to_numeric(df[v], errors="coerce").dropna()
    # 【重要技巧】有些变量（如 Mfee）有极少数特别大的值，
    # 如果按全部范围画，99% 的观测会被挤成一根柱子，形状完全看不出来。
    # 所以把横轴限制在分位数之间，牺牲 1%~5% 的极端点换取整体形状可见。
    # 自适应规则：如果 99% 分位还远大于 90% 分位（说明尾巴特别厚），
    # 就退到 95% 分位再截一次，否则用 1%~99%。
    lo = s.quantile(0.01)
    hi = s.quantile(0.99)
    upper_q = 99
    if s.quantile(0.90) > 0 and hi > 5 * s.quantile(0.90):
        hi = s.quantile(0.95)
        upper_q = 95
    s_plot = s[(s >= lo) & (s <= hi)] if hi > lo else s
    # bins=50：切成 50 个区间。区间太少看不出形状，太多会全是毛刺
    ax.hist(s_plot, bins=50, color="#4C78A8", edgecolor="white", linewidth=0.3, alpha=0.85)
    ax.axvline(s.mean(), color="#D62728", linestyle="--", linewidth=1.2, label="均值")
    ax.axvline(s.median(), color="#2CA02C", linestyle=":", linewidth=1.2, label="中位数")
    ax.set_title(f"{cfg.cn(v)}（{v}）\n均值{s.mean():.3f}  标准差{s.std():.3f}", fontsize=10)
    ax.set_ylabel("频数", fontsize=9)
    ax.set_xlabel(f"（横轴截到 1%~{upper_q}% 分位，极端值未显示）", fontsize=7, color="#777777")
    ax.tick_params(labelsize=8)
    ax.legend(fontsize=7, loc="upper right")

for ax in axes[n:]:      # 多出来的空子图隐藏掉
    ax.axis("off")

fig.suptitle("图1  核心变量分布（红色虚线=均值，绿色点线=中位数）", fontsize=13, y=1.02)
fig.tight_layout()
p1 = os.path.join(cfg.OUT_DIR, "04_图1_核心变量分布.png")
fig.savefig(p1)
plt.close(fig)
print("  已保存：", p1)


# ============================================================
# 第 3 步：相关系数热力图
# ============================================================
# 【在干嘛】把相关矩阵画成"颜色格子图"：红=正相关，蓝=负相关，颜色越深越强。
# 【原理】30 个变量的矩阵太大看不清，所以只挑 15 个有代表性的。
#        热力图的价值在于"一眼扫出成块的深色区域"——
#        如果几个变量之间颜色很深，说明它们在讲同一件事，
#        放进同一个回归会共线。
print("\n" + "=" * 70)
print("第 3 步：绘制相关系数热力图")
print("=" * 70)

heat_vars = ["Size", "Lev", "ROA", "Growth", "ATO", "Cashflow", "TobinQ",
             "Top1", "Balance1", "Indep", "Board", "Dual", "SOE",
             "ListAge", "INST", "Mfee"]
heat_vars = [v for v in heat_vars if v in df.columns]

sub = df[heat_vars].apply(pd.to_numeric, errors="coerce")
cmat = sub.corr()

fig, ax = plt.subplots(figsize=(11, 9))
# RdBu_r：负值蓝、正值红、中间白。vmin/vmax 对称设置，保证 0 对应白色
im = ax.imshow(cmat.values, cmap="RdBu_r", vmin=-1, vmax=1)

ax.set_xticks(range(len(heat_vars)))
ax.set_yticks(range(len(heat_vars)))
ax.set_xticklabels([cfg.cn(v) for v in heat_vars], rotation=45, ha="right", fontsize=9)
ax.set_yticklabels([cfg.cn(v) for v in heat_vars], fontsize=9)
ax.grid(False)   # 热力图不要网格线，否则看不清格子

# 在格子里写数值，方便精确读数
for i in range(len(heat_vars)):
    for j in range(len(heat_vars)):
        val = cmat.values[i, j]
        ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                fontsize=7.5, color="white" if abs(val) > 0.55 else "#333333")

fig.colorbar(im, ax=ax, shrink=0.75, label="Pearson 相关系数")
ax.set_title("图2  主要变量相关系数热力图", fontsize=13, pad=14)
fig.tight_layout()
p2 = os.path.join(cfg.OUT_DIR, "04_图2_相关系数热力图.png")
fig.savefig(p2)
plt.close(fig)
print("  已保存：", p2)


# ============================================================
# 第 4 步：样本的年度分布
# ============================================================
# 【在干嘛】柱状图看每年观测数，折线看累计公司数（双轴）。
# 【原理】双 y 轴（twinx）用于两个量纲不同的序列画在同一张图上：
#        左轴放"当年的观测数"，右轴放"当年有多少家公司"。
#        这类图用来判断样本是不是"随时间扩张"——
#        A 股上市公司数量逐年增加，所以柱状图应该是单调上升的。
#        如果不上升反而某年骤降，那就要查数据是不是缺了一年。
print("\n" + "=" * 70)
print("第 4 步：绘制样本年度分布")
print("=" * 70)

yd = df.groupby("year").agg(obs=("stkcd", "size"), firms=("stkcd", "nunique"))

fig, ax1 = plt.subplots(figsize=(12, 5.5))
ax1.bar(yd.index, yd["obs"], color="#8FB8DE", edgecolor="#4C78A8", label="观测值数（左轴）")
ax1.set_xlabel("年份")
ax1.set_ylabel("观测值数", color="#4C78A8")
ax1.tick_params(axis="y", labelcolor="#4C78A8")

ax2 = ax1.twinx()
ax2.plot(yd.index, yd["firms"], color="#D62728", marker="o", markersize=4,
         linewidth=1.6, label="公司数（右轴）")
ax2.set_ylabel("公司数", color="#D62728")
ax2.tick_params(axis="y", labelcolor="#D62728")
ax2.grid(False)

ax1.set_xticks(list(yd.index))
ax1.set_xticklabels([str(int(y)) for y in yd.index], rotation=45, fontsize=8)
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=9)
ax1.set_title("图3  样本年度分布：观测值数（柱）与公司数（线）", fontsize=13)
fig.tight_layout()
p3 = os.path.join(cfg.OUT_DIR, "04_图3_样本年度分布.png")
fig.savefig(p3)
plt.close(fig)
print("  已保存：", p3)


# ============================================================
# 第 5 步：虚拟变量的构成
# ============================================================
# 【在干嘛】把 0/1 变量画成条形图，直观看"两类各占多少"。
# 【原理】虚拟变量的"均值"就等于"取 1 的比例"，
#        所以画占比图比画直方图有意义得多。
#        一眼能看出样本里国企占多少、四大审计占多少、
#        以及最要紧的——有没有某一类少到几乎没有（那样就没法做对比）。
print("\n" + "=" * 70)
print("第 5 步：绘制虚拟变量构成")
print("=" * 70)

dummy_vars = ["SOE", "Big4", "Dual", "Loss", "管制行业"]
dummy_vars = [v for v in dummy_vars if v in df.columns]

rates = {cfg.cn(v): df[v].dropna().mean() for v in dummy_vars}

fig, axes = plt.subplots(1, len(rates), figsize=(14, 4))
if len(rates) == 1:
    axes = [axes]
for ax, (name, rate) in zip(axes, rates.items()):
    ax.bar(["=0", "=1"], [1 - rate, rate], color=["#B0C4DE", "#E45756"],
           edgecolor="#333333", linewidth=0.5)
    ax.set_ylim(0, 1)
    ax.set_title(name, fontsize=11)
    for i, val in enumerate([1 - rate, rate]):
        ax.text(i, val + 0.02, f"{val*100:.1f}%", ha="center", fontsize=10)
    ax.tick_params(labelsize=9)

fig.suptitle("图4  虚拟变量构成（占比）", fontsize=13, y=1.03)
fig.tight_layout()
p4 = os.path.join(cfg.OUT_DIR, "04_图4_虚拟变量构成.png")
fig.savefig(p4)
plt.close(fig)
print("  已保存：", p4)


# ============================================================
# 第 6 步：核心变量的时间趋势
# ============================================================
# 【在干嘛】把核心变量按年均值画成折线，一张图 4 个变量。
# 【原理】这一步为"要不要控制年份固定效应"提供直观依据。
#        如果某个变量的均值随年份系统性地漂移（比如 SOE 一路下降、
#        Size 一路上升），说明"年份"本身就是重要的解释因素。
#        回归里如果不放年份固定效应，这个趋势就会被错误地归因到
#        你真正的解释变量上（遗漏变量偏误）。
print("\n" + "=" * 70)
print("第 6 步：绘制核心变量年度趋势")
print("=" * 70)

trend_vars = ["Lev", "ROA", "TobinQ", "SOE"]
trend_vars = [v for v in trend_vars if v in df.columns]
ym = df.groupby("year")[trend_vars].mean()

fig, axes = plt.subplots(2, 2, figsize=(13, 7))
axes = axes.ravel()
for ax, v in zip(axes, trend_vars):
    ax.plot(ym.index, ym[v], color="#4C78A8", marker="o", markersize=3.5, linewidth=1.6)
    ax.set_title(f"{cfg.cn(v)}（{v}）年度均值", fontsize=11)
    ax.set_xlabel("年份")
    ax.tick_params(labelsize=8)
    ax.set_xticks(list(ym.index)[::2])   # 每两年标一个刻度，避免挤在一起
    ax.grid(True, alpha=0.3)

fig.suptitle("图5  核心变量年度均值趋势（判断是否需要控制年份固定效应）", fontsize=13, y=1.01)
fig.tight_layout()
p5 = os.path.join(cfg.OUT_DIR, "04_图5_核心变量年度趋势.png")
fig.savefig(p5)
plt.close(fig)
print("  已保存：", p5)

print("\n【第 04 步完成】共输出 5 张图。")
print("全部脚本运行完毕，结果都在：", cfg.OUT_DIR)
