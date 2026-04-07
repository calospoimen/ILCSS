# ILCSS — Iterative Longest Common SubStrings Similarity

A string similarity measure specifically designed for approximate matching of
multi-part personal names from heterogeneous sources.

**Preprint:** https://doi.org/10.5281/zenodo.19462182

---

## Overview

ILCSS addresses a problem that defeats character-level measures such as
Levenshtein distance and Jaro-Winkler: matching names whose components appear
in different orders or with a different number of parts across administrative
databases, criminal intelligence systems, or bibliographic records.

The algorithm iteratively extracts the longest common substrings shared by two
strings, consuming matched blocks at each step and applying a positional penalty
that attenuates with block length, thereby rewarding component-level agreement
while retaining sensitivity to ordering conventions.

**Example:** `abdullah abdel aziz` vs `aziz abdullah abdel` → ILCSS = 0.93

### Performance

| Dataset | F1 | Score gap (same vs different person) |
|---|---|---|
| Synthetic (295 pairs, 5 naming traditions) | 0.998 | 0.729 |
| DBLP-ACM (bibliographic records) | 0.994 | 0.758 |
| FEBRL (civil registry, name swaps) | 0.989 | 0.816 |

Competing measures (Levenshtein, Jaro-Winkler, Ratcliff/Obershelp) achieve
score gaps of 0.262–0.361 on the same synthetic benchmark.

---

## Repository Structure

```
ILCSS_sim.pl          Perl reference implementation
ILCSS_sim.cr          Crystal implementation
t_LCS.cr              LCS with full matrix (Crystal)
t_LCS_opt.cr          Space-optimised LCS, returns all maximal blocks (Crystal)
ILCSS_paper.pdf       Published preprint
ILCSS_paper.tex       LaTeX source
eval/
  eval_ilcss.py       Synthetic evaluation (295 pairs, 5 naming traditions)
  eval_real.py        Real-world evaluation (DBLP-ACM, FEBRL)
  results.csv         Synthetic results
  results_dblp_acm.csv
  results_febrl.csv
  FEBRL_dataset1.csv  FEBRL benchmark dataset (BSD-3-Clause)
  DBLP-ACM/           Leipzig benchmark dataset (CC BY 4.0)
literature/
  references.bib      BibTeX references (29 entries)
```

---

## Algorithm

```
function ilcss_sim(s1, s2):
    remove spaces from s1, s2
    total_len = len(s1) + len(s2)
    score = 0
    loop:
        block = longest_common_substring(s1, s2)
        if len(block) < 3: break
        pos1 = s1.find(block)
        pos2 = s2.find(block)
        r_len = len(block) / (total_len / 2)
        r_dist = |pos1 - pos2| / (total_len / 2)
        r_penalty = r_dist * (1 - r_len)
        score += r_len * (1 - r_penalty)
        mask block in s1 and s2
    return score / (score + 1)   # normalise to [0, 1)
```

Recommended matching threshold: **0.40**

---

## Running the Evaluation

Requires Python 3.8+ with `jellyfish` and `difflib` (standard library):

```bash
pip install jellyfish
python eval/eval_ilcss.py    # synthetic evaluation
python eval/eval_real.py     # DBLP-ACM + FEBRL evaluation
```

---

## Citation

```bibtex
@misc{calao2026ilcss,
  author    = {Calao, Raoul Sotero},
  title     = {{ILCSS}: An Iterative Longest Common SubStrings Similarity
               Algorithm for Multi-Part Personal Name Matching},
  year      = {2026},
  doi       = {10.5281/zenodo.19462182},
  url       = {https://doi.org/10.5281/zenodo.19462182},
  note      = {Preprint}
}
```

---

## License

Code: [MIT License](LICENSE)

Datasets:
- DBLP-ACM: CC BY 4.0 — Köpcke et al., Leipzig University
- FEBRL: BSD-3-Clause — Christen & Goiser

---

## Author

Raoul Sotero Calao
Chief Commissioner, Italian National Police — Central Anticrime Directorate
raoulsotero.calao@poliziadistato.it | rscalao@gmail.com
