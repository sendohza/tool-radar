#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描本机已安装的 Codex skills / plugins，比对候选列表，输出"本地已装类似项目"。

tool-radar 综合评价第5项用：动态检测，不写死，每次调研现扫。
扫描目录：
- ~/.agents/skills/         （用户 skills）
- D:/codex-skills/          （本地 skills 库）
- ~/.codex/plugins/         （插件缓存）

用法: python local_installed.py candidate1 candidate2 ...
      candidate 用 owner/repo 或名称，多个空格分隔
输出: JSON {"installed": [...], "note": "..."}
"""
import io
import json
import os
import sys

SCAN_DIRS = [
    os.path.join(os.path.expanduser("~"), ".agents", "skills"),
    r"D:\codex-skills",
    os.path.join(os.path.expanduser("~"), ".codex", "plugins", "cache"),
]


def collect_local_skills():
    """收集本地 skill 目录名与 SKILL.md 中的 name/description。"""
    found = {}  # dir_name -> (name, desc, path)
    for base in SCAN_DIRS:
        if not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
            # 跳过噪声目录
            dirs[:] = [d for d in dirs if d not in (
                "__pycache__", "node_modules", ".venv", ".git")]
            if "SKILL.md" in files:
                skill_md = os.path.join(root, "SKILL.md")
                try:
                    with io.open(skill_md, encoding="utf-8", errors="replace") as f:
                        head = f.read(600)
                    import re
                    nm = re.search(r"^name:\s*(.+)$", head, re.M)
                    dc = re.search(r"description:\s*>?\s*\n?((?:.+\n?){1,3})", head)
                    name = nm.group(1).strip() if nm else os.path.basename(root)
                    desc = dc.group(1).strip().replace("\n", " ")[:120] if dc else ""
                    found[os.path.basename(root)] = (name, desc, root)
                except Exception:
                    found[os.path.basename(root)] = (os.path.basename(root), "", root)
    return found


def match(candidates, local):
    """候选（owner/repo 末段）与本地 skill 目录名精确边界匹配，避免子串误报。"""
    hits = []
    cand_tokens = []
    for c in candidates:
        # 保留横线的 repo 末段，作为词边界匹配基准
        token = c.split("/")[-1].lower()
        cand_tokens.append((c, token))
    for dirname, (name, desc, path) in local.items():
        dn = dirname.lower()
        for c, token in cand_tokens:
            if len(token) < 5:
                continue
            # 精确相等，或以 token 为完整词段（带 - 边界）匹配，避免 skill 误匹配 skills
            if dn == token or dn.startswith(token + "-") or dn.endswith("-" + token) or token.startswith(dn + "-"):
                hits.append({"candidate": c, "local_skill": name,
                             "dir": dirname, "path": path, "desc": desc})
    return hits


def main():
    candidates = sys.argv[1:]
    local = collect_local_skills()
    hits = match(candidates, local)
    total = len(local)
    if hits:
        note = "本机已安装 %d 个 skill，其中与候选匹配 %d 个（见 installed 列表）" % (total, len(hits))
    else:
        note = "本机已安装 %d 个 skill，未发现与本次候选直接匹配的项目（候选均未本地安装）" % total
    result = {"installed": hits, "local_total": total, "note": note}
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()