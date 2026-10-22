"""由第 k 轮结束后的岗位对照表反推单轮换位表。

约定
----
``after[i]`` 是起点在 i 号岗位的人，按同一张换位表执行 ``rounds`` 轮之后所在的岗位。
``root[p]`` 是 p 号岗位上的人下一轮去的岗位，``root`` 必须是一个置换。

圈怎么拆
--------
单轮换位表 ``root`` 里一个长 ``L`` 的圈，如果把它写成
``y[0] -> y[1] -> ... -> y[L-1] -> y[0]``，那么 ``root`` 作用 ``rounds`` 次就是
沿这个圈每次跳 ``rounds`` 格。令 ``g = gcd(L, rounds)``、``m = L / g``，跳
``rounds`` 格会把长圈拆成 ``g`` 个长度 ``m`` 的圈，跳的步长在圈内化成
``rounds/g`` 格。

反过来拼
--------
对照表里同一长度 ``m`` 的若干个圈，要拼回 ``root`` 的长圈。一组 ``g`` 个同长圈
对应 ``root`` 的一个长 ``m*g`` 圈，前提有三条：

1. ``g`` 整除 ``rounds``（长圈长度 ``m*g`` 决定拆出的份数）；
2. ``gcd(rounds/g, m) = 1``（否则 ``gcd(m*g, rounds)`` 会大于 ``g``，拆出来不是 ``g`` 份）；
3. ``m*g > rounds``。这一条来自内控口径：从某一轮出发、连同出发那一轮算起，
   连续 ``rounds`` 轮不能重复落位，等价于 ``root`` 每个圈的长度都大于 ``rounds``。

一组 ``g`` 个给定的圈能拼出的不同长圈数是 ``(g-1)! * m**(g-1)``：``g`` 个圈在组内
的先后有 ``(g-1)!`` 种排法，除第一个圈外每个圈可以整体错开 ``m`` 种相位。

计数
----
各长度互相独立，总张数等于各长度方案数的乘积。同一长度内把 ``count`` 个圈分成若干组，
按组大小做一次背包：

    ways[t] = sum over g, j of  C(t, g*j) * ways[t - g*j] * W(g, j)

``W(g, j)`` 是把 ``g*j`` 个圈分成 ``j`` 个无序组、每组 ``g`` 个、再乘上组内排法：

    W(g, j) = (g*j)! / ((g!)**j * j!) * ((g-1)! * m**(g-1))**j

拼出一张具体的换位表
--------------------
一组 ``g`` 个圈 ``c[0..g-1]``（每个长 ``m``）拼成长 ``m*g`` 的圈：令
``s = rounds/g``、``inv`` 为 ``s`` 在模 ``m`` 下的逆，把第 ``r`` 个圈的元素按
``y[r + g*t] = c[r][(t*inv) mod m]`` 摆进长圈，再令 ``root`` 沿 ``y`` 每次走一格。
这样 ``root**rounds`` 恰好等于 ``after``，且长圈长度 ``m*g > rounds``。
"""

from __future__ import annotations

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


def _grouping_plan(count, length, rounds):
    """找出一种把 count 个同长圈分组的方案，返回各组的圈数。"""
    sizes = allowed_group_sizes(length, rounds)
    reached = {0: []}
    frontier = [0]
    while frontier:
        following = []
        for used in frontier:
            for size in sizes:
                step = used + size
                if step <= count and step not in reached:
                    reached[step] = reached[used] + [size]
                    following.append(step)
        frontier = following
    return reached.get(count)


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


def build_root(after, rounds):
    """给出一张符合内控要求的单轮换位表；不存在时返回 None。"""
    root = [None] * len(after)
    for length in sorted(perm.cycle_counts(after)):
        same = [walk for walk in perm.cycles(after) if len(walk) == length]
        plan = _grouping_plan(len(same), length, rounds)
        if plan is None:
            return None
        taken = 0
        for size in plan:
            group = same[taken:taken + size]
            taken += size
            step = rounds // size
            back = _inverse(step, length)
            order = [None] * (length * size)
            for slot in range(size):
                for offset in range(length):
                    order[slot + size * offset] = group[slot][(offset * back) % length]
            span = length * size
            for i in range(span):
                root[order[i]] = order[(i + 1) % span]
    return root
