# KnowledgeHub — 模块化 RAG + MCP 知识库系统

> "一个为学习而设计、为面试而打磨、为生产而预留的本地 RAG + MCP 知识库系统。"

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## 项目简介

KnowledgeHub 是一个**模块化的 RAG（检索增强生成）系统**，同时包装为 **MCP Server（Model Context Protocol）**，使得 GitHub Copilot、Claude Desktop 等 AI 助手可以通过 Stdio Transport 直接调用本地知识库进行问答。

### 核心亮点

- **混合检索 + 两段式重排**：BM25 + Dense Embedding → RRF 融合 → Cross-Encoder 粗排 → LLM 精排
- **全链路可插拔**：LLM / Embedding / Reranker / VectorStore / Splitter / Evaluator 六大组件通过 `settings.yaml` 配置切换
- **多模态 Image-to-Text**：Vision LLM 生成图片描述，注入 chunk 文本
- **全链路可观测**：JSONL 结构化日志 + SQLite Trace 存储 + Streamlit 本地 Dashboard
- **可插拔评估**：Ragas + 自定义指标（hit_rate、MRR、context_precision）
- **MCP 集成**：Python 官方 MCP SDK，Stdio Transport 本地子进程通信
- **增量摄取**：SHA256 文件指纹，已摄入文件自动跳过
- **本地优先**：SQLite 持久化，零外部服务依赖，开箱即用

## 快速开始

### 环境要求

- Python 3.11+
- [Ollama](https://ollama.com/)（可选，用于本地 LLM）
- [Claude Desktop](https://claude.ai/download)（可选，用于 MCP Client 测试）

### 安装

```bash
# 克隆项目
git clone <repo-url>
cd knowledge-hub

# 安装依赖
make install-dev

# 复制配置文件
cp .env.example .env
cp settings.example.yaml settings.yaml
# 编辑 .env 填入 API Key
```

### 使用

```bash
# 启动 MCP Server
make run-mcp

# 启动 Dashboard
make run-dashboard

# 运行测试
make test
```

## 项目结构

```
knowledge-hub/
├── src/knowledge_hub/    # 源代码
│   ├── config/           # 配置管理
│   ├── core/             # 核心抽象（ABC）
│   ├── factories/        # 工厂模式
│   ├── providers/        # 具体实现
│   ├── ingestion/        # 数据摄取流水线
│   ├── retrieval/        # 检索流水线
│   ├── mcp/              # MCP Server
│   ├── evaluation/       # 评估框架
│   ├── observability/    # 可观测性
│   ├── dashboard/        # Streamlit Dashboard
│   ├── storage/          # 存储层
│   └── utils/            # 工具函数
├── tests/                # 测试
│   ├── unit/             # 单元测试
│   ├── integration/      # 集成测试
│   └── e2e/              # 端到端测试
├── data/                 # 数据目录
├── docs/                 # 文档
├── settings.yaml         # 主配置文件
└── DEV_SPEC.md           # 开发规范文档
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 语言 | Python 3.11+ |
| 异步 | asyncio |
| 配置 | Pydantic Settings + YAML |
| LLM | OpenAI / Azure / Ollama / DeepSeek |
| 向量库 | ChromaDB |
| 检索 | BM25 (rank_bm25) + Dense |
| 重排 | sentence-transformers + LLM Rerank |
| 文档解析 | MarkItDown |
| 评估 | Ragas + 自定义指标 |
| MCP | mcp Python SDK |
| Dashboard | Streamlit |
| 持久化 | SQLite |
| 日志 | structlog → JSONL |
| 测试 | pytest + pytest-asyncio |

## 开发

```bash
make lint        # 代码检查
make format      # 代码格式化
make typecheck   # 类型检查
make test        # 运行所有测试
make test-cov    # 测试 + 覆盖率报告
```

## License

MIT
