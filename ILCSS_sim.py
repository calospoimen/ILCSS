#!/usr/bin/env python3
"""
ILCSS_sim.py — Iterative Longest Common SubStrings Similarity

Reference implementation in Python.
See also: ILCSS_sim.pl (Perl), ILCSS_sim.cr (Crystal)

Preprint: https://doi.org/10.5281/zenodo.19462182
"""


def _longest_common_substrings(s1: str, s2: str) -> list[str]:
    """Return all maximum-length common substrings of s1 and s2."""
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
    """
    ILCSS similarity between s1 and s2.

    Strips internal whitespace so that multi-part names are compared as
    a single character sequence, then iteratively extracts the longest
    common substrings, applying a positional penalty to each block.
    Blocks shorter than `threshold` characters are discarded.

    Returns a value in [0, 1). Recommended matching threshold: 0.40.
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
            pos1 = str1.find(block)
            pos2 = str2.find(block)
            if pos1 == -1 or pos2 == -1:
                continue
            str1 = str1[:pos1] + "{" * block_len + str1[pos1 + block_len:]
            str2 = str2[:pos2] + "}" * block_len + str2[pos2 + block_len:]

            distance      = abs(pos2 - pos1)
            dist_ratio    = distance / strlen_max
            len_ratio     = block_len / strlen_max
            penalty_ratio = dist_ratio * (1.0 - len_ratio)
            tot_score    += block_len * (1.0 - penalty_ratio)

    return tot_score / strlen_max


if __name__ == "__main__":
    examples = [
        ("abdullah abdel aziz",   "aziz abdullah abdel"),
        ("juan garcia lopez",     "garcia lopez juan"),
        ("mario rossi",           "rossi mario"),
        ("ahmed khalid saleh mansour", "khalid mansour ahmed saleh"),
        ("mario rossi",           "luigi ferrari"),
    ]
    print(f"{'Name 1':<35} {'Name 2':<35} {'ILCSS':>7}")
    print("-" * 79)
    for s1, s2 in examples:
        print(f"{s1:<35} {s2:<35} {ilcss_sim(s1, s2):>7.4f}")
