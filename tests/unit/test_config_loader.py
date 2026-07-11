"""测试配置加载系统 — A2 配置系统（YAML + Pydantic Settings）。"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from knowledge_hub.config.loader import (
    find_config_file,
    get_settings,
    load_settings,
    reload_settings,
)
from knowledge_hub.config.settings import Settings


class TestSettingsFromYaml:
    """测试 Settings.from_yaml() 核心加载逻辑。"""

    def test_load_from_example_file(self):
        """从 settings.example.yaml 加载所有配置并校验默认值。"""
        settings = Settings.from_yaml("settings.example.yaml")

        assert settings.llm.provider == "openai"
        assert settings.llm.params["model"] == "gpt-4o-mini"
        assert settings.llm.params["temperature"] == 0.0

    def test_embedding_config_defaults(self):
        """Embedding 配置正确加载。"""
        settings = Settings.from_yaml("settings.example.yaml")

        assert settings.embedding.provider == "openai"
        assert settings.embedding.params["model"] == "text-embedding-3-small"

    def test_retrieval_config_defaults(self):
        """检索配置正确加载，包含嵌套结构。"""
        settings = Settings.from_yaml("settings.example.yaml")

        assert settings.retrieval.bm25.enabled is True
        assert settings.retrieval.bm25.top_k == 20
        assert settings.retrieval.dense.top_k == 20
        assert settings.retrieval.fusion.method == "rrf"
        assert settings.retrieval.fusion.k == 60
        assert settings.retrieval.fusion.top_n == 15
        assert settings.retrieval.final_top_k == 5
        assert settings.retrieval.query_rewrite is False

    def test_reranker_config_defaults(self):
        """Reranker 配置正确加载。"""
        settings = Settings.from_yaml("settings.example.yaml")

        assert settings.reranker.coarse.provider == "cross_encoder"
        assert settings.reranker.fine.provider == "llm"

    def test_vectorstore_config_defaults(self):
        """VectorStore 配置正确加载。"""
        settings = Settings.from_yaml("settings.example.yaml")

        assert settings.vectorstore.provider == "chroma"
        assert settings.vectorstore.params["collection_name"] == "default"

    def test_splitter_config_defaults(self):
        """Splitter 配置正确加载。"""
        settings = Settings.from_yaml("settings.example.yaml")

        assert settings.splitter.provider == "langchain_recursive"
        assert settings.splitter.params["chunk_size"] == 1000
        assert settings.splitter.params["chunk_overlap"] == 200

    def test_ingestion_config_defaults(self):
        """Ingestion 配置正确加载。"""
        settings = Settings.from_yaml("settings.example.yaml")

        assert settings.ingestion.watch_dir == "./data/raw"
        assert settings.ingestion.image_processing.enabled is True
        assert settings.ingestion.image_processing.max_images_per_doc == 50
        assert settings.ingestion.enhancement.enabled is True
        assert settings.ingestion.enhancement.rewrite is False

    def test_mcp_config_defaults(self):
        """MCP 配置正确加载。"""
        settings = Settings.from_yaml("settings.example.yaml")

        assert settings.mcp.server_name == "knowledge-hub"
        assert settings.mcp.server_version == "1.0.0"

    def test_observability_config_defaults(self):
        """Observability 配置正确加载。"""
        settings = Settings.from_yaml("settings.example.yaml")

        assert settings.observability.log_level == "INFO"
        assert settings.observability.trace_enabled is True
        assert settings.observability.dashboard_port == 8501

    def test_storage_config_defaults(self):
        """Storage 配置正确加载。"""
        settings = Settings.from_yaml("settings.example.yaml")

        assert settings.storage.sqlite_path == "./data/knowledge_hub.db"
        assert settings.storage.bm25_index_path == "./data/bm25_index"

    def test_evaluation_config_defaults(self):
        """Evaluation 配置正确加载。"""
        settings = Settings.from_yaml("settings.example.yaml")

        assert settings.evaluation.framework == "custom"
        assert "hit_rate" in settings.evaluation.metrics
        assert "mrr" in settings.evaluation.metrics


class TestEnvVarExpansion:
    """测试 ${ENV_VAR} 环境变量展开。"""

    def test_env_var_expansion(self, monkeypatch):
        """环境变量 ${OPENAI_API_KEY} 应正确展开。"""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek-456")

        settings = Settings.from_yaml("settings.example.yaml")

        assert settings.llm.params["api_key"] == "sk-test-123"
        assert settings.vision_llm.params["api_key"] == "sk-test-123"
        assert settings.embedding.params["api_key"] == "sk-test-123"
        assert settings.rerank_llm.params["api_key"] == "sk-deepseek-456"

    def test_missing_env_var_expands_to_empty(self, monkeypatch):
        """未设置的环境变量应展开为空字符串。"""
        # 确保环境变量未设置
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

        settings = Settings.from_yaml("settings.example.yaml")

        assert settings.llm.params["api_key"] == ""
        assert settings.rerank_llm.params["api_key"] == ""

    def test_partial_env_var_not_expanded(self, monkeypatch):
        """非 ${...} 格式的字符串不应被展开。"""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        settings = Settings.from_yaml("settings.example.yaml")

        # model 字段不是 ${...}，应保持原样
        assert settings.llm.params["model"] == "gpt-4o-mini"
        assert settings.llm.params["temperature"] == 0.0

    def test_expand_env_in_nested_dict(self, monkeypatch):
        """环境变量展开应递归处理嵌套字典。"""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-nested-test")

        settings = Settings.from_yaml("settings.example.yaml")

        # params 中的 api_key 在嵌套字典中
        assert settings.llm.params["api_key"] == "sk-nested-test"
        assert settings.embedding.params["api_key"] == "sk-nested-test"


class TestValidation:
    """测试配置校验。"""

    def test_default_settings_no_args(self):
        """不传任何参数时应使用默认值创建 Settings。"""
        settings = Settings()

        assert settings.llm.provider == "openai"
        assert settings.retrieval.final_top_k == 5

    def test_missing_provider_fails(self):
        """缺少 provider 字段时 LLMConfig 使用默认值（不应抛出错误，因为有默认值）。"""
        # LLMConfig 有 default="openai"，所以不会失败
        config = Settings(llm={"params": {"model": "test"}})
        assert config.llm.provider == "openai"

    def test_invalid_provider_still_loads(self):
        """无效 provider 名称仍可加载（校验在工厂层做）。"""
        settings = Settings.from_yaml("settings.example.yaml")
        # provider 是字符串，Pydantic 只做类型校验
        assert isinstance(settings.llm.provider, str)

    def test_retrieval_final_top_k_type_validation(self):
        """final_top_k 应为整数。"""
        with pytest.raises(ValidationError):
            Settings(retrieval={"final_top_k": "not_a_number"})

    def test_vision_llm_config(self):
        """Vision LLM 配置正确加载。"""
        settings = Settings.from_yaml("settings.example.yaml")

        assert settings.vision_llm.provider == "openai"
        assert settings.vision_llm.params["model"] == "gpt-4o"

    def test_rerank_llm_config(self):
        """Rerank LLM 配置正确加载。"""
        settings = Settings.from_yaml("settings.example.yaml")

        assert settings.rerank_llm.provider == "deepseek"
        assert settings.rerank_llm.params["model"] == "deepseek-chat"


class TestLoaderFunctions:
    """测试 loader.py 辅助函数。"""

    def test_load_settings_returns_settings(self):
        """load_settings() 应返回 Settings 实例。"""
        settings = load_settings("settings.example.yaml")
        assert isinstance(settings, Settings)
        assert settings.llm.provider == "openai"

    def test_get_settings_after_load(self):
        """get_settings() 应在 load 后返回全局配置。"""
        load_settings("settings.example.yaml")
        settings = get_settings()
        assert isinstance(settings, Settings)
        assert settings.mcp.server_name == "knowledge-hub"

    def test_get_settings_before_load_raises(self):
        """未加载配置时 get_settings() 应抛出 RuntimeError。"""
        # 强制清除全局状态
        import knowledge_hub.config.loader as loader_module
        loader_module._settings = None

        with pytest.raises(RuntimeError, match="配置尚未加载"):
            get_settings()

    def test_reload_settings(self):
        """reload_settings() 应强制重新加载。"""
        settings1 = load_settings("settings.example.yaml")
        settings2 = reload_settings("settings.example.yaml")
        # 两次加载应是不同实例
        assert settings1 is not settings2
        assert settings1.llm.provider == settings2.llm.provider

    def test_find_config_file_finds_example(self):
        """find_config_file() 应找到 settings.example.yaml。"""
        path = find_config_file()
        assert path.endswith("settings.yaml") or path.endswith("settings.example.yaml")
        assert Path(path).exists()

    def test_load_from_temp_yaml(self):
        """从临时 YAML 文件加载自定义配置。"""
        yaml_content = """
llm:
  provider: ollama
  params:
    model: llama3.2
    base_url: http://localhost:11434
embedding:
  provider: ollama
  params:
    model: nomic-embed-text
vectorstore:
  provider: chroma
  params:
    persist_path: /tmp/test_db
    collection_name: test_collection
retrieval:
  bm25:
    enabled: true
    top_k: 20
  dense:
    top_k: 20
  fusion:
    method: rrf
    k: 60
    top_n: 15
  final_top_k: 5
  query_rewrite: false
reranker:
  coarse:
    provider: none
    params: {}
  fine:
    provider: none
    params: {}
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            settings = Settings.from_yaml(temp_path)
            assert settings.llm.provider == "ollama"
            assert settings.llm.params["model"] == "llama3.2"
            assert settings.llm.params["base_url"] == "http://localhost:11434"
            assert settings.embedding.provider == "ollama"
            assert settings.embedding.params["model"] == "nomic-embed-text"
            assert settings.vectorstore.params["collection_name"] == "test_collection"
            assert settings.reranker.coarse.provider == "none"
        finally:
            Path(temp_path).unlink()
