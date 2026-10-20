import itertools
import statistics

import networkx as nx
import pytest

from fattree import build_fat_tree, fail_links, host_path_stats, summary, switch_links

KS = [4, 6, 8]


@pytest.mark.parametrize("k", KS)
def test_node_counts(k):
    s = summary(build_fat_tree(k))
    assert s["host"] == k**3 // 4
    assert s["edge"] == k * (k // 2)
    assert s["agg"] == k * (k // 2)
    assert s["core"] == (k // 2) ** 2


@pytest.mark.parametrize("k", KS)
def test_switch_degree_is_k(k):
    G = build_fat_tree(k)
    for n, t in G.nodes(data="type"):
        if t != "host":
            assert G.degree(n) == k, n


@pytest.mark.parametrize("k", KS)
def test_host_degree_is_1(k):
    G = build_fat_tree(k)
    assert all(G.degree(n) == 1 for n, t in G.nodes(data="type") if t == "host")


@pytest.mark.parametrize("k", KS)
def test_link_count(k):
    assert build_fat_tree(k).number_of_edges() == 3 * k**3 // 4


@pytest.mark.parametrize("k", KS)
def test_connected(k):
    assert nx.is_connected(build_fat_tree(k))


@pytest.mark.parametrize("k", KS)
def test_each_core_reaches_every_pod_once(k):
    G = build_fat_tree(k)
    for n, t in G.nodes(data="type"):
        if t == "core":
            pods = sorted(G.nodes[m]["pod"] for m in G[n])
            assert pods == list(range(k)), n


@pytest.mark.parametrize("k", [0, 3, 5, -2])
def test_bad_k_rejected(k):
    with pytest.raises(ValueError):
        build_fat_tree(k)


# --- failures ---

@pytest.mark.parametrize("k", KS)
@pytest.mark.parametrize("pct", [0, 1, 10, 50, 100])
def test_fail_removes_exact_count_of_switch_links_only(k, pct):
    G = build_fat_tree(k)
    H = fail_links(G, pct, seed=1)
    n_switch = len(switch_links(G))
    assert n_switch == k**3 // 2
    assert H.graph["failed"] == round(pct / 100 * n_switch)
    assert G.number_of_edges() - H.number_of_edges() == H.graph["failed"]
    assert all(H.degree(n) == 1 for n, t in H.nodes(data="type") if t == "host")


def test_fail_is_reproducible_and_does_not_touch_original():
    G = build_fat_tree(4)
    a, b, c = fail_links(G, 30, seed=7), fail_links(G, 30, seed=7), fail_links(G, 30, seed=8)
    assert set(a.edges) == set(b.edges)
    assert set(a.edges) != set(c.edges)
    assert G.number_of_edges() == 48


@pytest.mark.parametrize("pct", [-1, 101])
def test_bad_pct_rejected(pct):
    with pytest.raises(ValueError):
        fail_links(build_fat_tree(4), pct)


# --- path-length metric ---

def has_updown_path(G, ea, eb):
    """Explicitly enumerate up-down paths: edge-agg-edge (same pod) or edge-agg-core-agg-edge."""
    k, pa, pb = G.graph["k"], G.nodes[ea]["pod"], G.nodes[eb]["pod"]
    half = k // 2
    if ea == eb:
        return True
    for j in range(half):
        a1, a2 = f"agg_p{pa}_{j}", f"agg_p{pb}_{j}"
        if not (G.has_edge(ea, a1) and G.has_edge(a2, eb)):
            continue
        if pa == pb:
            return True
        if any(G.has_edge(a1, f"core_{j}_{i}") and G.has_edge(f"core_{j}_{i}", a2) for i in range(half)):
            return True
    return False


def brute_force_stats(G):
    hosts = [n for n, t in G.nodes(data="type") if t == "host"]
    edge_of = {x: next(iter(G[x])) for x in hosts}
    dist = dict(nx.all_pairs_shortest_path_length(G))
    pairs = list(itertools.combinations(hosts, 2))
    lengths = [dist[a].get(b) for a, b in pairs]
    ok = [d for d in lengths if d is not None]
    no_ud = sum(not has_updown_path(G, edge_of[a], edge_of[b]) for a, b in pairs)
    return sum(ok) / len(ok), 1 - len(ok) / len(pairs), no_ud / len(pairs)


@pytest.mark.parametrize("k", KS)
def test_baseline_path_length_matches_formula(k):
    # Other hosts: h-1 at 2 hops (same edge), (h-1)*h at 4 (same pod), (k-1)*h^2 at 6 (other pods).
    h = k // 2
    expected = (2 * (h - 1) + 4 * (h - 1) * h + 6 * (k - 1) * h * h) / (k**3 // 4 - 1)
    mean, disc, no_ud = host_path_stats(build_fat_tree(k))
    assert mean == pytest.approx(expected)
    assert disc == 0 and no_ud == 0


@pytest.mark.parametrize("k", [4, 6])
@pytest.mark.parametrize("pct", [10, 40, 70, 90])
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_path_stats_match_brute_force(k, pct, seed):
    H = fail_links(build_fat_tree(k), pct, seed)
    assert host_path_stats(H) == pytest.approx(brute_force_stats(H))


# --- theory lower bound (experiment.py) ---

def isolated_pair_fraction(G):
    """Fraction of host pairs where at least one host's edge switch has no uplink left."""
    k = G.graph["k"]
    h = k // 2
    edges = [n for n, t in G.nodes(data="type") if t == "edge"]
    cut = sum(G.degree(e) == h for e in edges)  # only its k/2 host links remain
    ok = len(edges) - cut
    hosts = k**3 // 4
    cross_pairs_with_cut = (cut * (cut - 1) // 2 + cut * ok) * h * h
    return cross_pairs_with_cut / (hosts * (hosts - 1) // 2)


@pytest.mark.parametrize("k", [4, 6])
@pytest.mark.parametrize("pct", [30, 60, 90])
def test_isolation_is_a_lower_bound_per_sample(k, pct):
    for seed in range(5):
        H = fail_links(build_fat_tree(k), pct, seed)
        assert isolated_pair_fraction(H) <= host_path_stats(H)[1] + 1e-12


@pytest.mark.parametrize("k,pct", [(4, 50), (4, 80), (6, 70)])
def test_isolation_bound_formula_matches_monte_carlo(k, pct):
    from experiment import isolation_bound
    G = build_fat_tree(k)
    sim = statistics.mean(isolated_pair_fraction(fail_links(G, pct, s)) for s in range(3000))
    assert sim == pytest.approx(isolation_bound(k, pct), abs=0.01)


def test_isolation_bound_edges():
    from experiment import isolation_bound
    assert isolation_bound(8, 0) == 0
    hosts, h, n_edge = 128, 4, 32
    cross_share = (n_edge * (n_edge - 1) // 2 * h * h) / (hosts * (hosts - 1) // 2)
    assert isolation_bound(8, 100) == pytest.approx(cross_share)
