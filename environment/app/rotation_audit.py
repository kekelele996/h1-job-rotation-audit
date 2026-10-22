#!/usr/bin/env python3
"""轮岗换位复核入口：读一张岗位对照表，写一行 JSON。

用法：
    python3 /app/rotation_audit.py <对照表.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from rotkit import perm, plan

USAGE = "用法：python3 /app/rotation_audit.py <对照表.json>"


def load_table(path):
    """读对照表并校验；返回 (rounds, after) 或 (None, 错误说明)。"""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        return None, f"读不到文件（{exc}）"
    except ValueError as exc:
        return None, f"不是合法 JSON（{exc}）"
    if not isinstance(data, dict):
        return None, "顶层必须是对象"
    rounds = data.get("rounds")
    after = data.get("after")
    if isinstance(rounds, bool) or not isinstance(rounds, int) or not 1 <= rounds <= 12:
        return None, "rounds 必须是 1 到 12 的整数"
    if not isinstance(after, list) or not after:
        return None, "after 必须是非空数组"
    if any(isinstance(post, bool) or not isinstance(post, int) for post in after):
        return None, "after 里的岗位编号必须是整数"
    if not perm.is_permutation(after):
        return None, "after 必须是岗位编号的一个排列"
    return (rounds, after), None


def main(argv):
    if len(argv) != 2:
        print(USAGE, file=sys.stderr)
        return 2
    table, problem = load_table(argv[1])
    if table is None:
        print(f"对照表不合法：{problem}", file=sys.stderr)
        return 2
    rounds, after = table
    found = plan.exists_root(after, rounds)
    root = plan.build_root(after, rounds) if found else None
    result = {
        "exists": found,
        "root_count": plan.count_roots(after, rounds),
        "root": root,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
