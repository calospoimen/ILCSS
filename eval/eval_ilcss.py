#!/usr/bin/env python3
"""
eval_ilcss.py — Synthetic evaluation of ILCSS vs. competing similarity measures
for multi-part personal name matching.

Algorithms compared:
  - ILCSS       (Iterative Longest Common SubStrings Similarity, this work)
  - NormLev     (Normalized Levenshtein: 1 - edit_dist / max(len1, len2))
  - JaroWinkler (Jaro-Winkler, jellyfish implementation)
  - RatcliffOb  (Ratcliff/Obershelp, difflib.SequenceMatcher)

Requires:
  pip install jellyfish rapidfuzz
"""

import csv
import difflib
import itertools
import os
import sys
from collections import defaultdict

try:
    import jellyfish
except ImportError:
    sys.exit("Missing dependency: pip install jellyfish")

try:
    from rapidfuzz.distance import Levenshtein as _LEV
except ImportError:
    sys.exit("Missing dependency: pip install rapidfuzz")


# ---------------------------------------------------------------------------
# ILCSS — Python port of ILCSS_sim.cr
# ---------------------------------------------------------------------------

def _longest_common_substrings(s1: str, s2: str) -> list[str]:
    """Return all maximum-length common substrings of s1 and s2."""
    n, m = len(s1), len(s2)
    prev = [0] * (m + 1)
    curr = [0] * (m + 1)
    best_len = 0
    results: list[str] = []

    for i in range(1, n + 1):          # outer loop: s1
        for j in range(1, m + 1):      # inner loop: s2
            if s1[i - 1] == s2[j - 1]:
                curr[j] = prev[j - 1] + 1
                if curr[j] > best_len:
                    best_len = curr[j]
                    results = [s1[i - best_len: i]]
                elif curr[j] == best_len:
                    results.append(s1[i - best_len: i])
        prev, curr = curr, [0] * (m + 1)

    return results


def ilcss_sim(s1: str, s2: str, threshold: int = 3) -> float:
    """
    ILCSS similarity between s1 and s2.

    Strips internal whitespace so that multi-part names are compared as
    a single character sequence, then iteratively extracts the longest
    common substrings, applying a positional penalty to each block.
    Blocks shorter than `threshold` characters are discarded.
    """
    str1 = s1.replace(" ", "")
    str2 = s2.replace(" ", "")

    strlen_max = max(len(str1), len(str2))
    if strlen_max == 0:
        return 1.0

    tot_score = 0.0

    while True:
        blocks = _longest_common_substrings(str1, str2)
        if not blocks:
            break
        block_len = len(blocks[0])
        if block_len < threshold:
            break

        for block in blocks:
            # Check before modifying: the same block string may appear multiple
            # times in `blocks` (duplicate DP cells) but only once in one of
            # the strings; skip rather than crash.
            pos1 = str1.find(block)
            pos2 = str2.find(block)
            if pos1 == -1 or pos2 == -1:
                continue
            str1 = str1[:pos1] + "{" * block_len + str1[pos1 + block_len:]
            str2 = str2[:pos2] + "}" * block_len + str2[pos2 + block_len:]

            distance        = abs(pos2 - pos1)
            dist_ratio      = distance / strlen_max
            len_ratio       = block_len / strlen_max
            penalty_ratio   = dist_ratio * (1.0 - len_ratio)
            tot_score      += block_len * (1.0 - penalty_ratio)

    return tot_score / strlen_max


# ---------------------------------------------------------------------------
# Competing algorithms
# ---------------------------------------------------------------------------

def norm_levenshtein(s1: str, s2: str) -> float:
    """Normalized Levenshtein: 1 - edit_dist / max(len1, len2)."""
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0
    return 1.0 - _LEV.distance(s1, s2) / max_len


def jaro_winkler(s1: str, s2: str) -> float:
    return jellyfish.jaro_winkler_similarity(s1, s2)


def ratcliff_obershelp(s1: str, s2: str) -> float:
    return difflib.SequenceMatcher(None, s1, s2).ratio()


# ---------------------------------------------------------------------------
# Base names — covering Arabic, Hispanic, Portuguese, and European structures
# ---------------------------------------------------------------------------

# Each entry: (name_string, culture, n_parts)
BASE_NAMES: list[tuple[str, str, int]] = [
    # Arabic — 3 components (given + father + grandfather)
    ("abdullah abdel aziz",      "Arabic",    3),
    ("ahmad khalil hassan",      "Arabic",    3),
    ("mohamed ali ibrahim",      "Arabic",    3),
    ("omar saeed rashid",        "Arabic",    3),
    # Arabic — 4 components
    ("ahmed khalid saleh mansour", "Arabic",  4),
    # Hispanic — nombre + 2 apellidos
    ("juan garcia lopez",        "Hispanic",  3),
    ("maria martinez fernandez", "Hispanic",  3),
    ("carlos rodriguez perez",   "Hispanic",  3),
    # Portuguese — nome + 2 apelidos
    ("joao silva ferreira",      "Portuguese",3),
    ("ana costa rodrigues",      "Portuguese",3),
    # Hispanic 4-part (nombre compuesto + 2 apellidos)
    ("juan carlos garcia lopez",         "Hispanic",  4),
    ("maria jose martinez fernandez",    "Hispanic",  4),
    ("luis miguel rodriguez perez",      "Hispanic",  4),
    # Hispanic 2-part (nombre + 1 apellido — informal/foreign contexts)
    ("carmen lopez",             "Hispanic",  2),
    ("luis garcia",              "Hispanic",  2),
    ("rosa perez",               "Hispanic",  2),
    # Portuguese 2-part (nome + 1 apelido)
    ("pedro silva",              "Portuguese",2),
    ("lucia ferreira",           "Portuguese",2),
    # European 2-part
    ("mario rossi",              "Italian",   2),
    ("anna ferrari",             "Italian",   2),
    ("pierre dupont",            "French",    2),
    ("hans mueller",             "German",    2),
]

# ---------------------------------------------------------------------------
# Variation generators
# ---------------------------------------------------------------------------

def permutations_of(parts: list[str]) -> list[tuple[str, list[str]]]:
    """Return all non-identity permutations as (label, parts) pairs."""
    result = []
    for perm in itertools.permutations(parts):
        if list(perm) != parts:
            label = "perm_" + "_".join(str(parts.index(p) + 1) for p in perm)
            result.append((label, list(perm)))
    return result


def generate_pairs(base: str, culture: str, n_parts: int,
                   all_bases: list[tuple[str, str, int]]) -> list[dict]:
    parts = base.split()
    rows = []

    def add(name2, variation):
        rows.append({
            "name1": base, "name2": name2,
            "variation": variation,
            "culture": culture,
            "same_person": 1,
        })

    # identity
    add(base, "identity")

    # all non-identity permutations
    for label, perm in permutations_of(parts):
        add(" ".join(perm), label)

    # drop one component (only for n_parts >= 3)
    if n_parts >= 3:
        for i in range(n_parts):
            dropped = parts[:i] + parts[i + 1:]
            pos_label = ["drop_first", "drop_middle", "drop_last"][i] if n_parts == 3 \
                        else f"drop_{i + 1}"
            add(" ".join(dropped), pos_label)

    # insert extra component (only for 2-part names)
    if n_parts == 2:
        add(parts[0] + " el " + parts[1], "insert_middle")
        add(parts[0] + " " + parts[1] + " jr",  "append_suffix")

    # negative examples: pair with 3 randomly chosen different base names
    others = [(b, c) for b, c, _ in all_bases if b != base]
    # pick the first, middle, and last to get cultural spread
    step = max(1, len(others) // 3)
    for b2, c2 in others[::step][:3]:
        rows.append({
            "name1": base, "name2": b2,
            "variation": f"negative ({culture} vs {c2})",
            "culture": culture,
            "same_person": 0,
        })

    return rows


# ---------------------------------------------------------------------------
# Build dataset and compute scores
# ---------------------------------------------------------------------------

def build_dataset() -> list[dict]:
    pairs = []
    for base, culture, n_parts in BASE_NAMES:
        pairs.extend(generate_pairs(base, culture, n_parts, BASE_NAMES))
    return pairs


def score_pair(row: dict) -> dict:
    s1, s2 = row["name1"], row["name2"]
    return {
        **row,
        "ilcss":    round(ilcss_sim(s1, s2),          4),
        "norm_lev": round(norm_levenshtein(s1, s2),    4),
        "jaro_wkl": round(jaro_winkler(s1, s2),        4),
        "ratcliff": round(ratcliff_obershelp(s1, s2),  4),
    }


# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------

ALGO_COLS = ["ilcss", "norm_lev", "jaro_wkl", "ratcliff"]
ALGO_LABELS = {
    "ilcss":    "ILCSS",
    "norm_lev": "NormLev",
    "jaro_wkl": "JaroWinkler",
    "ratcliff": "Ratcliff/Ob",
}

# Canonical variation order for the summary
VARIATION_ORDER = [
    "identity",
    "perm_2_1",                          # 2-part swap
    "perm_2_1_3", "perm_3_1_2",         # 3-part rotations
    "perm_3_2_1", "perm_1_3_2",         # 3-part reversals / others
    "perm_2_3_1",
    "drop_first", "drop_middle", "drop_last",
    "insert_middle", "append_suffix",
]


def summarize(rows: list[dict]) -> None:
    # group by variation
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r["variation"]].append(r)

    col_w = 13
    header = f"{'Variation':<28}" + "".join(f"{ALGO_LABELS[c]:>{col_w}}" for c in ALGO_COLS) + f"{'N':>5}"
    print()
    print("Mean similarity score by variation type")
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    def sort_key(var):
        if var in VARIATION_ORDER:
            return (0, VARIATION_ORDER.index(var))
        elif var.startswith("perm_"):
            return (1, var)
        elif var.startswith("negative"):
            return (3, var)
        else:
            return (2, var)

    for var in sorted(groups.keys(), key=sort_key):
        grp = groups[var]
        n = len(grp)
        means = {c: sum(r[c] for r in grp) / n for c in ALGO_COLS}
        label = var[:27]
        print(f"{label:<28}" + "".join(f"{means[c]:>{col_w}.4f}" for c in ALGO_COLS) + f"{n:>5}")

    print("=" * len(header))
    print()

    # same-person vs different-person summary
    same    = [r for r in rows if r["same_person"] == 1 and r["variation"] != "identity"]
    diff    = [r for r in rows if r["same_person"] == 0]
    identity = [r for r in rows if r["variation"] == "identity"]

    print(f"{'Category':<28}" + "".join(f"{ALGO_LABELS[c]:>{col_w}}" for c in ALGO_COLS) + f"{'N':>5}")
    print("-" * len(header))
    for label, grp in [("identity (baseline)", identity),
                        ("same person (all variants)", same),
                        ("different person (negative)", diff)]:
        n = len(grp)
        if n == 0:
            continue
        means = {c: sum(r[c] for r in grp) / n for c in ALGO_COLS}
        print(f"{label[:27]:<28}" + "".join(f"{means[c]:>{col_w}.4f}" for c in ALGO_COLS) + f"{n:>5}")
    print("=" * len(header))
    print()


# ---------------------------------------------------------------------------
# Threshold analysis: precision, recall, F1 at each candidate threshold
# ---------------------------------------------------------------------------

def threshold_analysis(rows: list[dict]) -> None:
    """
    For each algorithm, sweep decision thresholds and report precision,
    recall, F1, and accuracy. Positive class = same_person (1).
    Identity pairs are excluded: they are trivially correct for all methods.
    """
    working = [r for r in rows if r["variation"] != "identity"]
    n_pos = sum(1 for r in working if r["same_person"] == 1)
    n_neg = sum(1 for r in working if r["same_person"] == 0)

    thresholds = [round(t / 20, 2) for t in range(1, 20)]   # 0.05 … 0.95

    print(f"Threshold analysis (positive = same person, N+={n_pos}, N-={n_neg})")
    print("(identity pairs excluded; best F1 per algorithm highlighted with *)")
    print()

    for algo in ALGO_COLS:
        print(f"  {ALGO_LABELS[algo]}")
        print(f"  {'Threshold':>10}  {'Precision':>10}  {'Recall':>10}  {'F1':>10}  {'Accuracy':>10}")
        print(f"  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*10}")

        best_f1, best_t = -1.0, None
        rows_out = []
        for t in thresholds:
            tp = sum(1 for r in working if r["same_person"] == 1 and r[algo] >= t)
            fp = sum(1 for r in working if r["same_person"] == 0 and r[algo] >= t)
            fn = sum(1 for r in working if r["same_person"] == 1 and r[algo] <  t)
            tn = sum(1 for r in working if r["same_person"] == 0 and r[algo] <  t)
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec  = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1   = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
            acc  = (tp + tn) / (n_pos + n_neg)
            if f1 > best_f1:
                best_f1, best_t = f1, t
            rows_out.append((t, prec, rec, f1, acc))

        for t, prec, rec, f1, acc in rows_out:
            marker = " *" if t == best_t else "  "
            print(f"  {t:>10.2f}  {prec:>10.4f}  {rec:>10.4f}  {f1:>10.4f}  {acc:>10.4f}{marker}")
        print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(out_dir, "results.csv")

    print("Building synthetic dataset and computing scores...")
    dataset = build_dataset()
    scored  = [score_pair(r) for r in dataset]

    fieldnames = ["name1", "name2", "variation", "culture", "same_person",
                  "ilcss", "norm_lev", "jaro_wkl", "ratcliff"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(scored)

    print(f"Results saved to: {csv_path}")
    print(f"Total pairs: {len(scored)}")
    summarize(scored)
    threshold_analysis(scored)


if __name__ == "__main__":
    main()
