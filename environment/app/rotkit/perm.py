"""置换的基本操作：合法性检查、圈分解、幂。

这里只做与业务无关的通用处理，不掺任何推算逻辑。
"""

from __future__ import annotations


def is_permutation(values):
    """values 是不是 0..n-1 的一个排列。"""
    if not isinstance(values, list) or not values:
        return False
    n = len(values)
    return sorted(values) == list(range(n))


def cycles(values):
    """把置换拆成圈，每个圈按 [p, values[p], ...] 的顺序列出。"""
    n = len(values)
    seen = [False] * n
    out = []
    for start in range(n):
        if seen[start]:
            continue
        walk = []
        post = start
        while not seen[post]:
            seen[post] = True
            walk.append(post)
            post = values[post]
        out.append(walk)
    return out


def cycle_counts(values):
    """每种圈长度各有多少个，返回 {长度: 个数}。"""
    counts = {}
    for walk in cycles(values):
        counts[len(walk)] = counts.get(len(walk), 0) + 1
    return counts


def power(values, times):
    """置换连乘 times 次。"""
    n = len(values)
    out = [0] * n
    for start in range(n):
        post = start
        for _ in range(times):
            post = values[post]
        out[start] = post
    return out


def shortest_cycle(values):
    """最短圈的长度；空置换返回 0。"""
    counts = cycle_counts(values)
    return min(counts) if counts else 0
