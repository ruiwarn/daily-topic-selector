# daily-topic-selector

每日选题抓取工具 - 从多个内容源获取最新文章并评分排序

## 触发方式

当用户说以下内容时触发此技能：
- "抓取今日选题"
- "获取每日选题"
- "运行 daily-topic-selector"
- "/daily-topic-selector"
- "fetch daily topics"

## 功能说明

此技能用于从多个内容源（RSS、API、HTML、JSON）抓取最新文章，并通过评分系统筛选出最值得阅读的内容。

支持的数据源：
- TLDR AI - AI 领域每日简报
- Hacker News - 技术社区热门内容
- Import AI - AI 政策与研究深度分析
- James Clear - 习惯与个人成长
- Wait But Why - 长文深度思考

## 使用指令

### 基础用法

```bash
# 抓取最近 1 天的内容（默认，自动查找配置）
python $SKILL_DIR/scripts/run.py

# 抓取最近 N 天的内容
python $SKILL_DIR/scripts/run.py --days 3

# 指定输出目录
python $SKILL_DIR/scripts/run.py --output_dir ./output
```

### 高级用法

```bash
# 只抓取特定源
python $SKILL_DIR/scripts/run.py --only_sources hn,import_ai

# 指定时间范围
python $SKILL_DIR/scripts/run.py --since 2024-01-01T00:00:00Z

# 调整抓取参数
python $SKILL_DIR/scripts/run.py --limit_per_source 100 --timeout 30
```

## 输出文件

运行后会生成 4 个文件：

| 文件 | 说明 |
|------|------|
| `daily_topics.md` | 人类可读的 Markdown 日报 |
| `daily_topics.json` | 机器可读的 JSON 数据 |
| `fetch_log.txt` | 抓取日志 |
| `run_meta.json` | 运行元信息 |

## 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--days` | 1 | 抓取最近 N 天的内容 |
| `--since` | - | 抓取该时间之后的内容 (ISO 格式) |
| `--output_dir` | . | 输出目录 |
| `--limit_per_source` | 50 | 每个源最大抓取条数 |
| `--only_sources` | - | 只抓取指定源 (逗号分隔) |
| `--config` | 自动 | 配置目录路径 |
| `--incremental` | true | 增量模式 |
| `--timeout` | 20 | 请求超时 (秒) |
| `--retries` | 2 | 失败重试次数 |

## 依赖要求

运行前请确保已安装依赖：

```bash
pip install requests feedparser beautifulsoup4 lxml PyYAML
```

## 配置说明

### 配置文件查找顺序

程序按以下优先级查找配置：

1. `--config` 参数指定的目录
2. `~/.config/daily-topic-selector/` （用户自定义配置）
3. `$SKILL_DIR/config/` （默认配置）

**推荐**：将自定义配置放在 `~/.config/daily-topic-selector/`，这样更新 skill 时不会丢失配置。

### 初始化用户配置

首次使用时，可复制默认配置到用户目录：

```bash
mkdir -p ~/.config/daily-topic-selector
cp $SKILL_DIR/config/*.yaml ~/.config/daily-topic-selector/
```

### 配置文件

- `sources.yaml` - 数据源配置
- `scoring.yaml` - 评分规则配置

### 添加新数据源

编辑 `~/.config/daily-topic-selector/sources.yaml`：

```yaml
my_new_source:
  enabled: true
  name: "新数据源"
  description: "描述"

  fetch_methods:
    - method: rss
      priority: 1
      config:
        url: "https://example.com/feed"

  default_tags: ["tag1"]

  scoring:
    base_score: 30
```

### 调整评分规则

编辑 `~/.config/daily-topic-selector/scoring.yaml`：

```yaml
global_keywords:
  ai_hot:
    keywords: ["OpenAI", "GPT", "Claude"]
    bonus: 15
```
