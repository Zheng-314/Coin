# 初始化RAG相关的全局变量
from config import (
    OPENAI_API_KEY, OPENAI_API_BASE, OPENAI_CHAT_MODEL,
    OPENAI_EMBED_MODEL, OPENAI_EMBED_API_BASE, OPENAI_EMBED_API_KEY,
    EMBED_PROVIDER_BLOCKED, RAG_IMPORTS_AVAILABLE, DATA_DIR, VECTOR_STORES_DIR
)

# 全局变量
llm = None
artifacts = None
global_search_engine = None
local_search_chain = None

# 尝试初始化LLM（即使没有GraphRAG依赖，也要初始化llm用于联网搜索）
if OPENAI_API_KEY:
    try:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            temperature=0,
            model_name=OPENAI_CHAT_MODEL,
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_API_BASE
        )
        print("LLM 初始化成功，联网搜索功能可用。")
    except Exception as e:
        print(f"LLM 初始化失败: {e}")
else:
    print("未检测到 OPENAI_API_KEY，GraphRAG 和联网总结功能将不可用。")

# 尝试初始化RAG系统
if not OPENAI_API_KEY:
    print("未检测到 OPENAI_API_KEY，GraphRAG 和联网总结功能将不可用。")
elif not RAG_IMPORTS_AVAILABLE:
    print("GraphRAG 依赖未安装，local/global 搜索将不可用。")
else:
    try:
        import pandas as pd
        import pickle
        from pathlib import Path
        from typing import cast, Any
        from langchain_graphrag.indexing.artifacts import IndexerArtifacts
        from langchain_openai import OpenAIEmbeddings, ChatOpenAI
        # 暂时跳过Chroma导入，避免Python 3.13兼容性问题
        # from langchain_chroma.vectorstores import Chroma as ChromaVectorStore
        from langchain_graphrag.query.global_search import GlobalSearch
        from langchain_graphrag.query.global_search.community_weight_calculator import CommunityWeightCalculator
        from langchain_graphrag.query.global_search.key_points_aggregator import (
            KeyPointsAggregator, KeyPointsAggregatorPromptBuilder, KeyPointsContextBuilder
        )
        from langchain_graphrag.query.global_search.key_points_generator import (
            CommunityReportContextBuilder, KeyPointsGenerator, KeyPointsGeneratorPromptBuilder
        )
        from langchain_graphrag.query.local_search import LocalSearch, LocalSearchPromptBuilder, LocalSearchRetriever
        from langchain_graphrag.query.local_search.context_builders import ContextBuilder
        from langchain_graphrag.query.local_search.context_selectors import ContextSelector
        from langchain_graphrag.types.graphs.community import CommunityLevel
        from langchain_graphrag.utils import TiktokenCounter

        def load_artifacts(path: Path) -> Any:
            """从指定路径读取 GraphRAG 的构件 (artifacts)。"""
            print(f"正在从以下路径加载构件: {path}")
            entities = pd.read_parquet(path / "artifacts/entities.parquet")
            relationships = pd.read_parquet(path / "artifacts/relationships.parquet")
            text_units = pd.read_parquet(path / "artifacts/text_units.parquet")
            communities_reports = pd.read_parquet(path / "artifacts/communities_reports.parquet")

            merged_graph, summarized_graph, communities = None, None, None

            merged_graph_pickled = path / "merged-graph.pickle"
            if merged_graph_pickled.exists():
                with merged_graph_pickled.open("rb") as fp:
                    merged_graph = pickle.load(fp)

            summarized_graph_pickled = path / "summarized-graph.pickle"
            if summarized_graph_pickled.exists():
                with summarized_graph_pickled.open("rb") as fp:
                    summarized_graph = pickle.load(fp)

            community_info_pickled = path / "community_info.pickle"
            if community_info_pickled.exists():
                with community_info_pickled.open("rb") as fp:
                    communities = pickle.load(fp)

            return IndexerArtifacts(
                entities=entities,
                relationships=relationships,
                text_units=text_units,
                communities_reports=communities_reports,
                merged_graph=merged_graph,
                summarized_graph=summarized_graph,
                communities=communities,
            )

        print("正在初始化 GraphRAG 问答系统...")
        artifacts = load_artifacts(DATA_DIR)

        # 如果llm还没有初始化，在这里初始化
        if not llm:
            llm = ChatOpenAI(
                temperature=0,
                model_name=OPENAI_CHAT_MODEL,
                api_key=OPENAI_API_KEY,
                base_url=OPENAI_API_BASE
            )

        # 全局搜索组件
        try:
            report_context_builder = CommunityReportContextBuilder(
                community_level=cast(CommunityLevel, 0),
                weight_calculator=CommunityWeightCalculator(),
                artifacts=artifacts,
                token_counter=TiktokenCounter(),
            )

            kp_generator = KeyPointsGenerator(
                llm=llm,
                prompt_builder=KeyPointsGeneratorPromptBuilder(show_references=True, repeat_instructions=True),
                context_builder=report_context_builder,
            )

            kp_aggregator = KeyPointsAggregator(
                llm=llm,
                prompt_builder=KeyPointsAggregatorPromptBuilder(show_references=True, repeat_instructions=True),
                context_builder=KeyPointsContextBuilder(token_counter=TiktokenCounter()),
                output_raw=True,
            )

            global_search_engine = GlobalSearch(
                kp_generator=kp_generator,
                kp_aggregator=kp_aggregator,
                generation_chain_config={"tags": ["kp-generation"]},
                aggregation_chain_config={"tags": ["kp-aggregation"]},
            )
            print("GraphRAG 全局搜索初始化成功。")
        except Exception as e:
            global_search_engine = None
            print(f"GraphRAG 全局搜索初始化失败: {e}")

        # 本地搜索组件
        try:
            if EMBED_PROVIDER_BLOCKED:
                raise RuntimeError(
                    "当前 Embedding API 指向 DeepSeek，未提供 OpenAI embeddings 兼容端点；已禁用 local search。"
                )

            # 暂时跳过Chroma初始化，避免Python 3.13兼容性问题
            # entities_vector_store = ChromaVectorStore(
            #     collection_name="entity-embedding",
            #     persist_directory=str(VECTOR_STORES_DIR),
            #     embedding_function=OpenAIEmbeddings(
            #         model=OPENAI_EMBED_MODEL,
            #         openai_api_base=OPENAI_EMBED_API_BASE,
            #         openai_api_key=OPENAI_EMBED_API_KEY
            #     )
            # )
            # 直接设置为None，这样local_search_chain会被设置为None
            entities_vector_store = None

            # 暂时跳过local search初始化，避免Python 3.13兼容性问题
            # context_selector = ContextSelector.build_default(
            #     entities_vector_store=entities_vector_store,
            #     entities_top_k=10,
            #     community_level=cast(CommunityLevel, 2),
            # )
            # 
            # context_builder = ContextBuilder.build_default(token_counter=TiktokenCounter())
            # 
            # retriever = LocalSearchRetriever(
            #     context_selector=context_selector,
            #     context_builder=context_builder,
            #     artifacts=artifacts,
            # )
            # 
            # local_search_engine = LocalSearch(
            #     prompt_builder=LocalSearchPromptBuilder(show_references=True, repeat_instructions=True),
            #     llm=llm,
            #     retriever=retriever,
            # )
            # local_search_chain = local_search_engine()
            # print("GraphRAG 本地搜索初始化成功。")
            local_search_chain = None
            print("GraphRAG 本地搜索暂时不可用，因为Chroma与Python 3.13不兼容。")
        except Exception as e:
            local_search_chain = None
            print(f"GraphRAG 本地搜索初始化失败: {e}")

        if global_search_engine is not None or local_search_chain is not None:
            print("GraphRAG 问答系统部分可用。")
        else:
            print("GraphRAG 问答系统初始化失败，将使用离线兜底。")
    except Exception as e:
        print(f"GraphRAG 初始化失败，系统将继续以降级模式运行: {e}")

__all__ = [
    'llm',
    'artifacts',
    'global_search_engine',
    'local_search_chain'
]