## 4. 测试方案

### 4.1 TDD 理念

**Red → Green → Refactor**

```
写测试（失败） → 写实现（通过） → 重构（保持通过）
```

- 每个 ~1 小时增量开发前，先写测试用例
- 测试覆盖核心逻辑，不追求 100% 覆盖率
- 测试本身也是文档，体现设计意图

### 4.2 分层测试架构

```
┌─────────────────────────────────────────────────┐
│                    E2E Tests                     │  ← 端到端：完整 Ingestion→Query 流程
│              (tests/e2e/)                        │     依赖: Chroma + LLM（mock 或真实）
├─────────────────────────────────────────────────┤
│              Integration Tests                   │  ← 集成：模块间协作
│           (tests/integration/)                   │     依赖: SQLite + Chroma（本地）
├─────────────────────────────────────────────────┤
│                  Unit Tests                      │  ← 单元：单个类/函数
│              (tests/unit/)                       │     依赖: 无（全部 mock）
└─────────────────────────────────────────────────┘

测试比例:  Unit 70% | Integration 20% | E2E 10%
```

### 4.3 测试目录结构

```
tests/
├── conftest.py                          # 公共 fixtures
├── unit/
│   ├── __init__.py
│   ├── test_rrf_fusion.py               # RRF 融合算法
│   ├── test_chunk_metadata.py            # Chunk 数据结构
│   ├── test_checksum.py                  # SHA256 去重
│   ├── test_config_loader.py             # 配置加载
│   ├── test_llm_factory.py               # LLM 工厂
│   ├── test_embedding_factory.py         # Embedding 工厂
│   ├── test_reranker_factory.py          # Reranker 工厂
│   ├── test_bm25_retriever.py            # BM25 检索
│   ├── test_cross_encoder_reranker.py    # Cross-Encoder 重排
│   ├── test_chunker.py                   # 语义分块
│   ├── test_context_injector.py          # 上下文注入
│   ├── test_image_processor.py           # 图片处理
│   ├── test_trace_logger.py              # Trace 日志
│   ├── test_evaluator_metrics.py         # 评估指标
│   └── test_mcp_tools.py                 # MCP 工具（mock）
├── integration/
│   ├── __init__.py
│   ├── test_chroma_store.py              # Chroma 读写
│   ├── test_sqlite_store.py              # SQLite 持久化
│   ├── test_ingestion_pipeline.py        # 完整摄取流程
│   ├── test_retrieval_pipeline.py        # 完整检索流程
│   └── test_bm25_persistence.py          # BM25 索引持久化
└── e2e/
    ├── __init__.py
    ├── test_full_rag_flow.py             # Ingestion→Query 全流程
    ├── test_mcp_server.py                # MCP Stdio 通信
    └── test_incremental_ingestion.py     # 增量摄取
```

### 4.4 测试策略详解

#### 4.4.1 单元测试

```python
# tests/unit/test_rrf_fusion.py
import pytest
from knowledge_hub.retrieval.fusion import rrf_fusion
from knowledge_hub.core.models import Chunk, RetrievalResult, ChunkMetadata

@pytest.fixture
def sample_chunks():
    return [
        Chunk(chunk_id="c1", content="chunk1", enhanced_content="chunk1",
              metadata=ChunkMetadata(source_file="doc.pdf", source_type="pdf",
              doc_title="Doc", page_number=1, section_path="", chunk_index=0,
              total_chunks=3, sha256="abc", image_descriptions=[], created_at=""),
              tokens=10),
        Chunk(chunk_id="c2", content="chunk2", enhanced_content="chunk2",
              metadata=ChunkMetadata(source_file="doc.pdf", source_type="pdf",
              doc_title="Doc", page_number=1, section_path="", chunk_index=1,
              total_chunks=3, sha256="abc", image_descriptions=[], created_at=""),
              tokens=10),
    ]

def test_rrf_fusion_basic(sample_chunks):
    """RRF 融合：两个检索器都返回相同 chunk，分数应更高"""
    bm25_results = [
        RetrievalResult(chunk=sample_chunks[0], score=0.9, retrieval_method="bm25", rank=1),
        RetrievalResult(chunk=sample_chunks[1], score=0.7, retrieval_method="bm25", rank=2),
    ]
    dense_results = [
        RetrievalResult(chunk=sample_chunks[1], score=0.95, retrieval_method="dense", rank=1),
        RetrievalResult(chunk=sample_chunks[0], score=0.8, retrieval_method="dense", rank=2),
    ]

    fused = rrf_fusion(bm25_results, dense_results, k=60, top_n=2)

    assert len(fused) == 2
    # c1 在 BM25 rank=1, Dense rank=2 → score = 1/61 + 1/62
    # c2 在 BM25 rank=2, Dense rank=1 → score = 1/62 + 1/61
    # 应该近似相等，但 c1 略高（更小的 rank sum）
    assert fused[0].score >= fused[1].score

def test_rrf_fusion_empty_inputs():
    """RRF 融合：空输入返回空列表"""
    assert rrf_fusion([], []) == []

def test_rrf_fusion_single_source(sample_chunks):
    """RRF 融合：只有一个检索器有结果"""
    bm25_results = [
        RetrievalResult(chunk=sample_chunks[0], score=0.9, retrieval_method="bm25", rank=1),
    ]
    fused = rrf_fusion(bm25_results, [], k=60, top_n=5)
    assert len(fused) == 1
    assert fused[0].chunk.chunk_id == "c1"
```

#### 4.4.2 集成测试

```python
# tests/integration/test_chroma_store.py
import pytest
import tempfile
import os
from knowledge_hub.providers.vectorstore.chroma_store import ChromaStore

@pytest.fixture
async def chroma_store():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ChromaStore(persist_path=tmpdir, collection_name="test")
        await store.init()
        yield store
        await store.cleanup()

@pytest.mark.asyncio
async def test_chroma_upsert_and_query(chroma_store):
    """测试 Chroma 向量写入和检索"""
    chunks = [
        {"chunk_id": "c1", "content": "hello world",
         "embedding": [0.1] * 1536, "metadata": {"source": "test"}},
        {"chunk_id": "c2", "content": "foo bar",
         "embedding": [0.2] * 1536, "metadata": {"source": "test"}},
    ]

    count = await chroma_store.upsert("test", chunks)
    assert count == 2

    results = await chroma_store.query("test", [0.1] * 1536, top_k=1)
    assert len(results) == 1
    assert results[0]["chunk_id"] == "c1"
```

#### 4.4.3 E2E 测试

```python
# tests/e2e/test_full_rag_flow.py
import pytest
import tempfile
from pathlib import Path

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_ingest_and_query_flow(test_app):
    """端到端：摄取一个 Markdown 文件 → 查询 → 验证回答"""
    # 1. 准备测试文档
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
        f.write("# RAG 简介\n\nRAG 是检索增强生成的缩写...")
        md_path = f.name

    # 2. 摄取
    result = await test_app.ingestion_pipeline.run(md_path)
    assert result.status == "success"
    assert result.chunk_count > 0

    # 3. 查询
    response = await test_app.retrieval_pipeline.query("RAG 是什么？")
    assert "检索增强生成" in response.answer
    assert len(response.contexts) > 0

    # 4. 验证 Trace
    assert response.trace.trace_id is not None
    assert len(response.trace.steps) > 5  # 至少经过 5 个步骤
```

### 4.5 RAG 质量评估

#### 4.5.1 评估指标

| 指标 | 类型 | 公式 | 说明 |
|------|------|------|------|
| **hit_rate** | 检索 | `命中查询数 / 总查询数` | Top-K 中是否包含正确文档 |
| **MRR** | 检索 | `mean(1/rank_of_first_hit)` | 第一个命中结果的倒数排名 |
| **context_precision** | 检索 | `相关chunk数 / 返回chunk总数` | 上下文精确率 |
| **context_recall** | 检索 | `召回的相关chunk数 / 总相关chunk数` | 上下文召回率 |
| **faithfulness** | 生成 | `答案中可被上下文支持的说法数 / 总说法数` | 忠实度（Ragas） |
| **answer_relevancy** | 生成 | LLM 评分 | 答案相关性（Ragas） |

#### 4.5.2 评估数据集格式

```json
// data/eval/eval_dataset.json
{
  "version": "1.0",
  "dataset": [
    {
      "query_id": "q001",
      "query": "什么是 RAG？",
      "ground_truth_doc_ids": ["doc_001"],
      "ground_truth_answer": "RAG 是检索增强生成...",
      "expected_chunks": ["chunk_001", "chunk_002"]
    },
    {
      "query_id": "q002",
      "query": "BM25 和 Dense 检索有什么区别？",
      "ground_truth_doc_ids": ["doc_002"],
      "ground_truth_answer": "BM25 是基于词频的稀疏检索...",
      "expected_chunks": ["chunk_010"]
    }
  ]
}
```

#### 4.5.3 评估执行

```python
# src/knowledge_hub/evaluation/evaluator.py
class EvaluationRunner:
    def __init__(self, settings: Settings):
        self.retrieval_pipeline = RetrievalPipeline(settings)
        self.metrics = {
            "hit_rate": HitRateMetric(),
            "mrr": MRRMetric(),
            "context_precision": ContextPrecisionMetric(),
        }
        if settings.evaluation.framework == "ragas":
            self.metrics["faithfulness"] = RagasFaithfulness()

    async def run(self, dataset_path: str) -> EvaluationReport:
        dataset = self._load_dataset(dataset_path)
        results = []

        for item in dataset:
            response = await self.retrieval_pipeline.query(item["query"])
            for name, metric in self.metrics.items():
                score = metric.compute(
                    query=item["query"],
                    response=response,
                    ground_truth=item,
                )
                results.append({
                    "query_id": item["query_id"],
                    "metric": name,
                    "score": score,
                })

        return EvaluationReport(results=results)
```

### 4.6 pytest 配置

```ini
# pyproject.toml [tool.pytest.ini_options]
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
markers = [
    "unit: 单元测试",
    "integration: 集成测试（需要本地存储）",
    "e2e: 端到端测试（需要完整环境）",
    "slow: 耗时较长的测试",
    "requires_llm: 需要 LLM API key 的测试",
]
addopts = [
    "-v",
    "--tb=short",
    "--strict-markers",
    "-m", "not requires_llm",  # 默认跳过需要 API key 的测试
]
```

---
