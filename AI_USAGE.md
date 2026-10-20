# AI Usage

AI assistant: Claude (Anthropic), via Claude Code. I reviewed, ran and understand all code and text.

| Date | What | Where |
|---|---|---|
| 2026-10-20 | Proposed the file layout and graph-construction plan (I made the design choices: node naming, pytest, repo setup) | — |
| 2026-10-20 | Wrote the fat-tree generator, CLI and layered drawing | `fattree.py` |
| 2026-10-20 | Wrote the validation tests (counts, degree = k, 3k³/4 links, connectivity, core-to-pod wiring) | `test_fattree.py` |
| 2026-10-20 | Drafted the README sections Topology, Inputs and How to Run | `README.md` |
| 2026-10-20 | Proposed the failure-model and metric options with tradeoffs (I chose: switch links only, exact fraction, avg path length, k = 4/8/16, 0–80%, 30 seeds) | — |
| 2026-10-20 | Wrote link-failure injection and the host path-length metric (edge-switch BFS), plus `--fail` / `--seed` | `fattree.py` |
| 2026-10-20 | Wrote tests for failures and the metric, including a brute-force cross-check | `test_fattree.py` |
| 2026-10-20 | Wrote the sweep, CSV output and plot | `experiment.py` |
| 2026-10-20 | Drafted the README sections Inputs, How to Run, Failure Model, Analysis and Results; I reviewed the explanation | `README.md` |
| 2026-10-20 | Added the theory lower bound (hypergeometric edge isolation) and the up-down routability metric with tests and a second plot; extended the README results | `experiment.py`, `fattree.py`, `test_fattree.py`, `README.md` |
