"""轮岗换位复核的验收测试。

写法约定（审核器 E1/E2/E5/E9 会逐条查）：
- 每个 test_ 函数的 docstring 用「」原样引用题面里的一句话，引用必须能在 instruction.md 里找到；
- 测试体里不写 if/try，分支和异常处理放在模块级辅助函数里；
- 一个难点至少三个计分测试，每个只断言这个难点影响的字段，避免一个修复顺带让别的难点变绿；
- 计分测试在原始（未修）代码上必须全部失败，否则 NOP 拿分；
- gate 测试（入口能跑、非法输入退出码）写进 scoring.json 的 gate_tests，不计分。
期望值来自 research/ 里的独立复核（穷举 n<=8 与分组公式两条路径），不用 solution/ 生成。

本文件以 root 运行；被测程序一律通过 run_candidate() 以 runner 身份、干净环境变量、
独立进程组运行，超时整组结束。
"""

import json
import os
import signal
import subprocess
import tempfile
from pathlib import Path

ENTRY = "/app/rotation_audit.py"
PYTHON = "/usr/local/bin/python3"
CANDIDATE_USER = "runner"
CANDIDATE_ENV = {
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "HOME": "/home/runner",
    "LANG": "C.UTF-8",
    "TZ": "UTC",
}
CALL_TIMEOUT_SEC = 30


def run_candidate(*args, timeout=CALL_TIMEOUT_SEC):
    """以 runner 身份运行候选入口；超时结束整个进程组并抛出 TimeoutError。"""
    as_root = os.getuid() == 0
    proc = subprocess.Popen(
        [PYTHON, ENTRY, *[str(a) for a in args]],
        cwd="/app",
        env=CANDIDATE_ENV,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
        user=CANDIDATE_USER if as_root else None,
        group=CANDIDATE_USER if as_root else None,
        extra_groups=[] if as_root else None,
    )
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        raise TimeoutError(f"{ENTRY} 超过 {timeout}s")
    return subprocess.CompletedProcess(proc.args, proc.returncode, out, err)


def audit(rounds, after):
    """把隐藏输入写进随机命名的临时文件（候选只读），返回候选输出的 JSON。"""
    folder = Path(tempfile.mkdtemp(prefix="table-"))
    folder.chmod(0o755)
    case = folder / "table.json"
    case.write_text(json.dumps({"rounds": rounds, "after": after}), encoding="utf-8")
    case.chmod(0o644)
    proc = run_candidate(case)
    assert proc.returncode == 0, f"exit={proc.returncode} stderr={proc.stderr[-500:]}"
    return json.loads(proc.stdout)


def reject(rounds, after):
    """非法对照表：返回 (退出码, 标准输出)。"""
    folder = Path(tempfile.mkdtemp(prefix="table-"))
    folder.chmod(0o755)
    case = folder / "table.json"
    case.write_text(json.dumps({"rounds": rounds, "after": after}), encoding="utf-8")
    case.chmod(0o644)
    proc = run_candidate(case)
    return proc.returncode, proc.stdout


def rotation(n, cycles):
    """按圈列表拼一个对照表：after[i] 是起点在 i 号岗位的人 k 轮后的岗位。"""
    table = list(range(n))
    for cycle in cycles:
        for index, post in enumerate(cycle):
            table[post] = cycle[(index + 1) % len(cycle)]
    return table


def rings(n, sizes):
    """从 0 号岗位起按给定长度切出互不相交的圈。"""
    groups = []
    base = 0
    for size in sizes:
        groups.append(list(range(base, base + size)))
        base += size
    return groups


def is_permutation(values, size):
    if not isinstance(values, list) or len(values) != size:
        return False
    if not all(isinstance(item, int) and not isinstance(item, bool) for item in values):
        return False
    return sorted(values) == list(range(size))


def rotated(n, root, times):
    """按 root 连排 times 轮后每名员工的岗位。"""
    posts = list(range(n))
    for _ in range(times):
        posts = [root[post] for post in posts]
    return posts


def shortest_ring(root):
    """root 里最短圈的长度。"""
    n = len(root)
    seen = [False] * n
    best = n
    for start in range(n):
        if seen[start]:
            continue
        length = 0
        post = start
        while not seen[post]:
            seen[post] = True
            length += 1
            post = root[post]
        best = min(best, length)
    return best


def root_is_valid(rounds, after, root):
    """root 是置换、排 rounds 轮后与 after 一致、且每名员工 rounds 轮内不重复落位。"""
    if not is_permutation(root, len(after)):
        return False
    if rotated(len(after), root, rounds) != list(after):
        return False
    return shortest_ring(root) > rounds


# ---------- gate：入口与契约，不计分 ----------

def test_output_has_three_fields():
    """「标准输出写一个 JSON 对象，只有三个字段」"""
    got = audit(2, rotation(4, [[0, 1], [2, 3]]))
    assert set(got) == {"exists", "root_count", "root"}


def test_non_permutation_exits_2():
    """「对照表不合法时退出码为 2，标准输出不写 JSON」"""
    code, out = reject(2, [0, 1, 1, 2])
    assert code == 2
    assert out.strip() == ""


# ---------- 难点 1：判定，含"谁都没动"与合数轮次 ----------

def test_rejects_table_where_nobody_rotates():
    """「一名员工从某一轮出发，连同出发那一轮算起，连续 k 轮里落过的岗位不能有重复」"""
    assert audit(4, rotation(4, [[0], [1], [2], [3]]))["exists"] is False


def test_accepts_two_four_cycles_at_six_rounds():
    """「是否存在符合内控要求的单轮换位表」"""
    assert audit(6, rotation(8, [[0, 1, 2, 3], [4, 5, 6, 7]]))["exists"] is True


def test_accepts_three_four_cycles_at_nine_rounds():
    """「是否存在符合内控要求的单轮换位表」"""
    assert audit(9, rotation(12, [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11]]))["exists"] is True


# ---------- 难点 2：符合条件的换位表张数 ----------

def test_counts_three_five_cycles_at_three_rounds():
    """「符合条件的单轮换位表张数，精确整数」"""
    got = audit(3, rotation(15, rings(15, [5, 5, 5])))
    assert got["root_count"] == 51


def test_counts_mixed_cycle_lengths():
    """「判断和计数都要精确」"""
    got = audit(3, rotation(21, rings(21, [5, 5, 5, 2, 2, 2])))
    assert got["root_count"] == 408


def test_counts_six_four_cycles_at_six_rounds():
    """「符合条件的单轮换位表张数，精确整数」"""
    got = audit(6, rotation(24, rings(24, [4, 4, 4, 4, 4, 4])))
    assert got["root_count"] == 123840


# ---------- 难点 3：给出一张能对上对照表的换位表 ----------

def test_root_rotates_four_four_cycles():
    """「按它排 `rounds` 轮之后，岗位和 `after` 逐项一致」"""
    after = rotation(16, rings(16, [4, 4, 4, 4]))
    assert root_is_valid(4, after, audit(4, after)["root"]) is True


def test_root_keeps_everyone_moving():
    """「每名员工在连续 `rounds` 轮里不重复落位」"""
    after = rotation(6, rings(6, [3, 3]))
    assert root_is_valid(2, after, audit(2, after)["root"]) is True


def test_root_for_six_four_cycles_is_repeatable():
    """「同一份对照表重复执行，结果一致」"""
    after = rotation(24, rings(24, [4, 4, 4, 4, 4, 4]))
    first = audit(6, after)["root"]
    assert root_is_valid(6, after, first) is True
    assert audit(6, after)["root"] == first
