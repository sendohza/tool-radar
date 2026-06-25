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
import subprocess
import shutil


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


def _run(cmd, timeout=15):
    try:
        out = subprocess.run(cmd, capture_output=True, encoding="utf-8",
                             errors="replace", timeout=timeout, shell=True)
        return out.stdout or ""
    except Exception:
        return ""


def collect_system_cli():
    """扫描 PATH / pip 全局包 / npm 全局包，返回 {name: source}。"""
    found = {}
    # PATH 可执行文件名（候选 token 的常见变体）
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if not d or not os.path.isdir(d):
            continue
        try:
            for f in os.listdir(d):
                lp = f.lower()
                if lp.endswith((".exe", ".cmd", ".bat", ".ps1")):
                    found[lp.rsplit(".", 1)[0]] = ("path", os.path.join(d, f))
        except Exception:
            continue
    # pip 全局包
    for line in _run("pip list --format=freeze 2>nul").splitlines():
        n = line.split("==")[0].strip().lower()
        if n:
            found[n] = ("pip", n)
    # npm 全局包
    for line in _run("npm ls -g --depth=0 2>nul").splitlines():
        m = line.strip()
        if m.startswith("+--") or m.startswith("`--"):
            n = m.lstrip("+`- ").split("@")[0].strip().lower()
            if n:
                found[n] = ("npm", n)
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


def match_cli(candidates, system_cli):
    """候选 token 与系统 CLI 包名匹配（normalize 去 - _ 后比较）。"""
    def norm(x):
        return x.lower().replace("-", "").replace("_", "").replace(".", "")
    hits = []
    normed = {norm(k): (k, v) for k, v in system_cli.items()}
    for c in candidates:
        token = norm(c.split("/")[-1])
        if len(token) < 5:
            continue
        for nk, (orig, (src, where)) in normed.items():
            if token == nk or nk.endswith(token) or token.endswith(nk):
                hits.append({"candidate": c, "system_cli": orig,
                             "source": src, "where": where})
    return hits


def main():
    candidates = sys.argv[1:]
    local = collect_local_skills()
    hits = match(candidates, local)
    system_cli = collect_system_cli()
    cli_hits = match_cli(candidates, system_cli)
    total = len(local)
    cli_total = len(system_cli)
    if hits or cli_hits:
        note = ("本机已安装 %d 个 skill + %d 个系统 CLI（PATH/pip/npm），"
                "其中与候选匹配 skill %d 个、CLI %d 个（见 installed/system_cli 列表）"
                % (total, cli_total, len(hits), len(cli_hits)))
    else:
        note = ("本机已安装 %d 个 skill + %d 个系统 CLI（PATH/pip/npm），"
                "未发现与本次候选匹配的项目（候选均未本地安装）"
                % (total, cli_total))
    result = {"installed": hits, "system_cli": cli_hits,
              "local_total": total, "cli_total": cli_total, "note": note}
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
