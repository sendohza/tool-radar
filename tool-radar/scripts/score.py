#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tool-radar 评分折算与排名。

维度满分与 references/scoring.md 保持一致；N/A 维度等比折算到 100。
用法: python score.py scores.json [-o report.md]

scores.json 示例:
{
  "tools": [
    {
      "name": "工具A",
      "repo": "owner/repo",
      "note": "一句话定位",
      "scores": {"功能": 22, "活跃": 18, "口碑": 12, "上手": 15, "架构": 8, "生态": 10},
      "na": []
    },
    {
      "name": "工具B",
      "scores": {"功能": 20, "活跃": 5, "上手": 10, "架构": 6, "生态": 5},
      "na": ["口碑"],
      "note": "口碑数据缺失"
    }
  ]
}
"""
import argparse
import io
import json
import sys

# 维度 (全名, 满分) — 与 references/scoring.md 保持一致
DIMS = [
    ("功能匹配度", 25),
    ("项目活跃/健康度", 20),
    ("用户口碑", 15),
    ("上手成本", 15),
    ("架构合理性", 10),
    ("生态/扩展", 15),
]
ALIAS = {
    "功能": "功能匹配度",
    "活跃": "项目活跃/健康度",
    "口碑": "用户口碑",
    "上手": "上手成本",
    "架构": "架构合理性",
    "生态": "生态/扩展",
}
SHORT = {full: short for short, full in ALIAS.items()}


def norm(k):
    return ALIAS.get(k, k)


def score_tool(t):
    name = t.get("name", "?")
    scores = {norm(k): v for k, v in t.get("scores", {}).items()}
    na = {norm(k) for k in t.get("na", [])}
    raw = 0.0
    denom = 0.0
    cells = {}
    for dim, full in DIMS:
        if dim in na or dim not in scores:
            cells[dim] = None
            continue
        s = scores[dim]
        if not isinstance(s, (int, float)) or not (0 <= s <= full):
            raise ValueError("%s 维度「%s」得分 %r 越界（应为 0~%s）" % (name, dim, s, full))
        raw += s
        denom += full
        cells[dim] = (s, full)
    if denom == 0:
        raise ValueError("%s 全部维度 N/A，无法折算" % name)
    scaled = raw / denom * 100
    return scaled, raw, denom, cells, na


def main():
    ap = argparse.ArgumentParser(description="tool-radar 评分折算与排名")
    ap.add_argument("input", nargs="?", help="scores JSON 文件；缺省读 stdin")
    ap.add_argument("-o", "--output", help="输出 Markdown 文件；缺省输出 stdout")
    ap.add_argument("--topic", help="调研主题，配合 --archive 输出归档 JSON")
    ap.add_argument("--archive", help="输出 archive.py 兼容的归档 JSON（top10），随后可直接 python archive.py 此文件累积归档")
    args = ap.parse_args()

    if args.input:
        src = io.open(args.input, encoding="utf-8")
        data = json.load(src)
        src.close()
    else:
        try:
            sys.stdin.reconfigure(encoding="utf-8")
        except Exception:
            pass
        data = json.load(sys.stdin)

    tools = data["tools"] if isinstance(data, dict) else data

    rows = []
    for t in tools:
        scaled, raw, denom, cells, na = score_tool(t)
        func = cells.get("功能匹配度")
        func_val = func[0] if func else 0
        rows.append((scaled, func_val, t, raw, denom, cells, na))
    # 排序：折算总分降序，相同按功能匹配度降序（与 scoring.md 一致）
    rows.sort(key=lambda r: (-r[0], -r[1]))

    out = []
    out.append("# 评分排名")
    out.append("")
    head = ["排名", "工具", "总分"] + [SHORT[d] for d, _ in DIMS] + ["一句话定位"]
    out.append("| " + " | ".join(head) + " |")
    out.append("|" + "|".join(["---"] * len(head)) + "|")
    for i, (scaled, _, t, raw, denom, cells, na) in enumerate(rows, 1):
        cells_md = []
        for dim, full in DIMS:
            c = cells.get(dim)
            cells_md.append("%s/%s" % (c[0], c[1]) if c else "N/A")
        out.append("| %d | %s | %.1f | %s | %s |" % (
            i, t.get("name", ""), scaled, " | ".join(cells_md), t.get("note", "")))
    out.append("")
    out.append("## 评分明细")
    out.append("")
    for i, (scaled, _, t, raw, denom, cells, na) in enumerate(rows, 1):
        out.append("### %d. %s — %.1f 分" % (i, t.get("name", ""), scaled))
        if t.get("repo"):
            out.append("- 仓库: %s" % t["repo"])
        for dim, full in DIMS:
            c = cells.get(dim)
            out.append("  - %s: %s/%s" % (dim, c[0], c[1]) if c else "  - %s: N/A" % dim)
        na_names = ",".join(SHORT[d] for d in na) if na else "无"
        out.append("- 原始合计 %.0f / 可评满分 %.0f -> 折算 %.1f；N/A 维度: %s" % (
            raw, denom, scaled, na_names))
        if t.get("note"):
            out.append("- 定位: %s" % t["note"])
        out.append("")

    text = "\n".join(out)
    if args.output:
        io.open(args.output, "w", encoding="utf-8", newline="\n").write(text)
    else:
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
        print(text)

    if args.archive:
        arch_entries = []
        for i, (scaled, _, t, raw, denom, cells, na) in enumerate(rows[:10], 1):
            arch_entries.append({
                "rank": i,
                "name": t.get("name", ""),
                "repo": t.get("repo", ""),
                "score": round(scaled, 1),
                "note": t.get("note", ""),
            })
        arch = {"topic": args.topic or "未命名调研", "entries": arch_entries}
        io.open(args.archive, "w", encoding="utf-8", newline="\n").write(
            json.dumps(arch, ensure_ascii=False, indent=2))
        print("已输出归档 JSON -> %s（可用 python archive.py 该文件 累积归档）" % args.archive)


if __name__ == "__main__":
    main()
