"""Sweep the link-failure percentage and measure host-to-host path length on k-ary fat-trees.

Outputs:
  results/path_length_raw.csv      one row per (k, fail %, seed)
  results/path_length_summary.csv  mean and 95% CI per (k, fail %)
  results/path_length_vs_failure.png
"""
import csv
import math
import statistics

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from fattree import build_fat_tree, fail_links, host_path_stats

KS = [4, 8, 16]
PCTS = list(range(0, 85, 5))   # 0-80% in 5% steps
SEEDS = range(30)              # 30 repetitions per point
Z95 = 1.96                     # normal approximation for the 95% CI


def run():
    raw = []
    for k in KS:
        G = build_fat_tree(k)
        for pct in PCTS:
            for seed in SEEDS:
                mean, disc = host_path_stats(fail_links(G, pct, seed))
                raw.append({"k": k, "fail_pct": pct, "seed": seed, "avg_path": mean, "disconnected": disc})
        print(f"k = {k} done")
    return raw


def summarize(raw):
    rows = []
    for k in KS:
        for pct in PCTS:
            pts = [r for r in raw if r["k"] == k and r["fail_pct"] == pct]
            row = {"k": k, "fail_pct": pct, "n": len(pts)}
            for col in ("avg_path", "disconnected"):
                vals = [r[col] for r in pts]
                row[col] = statistics.mean(vals)
                row[col + "_ci"] = Z95 * statistics.stdev(vals) / math.sqrt(len(vals))
            rows.append(row)
    return rows


def write_csv(rows, path):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)


def plot(rows, path):
    colors = {4: "#2a78d6", 8: "#eb6834", 16: "#1baf7a"}
    markers = {4: "o", 8: "s", 16: "^"}
    ink, muted, grid = "#2b2b2b", "#6b6b6b", "#e6e6e6"

    fig, (top, bot) = plt.subplots(2, 1, figsize=(8, 7), sharex=True, gridspec_kw={"height_ratios": [3, 2]})
    for k in KS:
        rs = [r for r in rows if r["k"] == k]
        x = [r["fail_pct"] for r in rs]
        for ax, col, scale in ((top, "avg_path", 1), (bot, "disconnected", 100)):
            y = [r[col] * scale for r in rs]
            ci = [r[col + "_ci"] * scale for r in rs]
            ax.plot(x, y, color=colors[k], marker=markers[k], markersize=5, linewidth=2, label=f"k = {k}")
            ax.fill_between(x, [a - b for a, b in zip(y, ci)], [a + b for a, b in zip(y, ci)],
                            color=colors[k], alpha=0.15, linewidth=0)
        # Label each curve directly at its right end.
        top.annotate(f"k = {k}", (x[-1], rs[-1]["avg_path"]), xytext=(6, 0), textcoords="offset points",
                     va="center", fontsize=9, color=ink)

    top.set_ylabel("Avg host-to-host path\n(hops, connected pairs)", color=ink)
    bot.set_ylabel("Disconnected host pairs (%)", color=ink)
    bot.set_xlabel("Failed switch-to-switch links (%)", color=ink)
    top.set_title("Fat-tree path length under random link failures (mean ± 95% CI, 30 seeds)",
                  color=ink, fontsize=11)
    top.legend(loc="upper left", frameon=False, fontsize=9)
    for ax in (top, bot):
        ax.grid(True, color=grid, linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(muted)
        ax.tick_params(colors=muted)
    bot.set_xticks(PCTS[::2])
    bot.set_xlim(0, PCTS[-1] + 6)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    raw = run()
    rows = summarize(raw)
    write_csv(raw, "results/path_length_raw.csv")
    write_csv(rows, "results/path_length_summary.csv")
    plot(rows, "results/path_length_vs_failure.png")
    print("saved results/path_length_*.csv and results/path_length_vs_failure.png")


if __name__ == "__main__":
    main()
