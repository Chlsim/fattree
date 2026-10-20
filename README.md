# Fat-Tree Topology Generator & Analysis

HW1, Communication Networks for Data Centers & AI (BGU, Sem A 2026–27).

This repo generates the 3-tier k-ary fat-tree of Al-Fares et al. [1] as a `networkx` graph, validates it, injects random link failures, and measures how host-to-host path length degrades as failures increase.

## Topology

A k-ary fat-tree is built entirely from identical k-port switches:

| Element | Count | Wiring |
|---|---|---|
| Pods | k | — |
| Edge switches | k/2 per pod (k²/2 total) | k/2 ports down to hosts, k/2 up to every agg in the pod |
| Aggregation switches | k/2 per pod (k²/2 total) | k/2 ports down to every edge in the pod, k/2 up to core |
| Core switches | (k/2)² | one port to each of the k pods |
| Hosts | k/2 per edge switch (k³/4 total) | one link to their edge switch |
| Links | 3k³/4 | k³/4 per layer (host–edge, edge–agg, agg–core) |

**Core wiring.** The core switches form a (k/2)×(k/2) grid. Aggregation switch *j* of every pod connects to all k/2 core switches in row *j*. As a result, each core switch has exactly one link into each pod, and every switch uses all k of its ports.

**Nodes.** Each node has a readable name, a `type` (`host`/`edge`/`agg`/`core`), a `pod` (all nodes except core) and an `addr` holding the paper's address:

| Node | Name | `addr` (paper) |
|---|---|---|
| Core (row j, column i) | `core_j_i` | `10.k.j+1.i+1` |
| Agg *s* in pod *p* | `agg_p{p}_{s}` | `10.p.(k/2+s).1` |
| Edge *s* in pod *p* | `edge_p{p}_{s}` | `10.p.s.1` |
| Host *h* under edge *s*, pod *p* | `host_p{p}_{s}_{h}` | `10.p.s.(h+2)` |

**k = 4 example** (16 hosts, 20 switches, 48 links):

![k=4 fat-tree](results/fattree_k4.png)

**Validation** (`test_fattree.py`, k = 4, 6, 8):
- node counts match the formulas above
- every switch has degree k and every host has degree 1
- the link count is 3k³/4
- the graph is connected
- each core switch connects to every pod exactly once
- odd or invalid k is rejected

## Inputs

| Parameter | Flag | Required | Description |
|---|---|---|---|
| Switch port count | `--k` | yes | Must be an even integer ≥ 2. It sets the whole topology scale: k³/4 hosts, 5k²/4 switches. |
| Link-failure percentage | `--fail PCT` | no (default 0) | Percentage (0–100) of **switch-to-switch** links to fail. See [Failure Model](#failure-model). |
| Random seed | `--seed N` | no (default 0) | Picks which links fail. The same seed always gives the same failures. |
| Drawing output | `--draw PATH` | no | Saves a layered drawing of the topology. Practical for k ≤ 6. |

The experiment's sweep parameters (k values, failure range, repetitions) are constants at the top of `experiment.py`.

## How to Run

Requires Python ≥ 3.10.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

```bash
python fattree.py --k 4                                  # topology summary
python fattree.py --k 8 --fail 30 --seed 3               # with 30% link failures
python fattree.py --k 4 --draw results/fattree_k4.png    # also save a drawing
python experiment.py                                     # full sweep (~25 s): CSVs + plot in results/
pytest -q                                                # run the validation tests
```

Example output:

```
k = 8 fat-tree
  hosts : 128
  edge  : 32
  agg   : 32
  core  : 16
  links : 307
  failed: 77 of 256 switch links (30%, seed 3)
  avg host-host path : 5.894 hops (connected pairs)
  disconnected pairs : 0.00%
```

## Failure Model

- **Which links can fail:** only switch-to-switch links (edge–agg and agg–core), N = k³/2 of them. Host–edge links never fail. A host has a single link with no backup, so failing it only strands that host and says nothing about the topology's redundancy, which is what we want to measure.
- **How failures are sampled:** for a failure percentage p, exactly round(p · N) links are removed, chosen uniformly at random without replacement. A fixed percentage therefore always means the same number of failed links, as the assignment's "percentage of link failures" implies. (The alternative, each link failing independently with probability p, would make the count vary between runs.)
- **Reproducibility:** the sample comes from `random.Random(seed)`, so a given (k, p, seed) always produces the same failed graph.
- Failed links are removed from a **copy** of the graph, so the original topology is never modified.

## Analysis

**Question:** how does the fat-tree's path redundancy hold up as links fail, and how does that depend on scale (k)?

**Metric: average host-to-host shortest-path length (hops)**, averaged over all host pairs that are still connected. Because the average is undefined for disconnected pairs, we also report the **fraction of host pairs that are disconnected**. Without that second number, a falling average could be mistaken for an improvement (see the results).

**Computation:** host links never fail, so two hosts under the same edge switch are 2 hops apart, and any other pair is dist(edge switch a, edge switch b) + 2. One BFS per edge switch (k²/2 of them) therefore gives the **exact** average over **all** host pairs, without sampling. `test_fattree.py` checks this against a brute-force all-pairs computation on failed graphs.

**Second metric: fraction of host pairs with no up-down path.** The paper's two-level routing only uses *up-down* paths: edge→agg→edge inside a pod, or edge→agg→core→agg→edge across pods, which is at most 6 hops host-to-host. In a fat-tree, the only edge-to-edge paths with the healthy length (2 hops inside a pod, 4 across pods) are exactly the up-down paths. Any longer path must go down and back up (a "valley"). So a pair keeps an up-down path **if and only if** its shortest path still has its healthy length, and the same BFS gives this metric for free. `test_fattree.py` cross-checks it against an explicit search that follows the wiring hop by hop.

**Theory lower bound for disconnection.** A host pair is *certainly* disconnected if one of its edge switches has lost all k/2 uplinks. With exactly n of the N = k³/2 switch links failed, the probability that j specific links have all failed is

  H(j) = ∏ᵢ₌₀^{j−1} (n − i)/(N − i) ≈ pʲ.

Two different edge switches have disjoint uplinks, so by inclusion–exclusion

  P(pair cut off) = 2·H(k/2) − H(k).

Multiplying by the share of pairs on different edge switches gives the expected lower bound. `test_fattree.py` checks that the bound never exceeds the true disconnected fraction in any sample, and that the formula matches 3,000 Monte Carlo samples.

**Validation of the metric at 0% failure:** a host's other hosts are h−1 at 2 hops (same edge), (h−1)·h at 4 hops (same pod) and (k−1)·h² at 6 hops (other pods), where h = k/2. The measured baselines match this formula exactly.

## Results

### Path length and disconnection vs. link-failure percentage

![path length vs failure](results/path_length_vs_failure.png)

**Setup:** `python experiment.py`
- k = 4, 8, 16 (16, 128 and 1,024 hosts)
- failure percentage of switch-to-switch links: 0–80% in 5% steps
- 30 repetitions per point (seeds 0–29)
- each point is the mean, with the shaded band showing the 95% confidence interval (normal approximation)
- dashed lines (bottom panel): the theory lower bound from [Analysis](#analysis)
- raw data: `results/path_length_raw.csv`; aggregated: `results/path_length_summary.csv`

**Observations:**

| Failure | k = 4: avg hops / disconnected | k = 8 | k = 16 |
|---|---|---|---|
| 0% | 5.47 / 0% | 5.72 / 0% | 5.86 / 0% |
| 30% | 5.95 / 21% | 5.84 / 1.2% | 5.87 / 0% |
| 50% | 5.21 / 64% | 6.59 / 11% | 6.09 / 0.8% |
| 70% | 3.14 / 88% | 8.42 / 57% | 7.32 / 10% |
| 80% | 2.20 / 92% | 6.04 / 91% | 9.01 / 33% |

1. **Flat region.** At low failure rates, path length doesn't change. For k = 16 the curve stays flat up to about 30% failure.
2. **Stretch region.** Next, paths get longer than the 6-hop maximum of a healthy fat-tree.
3. **Collapse region.** Finally, the average *drops*, and the bottom panel shows why: most pairs are disconnected by then.
4. **Effect of scale.** A larger k shifts all three regions to the right.
5. **Theory vs. simulation.** For k = 8 and k = 16, the dashed lower bound lies almost exactly on the simulated curve (within the confidence band). For k = 4, the simulation pulls clearly above the bound once failure exceeds about 30%.

**Explanation:**
- **Flat region:** two hosts in different pods have (k/2)² equal-length 6-hop paths (k/2 aggs × k/2 cores each). As long as at least one survives, the shortest-path length is unchanged. With 64 such paths for k = 16, a lot of failure is needed before every one is broken.
- **Stretch region:** once all shortest paths between two edge switches are broken, the surviving route detours, for example by going down to another edge switch and back up. Each detour like that adds 2 hops, which is why averages climb above 6.
- **Collapse region:** the average only covers *connected* pairs. Long-distance pairs disconnect first, so the survivors are mostly short pairs (2 hops, under the same edge switch), and the mean falls toward 2. This is a survivorship effect, not an improvement, which is why the disconnection panel is essential.
- **Scale:** an edge switch is cut off from the rest of the network only when all k/2 of its uplinks fail, which happens with probability ≈ p^(k/2). At p = 50% that's 25% for k = 4 but 0.4% for k = 16. Bigger switches give every edge switch more independent uplinks.
- **Theory vs. simulation:** where the curves coincide, losing an edge switch's uplinks is essentially the *only* way pairs get disconnected. Every other cut, such as a whole pod losing its core links (all k/2 aggs × k/2 core links), needs far more failures at once. For k = 4 those other cuts need only 4 links, so they happen often and push the simulation above the bound. (At individual points the 30-sample mean can dip slightly below the bound. That's sampling noise: the bound holds exactly in every single sample, as the tests verify.)

**Significance:**
- **The fat-tree degrades gracefully.** Its many equal-cost paths absorb a large fraction of random link failures with no change in path length. For k = 16, 30% of switch links can fail with essentially no effect.
- **Scale buys robustness.** Robustness improves with k at no extra cost per switch, since the same commodity switches are used. This supports the paper's argument for building large networks from commodity switches.
- **Path stretch is an early warning.** It appears before disconnection, so an operator can see the redundancy running out before hosts lose reachability.
- **Limitation: shortest-path routing is optimistic.** Shortest paths may use detours that the paper's routing never takes. The next plot measures how big that gap is.

### Up-down routability vs. link-failure percentage

![up-down vs failure](results/updown_vs_failure.png)

**Setup:** the same run as above (`python experiment.py`: k = 4, 8, 16; 0–80% in 5% steps; 30 seeds; mean ± 95% CI). For each k, the solid line is the fraction of host pairs with **no up-down path**, meaning pairs the paper's two-level routing cannot serve. The dashed line is the fraction that is **physically disconnected**. The shaded gap between them is pairs that are still connected, but only through detours.

**Observations:**

| Failure | k = 4: no up-down / disconnected | k = 8 | k = 16 |
|---|---|---|---|
| 30% | 39% / 21% | 7.3% / 1.2% | 0.4% / 0% |
| 50% | 71% / 64% | 44% / 11% | 12% / 0.8% |
| 70% | 88% / 88% | 86% / 57% | 66% / 10% |

- The solid curve always lies above the dashed one, and it rises much earlier.
- For k = 16 at 70% failure, only 10% of pairs are disconnected, but 66% have lost every up-down path.
- For k = 4 the two curves nearly coincide, because a small fat-tree has few detours to offer.

**Explanation:** an up-down path between pods needs four specific links to all survive: edge→agg *j*, agg *j*→core, core→agg *j*, and agg *j*→edge. A cross-pod pair has (k/2)² such paths. A detour can mix links from many different paths, so it survives long after every one of the (k/2)² "clean" paths has lost at least one link. A larger k gives more detour options, which is why the gap grows with k.

**Significance:** the physical network is much more robust than the paper's routing can use. The paper's failure-broadcast scheme (§3.8 of [1]) reroutes around failed links, but it still only chooses among up-down paths. The solid curve is therefore the *best case* for the paper's routing: pairs above it are unreachable even with perfect failure knowledge. Recovering them requires routing that allows detours, such as F10 [2]. The lesson: "the graph is connected" is not the same as "the network can deliver packets".

## AI Usage

See [AI_USAGE.md](AI_USAGE.md).

## References

[1] M. Al-Fares, A. Loukissas, and A. Vahdat, "A scalable, commodity data center network architecture," *SIGCOMM Comput. Commun. Rev.*, vol. 38, no. 4, pp. 63–74, Oct. 2008, doi: 10.1145/1402946.1402967.

[2] V. Liu, D. Halperin, A. Krishnamurthy, and T. Anderson, "F10: A fault-tolerant engineered network," in *Proc. USENIX NSDI*, 2013.
