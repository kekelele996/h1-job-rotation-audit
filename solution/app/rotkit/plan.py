"""由第 k 轮结束后的岗位对照表反推单轮换位表。

约定
----
``after[i]`` 是扫描仪坐标系里 i 号岗位的记录。扫描仪每次上电的零点随机：设真实岗位
编号 p 在扫描仪上的编号是 ``(p + 偏移) mod n``，那么记录到的是

    after(q) = 真实换位表^k (q - 偏移) + 偏移

反过来，对某个偏移 o，真实坐标系里的 k 次幂是 ``target(p) = after(p + o) - o``。
哪个 o 是对的并不知道，所以要把所有 o 的结果并起来，同一张表只算一次。

内控口径：从某一轮出发、连同出发那一轮算起，连续 k 轮不重复落位，等价于换位表每个圈
的长度都大于 k。岗位沿走廊编号，总路程是 ``sum_p |root[p] - p|``。

怎么推
------
置换 ρ 的一个长 L 圈，k 次幂后拆成 ``gcd(L, k)`` 个长 ``L/gcd(L,k)`` 的圈。反过来，对照表里
同一长度 m 的一组 g 个圈能拼回 ρ 的一个长 m*g 圈，条件是 ``g | k``、``gcd(k/g, m) = 1``、
``m*g > k``；一组的拼法有 ``(g-1)! * m**(g-1)`` 种。

实现上对每个偏移 o 把观测转回真实坐标（``target_o(p) = after(p + o) - o``），枚举它的全部
合规根，再对所有偏移取并集；同一张表只算一次。
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


def _group_variants(length, size, group, rounds):
    """一组圈能拼出的所有长圈（只保留不同的映射）。"""
    step = rounds // size
    back = _inverse(step, length)
    span = length * size
    found = {}
    for order in itertools.permutations(range(size)):
        for offsets in itertools.product(range(length), repeat=max(0, size - 1)):
            shift = (0,) + offsets
            slots = [None] * span
            for slot in range(size):
                cycle = group[order[slot]]
                for offset in range(length):
                    slots[slot + size * offset] = cycle[(offset * back + shift[slot]) % length]
            found[tuple(slots[i] for i in range(span))] = {
                slots[i]: slots[(i + 1) % span] for i in range(span)
            }
    return list(found.values())


def _partitions(items, sizes):
    """把 items 切成若干组，组大小取自 sizes。"""
    if not items:
        yield []
        return
    first = items[0]
    for size in sizes:
        if size > len(items):
            continue
        for rest in itertools.combinations(items[1:], size - 1):
            group = [first, *rest]
            left = [item for item in items if item not in group]
            for tail in _partitions(left, sizes):
                yield [group, *tail]


def _length_variants(length, cycles, rounds):
    """同一长度的圈能拼出的所有局部映射。"""
    sizes = allowed_group_sizes(length, rounds)
    merged = {}
    for part in _partitions(cycles, sizes):
        pieces = [_group_variants(length, len(group), group, rounds) for group in part]
        for combo in itertools.product(*pieces):
            mapping = {}
            for piece in combo:
                mapping.update(piece)
            merged[tuple(sorted(mapping.items()))] = mapping
    return list(merged.values())


def _valid_tables(target, rounds):
    """target 的全部合规根（每张表一个 tuple）。"""
    by_length = {}
    for walk in perm.cycles(target):
        by_length.setdefault(len(walk), []).append(walk)
    if not by_length:
        return []
    options = [
        _length_variants(length, cycles, rounds)
        for length, cycles in sorted(by_length.items())
    ]
    tables = set()
    for combo in itertools.product(*options):
        root = [None] * len(target)
        for piece in combo:
            for post, target_post in piece.items():
                root[post] = target_post
        tables.add(tuple(root))
    return sorted(tables)


def _rotate(table, offset):
    """把表搬到偏移 offset 的坐标系：task(p) = table(p + offset) - offset。"""
    n = len(table)
    return [(table[(p + offset) % n] - offset) % n for p in range(n)]


def _union(after, rounds):
    """所有偏移下能解释观测的合规表（真实坐标，去重）。"""
    tables = set()
    for offset in range(len(after)):
        tables.update(_valid_tables(_rotate(after, offset), rounds))
    return sorted(tables)


def cheapest_plan(after, rounds):
    """并集里总路程最小的表：返回 (总路程, root)；并集为空时返回 None。"""
    best = None
    for table in _union(after, rounds):
        cost = sum(abs(table[post] - post) for post in range(len(table)))
        if best is None or cost < best[0] or (cost == best[0] and table < best[1]):
            best = (cost, table)
    return None if best is None else (best[0], list(best[1]))


def exists_root(after, rounds):
    """判断是否存在某个偏移与一张合规换位表能解释这份记录。"""
    return bool(_union(after, rounds))


def count_roots(after, rounds):
    """数一数能解释这份记录的不同合规换位表有多少张。"""
    return len(_union(after, rounds))


def min_cost(after, rounds):
    """能解释这份记录的表里，总路程最小是多少。"""
    picked = cheapest_plan(after, rounds)
    return None if picked is None else picked[0]


def build_root(after, rounds):
    """给出并集里总路程最小的一张表；不存在时返回 None。"""
    picked = cheapest_plan(after, rounds)
    return None if picked is None else picked[1]
