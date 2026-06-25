---
name: tool-radar
description: >
  调研同类工具并评分排名、按场景推荐；同时积累调研中实际用到的工具方法与卡点备忘，
  避免重复踩坑。MUST USE when 用户要求：找同类工具 / 评估并评分排名 / 整理调研卡点 /
  调研复盘 / 记录调研工具方法 / 工具雷达 / tool-radar。
---

# Tool Radar — 同类工具调研 · 评分排名 · 卡点备忘

三件事：(1) 找同类工具并深挖每个；(2) 用统一评分框架打分排名、按场景推荐；
(3) 积累调研工具方法与踩坑解法。每条工具/卡点都来自真实调研，不写理论可能。

## 路由表

| 用途 | 详细文档 |
|---------|---------|
| 评分框架（6 维度 100 分 + 排名表格式 + N/A 处理） | references/scoring.md |
| GitHub 仓库调研（找同类/竞品、评估架构）工具方法与卡点 | references/github-research.md |
| 评分折算与排名（自动算分 + N/A 折算，输出 Markdown 排名表与明细） | scripts/score.py |
| 调研结果累积归档（前10榜单 + 目录索引 + 同仓库更新替换） | scripts/archive.py |

## 维护规则

- 评分一律用 references/scoring.md 的 6 维度框架，不自创维度。
- 调研只补「实际用过、确实有效」的工具方法，不堆砌未验证命令。
- 卡点必须写三段：现象 → 根因 → 解法，缺一不可。
- 命令示例标注易错点（字段名、编码、超时等）。
- 新调研场景在 references/ 下新建 .md，并在路由表登记。
- 评分折算与排名用 scripts/score.py 自动算分，不手算折算；维度满分以 references/scoring.md 为准。
- 调研排名后用 scripts/score.py --archive 输出归档 JSON，再 scripts/archive.py 累积到 ~/.tool-radar/research-archive.md；同一仓库重调研时工具速查索引自动更新替换。