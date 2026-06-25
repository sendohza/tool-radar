#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tool-radar 调研结果累积归档。

每次调研的前10榜单追加到同一 Markdown 归档文件，自动维护：
- 目录索引：所有历次调研（序号 / 主题 / 时间 / 入榜数 / 跳转）
- 工具速查索引：同一仓库只保留最近一次调研数据（即"更新替换"）
- 调研明细段落：每次调研一张榜单表 + 可选综合评价
- 综合评价（可选 --summary）：优劣势/功能完整度/活跃更新/安装建议/本地已装

输入 JSON:
{
  "topic": "uv 类 Python 包管理器",
  "scanned_at": "2026-06-26 12:00",
  "entries": [
    {"rank":1,"name":"uv","repo":"astral-sh/uv","score":90.0,"note":"极速 Rust 包管理"}
  ]
}
综合评价(可选 --summary) JSON:
{
  "strengths": "上榜项目整体优势与劣势...",
  "features": "功能完整度评价...",
  "activity": "活跃情况与更新情况...",
  "install": "安装建议...",
  "local_installed": "本机已装类似项目清单或检测结论..."
}
用法: python archive.py result.json
      python archive.py result.json -o D:/path/research-archive.md
      python archive.py result.json --summary eval.json
"""
import argparse
import io
import json
import os
import re
import sys
from datetime import datetime

DEFAULT_ARCHIVE = os.path.join(os.path.expanduser("~"), ".tool-radar", "research-archive.md")

ROW_RE = re.compile(r"\|\s*(\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*([\d.]+)\s*\|\s*(.*?)\s*\|")
SUMMARY_KEYS = [
    ("strengths", "上榜项目优劣势"),
    ("features", "功能完整度"),
    ("activity", "活跃情况与更新情况"),
    ("install", "安装建议"),
    ("local_installed", "本地是否已安装类似项目"),
]


def cell(s):
    """转义表格单元格内容：| 会断列、换行会断行。"""
    return str(s).replace("|", "/").replace("\n", " ").replace("\r", " ")


def parse_archive(text):
    """解析已有归档，返回 (历次调研列表, summaries dict)。"""
    segs = []
    summaries = {}
    for chunk in text.split('<a id="r')[1:]:
        hm = re.match(r'(\d+)"></a>\s*\n## 调研 #\1 · (.+?) · (.+?)\n', chunk)
        if not hm:
            continue
        num = int(hm.group(1))
        topic = hm.group(2).strip()
        ts = hm.group(3).strip()
        body = chunk[hm.end():]
        # 解析综合评价段
        sm = re.search(r'<!--summary:%d-->(.*?)(?=<a id="r\d|<!--summary:|\Z)' % num, body, re.S)
        summary = None
        if sm:
            summary = {}
            for key, label in SUMMARY_KEYS:
                lm = re.search(r'### %s\n(.+?)(?=\n### |\Z)' % re.escape(label), sm.group(1), re.S)
                if lm:
                    summary[key] = lm.group(1).strip()
            if not summary:
                summary = None
        if summary:
            summaries[num] = summary
        entries = []
        for line in body.splitlines():
            rm = ROW_RE.match(line)
            if rm:
                entries.append({
                    "rank": int(rm.group(1)),
                    "name": rm.group(2).strip(),
                    "repo": rm.group(3).strip(),
                    "score": float(rm.group(4)),
                    "note": rm.group(5).strip(),
                })
        segs.append({"num": num, "topic": topic, "ts": ts, "entries": entries})
    return segs, summaries


def render_summary(summary):
    """渲染单个调研的综合评价段。"""
    out = ["<!--summary:eval-->"]
    out.append("## 综合评价")
    out.append("")
    for key, label in SUMMARY_KEYS:
        val = summary.get(key, "")
        out.append("### %s" % label)
        out.append("")
        out.append(str(val).strip() if val else "（暂无）")
        out.append("")
    return out


def render(segs, summaries):
    out = ["# Tool Radar 调研归档", ""]
    out.append("> 累积所有 tool-radar 调研的前10榜单。历史榜单为快照；工具速查索引中同一仓库只保留最近一次调研数据。")
    out.append("")
    # 目录索引
    out.append("## 目录索引")
    out.append("")
    out.append("| # | 调研主题 | 时间 | 入榜数 | 评价 | 跳转 |")
    out.append("|---|---|---|---|---|---|")
    for s in segs:
        has_sum = "✓" if s["num"] in summaries else "—"
        out.append("| %d | %s | %s | %d | %s | [#%d](#r%d) |" % (
            s["num"], s["topic"], s["ts"], len(s["entries"]), has_sum, s["num"], s["num"]))
    out.append("")
    # 工具速查索引：同 repo 取序号最大（最新）
    out.append("## 工具速查索引")
    out.append("")
    out.append("> 同一仓库只保留最近一次（序号最大）调研数据。")
    out.append("")
    out.append("| 仓库 | 最近调研主题 | 总分 | 定位 | 来源 |")
    out.append("|---|---|---|---|---|")
    latest = {}
    for s in segs:
        for e in s["entries"]:
            latest[e["repo"]] = (s, e)
    for repo, (s, e) in sorted(latest.items(), key=lambda kv: -kv[1][1]["score"]):
        out.append("| %s | %s | %.1f | %s | [#%d](#r%d) |" % (
            cell(repo), cell(s["topic"]), e["score"], cell(e["note"]), s["num"], s["num"]))
    out.append("")
    out.append("---")
    out.append("")
    # 各调研明细段落
    for s in segs:
        out.append('<a id="r%d"></a>' % s["num"])
        out.append("## 调研 #%d · %s · %s" % (s["num"], s["topic"], s["ts"]))
        out.append("")
        out.append("| 排名 | 工具 | 仓库 | 总分 | 定位 |")
        out.append("|---|---|---|---|---|")
        for e in s["entries"]:
            out.append("| %d | %s | %s | %.1f | %s |" % (
                e["rank"], cell(e["name"]), cell(e["repo"]), e["score"], cell(e["note"])))
        out.append("")
        if s["num"] in summaries:
            out.append("<!--summary:%d-->" % s["num"])
            out.append("")
            for line in render_summary(summaries[s["num"]])[1:]:
                out.append(line)
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="tool-radar 调研结果累积归档")
    ap.add_argument("input", help="单次调研结果 JSON")
    ap.add_argument("-o", "--output", default=DEFAULT_ARCHIVE, help="归档 MD 路径")
    ap.add_argument("--summary", help="综合评价 JSON（优劣势/功能/活跃/安装/本地已装）")
    args = ap.parse_args()

    with io.open(args.input, encoding="utf-8") as f:
        data = json.load(f)
    topic = data.get("topic", "未命名调研")
    ts = data.get("scanned_at") or datetime.now().strftime("%Y-%m-%d %H:%M")
    entries = data.get("entries", [])[:10]
    for i, e in enumerate(entries, 1):
        e.setdefault("rank", i)

    summary = None
    if args.summary:
        with io.open(args.summary, encoding="utf-8") as f:
            summary = json.load(f)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    existing = ""
    if os.path.exists(args.output):
        existing = io.open(args.output, encoding="utf-8").read()
    segs, summaries = parse_archive(existing)
    next_num = max([s["num"] for s in segs], default=0) + 1
    if summary:
        summaries[next_num] = summary
    segs.append({"num": next_num, "topic": topic, "ts": ts, "entries": entries})

    text = render(segs, summaries)
    io.open(args.output, "w", encoding="utf-8", newline="\n").write(text)

    unique = {e["repo"] for s in segs for e in s["entries"]}
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print("已归档 #%d「%s」-> %s（共 %d 次调研，%d 个唯一仓库，综合评价: %s）" % (
        next_num, topic, args.output, len(segs), len(unique), "已附" if summary else "无"))


if __name__ == "__main__":
    main()