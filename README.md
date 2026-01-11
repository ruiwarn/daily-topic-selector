# Daily Topic Selector Skill

## 项目概述

这是一个 **Claude Code 技能插件**，用于从多个内容源抓取最新文章并智能评分排序，帮助你快速筛选每日值得阅读的内容。

## 核心功能

该工具解决了内容筛选的痛点：

| 问题 | 描述 |
|------|------|
| 信息过载 | 每天需要浏览多个网站寻找优质内容 |
| 手动筛选 | 逐个查看文章标题，效率低下 |
| 重复阅读 | 难以追踪已读内容，经常重复浏览 |

使用此技能后，**每日选题时间从 30+ 分钟缩短至 2-3 分钟**。

## 工作流程

```
多数据源 → Python 抓取 → 智能评分 → 去重过滤 → Claude 翻译增强 → 中文日报
```

## 项目结构

```
daily-topic-selector/
├── skills/
│   └── daily-topic-selector/
│       ├── SKILL.md                 # 技能指令
│       ├── requirements.txt         # Python 依赖
│       ├── config/                  # 默认配置
│       ├── scripts/
│       │   └── run.py               # CLI 入口
│       └── src/                     # 源代码
├── README.md                        # 说明文档
└── LICENSE                          # MIT 许可证
```

## 系统要求

- **Claude Code** - 来自 claude.ai/code
- **Python 3.9+** 及依赖：`pip install requests feedparser beautifulsoup4 lxml PyYAML`

## 首次安装方式

```bash
git clone https://github.com/yourname/daily-topic-selector.git
cp -r daily-topic-selector/skills/daily-topic-selector ~/.claude/skills/
pip install -r ~/.claude/skills/daily-topic-selector/requirements.txt
```

安装后即可使用，程序会自动使用默认配置。如需自定义配置，见下方「配置说明」。

## 更新方式

```bash
cd daily-topic-selector
git pull && rm -rf ~/.claude/skills/daily-topic-selector && cp -r skills/daily-topic-selector ~/.claude/skills/
```

更新后会自动获取新增的数据源。你的自定义配置（如果有）位于 `~/.config/daily-topic-selector/`，不会被覆盖。

## 使用方法

```
抓取今日选题
```

或

```
/daily-topic-selector
```

### 高级用法

```
抓取最近 3 天的选题，只看 Hacker News 和 Import AI
```

## 配置说明

程序按以下优先级查找配置：

1. `--config` 参数指定的目录
2. `~/.config/daily-topic-selector/` （用户自定义配置）
3. skill 自带的 `config/` 目录（默认配置）

如果你从仓库根目录直接运行脚本，建议显式传入
`--config skills/daily-topic-selector/config`。

### 配置合并机制

用户配置会与默认配置**自动合并**，而不是完全替换。这意味着：

- 仓库新增数据源时，你无需修改配置即可使用
- 你只需要写想修改的部分，其余使用默认值
- 你可以通过 `enabled: false` 禁用不想要的源

| 场景 | 行为 |
|------|------|
| 默认源，用户未修改 | 使用默认配置（自动获取仓库更新） |
| 默认源，用户有自定义 | 用户配置覆盖默认配置 |
| 仓库新增源，用户无配置 | 自动启用新源 |
| 仓库新增源，用户设置 `enabled: false` | 保持禁用 |

### 自定义配置示例

创建 `~/.config/daily-topic-selector/sources.yaml`，只需写需要修改的部分：

```yaml
sources:
  # 禁用不想要的源
  wait_but_why:
    enabled: false

  # 修改现有源的评分
  hacker_news:
    scoring:
      base_score: 25

  # 添加自定义源（见下方"添加新数据源"）
```

### 自定义评分关键词

创建 `~/.config/daily-topic-selector/scoring.yaml`：

```yaml
global_keywords:
  my_interests:
    keywords: ["Rust", "WebAssembly", "边缘计算"]
    bonus: 15
```

## 支持的数据源

| 来源 | 抓取方式 | 说明 |
|------|----------|------|
| TLDR AI | 内嵌 JSON | AI 领域每日简报 |
| Hacker News | Firebase API | 技术社区热门内容 |
| Import AI | RSS | AI 政策与研究深度分析 |
| James Clear | HTML | 习惯与个人成长 |
| Wait But Why | RSS | 长文深度思考 |
| The Rundown AI | RSS/HTML | 每日 AI 新闻简报 |
| Superhuman AI | HTML/RSS | 每日 3 分钟 AI 快讯 |
| Ben's Bites | RSS/HTML | 每日 AI 新闻摘要 |
| The Neuron | HTML/RSS | 每日 AI 新闻与工具教程 |
| Last Week in AI | RSS/HTML | 每周 AI 新闻总结 |
| Nate's Newsletter | RSS | AI 前沿动态与策略 |
| OpenAI Blog | RSS/HTML | OpenAI 官方博客 |
| Hugging Face Blog | RSS/HTML | 开源 AI 社区博客 |
| MarkTechPost | RSS/HTML | AI 研究新闻平台 |
| KDnuggets | RSS/HTML | 数据科学与 AI 新闻 |
| Qbit AI | HTML/RSS | 中文 AI 媒体 |
| AI Weekly | RSS/HTML | 每周 AI 新闻总结 |
| Linux Do | RSS | Linux Do 社区最新帖子 |

## 输出文件

| 文件 | 说明 |
|------|------|
| `daily_topics.md` | 原始 Markdown 日报 |
| `daily_topics_zh.md` | 增强版日报（含中文翻译和摘要） |
| `daily_topics.json` | 机器可读的 JSON 数据 |
| `fetch_log.txt` | 抓取日志 |
| `run_meta.json` | 运行元信息 |

`daily_topics.md` 顶部会包含“健康检查”摘要，列出抓取失败的来源及错误原因，并提示频繁运行可能触发站点限制。

## 关键特性

- **多源抓取**：支持 RSS、API、HTML、内嵌 JSON 多种方式
- **智能评分**：基于关键词、互动数据等多维度评分
- **增量模式**：自动去重，只输出新内容
- **中文增强**：自动翻译英文标题并生成中文摘要
- **配置驱动**：通过 YAML 配置数据源，无需修改代码
- **容错机制**：单个源失败不影响其他源
- **配置分离**：用户配置与 skill 代码分离，更新无忧

## 添加新数据源

编辑 `~/.config/daily-topic-selector/sources.yaml`：

```yaml
sources:
  my_new_source:
    enabled: true
    name: "新数据源"
    description: "数据源描述"

    fetch_methods:
      - method: rss          # 支持: rss, api, html, json_extract
        priority: 1
        config:
          url: "https://example.com/feed"

    field_mapping:           # 字段映射（可选）
      title: title
      url: link
      published_at: pubDate

    default_tags: ["tag1", "tag2"]

    scoring:
      base_score: 30
      keyword_bonus:
        - keywords: ["关键词1", "关键词2"]
          bonus: 10
```

### 支持的抓取方式

| 方式 | 适用场景 | 配置示例 |
|------|----------|----------|
| `rss` | RSS/Atom 订阅 | `url: "https://example.com/feed"` |
| `api` | REST API | `endpoints: {list: "...", item: "..."}` |
| `html` | 网页抓取 | `url: "...", selectors: {title: "h2 a"}` |
| `json_extract` | 页面内嵌 JSON | `url: "...", json_pattern: "..."` |

## License

MIT
