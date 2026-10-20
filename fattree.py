"""k-ary fat-tree generator, following Al-Fares et al., SIGCOMM 2008, Section 3."""
import argparse
import random

import networkx as nx


def build_fat_tree(k):
    """Return a 3-tier k-ary fat-tree as an undirected networkx Graph.

    Every node has a 'type' (host/edge/agg/core) and an 'addr' (the paper's
    10.x.y.z address). Every node except core switches also has a 'pod'.
    """
    if k < 2 or k % 2:
        raise ValueError(f"k must be an even integer >= 2, got {k}")
    half = k // 2
    G = nx.Graph(k=k)

    # Core: (k/2)^2 switches in a (k/2) x (k/2) grid. Paper address: 10.k.j.i, with j, i from 1.
    for j in range(half):
        for i in range(half):
            G.add_node(f"core_{j}_{i}", type="core", addr=f"10.{k}.{j + 1}.{i + 1}")

    for p in range(k):
        # Paper numbers pod switches 0..k-1: edge first (0..k/2-1), then agg (k/2..k-1).
        edges = [f"edge_p{p}_{s}" for s in range(half)]
        aggs = [f"agg_p{p}_{s}" for s in range(half)]
        for s, e in enumerate(edges):
            G.add_node(e, type="edge", pod=p, addr=f"10.{p}.{s}.1")
        for s, a in enumerate(aggs):
            G.add_node(a, type="agg", pod=p, addr=f"10.{p}.{half + s}.1")

        # Hosts: k/2 per edge switch. Paper address: 10.pod.switch.ID, ID from 2.
        for s, e in enumerate(edges):
            for h in range(half):
                host = f"host_p{p}_{s}_{h}"
                G.add_node(host, type="host", pod=p, addr=f"10.{p}.{s}.{h + 2}")
                G.add_edge(host, e)

        # Edge <-> agg: complete bipartite inside the pod.
        for e in edges:
            for a in aggs:
                G.add_edge(e, a)

        # Agg j <-> every core in row j, so each core gets exactly one link per pod.
        for j, a in enumerate(aggs):
            for i in range(half):
                G.add_edge(a, f"core_{j}_{i}")

    return G


def switch_links(G):
    """Return the links that may fail: those with no host endpoint (edge-agg and agg-core)."""
    return [(u, v) for u, v in G.edges if G.nodes[u]["type"] != "host" and G.nodes[v]["type"] != "host"]


def fail_links(G, pct, seed=0):
    """Return a copy of G with exactly round(pct% of switch links) removed, chosen uniformly at random.

    Host-edge links never fail, because a host has no backup link, so a failure there says nothing
    about the topology.
    """
    if not 0 <= pct <= 100:
        raise ValueError(f"pct must be in [0, 100], got {pct}")
    candidates = switch_links(G)
    n_fail = round(pct / 100 * len(candidates))
    H = G.copy()
    H.remove_edges_from(random.Random(seed).sample(candidates, n_fail))
    H.graph["failed"] = n_fail
    return H


def host_path_stats(G):
    """Return (mean hops over connected host pairs, fraction of host pairs that are disconnected).

    Host links never fail, so two hosts on the same edge switch are 2 hops apart, and any other pair
    is dist(edge_a, edge_b) + 2. One BFS per edge switch therefore covers all host pairs exactly.
    """
    edges = [n for n, t in G.nodes(data="type") if t == "edge"]
    h = G.graph["k"] // 2  # hosts per edge switch
    hops = connected = disconnected = 0
    for i, a in enumerate(edges):
        same = h * (h - 1) // 2  # host pairs under switch a
        hops += 2 * same
        connected += same
        dist = nx.single_source_shortest_path_length(G, a)
        for b in edges[i + 1:]:
            if b in dist:
                hops += h * h * (dist[b] + 2)
                connected += h * h
            else:
                disconnected += h * h
    mean = hops / connected if connected else float("nan")
    return mean, disconnected / (connected + disconnected)


def summary(G):
    """Count nodes by type, plus the total link count."""
    counts = {t: 0 for t in ("host", "edge", "agg", "core")}
    for _, t in G.nodes(data="type"):
        counts[t] += 1
    counts["links"] = G.number_of_edges()
    return counts


def draw(G, path):
    """Save a layered drawing (core on top, hosts at the bottom) to path."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    k = G.graph["k"]
    half = k // 2
    y = {"host": 0, "edge": 1, "agg": 2, "core": 3}
    pos = {}
    # Hosts are evenly spaced in one row, and each edge switch is centered over its hosts.
    hosts_per_pod = half * half
    for p in range(k):
        for s in range(half):
            xs = [p * (hosts_per_pod + 1) + s * half + h for h in range(half)]
            for h, x in enumerate(xs):
                pos[f"host_p{p}_{s}_{h}"] = (x, y["host"])
            center = sum(xs) / half
            pos[f"edge_p{p}_{s}"] = (center, y["edge"])
            pos[f"agg_p{p}_{s}"] = (center, y["agg"])
    # Core switches are spread evenly across the full width.
    width = k * (hosts_per_pod + 1) - 2
    n_core = half * half
    for j in range(half):
        for i in range(half):
            idx = j * half + i
            pos[f"core_{j}_{i}"] = (width * (idx + 0.5) / n_core, y["core"])

    colors = {"host": "#9aa5b1", "edge": "#2f7ed8", "agg": "#e8a33d", "core": "#c0392b"}
    fig, ax = plt.subplots(figsize=(max(8, width * 0.35), 5))
    nx.draw_networkx_edges(G, pos, ax=ax, width=0.6, alpha=0.5)
    for t, c in colors.items():
        nodes = [n for n, nt in G.nodes(data="type") if nt == t]
        nx.draw_networkx_nodes(G, pos, nodelist=nodes, node_color=c, node_size=120 if t == "host" else 260,
                               ax=ax, label=t)
    ax.set_title(f"k = {k} fat-tree")
    ax.legend(loc="upper left", fontsize=8)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Generate a k-ary fat-tree (Al-Fares et al. 2008).")
    parser.add_argument("--k", type=int, required=True, help="switch port count, must be even")
    parser.add_argument("--fail", type=float, default=0.0, metavar="PCT",
                        help="percentage of switch-to-switch links to fail, 0-100 (default 0)")
    parser.add_argument("--seed", type=int, default=0, help="random seed for link failures (default 0)")
    parser.add_argument("--draw", metavar="PATH", help="save a drawing of the topology to PATH (practical for k <= 6)")
    args = parser.parse_args()
    if args.k < 2 or args.k % 2:
        parser.error("--k must be an even integer >= 2")
    if not 0 <= args.fail <= 100:
        parser.error("--fail must be between 0 and 100")

    G = fail_links(build_fat_tree(args.k), args.fail, args.seed)
    s = summary(G)
    print(f"k = {args.k} fat-tree")
    print(f"  hosts : {s['host']}")
    print(f"  edge  : {s['edge']}")
    print(f"  agg   : {s['agg']}")
    print(f"  core  : {s['core']}")
    print(f"  links : {s['links']}")
    print(f"  failed: {G.graph['failed']} of {len(switch_links(G)) + G.graph['failed']} switch links "
          f"({args.fail:g}%, seed {args.seed})")
    mean, disc = host_path_stats(G)
    print(f"  avg host-host path : {mean:.3f} hops (connected pairs)")
    print(f"  disconnected pairs : {disc:.2%}")
    if args.draw:
        draw(G, args.draw)
        print(f"  drawing saved to {args.draw}")


if __name__ == "__main__":
    main()
