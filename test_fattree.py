import networkx as nx
import pytest

from fattree import build_fat_tree, summary

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
