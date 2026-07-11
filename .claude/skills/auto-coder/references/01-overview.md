## 1. 项目概述

### 1.1 设计理念

| 维度 | 理念 |
|------|------|
| **教是最好的学** | 边做边录视频教学，架构清晰、易于讲解，每个模块配套技术文档与代码示范 |
| **可插拔优先** | 所有核心组件（LLM、Embedding、Reranker、VectorStore、Splitter、Evaluator）通过配置切换，不硬编码任何厂商 |
| **本地优先** | 零外部服务依赖（SQLite 做持久化），开箱即用，同时支持深度扩展 |
| **面试驱动** | 每个模块整理面试高频题和简历撰写建议，项目本身作为简历核心项目 |
| **可观测** | 全链路 Trace + 本地 Dashboard，让 RAG 黑盒透明化 |

### 1.2 项目定位

KnowledgeHub 是一个**模块化的 RAG 系统**，同时包装为 **MCP Server（Model Context Protocol）**，使得 GitHub Copilot、Claude Desktop 等 AI 助手可以通过 Stdio Transport 直接调用本地知识库进行问答。

**一句话定位**: "一个为学习而设计、为面试而打磨、为生产而预留的本地 RAG + MCP 知识库系统。"

### 1.3 技术约束

| 约束项 | 说明 |
|--------|------|
| 语言 | Python 3.11+ |
| 框架限制 | **不使用 LlamaIndex / LangChain 框架**（仅允许使用 LangChain 的 `RecursiveCharacterTextSplitter`） |
| 向量库 | 首批仅实现 Chroma，架构层预留 Milvus / Qdrant 扩展接口 |
| 持久化 | SQLite（元数据、Trace、评估结果），零外部数据库 |
| 通信方式 | MCP Stdio Transport（本地子进程），不做 HTTP 部署 |
| 测试框架 | pytest + pytest-asyncio |

---
