#!/usr/bin/env bash
# 参考解：把 solution/app/rotkit/plan.py 装进 /app/rotkit/plan.py。
# 三个难点各自是一个函数，留一法按函数名把对应函数退回镜像里的原写法：
#   difficulty_1  exists_root   （判定：允许的组大小与每条长度是否分得出来）
#   difficulty_2  count_roots   （计数：分组背包的权重）
#   difficulty_3  build_root    （构造：模逆交错的拼法）
# 留一法：HTB_SKIP=difficulty_1[,difficulty_2,...]；正式 Oracle 不设该变量。
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"

# 镜像里的原写法先留一份，留一法要按函数名取回。
cp /app/rotkit/plan.py /tmp/plan_original.py
install -m 0644 "$HERE/app/rotkit/plan.py" /app/rotkit/plan.py

SKIP="${HTB_SKIP:-}" /usr/local/bin/python3 - <<'PY'
import ast
import os
import sys
from pathlib import Path

FIXED = Path("/app/rotkit/plan.py")
ORIGINAL = Path("/tmp/plan_original.py")
TARGETS = {
    "difficulty_1": "exists_root",
    "difficulty_2": "count_roots",
    "difficulty_3": "build_root",
}


def function_span(path, name):
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    hits = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    if len(hits) != 1:
        sys.exit(f"{path} 里名为 {name} 的函数有 {len(hits)} 个，应为 1")
    node = hits[0]
    lines = text.splitlines(keepends=True)
    return lines, node.lineno - 1, node.end_lineno


skip = [item for item in os.environ.get("SKIP", "").split(",") if item]
unknown = sorted(set(skip) - set(TARGETS))
if unknown:
    sys.exit(f"HTB_SKIP 里有未知难点：{unknown}")

text = FIXED.read_text(encoding="utf-8")
for key in skip:
    name = TARGETS[key]
    _, old_start, old_end = function_span(FIXED, name)
    original_lines, new_start, new_end = function_span(ORIGINAL, name)
    fixed_lines = text.splitlines(keepends=True)
    if fixed_lines[old_start:old_end] == original_lines[new_start:new_end]:
        sys.exit(f"{key} 的修复片段和原写法相同，留一法不会生效")
    text = "".join(
        fixed_lines[:old_start]
        + original_lines[new_start:new_end]
        + fixed_lines[old_end:]
    )
    print(f"留一法：{key} 退回原写法（{name}）", file=sys.stderr)

FIXED.write_text(text, encoding="utf-8")
PY

chown runner:runner /app/rotkit/plan.py 2>/dev/null || true

# 装完跑一次样张，确认入口还能出三个字段。
cd /app
/usr/local/bin/python3 /app/rotation_audit.py /app/samples/S-01/table.json >/dev/null
echo "recheck entry OK" >&2
