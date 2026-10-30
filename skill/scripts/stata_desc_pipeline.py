# -*- coding: utf-8 -*-
"""
上市公司面板数据（.dta）描述性统计一键流水线
================================================
一条命令，从 Stata 数据文件得到论文用的全套描述统计结果：
    变量清单 / 缺失情况 / 面板重复检查 / 描述统计表 / 虚拟变量频数 /
    分年度均值 / 量纲警报 / 相关系数矩阵 / VIF 共线性 / 5 张图

用法：
    python stata_desc_pipeline.py 你的数据.dta
    python stata_desc_pipeline.py 你的数据.dta --out 输出结果 --id stkcd --year year
    python stata_desc_pipeline.py 你的数据.dta --core Size Lev ROA     # 只画指定变量的图

依赖：pip install pandas numpy pyreadstat matplotlib openpyxl scipy

每一步都做了什么、为什么这么做，看下面各函数的 docstring 和 print 输出。
"""
import sys, os, argparse

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import pandas as pd
import numpy as np

# ---- 中文字体（matplotlib）----
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "KaiTi"]
plt.rcParams["axes.unicode_minus"] = False

ID_CANDIDATES = ["stkcd", "Stkcd", "StkCd", "code", "Code", "证券代码", "股票代码", "证券代码 ", "id", "ID", "firm", "Firm"]
YEAR_CANDIDATES = ["year", "Year", "年份", "年度", "会计年度", "date", "Date"]


def guess_col(df, candidates, kw=None):
    """在列名里猜 id / year 列。猜不到就返回 None，不硬报错。"""
    for c in candidates:
        if c in df.columns:
            return c
    if kw:
        for c in df.columns:
            if kw in str(c):
                return c
    return None


# ============================================================
# 第 1 步：读数据
# ============================================================
def load_dta(path):
    """用 pyreadstat 读 .dta。
    为什么不用 pandas.read_stata：pyreadstat 能带出 Stata 里的中文变量标签
    （meta.column_labels），后面做中文表格全靠它。"""
    import pyreadstat
    df, meta = pyreadstat.read_dta(path)
    labels = {}
    if meta is not None and meta.column_names and meta.column_labels:
        labels = dict(zip(meta.column_names, meta.column_labels))
    # 标签为空时退回变量名
    labels = {c: (labels.get(c) or c) for c in df.columns}
    return df, labels


# ============================================================
# 第 2 步：数据体检
# ============================================================
def step_check(df, labels, id_col, year_col, out_dir):
    print("\n" + "=" * 70)
    print("第 1 步：数据体检")
    print("=" * 70)
    print("样本量：%s 行 × %s 列" % (f"{len(df):,}", df.shape[1]))

    # --- 变量清单 ---
    varlist = pd.DataFrame({
        "变量名": list(df.columns),
        "中文标签": [labels.get(c, c) for c in df.columns],
        "类型": [str(df[c].dtype) for c in df.columns],
        "非缺失数": [int(df[c].notna().sum()) for c in df.columns],
        "缺失率(%)": [round(df[c].isna().mean() * 100, 2) for c in df.columns],
        "唯一值数": [int(df[c].nunique(dropna=True)) for c in df.columns],
    })
    varlist.to_csv(os.path.join(out_dir, "01_变量清单.csv"),
                   index=False, encoding="utf-8-sig")
    print("\n缺失最严重的 8 个变量：")
    print(varlist.sort_values("缺失率(%)", ascending=False)
          .head(8).to_string(index=False))

    # --- 面板重复检查 ---
    msg = ""
    if id_col and year_col:
        dup = df.duplicated(subset=[id_col, year_col]).sum()
        msg = "公司-年度 重复行：%s 条（应为 0）\n公司数：%s，年份：%s—%s（%s 年）" % (
            f"{dup:,}", f"{df[id_col].nunique():,}",
            int(df[year_col].min()), int(df[year_col].max()), df[year_col].nunique())
    elif id_col:
        msg = "公司数：%s" % f"{df[id_col].nunique():,}"
    print("\n" + msg)
    with open(os.path.join(out_dir, "01_重复检查.txt"), "w", encoding="utf-8") as f:
        f.write(msg)

    # --- 常数列（唯一值 <=1，进回归没有信息量）---
    const = [c for c in df.columns if df[c].nunique(dropna=True) <= 1]
    if const:
        print("\n【注意】以下变量只有 1 个取值（常数列），不能进回归：%s" % ", ".join(const[:12]))

    # --- 重复列（两列逐行完全相同，同时进回归会导致矩阵奇异）---
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    dup_pairs = []
    cols = [c for c in num_cols if df[c].notna().sum() > 0]
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            a, b = cols[i], cols[j]
            if df[[a, b]].dropna().shape[0] < 10:
                continue
            if df[a].equals(df[b]):
                dup_pairs.append((a, b))
    if dup_pairs:
        print("\n【注意】以下变量数值完全相同，不能同时进回归：")
        for a, b in dup_pairs:
            print("  %s ≡ %s（%s / %s）" % (a, b, labels.get(a), labels.get(b)))
    else:
        print("\n未发现完全重复的变量对。")
    return varlist, const, dup_pairs


def split_vars(df, labels, id_col, year_col):
    """自动分组：连续变量 / 虚拟变量 / 分类变量。
    规则：数值型且唯一值 >10 → 连续；数值型且唯一值 ≤10 → 虚拟或分类；其余 → 分类。"""
    skip = {id_col, year_col}
    cont, dummy, cat = [], [], []
    for c in df.columns:
        if c in skip:
            continue
        s = pd.to_numeric(df[c], errors="coerce")
        nonnull = s.notna().sum()
        if nonnull == 0:
            continue
        if pd.api.types.is_numeric_dtype(df[c]):
            if df[c].nunique(dropna=True) > 10:
                cont.append(c)
            else:
                dummy.append(c)
        else:
            cat.append(c)
    return cont, dummy, cat


# ============================================================
# 第 3 步：描述统计
# ============================================================
def step_describe(df, labels, cont, dummy, year_col, out_dir):
    print("\n" + "=" * 70)
    print("第 2 步：描述统计")
    print("=" * 70)

    rows = []
    for v in cont:
        s = pd.to_numeric(df[v], errors="coerce").dropna()
        rows.append({
            "变量名称": labels.get(v, v), "变量名": v,
            "样本量": len(s), "均值": s.mean(), "标准差": s.std(),
            "最小值": s.min(), "中位数": s.median(), "最大值": s.max(),
            "偏度": s.skew(), "峰度": s.kurtosis(),
            "p25": s.quantile(.25), "p75": s.quantile(.75),
        })
    for v in dummy:
        s = pd.to_numeric(df[v], errors="coerce").dropna()
        rows.append({
            "变量名称": labels.get(v, v), "变量名": v,
            "样本量": len(s), "均值": s.mean(), "标准差": s.std(),
            "最小值": s.min(), "中位数": s.median(), "最大值": s.max(),
            "偏度": np.nan, "峰度": np.nan, "p25": np.nan, "p75": np.nan,
        })
    desc = pd.DataFrame(rows)

    show = desc[["变量名称", "样本量", "均值", "标准差", "最小值", "中位数", "最大值"]].copy()
    print(show.round(4).to_string(index=False))

    # 论文格式（只要 7 列，4 位小数）
    paper = show.copy()
    for c in ["均值", "标准差", "最小值", "中位数", "最大值"]:
        paper[c] = paper[c].astype(float).round(4).map(lambda x: "%.4f" % x)
    paper["样本量"] = paper["样本量"].astype(int).map(lambda x: f"{x:,}")
    paper.to_csv(os.path.join(out_dir, "02_描述统计_论文格式.csv"),
                 index=False, encoding="utf-8-sig")

    # --- 虚拟变量频数 ---
    freq_rows = []
    for v in dummy:
        s = pd.to_numeric(df[v], errors="coerce").dropna()
        for val, n in s.value_counts().sort_index().items():
            freq_rows.append({"变量名称": labels.get(v, v), "变量名": v,
                              "取值": val, "频数": int(n),
                              "占比(%)": round(n / len(s) * 100, 2)})
    cat_freq = pd.DataFrame(freq_rows)

    # --- 分年度均值 ---
    year_mean = pd.DataFrame()
    if year_col:
        year_mean = df.groupby(year_col)[cont].mean().round(4)
        year_mean.insert(0, "样本量", df.groupby(year_col).size())
        print("\n核心变量分年度均值（看时间趋势）：")
        print(year_mean.iloc[:, :7].to_string())

    # --- 量纲警报：比率变量不该超过 1 ---
    print("\n量纲检查（比率变量中 >1 的观测）：")
    alert_rows = []
    for v in cont:
        s = pd.to_numeric(df[v], errors="coerce").dropna()
        if s.median() <= 0 or s.max() <= 1:
            continue
        n_big = int((s > 1).sum())
        if n_big == 0:
            continue
        alert_rows.append({"变量名称": labels.get(v, v), "变量名": v,
                           "超过1的观测数": n_big,
                           "占比(%)": round(n_big / len(s) * 100, 2),
                           "最大值": round(s.max(), 3),
                           "中位数": round(s.median(), 4)})
    alert = pd.DataFrame(alert_rows)
    if len(alert):
        print(alert.to_string(index=False))
        whole = alert[alert["占比(%)"] > 90]
        mixed = alert[alert["占比(%)"] <= 90]
        if len(whole):
            print("\n  (1) 整列按百分数记录（单位统一，只是尺度不同于 0~1 比率）：")
            for _, r in whole.iterrows():
                print("      %s（%s）：%.0f%% 的观测 >1，最大 %.2f"
                      % (r["变量名称"], r["变量名"], r["占比(%)"], r["最大值"]))
            print("      含义：33.33 表示 33.33%，不是 0.3333。回归系数按「1 个百分点」解释。")
        if len(mixed):
            print("\n  (2) 需要人工判断（部分观测 >1）：")
            for _, r in mixed.iterrows():
                print("      %s（%s）：%s 条（%.1f%%），中位 %.4f 但最大 %.2f"
                      % (r["变量名称"], r["变量名"], f"{int(r['超过1的观测数']):,}",
                         r["占比(%)"], r["中位数"], r["最大值"]))
            print("      两种可能，别急着改数据：")
            print("      a) 量纲混杂：中位数在 0~0.3 但最大值几十——典型的「7.8% 写成 7.8」；")
            print("         只对 >1 的那部分除以 100，不要整列除（会把本来对的改错）。")
            print("      b) 本来就可以 >1 的比值：如「资产总计/营业收入」这类分子分母不是")
            print("         包含关系的比值，>1 完全正常，不用处理。")
            print("      判断方法：看该变量的定义。拿不准就按年份分组看，")
            print("      若某几年突然全部 >1、其他年份全没有，基本是口径变了。")
    else:
        print("  未发现异常。")

    xlsx = os.path.join(out_dir, "02_描述统计.xlsx")
    with pd.ExcelWriter(xlsx, engine="openpyxl") as w:
        desc.round(4).to_excel(w, sheet_name="描述统计", index=False)
        paper.to_excel(w, sheet_name="论文格式", index=False)
        if len(cat_freq):
            cat_freq.to_excel(w, sheet_name="虚拟变量频数", index=False)
        if len(year_mean):
            year_mean.to_excel(w, sheet_name="分年度均值")
        if len(alert):
            alert.to_excel(w, sheet_name="量纲警报", index=False)
    print("\n已导出：%s" % xlsx)
    return desc, paper, cat_freq, year_mean, alert


# ============================================================
# 第 4 步：相关性与共线性
# ============================================================
def star(p):
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return ""
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "**"
    if p < 0.1:
        return "*"
    return ""


def step_corr(df, labels, cont, out_dir):
    print("\n" + "=" * 70)
    print("第 3 步：相关性与共线性")
    print("=" * 70)
    use = [v for v in cont if pd.to_numeric(df[v], errors="coerce").notna().sum() > 100]
    sub = df[use].apply(pd.to_numeric, errors="coerce")

    pear = sub.corr(method="pearson")
    spear = sub.corr(method="spearman")
    print("Pearson 相关系数矩阵（%d×%d）已计算。" % (len(use), len(use)))

    # 带显著性星号的长表
    try:
        from scipy import stats
        ok = True
    except ImportError:
        ok = False
    rows = []
    for i, a in enumerate(use):
        for b in use[i + 1:]:
            pair = sub[[a, b]].dropna()
            r = pear.loc[a, b]
            p = np.nan
            if ok and len(pair) > 3:
                p = stats.pearsonr(pair[a], pair[b])[1]
            # 标签可能重名（如两个"股权制衡度"），所以把变量名一并显示，方便区分
            rows.append({"变量1": "%s（%s）" % (labels.get(a, a), a),
                         "变量2": "%s（%s）" % (labels.get(b, b), b),
                         "Pearson": r, "Spearman": spear.loc[a, b],
                         "p值": p, "显著性": star(p)})
    long = pd.DataFrame(rows).sort_values("Pearson", key=lambda s: s.abs(), ascending=False)
    print("\n相关性最强的 10 对：")
    print(long.head(10).round(4).to_string(index=False))

    # VIF：方差膨胀因子，>10 说明严重共线
    vif_rows = []
    X = sub.dropna()
    if len(X) > 100 and len(use) > 1:
        for v in use:
            y = X[v].astype(float)
            others = X.drop(columns=[v]).astype(float)
            try:
                from numpy.linalg import lstsq
                A = np.column_stack([np.ones(len(others)), others.values])
                beta, *_ = lstsq(A, y.values, rcond=None)
                pred = A @ beta
                ss_res = ((y.values - pred) ** 2).sum()
                ss_tot = ((y.values - y.mean()) ** 2).sum()
                r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
                vif_rows.append({"变量名称": labels.get(v, v), "变量名": v,
                                 "VIF": np.inf if r2 >= 1 else 1 / (1 - r2)})
            except Exception:
                pass
    vif = pd.DataFrame(vif_rows).sort_values("VIF", ascending=False)
    if len(vif):
        print("\nVIF 共线性诊断（>10 为严重共线）：")
        print(vif.head(10).round(2).to_string(index=False))
        bad = vif[vif["VIF"] > 10]
        if len(bad):
            print("\n【注意】以下变量 VIF>10，不要同时放进同一个回归：")
            for _, r in bad.iterrows():
                print("  %s（%s）：VIF=%.1f" % (r["变量名称"], r["变量名"], r["VIF"]))

    xlsx = os.path.join(out_dir, "03_相关系数矩阵.xlsx")
    with pd.ExcelWriter(xlsx, engine="openpyxl") as w:
        pear.round(4).to_excel(w, sheet_name="Pearson")
        spear.round(4).to_excel(w, sheet_name="Spearman")
        long.round(4).to_excel(w, sheet_name="相关性长表带星号", index=False)
        if len(vif):
            vif.round(4).to_excel(w, sheet_name="VIF", index=False)
    long.round(4).to_csv(os.path.join(out_dir, "03_相关系数_带星号.csv"),
                         index=False, encoding="utf-8-sig")
    print("\n已导出：%s" % xlsx)
    return pear, long, vif


# ============================================================
# 第 5 步：画图
# ============================================================
def step_plot(df, labels, cont, year_col, out_dir, core=None):
    print("\n" + "=" * 70)
    print("第 4 步：画图")
    print("=" * 70)
    if core:
        plot_vars = [v for v in core if v in cont]
    else:
        # 默认：缺失最少的前 9 个连续变量
        miss = {v: df[v].isna().mean() for v in cont}
        plot_vars = sorted(cont, key=lambda v: miss[v])[:9]
    if not plot_vars:
        print("没有可画的连续变量，跳过。")
        return []

    n = len(plot_vars)
    ncols = 3
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.2 * ncols, 3.1 * nrows))
    axes = np.atleast_1d(axes).ravel()
    for ax, v in zip(axes, plot_vars):
        s = pd.to_numeric(df[v], errors="coerce").dropna()
        lo, hi = s.quantile(0.01), s.quantile(0.99)
        s_plot = s[(s >= lo) & (s <= hi)] if hi > lo else s
        ax.hist(s_plot, bins=50, color="#4C78A8", edgecolor="white", linewidth=.3, alpha=.85)
        ax.axvline(s.mean(), color="#D62728", ls="--", lw=1.2, label="均值")
        ax.axvline(s.median(), color="#2CA02C", ls=":", lw=1.2, label="中位数")
        ax.set_title("%s（%s）\n均值%.3f  标准差%.3f" % (labels.get(v, v), v, s.mean(), s.std()),
                     fontsize=10)
        ax.set_ylabel("频数", fontsize=9)
        ax.set_xlabel("横轴截到 1%—99% 分位", fontsize=7, color="#777777")
        ax.tick_params(labelsize=8)
        ax.legend(fontsize=7)
    for ax in axes[n:]:
        ax.axis("off")
    fig.suptitle("核心变量分布", fontsize=13)
    fig.tight_layout()
    p1 = os.path.join(out_dir, "04_图1_核心变量分布.png")
    fig.savefig(p1, dpi=130)
    plt.close(fig)
    print("  %s" % p1)

    # 热力图
    sub = df[plot_vars].apply(pd.to_numeric, errors="coerce")
    cm = sub.corr()
    fig, ax = plt.subplots(figsize=(1.0 * len(plot_vars) + 3, 0.85 * len(plot_vars) + 2.5))
    im = ax.imshow(cm.values, cmap="RdBu_r", vmin=-1, vmax=1)
    short = [labels.get(v, v)[:8] for v in plot_vars]
    ax.set_xticks(range(len(plot_vars)))
    ax.set_xticklabels(short, rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(len(plot_vars)))
    ax.set_yticklabels(short, fontsize=9)
    for i in range(len(plot_vars)):
        for j in range(len(plot_vars)):
            ax.text(j, i, "%.2f" % cm.values[i, j], ha="center", va="center", fontsize=8)
    ax.set_title("相关系数热力图", fontsize=12)
    fig.colorbar(im, ax=ax, shrink=.8)
    fig.tight_layout()
    p2 = os.path.join(out_dir, "04_图2_相关系数热力图.png")
    fig.savefig(p2, dpi=130)
    plt.close(fig)
    print("  %s" % p2)

    # 年度趋势
    outs = [p1, p2]
    if year_col:
        ym = df.groupby(year_col)[plot_vars].mean()
        fig, axes = plt.subplots(nrows, ncols, figsize=(4.2 * ncols, 3.1 * nrows))
        axes = np.atleast_1d(axes).ravel()
        for ax, v in zip(axes, plot_vars):
            ax.plot(ym.index, ym[v], marker="o", ms=3, lw=1.5, color="#4C78A8")
            ax.set_title("%s（%s）" % (labels.get(v, v), v), fontsize=10)
            ax.tick_params(labelsize=8)
            ax.grid(alpha=.3)
        for ax in axes[n:]:
            ax.axis("off")
        fig.suptitle("核心变量年度趋势", fontsize=13)
        fig.tight_layout()
        p3 = os.path.join(out_dir, "04_图3_核心变量年度趋势.png")
        fig.savefig(p3, dpi=130)
        plt.close(fig)
        print("  %s" % p3)
        outs.append(p3)
    return outs


# ============================================================
# 主流程
# ============================================================
def main():
    ap = argparse.ArgumentParser(description="上市公司面板数据描述性统计一键流水线")
    ap.add_argument("data", help=".dta 数据文件路径")
    ap.add_argument("--out", default=None, help="输出目录，默认 数据所在目录/输出结果")
    ap.add_argument("--id", default=None, help="公司代码列名，默认自动识别")
    ap.add_argument("--year", default=None, help="年份列名，默认自动识别")
    ap.add_argument("--core", nargs="*", default=None, help="画图的变量列表，默认取缺失最少的9个")
    a = ap.parse_args()

    if not os.path.exists(a.data):
        print("找不到数据文件：%s" % a.data)
        sys.exit(1)
    out_dir = a.out or os.path.join(os.path.dirname(os.path.abspath(a.data)), "输出结果")
    os.makedirs(out_dir, exist_ok=True)

    df, labels = load_dta(a.data)
    print("已读取：%s" % a.data)
    print("规模：%s 行 × %s 列" % (f"{len(df):,}", df.shape[1]))

    id_col = a.id or guess_col(df, ID_CANDIDATES)
    year_col = a.year or guess_col(df, YEAR_CANDIDATES)
    print("识别到：公司代码列 = %s，年份列 = %s" % (id_col, year_col))

    step_check(df, labels, id_col, year_col, out_dir)
    cont, dummy, cat = split_vars(df, labels, id_col, year_col)
    print("\n变量分组：连续 %d 个，虚拟/低基数 %d 个，文本分类 %d 个"
          % (len(cont), len(dummy), len(cat)))

    desc, paper, cat_freq, year_mean, alert = step_describe(
        df, labels, cont, dummy, year_col, out_dir)
    pear, long, vif = step_corr(df, labels, cont, out_dir)
    step_plot(df, labels, cont, year_col, out_dir, core=a.core)

    print("\n" + "=" * 70)
    print("全部完成，结果在：%s" % os.path.abspath(out_dir))
    print("下一步：用 make_three_line_docx.py 把 02_描述统计_论文格式.csv 转成 Word 三线表")
    print("=" * 70)


if __name__ == "__main__":
    main()
