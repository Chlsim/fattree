import itertools

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

def brute_force_stats(G):
    hosts = [n for n, t in G.nodes(data="type") if t == "host"]
    dist = dict(nx.all_pairs_shortest_path_length(G))
    lengths = [dist[a].get(b) for a, b in itertools.combinations(hosts, 2)]
    ok = [d for d in lengths if d is not None]
    return sum(ok) / len(ok), 1 - len(ok) / len(lengths)


@pytest.mark.parametrize("k", KS)
def test_baseline_path_length_matches_formula(k):
    # Other hosts: h-1 at 2 hops (same edge), (h-1)*h at 4 (same pod), (k-1)*h^2 at 6 (other pods).
    h = k // 2
    expected = (2 * (h - 1) + 4 * (h - 1) * h + 6 * (k - 1) * h * h) / (k**3 // 4 - 1)
    mean, disc = host_path_stats(build_fat_tree(k))
    assert mean == pytest.approx(expected)
    assert disc == 0


@pytest.mark.parametrize("k", [4, 6])
@pytest.mark.parametrize("pct", [10, 40, 70, 90])
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_path_stats_match_brute_force(k, pct, seed):
    H = fail_links(build_fat_tree(k), pct, seed)
    assert host_path_stats(H) == pytest.approx(brute_force_stats(H))
