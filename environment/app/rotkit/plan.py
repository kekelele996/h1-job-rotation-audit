"""由第 k 轮结束后的岗位对照表反推单轮换位表。

一轮换位就是一个置换。同一个置换连着作用 k 次，原来一个长圈会被拆成若干个
等长的圈，所以反过来看，对照表里长度相同的圈可以并回一个长圈。这里按"每 k 个
同长圈并成一个"来推算：只有每种长度的圈数都是轮次数 k 的整数倍，这张对照表
才可能由某张换位表排出来。

岗位沿走廊按编号排开，一次交接从 p 号岗位到 q 号岗位的路程是 |p - q|，
一张换位表的总路程是 sum(|root[p] - p|)。
"""

from __future__ import annotations

from math import factorial

from . import perm


def exists_root(after, rounds):
    """每种长度的圈数都能被轮次数整除时，认为对照表可以复原。"""
    return all(count % rounds == 0 for count in perm.cycle_counts(after).values())


def count_roots(after, rounds):
    """每种长度按"每 rounds 个圈并成一个长圈"计数，再把各长度乘起来。"""
    total = 1
    for length, count in perm.cycle_counts(after).items():
        if count % rounds:
            return 0
        groups = count // rounds
        splits = factorial(count) // (factorial(rounds) ** groups * factorial(groups))
        per_group = factorial(rounds - 1) * length ** (rounds - 1)
        total *= splits * per_group ** groups
    return total


def build_root(after, rounds):
    """把同长的圈按顺序每 rounds 个接成一个大圈，得到一张换位表。"""
    if not exists_root(after, rounds):
        return None
    root = [None] * len(after)
    for length in perm.cycle_counts(after):
        same = [walk for walk in perm.cycles(after) if len(walk) == length]
        for start in range(0, len(same), rounds):
            block = same[start:start + rounds]
            flat = [post for walk in block for post in walk]
            size = len(flat)
            for i in range(size):
                root[flat[i]] = flat[(i + 1) % size]
    return root


def min_cost(after, rounds):
    """报出这张换位表的总路程。"""
    root = build_root(after, rounds)
    if root is None:
        return None
    return sum(abs(root[post] - post) for post in range(len(root)))
