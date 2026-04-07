#!/usr/bin/env python3
"""
eval_real.py — ILCSS evaluation on real-world datasets:
  1. DBLP-ACM (Leipzig benchmark, CC BY 4.0): publication record matching;
     author name strings compared pair-wise.
  2. FEBRL dataset1 (BSD-3): synthetic record linkage with controlled corruptions
     including given-name / surname field swaps.

Requires:
  pip install jellyfish rapidfuzz
"""

import csv
import difflib
import os
import re
import sys
from collections import defaultdict

try:
    import jellyfish
except ImportError:
    sys.exit("pip install jellyfish")
try:
    from rapidfuzz.distance import Levenshtein as _LEV
except ImportError:
    sys.exit("pip install rapidfuzz")

# ---------------------------------------------------------------------------
# Paste ILCSS + competitors from eval_ilcss.py (kept in sync)
# ---------------------------------------------------------------------------

def _longest_common_substrings(s1: str, s2: str) -> list[str]:
    n, m = len(s1), len(s2)
    prev = [0] * (m + 1)
    curr = [0] * (m + 1)
    best_len = 0
    results: list[str] = []
    for i in range(1, n + 1):
        for j in range(1, m + 1):
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
    str1 = s1.replace(" ", "")
    str2 = s2.replace(" ", "")
    strlen_max = max(len(str1), len(str2))
    if strlen_max == 0:
        return 1.0
    tot_score = 0.0
    while True:
        blocks = _longest_common_substrings(str1, str2)
        if not blocks or len(blocks[0]) < threshold:
            break
        block_len = len(blocks[0])
        for block in blocks:
            pos1 = str1.find(block)
            pos2 = str2.find(block)
            if pos1 == -1 or pos2 == -1:
                continue
            str1 = str1[:pos1] + "{" * block_len + str1[pos1 + block_len:]
            str2 = str2[:pos2] + "}" * block_len + str2[pos2 + block_len:]
            dist_ratio    = abs(pos2 - pos1) / strlen_max
            len_ratio     = block_len / strlen_max
            penalty_ratio = dist_ratio * (1.0 - len_ratio)
            tot_score    += block_len * (1.0 - penalty_ratio)
    return tot_score / strlen_max


def norm_levenshtein(s1: str, s2: str) -> float:
    ml = max(len(s1), len(s2))
    return 0.0 if ml == 0 else 1.0 - _LEV.distance(s1, s2) / ml


def jaro_winkler(s1: str, s2: str) -> float:
    return jellyfish.jaro_winkler_similarity(s1, s2)


def ratcliff_obershelp(s1: str, s2: str) -> float:
    return difflib.SequenceMatcher(None, s1, s2).ratio()


ALGOS = ["ilcss", "norm_lev", "jaro_wkl", "ratcliff"]
LABELS = {"ilcss": "ILCSS", "norm_lev": "NormLev",
          "jaro_wkl": "JaroWinkler", "ratcliff": "Ratcliff/Ob"}


def score(s1, s2):
    return {
        "ilcss":    round(ilcss_sim(s1, s2),         4),
        "norm_lev": round(norm_levenshtein(s1, s2),   4),
        "jaro_wkl": round(jaro_winkler(s1, s2),       4),
        "ratcliff": round(ratcliff_obershelp(s1, s2), 4),
    }


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def mean(values):
    return sum(values) / len(values) if values else float("nan")


def f1_at_threshold(rows, algo, t):
    tp = sum(1 for r in rows if r["same_person"] == 1 and r[algo] >= t)
    fp = sum(1 for r in rows if r["same_person"] == 0 and r[algo] >= t)
    fn = sum(1 for r in rows if r["same_person"] == 1 and r[algo] <  t)
    tn = sum(1 for r in rows if r["same_person"] == 0 and r[algo] <  t)
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec  = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1   = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    acc  = (tp + tn) / len(rows)
    return prec, rec, f1, acc


def best_threshold(rows, algo):
    best = (-1, 0, 0, 0, 0)
    for t_int in range(1, 20):
        t = t_int / 20
        p, r, f, a = f1_at_threshold(rows, algo, t)
        if f > best[1]:
            best = (t, f, p, r, a)
    return best   # (threshold, f1, precision, recall, accuracy)


def print_summary(title, rows):
    same = [r for r in rows if r["same_person"] == 1]
    diff = [r for r in rows if r["same_person"] == 0]
    col  = 14
    hdr  = f"{'':30}" + "".join(f"{LABELS[a]:>{col}}" for a in ALGOS)
    print(f"\n{'-' * len(hdr)}")
    print(title)
    print('-' * len(hdr))
    print(hdr)
    print('-' * len(hdr))
    for label, grp in [("same person", same), ("different person", diff)]:
        if not grp:
            continue
        n = len(grp)
        print(f"  {label} (N={n})".ljust(30) +
              "".join(f"{mean([r[a] for r in grp]):>{col}.4f}" for a in ALGOS))
    gap = {a: mean([r[a] for r in same]) - mean([r[a] for r in diff]) for a in ALGOS}
    print(f"  {'gap (same-diff)':28}" +
          "".join(f"{gap[a]:>{col}.4f}" for a in ALGOS))
    print('-' * len(hdr))
    print(f"\n  Optimal threshold (best F1, identity pairs excluded):")
    print(f"  {'':10}{'thr':>7}  {'F1':>8}  {'Precision':>10}  {'Recall':>8}  {'Accuracy':>10}")
    for a in ALGOS:
        t, f1, p, r, acc = best_threshold(rows, a)
        print(f"  {LABELS[a]:10}{t:>7.2f}  {f1:>8.4f}  {p:>10.4f}  {r:>8.4f}  {acc:>10.4f}")
    print()


# ---------------------------------------------------------------------------
# Dataset 1 — DBLP-ACM
# ---------------------------------------------------------------------------

def normalize_authors(raw: str) -> str:
    """Lower-case, collapse whitespace, strip initials like 'A.'."""
    s = raw.lower().strip()
    s = re.sub(r'\b[a-z]\.\s*', '', s)      # remove single-letter initials
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


def load_dblp_acm(data_dir: str) -> list[dict]:
    def load_csv(path, id_field, author_field, encoding="utf-8"):
        rows = {}
        with open(path, encoding=encoding, errors="replace") as f:
            for row in csv.DictReader(f):
                rows[row[id_field].strip('"')] = row[author_field].strip('"')
        return rows

    dblp = load_csv(os.path.join(data_dir, "DBLP2.csv"),  "id", "authors", "latin-1")
    acm  = load_csv(os.path.join(data_dir, "ACM.csv"),    "id", "authors", "ascii")

    pairs = []
    with open(os.path.join(data_dir, "DBLP-ACM_perfectMapping.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            dblp_id = row["idDBLP"].strip('"')
            acm_id  = row["idACM"].strip('"')
            a1 = normalize_authors(dblp.get(dblp_id, ""))
            a2 = normalize_authors(acm.get(acm_id,  ""))
            if not a1 or not a2:
                continue
            s = score(a1, a2)
            pairs.append({
                "name1": a1, "name2": a2,
                "same_person": 1,
                "token_order_differs": sorted(a1.split(",")) == sorted(a2.split(",")),
                **s
            })
    return pairs


def eval_dblp_acm(data_dir: str, out_csv: str):
    print("Loading DBLP-ACM...")
    matched = load_dblp_acm(data_dir)
    print(f"  Matched pairs loaded: {len(matched)}")

    # Build non-matched pairs: pair each DBLP record with a random ACM record
    # that is NOT its match. Use every 10th matched pair to keep it tractable.
    non_matched = []
    n = len(matched)
    for i in range(0, n, 10):
        j = (i + n // 3) % n           # deliberately misaligned index
        a1 = matched[i]["name1"]
        a2 = matched[j]["name2"]
        if a1 == a2:
            continue
        s = score(a1, a2)
        non_matched.append({"name1": a1, "name2": a2, "same_person": 0,
                             "token_order_differs": False, **s})

    all_rows = matched + non_matched

    # Subset: pairs where the token SET is the same but ORDER differs
    reordered = [r for r in matched
                 if sorted(r["name1"].split()) != sorted(r["name2"].split())
                 and set(r["name1"].split()) == set(r["name2"].split())]

    fieldnames = ["name1", "name2", "same_person"] + ALGOS
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=fieldnames,
                       extrasaction="ignore").writerows(all_rows)

    print_summary("DBLP-ACM: all matched pairs vs. non-matched", all_rows)
    if reordered:
        print(f"  Subset: same author tokens, different order — N={len(reordered)}")
        for a in ALGOS:
            print(f"    {LABELS[a]:12}: mean = {mean([r[a] for r in reordered]):.4f}")
        print()


# ---------------------------------------------------------------------------
# Dataset 2 — FEBRL dataset1
# ---------------------------------------------------------------------------

def load_febrl(path: str) -> list[dict]:
    rows = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f, skipinitialspace=True):
            rec_id = row["rec_id"].strip()
            gn = row["given_name"].strip().lower()
            sn = row["surname"].strip().lower()
            rows[rec_id] = (gn, sn)

    pairs = []
    seen = set()
    for rec_id, (gn, sn) in rows.items():
        # rec-N-org  <->  rec-N-dup-0
        if not rec_id.endswith("-org"):
            continue
        base = rec_id[:-4]          # strip "-org"
        dup_id = base + "-dup-0"
        if dup_id not in rows:
            continue
        gn2, sn2 = rows[dup_id]

        full1 = f"{gn} {sn}".strip()
        full2 = f"{gn2} {sn2}".strip()

        swapped = (gn == sn2 and sn == gn2)
        s = score(full1, full2)
        pairs.append({"name1": full1, "name2": full2,
                      "same_person": 1, "swap": swapped, **s})

    # Non-matched: pair org records with a distant dup record
    org_ids = [rid for rid in rows if rid.endswith("-org")]
    non_matched = []
    n = len(org_ids)
    for i in range(0, n, 5):
        j = (i + n // 2) % n
        id1, id2 = org_ids[i], org_ids[j]
        if id1 == id2:
            continue
        full1 = "{} {}".format(*rows[id1]).strip()
        full2 = "{} {}".format(*rows[id2]).strip()
        s = score(full1, full2)
        non_matched.append({"name1": full1, "name2": full2,
                             "same_person": 0, "swap": False, **s})

    return pairs + non_matched


def eval_febrl(path: str, out_csv: str):
    print("Loading FEBRL dataset1...")
    all_rows = load_febrl(path)
    matched  = [r for r in all_rows if r["same_person"] == 1]
    swapped  = [r for r in matched  if r["swap"]]
    print(f"  Matched pairs: {len(matched)}  (of which given/surname swapped: {len(swapped)})")
    print(f"  Non-matched pairs: {sum(1 for r in all_rows if r['same_person'] == 0)}")

    fieldnames = ["name1", "name2", "same_person", "swap"] + ALGOS
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=fieldnames,
                       extrasaction="ignore").writerows(all_rows)

    print_summary("FEBRL dataset1: all matched pairs vs. non-matched", all_rows)

    if swapped:
        print(f"  Subset: given/surname swapped pairs (N={len(swapped)})")
        for a in ALGOS:
            print(f"    {LABELS[a]:12}: mean = {mean([r[a] for r in swapped]):.4f}")
        print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))

def main():
    eval_dblp_acm(
        data_dir = os.path.join(EVAL_DIR, "DBLP-ACM"),
        out_csv  = os.path.join(EVAL_DIR, "results_dblp_acm.csv"),
    )
    eval_febrl(
        path    = os.path.join(EVAL_DIR, "FEBRL_dataset1.csv"),
        out_csv = os.path.join(EVAL_DIR, "results_febrl.csv"),
    )


if __name__ == "__main__":
    main()
