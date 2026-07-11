## 2. 核心特点

### 2.1 智能分块 + 上下文增强

- **语义感知分块**: 在 LangChain `RecursiveCharacterTextSplitter` 基础上，叠加 Markdown 标题层级感知、代码块完整性保护
- **上下文注入**: 每个 chunk 自动注入文档元数据（来源、页码、章节路径）、图片描述文本
- **LLM 增强**: 可选的 chunk 重写/摘要，提升检索召回率

### 2.2 混合检索 + 两段式重排

```
Query
  ├─ BM25 (稀疏) → Top-K₁ ─┐
  ├─ Dense (稠密) → Top-K₁ ─┤
  │                          ├─ RRF 融合 → Top-K₂
  │                          │     │
  │                          │     ├─ Cross-Encoder 粗排 → Top-K₃
  │                          │     │     │
  │                          │     │     └─ LLM 精排 → Final Top-K
  │                          │     │
```

- **融合策略**: RRF（Reciprocal Rank Fusion），参数 k=60
- **粗排**: Cross-Encoder（如 BAAI/bge-reranker-base）
- **精排**: LLM Rerank（让 LLM 对候选 chunk 打分/排序）

### 2.3 全链路可插拔架构

- **六大可插拔组件**: LLM、Embedding、Reranker、VectorStore、Splitter、Evaluator
- **设计模式**: 抽象基类（ABC） + 工厂模式 + 配置驱动（`settings.yaml`）
- **首批实现**:
  - LLM: Azure OpenAI、OpenAI、Ollama、DeepSeek
  - Embedding: OpenAI text-embedding-3-small、Ollama
  - Reranker: Cross-Encoder（HuggingFace）、LLM Rerank
  - VectorStore: Chroma
  - Splitter: LangChain RecursiveCharacterTextSplitter
  - Evaluator: Ragas + 自定义指标

### 2.4 多模态 Image-to-Text

- **策略**: Vision LLM 生成图片描述 → 缝进 chunk 文本
- **不使用**: CLIP 多模态向量（避免复杂的多模态索引）
- **流程**: PDF 提取图片 → Vision LLM 生成描述 → 描述注入最近 chunk

### 2.5 全链路可观测性

- **结构化日志**: JSON Lines 格式，记录 Ingestion 链路 + Query 链路全量 Trace
- **本地 Dashboard**: Streamlit 多页面应用，零外部平台依赖（不依赖 LangSmith）
- **Dashboard 页面**: 系统总览、数据浏览、Ingestion 管理、追踪查看、评估面板

### 2.6 可插拔评估体系

- **框架**: 支持 Ragas（faithfulness、answer_relevancy 等）
- **自定义指标**: hit_rate、MRR、context_precision、context_recall
- **离线评估**: 构建评估数据集 → 批量跑测 → 生成报告

### 2.7 MCP 集成

- **SDK**: Python 官方 MCP SDK（`mcp` 包）
- **Transport**: Stdio（本地子进程模式）
- **暴露 Tools**: `query_knowledge_hub`、`list_collections`、`get_document_summary`、`ingest_document` 等

### 2.8 增量摄取

- **SHA256 指纹**: 文件级别去重，已摄入文件自动跳过
- **SQLite 记录**: 文件路径、SHA256、摄取时间、chunk 数量、状态

---
