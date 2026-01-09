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
多数据源 → Python 抓取 → 智能评分 → 去重过滤 → Markdown 日报
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
cp -r daily-topic-selector/skills/daily-topic-selector ~/.claude/skills/ && mkdir -p ~/.config/daily-topic-selector && cp ~/.claude/skills/daily-topic-selector/config/*.yaml ~/.config/daily-topic-selector/
pip install -r ~/.claude/skills/daily-topic-selector/requirements.txt

```

## 更新方式

```bash
cd daily-topic-selector
git pull && rm -rf ~/.claude/skills/daily-topic-selector && cp -r skills/daily-topic-selector ~/.claude/skills/
```

用户配置位于 `~/.config/daily-topic-selector/`，更新时不会丢失。

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

## 支持的数据源

| 来源 | 抓取方式 | 说明 |
|------|----------|------|
| TLDR AI | 内嵌 JSON | AI 领域每日简报 |
| Hacker News | Firebase API | 技术社区热门内容 |
| Import AI | RSS | AI 政策与研究深度分析 |
| James Clear | HTML | 习惯与个人成长 |
| Wait But Why | RSS | 长文深度思考 |

## 输出文件

| 文件 | 说明 |
|------|------|
| `daily_topics.md` | 人类可读的 Markdown 日报 |
| `daily_topics.json` | 机器可读的 JSON 数据 |
| `fetch_log.txt` | 抓取日志 |
| `run_meta.json` | 运行元信息 |

## 关键特性

- **多源抓取**：支持 RSS、API、HTML、内嵌 JSON 多种方式
- **智能评分**：基于关键词、互动数据等多维度评分
- **增量模式**：自动去重，只输出新内容
- **配置驱动**：通过 YAML 配置数据源，无需修改代码
- **容错机制**：单个源失败不影响其他源
- **配置分离**：用户配置与 skill 代码分离，更新无忧

## 添加新数据源

编辑 `~/.config/daily-topic-selector/sources.yaml`：

```yaml
my_new_source:
  enabled: true
  name: "新数据源"
  fetch_methods:
    - method: rss
      priority: 1
      config:
        url: "https://example.com/feed"
  default_tags: ["tag1"]
  scoring:
    base_score: 30
```

## License

MIT
