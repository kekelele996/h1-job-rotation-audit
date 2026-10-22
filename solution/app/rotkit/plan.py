"""由第 k 轮结束后的岗位对照表反推单轮换位表。

约定
----
``after[i]`` 是起点在 i 号岗位的人，按同一张换位表执行 ``rounds`` 轮之后所在的岗位。
``root[p]`` 是 p 号岗位上的人下一轮去的岗位，``root`` 必须是一个置换。
岗位沿走廊按编号排开，一次交接从 p 号岗位到 q 号岗位的路程是 ``|p - q|``，
一张换位表的总路程是 ``sum(|root[p] - p|)``。

圈怎么拆
--------
单轮换位表 ``root`` 里一个长 ``L`` 的圈，写成 ``y[0] -> y[1] -> ... -> y[L-1] -> y[0]`` 之后，
``root`` 作用 ``rounds`` 次就是沿圈每次跳 ``rounds`` 格。令 ``g = gcd(L, rounds)``、
``m = L / g``，跳 ``rounds`` 格把长圈拆成 ``g`` 个长 ``m`` 的圈。

反过来拼
--------
对照表里同一长度 ``m`` 的若干个圈，要拼回 ``root`` 的长圈。一组 ``g`` 个同长圈对应一个
长 ``m*g`` 圈，前提是：

1. ``g`` 整除 ``rounds``；
2. ``gcd(rounds/g, m) = 1``，否则 ``gcd(m*g, rounds)`` 会大于 ``g``；
3. ``m*g > rounds``，来自内控口径（含起点，连续 ``rounds`` 轮不重复落位）。

一组 ``g`` 个给定的圈能拼出 ``(g-1)! * m**(g-1)`` 张不同的长圈；摆法用模逆交错：
令 ``s = rounds/g``、``inv`` 为 ``s`` 在模 ``m`` 下的逆，``y[r + g*t] = c[r][(t*inv + 偏移) mod m]``。

挑总路程最小的那张
------------------
同一长度可以按不同方式分组（如 ``k=6, m=4`` 既能六圈一组，也能两圈一组），不同分组、
不同摆法的总路程不同。各长度、各组之间元素互不相交，总路程可以直接相加，所以在每个
长度上按"取哪个圈做一组"做集合划分动态规划：

    best[mask] = min over 含有最低位元素的组 G ( 组内最小路程 + best[mask \\ G] )

组内最小路程对 ``g! * m**(g-1)`` 种摆法逐个算，规模由测试输入控制得很小。
"""

from __future__ import annotations

import itertools
from math import comb, factorial, gcd

from . import perm


def allowed_group_sizes(length, rounds):
    """长度为 length 的圈，一组允许放几个。"""
    sizes = []
    for size in range(1, rounds + 1):
        if rounds % size:
            continue
        if gcd(rounds // size, length) != 1:
            continue
        if length * size <= rounds:
            continue
        sizes.append(size)
    return sizes


def _cover_ways(count, length, rounds):
    """把 count 个长度为 length 的圈归组，返回方案数；0 表示分不出来。"""
    ways = [0] * (count + 1)
    ways[0] = 1
    for size in allowed_group_sizes(length, rounds):
        per_group = factorial(size - 1) * length ** (size - 1)
        nxt = [0] * (count + 1)
        for used in range(count + 1):
            if not ways[used]:
                continue
            groups = 0
            while used + size * groups <= count:
                block = factorial(size * groups) // (
                    factorial(size) ** groups * factorial(groups)
                )
                nxt[used + size * groups] += (
                    ways[used] * comb(used + size * groups, size * groups)
                    * block * per_group ** groups
                )
                groups += 1
        ways = nxt
    return ways[count]


def exists_root(after, rounds):
    """判断是否存在符合内控要求的单轮换位表。"""
    for length, count in perm.cycle_counts(after).items():
        if _cover_ways(count, length, rounds) == 0:
            return False
    return True


def count_roots(after, rounds):
    """数一数符合条件的单轮换位表有多少张。"""
    total = 1
    for length, count in perm.cycle_counts(after).items():
        ways = _cover_ways(count, length, rounds)
        if ways == 0:
            return 0
        total *= ways
    return total


def _inverse(value, modulus):
    """求 value 在模 modulus 下的逆（扩展欧几里得）。"""
    old_r, r = value % modulus, modulus
    old_s, s = 1, 0
    while r:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
    if old_r != 1:
        raise ValueError(f"{value} 在模 {modulus} 下没有逆")
    return old_s % modulus


def _best_group(length, size, group, rounds):
    """一组圈的最省摆法：返回 (总路程, {元素: 下一个元素})。"""
    step = rounds // size
    back = _inverse(step, length)
    span = length * size
    best = None
    for order in itertools.permutations(range(size)):
        for offsets in itertools.product(range(length), repeat=max(0, size - 1)):
            shift = (0,) + offsets
            slots = [None] * span
            for slot in range(size):
                cycle = group[order[slot]]
                for offset in range(length):
                    slots[slot + size * offset] = cycle[(offset * back + shift[slot]) % length]
            cost = sum(abs(slots[(i + 1) % span] - slots[i]) for i in range(span))
            if best is None or cost < best[0]:
                best = (cost, {slots[i]: slots[(i + 1) % span] for i in range(span)})
    return best


def _best_for_length(length, cycles, rounds):
    """同一长度的圈怎么分组最省：返回 (总路程, 合并后的映射)。"""
    count = len(cycles)
    sizes = allowed_group_sizes(length, rounds)
    if not sizes:
        return None
    full = (1 << count) - 1
    best = [None] * (1 << count)
    best[0] = (0, {})
    for mask in range(1, 1 << count):
        lowest = mask & -mask
        rest = mask ^ lowest
        subset = rest
        choice = None
        while True:
            group_mask = subset | lowest
            size = bin(group_mask).count("1")
            if size in sizes:
                members = [cycles[i] for i in range(count) if group_mask >> i & 1]
                piece = _best_group(length, size, members, rounds)
                left = best[mask ^ group_mask]
                if piece is not None and left is not None:
                    cost = left[0] + piece[0]
                    if choice is None or cost < choice[0]:
                        merged = dict(left[1])
                        merged.update(piece[1])
                        choice = (cost, merged)
            if subset == 0:
                break
            subset = (subset - 1) & rest
        best[mask] = choice
    return best[full]


def cheapest_plan(after, rounds):
    """总路程最小的合规换位表：返回 (总路程, root)；不存在时返回 None。"""
    counts = perm.cycle_counts(after)
    total = 0
    root = [None] * len(after)
    for length in sorted(counts):
        same = [walk for walk in perm.cycles(after) if len(walk) == length]
        picked = _best_for_length(length, same, rounds)
        if picked is None:
            return None
        total += picked[0]
        for post, target in picked[1].items():
            root[post] = target
    return total, root


def min_cost(after, rounds):
    """所有合规换位表里最小的总路程；不存在时返回 None。"""
    picked = cheapest_plan(after, rounds)
    return None if picked is None else picked[0]


def build_root(after, rounds):
    """给出总路程最小的那张合规换位表；不存在时返回 None。"""
    picked = cheapest_plan(after, rounds)
    return None if picked is None else picked[1]
