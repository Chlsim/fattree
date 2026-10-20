"""Sweep the link-failure percentage and measure host-to-host path length on k-ary fat-trees.

Outputs:
  results/path_length_raw.csv      one row per (k, fail %, seed)
  results/path_length_summary.csv  mean and 95% CI per (k, fail %), plus the theory lower bound
  results/path_length_vs_failure.png   avg path length + disconnected pairs (with theory bound)
  results/updown_vs_failure.png        pairs with no up-down path vs. disconnected pairs
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
METRICS = ("avg_path", "disconnected", "no_updown")

COLORS = {4: "#2a78d6", 8: "#eb6834", 16: "#1baf7a"}
MARKERS = {4: "o", 8: "s", 16: "^"}
INK, MUTED, GRID = "#2b2b2b", "#6b6b6b", "#e6e6e6"


def all_failed(j, n, N):
    """Probability that j specific links are all among n failed links, drawn from N without replacement."""
    p = 1.0
    for i in range(j):
        p *= (n - i) / (N - i)
    return p


def isolation_bound(k, pct):
    """Expected fraction of host pairs that are certainly disconnected: one of their edge switches lost
    all k/2 uplinks. This is a lower bound on the disconnected fraction.

    For two different edge switches (disjoint uplink sets), inclusion-exclusion gives
    P(a cut off or b cut off) = 2 * P(k/2 links all failed) - P(k links all failed).
    Hosts on the same edge switch are never disconnected.
    """
    h, n_edge, N = k // 2, k * k // 2, k**3 // 2
    n = round(pct / 100 * N)
    hosts = k**3 // 4
    cross_pairs = n_edge * (n_edge - 1) // 2 * h * h
    p_pair = 2 * all_failed(h, n, N) - all_failed(2 * h, n, N)
    return cross_pairs / (hosts * (hosts - 1) // 2) * p_pair


def run():
    raw = []
    for k in KS:
        G = build_fat_tree(k)
        for pct in PCTS:
            for seed in SEEDS:
                vals = host_path_stats(fail_links(G, pct, seed))
                raw.append({"k": k, "fail_pct": pct, "seed": seed, **dict(zip(METRICS, vals))})
        print(f"k = {k} done")
    return raw


def summarize(raw):
    rows = []
    for k in KS:
        for pct in PCTS:
            pts = [r for r in raw if r["k"] == k and r["fail_pct"] == pct]
            row = {"k": k, "fail_pct": pct, "n": len(pts)}
            for col in METRICS:
                vals = [r[col] for r in pts]
                row[col] = statistics.mean(vals)
                row[col + "_ci"] = Z95 * statistics.stdev(vals) / math.sqrt(len(vals))
            row["isolation_bound"] = isolation_bound(k, pct)
            rows.append(row)
    return rows


def write_csv(rows, path):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)


def style(ax):
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=MUTED)


def series(rows, k, col, scale=1):
    rs = [r for r in rows if r["k"] == k]
    x = [r["fail_pct"] for r in rs]
    y = [r[col] * scale for r in rs]
    ci = [r[col + "_ci"] * scale for r in rs] if col + "_ci" in rs[0] else None
    return x, y, ci


def band(ax, x, y, ci, color):
    ax.fill_between(x, [a - b for a, b in zip(y, ci)], [a + b for a, b in zip(y, ci)],
                    color=color, alpha=0.15, linewidth=0)


def plot_path_length(rows, path):
    fig, (top, bot) = plt.subplots(2, 1, figsize=(8, 7), sharex=True, gridspec_kw={"height_ratios": [3, 2]})
    for k in KS:
        c = COLORS[k]
        for ax, col, scale in ((top, "avg_path", 1), (bot, "disconnected", 100)):
            x, y, ci = series(rows, k, col, scale)
            ax.plot(x, y, color=c, marker=MARKERS[k], markersize=5, linewidth=2, label=f"k = {k}")
            band(ax, x, y, ci, c)
        x, y, _ = series(rows, k, "isolation_bound", 100)
        bot.plot(x, y, color=c, linewidth=1.5, linestyle="--")
        # Label each curve directly at its right end.
        x, y, _ = series(rows, k, "avg_path")
        top.annotate(f"k = {k}", (x[-1], y[-1]), xytext=(6, 0), textcoords="offset points",
                     va="center", fontsize=9, color=INK)

    top.set_ylabel("Avg host-to-host path\n(hops, connected pairs)", color=INK)
    bot.set_ylabel("Disconnected host pairs (%)", color=INK)
    bot.set_xlabel("Failed switch-to-switch links (%)", color=INK)
    top.set_title("Fat-tree path length under random link failures (mean ± 95% CI, 30 seeds)",
                  color=INK, fontsize=11)
    top.legend(loc="upper left", frameon=False, fontsize=9)
    bot.plot([], [], color=MUTED, linestyle="-", linewidth=2, label="simulated")
    bot.plot([], [], color=MUTED, linestyle="--", linewidth=1.5, label="theory lower bound:\nan edge switch lost all k/2 uplinks")
    bot.legend(loc="upper left", frameon=False, fontsize=8)
    for ax in (top, bot):
        style(ax)
    bot.set_xticks(PCTS[::2])
    bot.set_xlim(0, PCTS[-1] + 6)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_updown(rows, path):
    fig, axes = plt.subplots(1, len(KS), figsize=(11, 4), sharey=True)
    for ax, k in zip(axes, KS):
        c = COLORS[k]
        x, ud, ud_ci = series(rows, k, "no_updown", 100)
        _, dc, dc_ci = series(rows, k, "disconnected", 100)
        ax.fill_between(x, dc, ud, color=c, alpha=0.12, linewidth=0, label="reachable only via detours")
        ax.plot(x, ud, color=c, marker=MARKERS[k], markersize=5, linewidth=2, label="no up-down path")
        band(ax, x, ud, ud_ci, c)
        ax.plot(x, dc, color=c, linewidth=1.5, linestyle="--", label="disconnected")
        ax.set_title(f"k = {k}", color=INK, fontsize=10)
        ax.set_xlabel("Failed switch links (%)", color=INK)
        ax.set_xticks(PCTS[::4])
        style(ax)
        ax.legend(loc="upper left", frameon=False, fontsize=8)
    axes[0].set_ylabel("Host pairs (%)", color=INK)
    fig.suptitle("Pairs the paper's up-down routing cannot serve vs. pairs that are truly cut off "
                 "(mean ± 95% CI, 30 seeds)", color=INK, fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    raw = run()
    rows = summarize(raw)
    write_csv(raw, "results/path_length_raw.csv")
    write_csv(rows, "results/path_length_summary.csv")
    plot_path_length(rows, "results/path_length_vs_failure.png")
    plot_updown(rows, "results/updown_vs_failure.png")
    print("saved results/path_length_*.csv, results/path_length_vs_failure.png, results/updown_vs_failure.png")


if __name__ == "__main__":
    main()
