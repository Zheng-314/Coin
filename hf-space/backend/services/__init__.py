import logging
from config import (
    OPENAI_API_KEY,
    OPENAI_API_BASE,
    OPENAI_CHAT_MODEL,
    OPENAI_EMBED_MODEL,
    OPENAI_EMBED_API_BASE,
    OPENAI_EMBED_API_KEY,
    EMBED_PROVIDER_BLOCKED,
    RAG_IMPORTS_AVAILABLE,
    DATA_DIR,
    VECTOR_STORES_DIR,
)

logger = logging.getLogger('services.init')

llm = None
artifacts = None
global_search_engine = None
local_search_chain = None
global_search_reason = ""
local_search_reason = ""

if OPENAI_API_KEY:
    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            temperature=0,
            model_name=OPENAI_CHAT_MODEL,
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_API_BASE,
        )
        logger.info("LLM initialized for QA features.")
    except Exception as e:
        logger.error(f"LLM initialization failed: {e}")
else:
    logger.warning("OPENAI_API_KEY is missing. GraphRAG and web QA summary are disabled.")

if not OPENAI_API_KEY:
    logger.warning("Skipping GraphRAG initialization because OPENAI_API_KEY is missing.")
elif not RAG_IMPORTS_AVAILABLE:
    logger.warning("Skipping GraphRAG initialization because required packages are missing.")
else:
    try:
        import pickle
        from pathlib import Path
        from typing import Any, cast

        import pandas as pd
        from langchain_chroma.vectorstores import Chroma as ChromaVectorStore
        from langchain_graphrag.indexing.artifacts import IndexerArtifacts
        from langchain_graphrag.query.global_search import GlobalSearch
        from langchain_graphrag.query.global_search.community_weight_calculator import CommunityWeightCalculator
        from langchain_graphrag.query.global_search.key_points_aggregator import (
            KeyPointsAggregator,
            KeyPointsAggregatorPromptBuilder,
            KeyPointsContextBuilder,
        )
        from langchain_graphrag.query.global_search.key_points_generator import (
            CommunityReportContextBuilder,
            KeyPointsGenerator,
            KeyPointsGeneratorPromptBuilder,
        )
        from langchain_graphrag.query.local_search import (
            LocalSearch,
            LocalSearchPromptBuilder,
            LocalSearchRetriever,
        )
        from langchain_graphrag.query.local_search.context_builders import ContextBuilder
        from langchain_graphrag.query.local_search.context_selectors import ContextSelector
        from langchain_graphrag.types.graphs.community import CommunityLevel
        from langchain_graphrag.utils import TiktokenCounter
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings

        def load_artifacts(path: Path) -> Any:
            logger.info(f"Loading GraphRAG artifacts from: {path}")
            entities = pd.read_parquet(path / "artifacts/entities.parquet")
            relationships = pd.read_parquet(path / "artifacts/relationships.parquet")
            text_units = pd.read_parquet(path / "artifacts/text_units.parquet")
            communities_reports = pd.read_parquet(path / "artifacts/communities_reports.parquet")

            merged_graph, summarized_graph, communities = None, None, None

            merged_graph_pickled = path / "artifacts/merged-graph.pickle"
            if merged_graph_pickled.exists():
                with merged_graph_pickled.open("rb") as fp:
                    merged_graph = pickle.load(fp)

            summarized_graph_pickled = path / "artifacts/summarized-graph.pickle"
            if summarized_graph_pickled.exists():
                with summarized_graph_pickled.open("rb") as fp:
                    summarized_graph = pickle.load(fp)

            community_info_pickled = path / "artifacts/community_info.pickle"
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

        logger.info("Initializing GraphRAG QA services...")
        artifacts = load_artifacts(DATA_DIR)

        if not llm:
            llm = ChatOpenAI(
                temperature=0,
                model_name=OPENAI_CHAT_MODEL,
                api_key=OPENAI_API_KEY,
                base_url=OPENAI_API_BASE,
            )

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
            logger.info("Global GraphRAG search initialized.")
        except Exception as e:
            global_search_engine = None
            global_search_reason = str(e)
            logger.error(f"Global GraphRAG search failed to initialize: {e}")

        try:
            if EMBED_PROVIDER_BLOCKED:
                raise RuntimeError("embedding provider does not support local search")

            entities_vector_store = ChromaVectorStore(
                collection_name="entity-embedding",
                persist_directory=str(VECTOR_STORES_DIR),
                embedding_function=OpenAIEmbeddings(
                    model=OPENAI_EMBED_MODEL,
                    openai_api_base=OPENAI_EMBED_API_BASE,
                    openai_api_key=OPENAI_EMBED_API_KEY,
                ),
            )
            collection_count = entities_vector_store._collection.count()
            if collection_count <= 0:
                raise RuntimeError("local vector store is empty")

            context_selector = ContextSelector.build_default(
                entities_vector_store=entities_vector_store,
                entities_top_k=10,
                community_level=cast(CommunityLevel, 2),
            )
            context_builder = ContextBuilder.build_default(token_counter=TiktokenCounter())
            retriever = LocalSearchRetriever(
                context_selector=context_selector,
                context_builder=context_builder,
                artifacts=artifacts,
            )
            local_search_engine = LocalSearch(
                prompt_builder=LocalSearchPromptBuilder(show_references=True, repeat_instructions=True),
                llm=llm,
                retriever=retriever,
            )
            local_search_chain = local_search_engine()
            logger.info(f"Local GraphRAG search initialized. vectors={collection_count}")
        except Exception as e:
            local_search_chain = None
            local_search_reason = str(e)
            logger.error(f"Local GraphRAG search failed to initialize: {e}")

        if global_search_engine is not None or local_search_chain is not None:
            logger.info("GraphRAG QA is partially available.")
        else:
            logger.warning("GraphRAG QA is unavailable. The app will use offline fallback.")
    except Exception as e:
        logger.error(f"GraphRAG initialization failed: {e}")

__all__ = [
    "llm",
    "artifacts",
    "global_search_engine",
    "local_search_chain",
    "global_search_reason",
    "local_search_reason",
]
