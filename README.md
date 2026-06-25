# Tool Radar

同类工具调研编排 skill：给定一个工具，找出功能类似的同类、深挖架构/功能/口碑、评分排名、按场景推荐，并把每次调研的前10榜单累积归档。

专为 [Codex CLI](https://github.com/openai/codex) 设计的 skill。数据采集委托已安装的 `agent-reach`（GitHub / Exa / Reddit / 网页阅读），本 skill 只负责编排与评分框架。

## 功能

- 5 步调研流水线：锁定目标 → 多源找同类 → 深挖每个 → 评分排名 → 分场景推荐
- 6 维度评分框架（总分 100，含 N/A 等比折算）
- 调研结果累积归档：目录索引 + 工具速查索引（同仓库重调研自动更新替换）+ 历史榜单快照

## 安装

把 `tool-radar/` 目录拷到 Codex skills 目录：

```powershell
Copy-Item -Recurse tool-radar "$env:USERPROFILE\.agents\skills\tool-radar"
```

依赖：本机已装 `gh` CLI（已登录）和 `agent-reach` skill。

## 用法

直接在 Codex 中说：

> 用 $tool-radar 调研和 uv 类似的 Python 包管理器，找同类、评分排名、给推荐

或手动跑脚本：

```powershell
# 1. 评分折算与排名（输入各维度得分 JSON，输出排名表 + 明细）
python tool-radar/scripts/score.py scores.json

# 2. 排名后直接输出归档 JSON，再累积归档到 ~/.tool-radar/research-archive.md
python tool-radar/scripts/score.py scores.json --topic "uv 类包管理器" --archive result.json
python tool-radar/scripts/archive.py result.json
```

## 评分维度

| 维度 | 分值 |
|---|---|
| 功能匹配度 | 25 |
| 项目活跃/健康度 | 20 |
| 用户口碑 | 15 |
| 上手成本 | 15 |
| 架构合理性 | 10 |
| 生态/扩展 | 15 |

详见 `tool-radar/references/scoring.md`。

## 结构

```
tool-radar/
├── SKILL.md                 # 主文件：5 步工作流 + 路由表
├── agents/openai.yaml       # UI 元数据
├── references/
│   ├── scoring.md           # 6 维度评分框架
│   └── github-research.md   # GitHub 调研工具方法 + 卡点速查
└── scripts/
    ├── score.py             # 评分折算与排名
    └── archive.py           # 调研结果累积归档
```