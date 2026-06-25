# GitHub 仓库调研

场景：找同类/竞品项目、评估架构、做评分排名。来源：2026-06 金融服务 AI agent 调研、AI 伴侣/VTuber（Open-LLM-VTuber 等）调研。

## 工具方法

### 1. 仓库检索（主力）

gh search repos 按 star 排序找候选，--json 指定字段控制输出：

```powershell
gh search repos "fintech" --sort stars --limit 15 --json fullName,stargazersCount,language,description
```

字段名是 stargazersCount（带 s），不是 stargazerCount。

### 2. 多关键词并行覆盖细分赛道

单一关键词会漏项目，并行跑多个 query（字面 + 行业 + 细分 + 技术栈）：

```
financial service   # 字面
fintech             # 行业
personal finance    # 细分
financial agent     # agent 赛道
financial llm       # 模型层
FinGPT / trading agent llm / investment research ai  # 项目名/技术词
```

### 3. 单仓库元信息（star/forks/issues/活跃度/license）

gh api repos/owner/repo 一次拿全评估指标：

```powershell
$j = gh api "repos/anthropics/financial-services" | ConvertFrom-Json
"star={0} forks={1} issues={2} pushed={3} lic={4}" -f `
  $j.stargazers_count,$j.forks_count,$j.open_issues_count,$j.pushed_at,$j.license.spdx_id
```

注意：gh api 字段是蛇形 stargazers_count，与 gh search 的驼峰 stargazersCount 不同。

### 4. 读 README（base64 解码）

GitHub API 返回 base64 编码的 README，需解码：

```powershell
gh api "repos/owner/repo/readme" -q .content |
  ForEach-Object { [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($_)) } |
  Select-Object -First 60
```

### 5. 批量拉指标——分批 + 加超时

8 个仓库串行 gh api 易超时。逐个调用、每个加 timeout_ms，或分 2-3 批。

### 6. 贡献者数（社区健康度）

gh api 取 contributors 列表长度（per_page=100 够用）：

```powershell
gh api "repos/owner/repo/contributors?per_page=100" --jq 'length'
```

易错：--jq 'length' 是单 token，不会被 PowerShell 拆参（对照卡点4）。贡献者多=社区健康。

### 7. 许可证类型（区分标准/自定义/无）

gh api license 端点拿许可证名：

```powershell
gh api "repos/owner/repo/license" --jq '.license.name'
```

返回 MIT/Apache-2.0=标准友好；返回 Other=自定义非标（商用需细读条款）；仓库无 LICENSE 文件时该端点 404（见卡点8）。

### 8. 发版节奏

gh release list 看 release 频率与最近版本时间：

```powershell
gh release list -R owner/repo --limit 6
```

### 9. 用户反馈采样（issue 标题）

gh issue list 取近期 open issue 标题，快速看痛点/bug 集中区：

```powershell
gh issue list -R owner/repo --state open --limit 8 --json title --jq '.[].title'
```

易错：--jq 必须配 --json，否则报 "cannot use --jq without --json"；jq 只取单字段 '[].title'、不含空格双引号，不会被拆参。

### 10. 口碑采样（免登录）：HN Algolia

Reddit 无 token 直连常超时（见卡点10），改用 Hacker News Algolia API（免登录）：

```powershell
$q = [uri]::EscapeDataString("open-llm-vtuber")
$j = Invoke-RestMethod "https://hn.algolia.com/api/v1/search?query=$q&tags=story&hitsPerPage=4" -TimeoutSec 12
$j.hits | Select-Object points,num_comments,title,url
# 取评论正文：Invoke-RestMethod "https://hn.algolia.com/api/v1/items/<objectID>"
```

### 11. 读 README（raw header，比 base64 稳）

第4条的 base64 解码经 ForEach-Object 管道写文件会丢成 0 行（见卡点9）。更稳的写法是用 raw Accept header 直接拿原文：

```powershell
gh api "repos/owner/repo/readme" -H "Accept: application/vnd.github.raw" > readme.md
```


### 12. 新兴高星筛选 + 星速排序（借鉴 radar_core.py 思路）

找近期爆发、过滤掉老牌停更项目：用 created:> 限定建库时间、stars:>= 阈值筛高星，自己算星速（star/年龄天数）。借鉴本机 github-trending-radar/radar_core.py 的搜索语法与星速算法，但 tool-radar 即时调研不依赖该脚本（其 TRACKS 为固定4赛道，无法按任意主题跑；只取其"按星速排序、近90天高星"的思路）。

```powershell
# 近90天、>=50星、按 star 降序，取候选池
$since = (Get-Date).AddDays(-90).ToString("yyyy-MM-dd")
gh search repos "<core-keyword> created:>$since stars:>=50" --sort stars --limit 20 --json fullName,stargazersCount,description,language,createdAt
```

星速排序（stargazers_count / 年龄天数，年龄用 createdAt 算）：年龄越小星越多=爆发期。可对候选池在 PS 内算星速后排序，或直接 import radar_core 的 age_days/velocity 算法。默认按 star 降序拿到候选池，再按星速重排作为补充视角——老牌高星项目星速未必高。

注意：GitHub Search API 的 created 限定符精确到日，stars:>=N 是闭区间。若候选不足，放宽 stars:>=30 或拉长 created:> 天数，不要直接去掉时间过滤（否则全是老项目）。

## 卡点速查

### 卡点1：agent-reach doctor --json 超时
- 现象：agent-reach doctor --json 14 秒无响应被杀。
- 根因：后端体检涉及多平台探测，慢且不稳。
- 解法：GitHub 调研不依赖 doctor，直接用 gh CLI（已认证即可）。

### 卡点2：gh search 字段名报错 Unknown JSON field
- 现象：--json stargazerCount 报 Unknown JSON field: "stargazerCount"。
- 根因：字段名是 stargazersCount（复数 s）。
- 解法：用正确名，或先不带 --json 跑 gh search repos --help 看字段列表。

### 卡点3：Format-Table 把字段显示成 {a,b,c}
- 现象：gh search --json | ConvertFrom-Json | Format-Table 列值变成 {microsoft/qlib, ...}。
- 根因：ConvertFrom-Json 把数组字段包成对象数组，Format-Table 折叠显示。
- 解法：用 Select-Object 计算属性取标量子串，如 @{n='desc';e={if($_.description){$_.description.Substring(0,90)}}}。

### 卡点4：gh api --jq 带空格被拆参数
- 现象：gh api "repos/$r" --jq '.a + " " + .b' 报 accepts 1 arg(s), received 11。
- 根因：PowerShell 把 jq 表达式里的空格拆成多个参数传给 gh。
- 解法：不用 --jq 拼字符串，改用完整 JSON 输出 + ConvertFrom-Json 在 PS 内拼接。

### 卡点5：stderr 重定向污染 JSON 解析
- 现象：gh api --jq ... 2>$null | ConvertFrom-Json 报 Invalid JSON primitive。
- 根因：2>&1 / 2>$null 时机不对，错误文本混入管道。
- 解法：不用 --jq，直接 gh api "repos/$r" | ConvertFrom-Json，不重定向 stderr。

### 卡点6：批量循环超时但部分输出已生效
- 现象：8 个仓库 for 循环 10 秒超时，但前 6 个已打印。
- 根因：串行 API 调用累积耗时超 timeout。
- 解法：逐个调用各自加 timeout_ms，或分批（每批 ≤3 个）。

### 卡点7：@tsv jq 输出在 PowerShell 不顺
- 现象：--jq '[...] | @tsv' 经 PS 解析异常。
- 根因：PS 对含制表符/特殊字符的 jq 输出处理不稳。
- 解法：同卡点4，回归完整 JSON + ConvertFrom-Json。

### 卡点8：gh api license 对无 LICENSE 仓库 404
- 现象：gh api repos/owner/repo/license 返回 HTTP 404 Not Found。
- 根因：仓库根目录无 LICENSE 文件，license 端点无数据。
- 解法：调用前不假设有许可；404 即视为"无许可证"（法律上不可直接复用），评分时许可证维度记最低。

### 卡点9：README base64 解码写文件变 0 行
- 现象：gh api .../readme -q .content | ForEach-Object {解 base64 写文件}，写完 Get-Content 显示 0 行。
- 根因：base64 内容经 PowerShell 管道 ForEach-Object 逐块写时编码/分块出错。
- 解法：改用 raw header 直拿原文（见工具方法11），避开 base64。

### 卡点10：Reddit 无登录直连超时
- 现象：Invoke-RestMethod www.reddit.com/search.json 无 token，30 秒挂起超时。
- 根因：Reddit 限制未认证请求，频繁超时。
- 解法：口碑改走 HN Algolia（工具方法10）+ GitHub issue 标题（工具方法9）；必须用 Reddit 则需 OAuth token 走 praw/rdt。

### 卡点11：mcporter exa 通道不可用
- 现象：mcporter call 'exa.web_search_exa(...)' 报 "Unable to load tool metadata"。
- 根因：mcporter 无法加载 exa 工具元数据（配置/后端缺失）。
- 解法：网页搜索退化为 gh search repos + 官网/README 直读（gh api readme raw header）；不依赖 exa。

### 卡点12：curl 在 PowerShell 是 Invoke-WebRequest 别名
- 现象：curl -s "https://..." 报 "Missing an argument for parameter 'SessionVariable'" 或 URI 解析错。
- 根因：PowerShell 的 curl 是 Invoke-WebRequest 别名，不是真 curl，参数不兼容。
- 解法：用 Invoke-RestMethod -Uri <u> -Headers @{User-Agent='...'} -TimeoutSec N。

### 卡点13：gh api --jq 默认值 // "x" 被转义破坏
- 现象：gh api ... --jq '{lic:(.license.spdx_id // "none")}' 报 invalid escape sequence \)。
- 根因：PowerShell 把 jq 表达式里双引号包裹的默认值串转义破坏。
- 解法：jq 表达式整体用单引号包裹，且避免内嵌双引号默认值；改用完整 JSON + ConvertFrom-Json 在 PS 内处理空值（同卡点4 思路）。

### 卡点14：radar_core.py 不能直接用于任意工具调研
- 现象：想用 python radar_core.py --track <某工具主题> 搜任意同类工具，只返回4个固定赛道或空。
- 根因：radar_core.py 顶部 TRACKS 硬编码 AI/Agent/自媒体/出海 4 赛道；--track 只做 track.lower() in k.lower() 过滤，无法新增主题。它是固定赛道被动监测，非任意主题主动搜索。
- 解法：tool-radar 即时调研用本条（工具方法12）的 gh search + 星速思路自行跑；radar_core.py 留作每日固定赛道趋势监测独立存在，不混用。
