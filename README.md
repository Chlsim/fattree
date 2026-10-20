# Fat-Tree Topology Generator & Analysis

HW1, Communication Networks for Data Centers & AI (BGU, Sem A 2026–27).

This repo generates the 3-tier k-ary fat-tree of Al-Fares et al. [1] as a `networkx` graph, validates it, and (in later commits) analyzes it under link failures.

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
| Drawing output | `--draw PATH` | no | Saves a layered drawing of the topology. Practical for k ≤ 6. |
| Link-failure percentage | — | — | *Coming in the full submission.* |

## How to Run

Requires Python ≥ 3.10.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

```bash
python fattree.py --k 4                                  # print a summary
python fattree.py --k 4 --draw results/fattree_k4.png    # also save a drawing
pytest -q                                                # run the validation tests
```

Example output:

```
k = 4 fat-tree
  hosts : 16
  edge  : 8
  agg   : 8
  core  : 4
  links : 48
```

## Failure Model

*TODO: which links can fail, how they are sampled, seeds.*

## Analysis

*TODO: metric, swept parameter, experimental setup.*

## Results

*TODO: plots, each with its setup and parameters, the observation, an explanation and its significance.*

## AI Usage

See [AI_USAGE.md](AI_USAGE.md).

## References

[1] M. Al-Fares, A. Loukissas, and A. Vahdat, "A scalable, commodity data center network architecture," *SIGCOMM Comput. Commun. Rev.*, vol. 38, no. 4, pp. 63–74, Oct. 2008, doi: 10.1145/1402946.1402967.
