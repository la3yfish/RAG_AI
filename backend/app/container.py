from __future__ import annotations

from dataclasses import dataclass

from backend.core.interfaces import (
    IEmbedder,
    IIngestor,
    ILogSink,
    IReranker,
    IVectorStore,
    IChunker,
)

from .settings import Settings


@dataclass(frozen=True)
class Container:
    settings: Settings
    vectorstore: IVectorStore
    embedder: IEmbedder
    chunker: IChunker
    reranker: IReranker
    ingestors: list[IIngestor]
    log_sink: ILogSink


def build_container(settings: Settings) -> Container:
    # Import adapters lazily so core stays clean and to avoid import-time SDK costs.
    vectorstore = _build_vectorstore(settings)
    embedder = _build_embedder(settings)
    chunker = _build_chunker(settings)
    reranker = _build_reranker(settings)
    ingestors = _build_ingestors(settings)
    log_sink = _build_log_sink(settings)

    return Container(
        settings=settings,
        vectorstore=vectorstore,
        embedder=embedder,
        chunker=chunker,
        reranker=reranker,
        ingestors=ingestors,
        log_sink=log_sink,
    )


def _build_vectorstore(settings: Settings) -> IVectorStore:
    provider = settings.vectorstore_provider
    if provider == "qdrant":
        from backend.adapters.vectorstores.qdrant_store import QdrantVectorStore
        return QdrantVectorStore(
            url=settings.qdrant_url,
            collection=settings.qdrant_collection,
        )
    if provider == "chroma":
        from backend.adapters.vectorstores.chroma_store import ChromaVectorStore
        return ChromaVectorStore(
            path=settings.chroma_path,
            collection=settings.chroma_collection,
        )
    raise ValueError(f"Unknown vectorstore provider: {provider}")


def _build_embedder(settings: Settings) -> IEmbedder:
    provider = settings.embeddings_provider
    if provider == "openai":
        from backend.adapters.embedders.openai_embedder import OpenAIEmbedder
        return OpenAIEmbedder(model=settings.openai_embedding_model)
    if provider == "stub":
        from backend.adapters.embedders.stub_embedder import StubEmbedder
        return StubEmbedder(dim=settings.stub_embedding_dim)
    raise ValueError(f"Unknown embeddings provider: {provider}")


def _build_chunker(settings: Settings) -> IChunker:
    # Core chunker implementation can be simple, but we will wrap it
    # with safe_runner in adapters if needed.
    from backend.adapters.chunkers.default_chunker import DefaultChunker
    base = DefaultChunker()

    # Safety wrapper can be toggled later via config flags.
    # For MVP, you can keep it always on for chunker tests.
    from backend.adapters.sandbox.safe_chunker import SafeChunker
    return SafeChunker(base_chunker=base)


def _build_reranker(settings: Settings) -> IReranker:
    # MVP: no reranking or a trivial score passthrough.
    from backend.adapters.rerankers.stub_reranker import StubReranker
    return StubReranker()


def _build_ingestors(settings: Settings) -> list[IIngestor]:
    # MVP: enable the core set of ingestors.
    # Order here is not critical because selection is by can_handle(),
    # but we keep it predictable.
    from backend.adapters.ingestors.md_ingestor import MarkdownIngestor
    from backend.adapters.ingestors.csv_ingestor import CsvIngestor
    from backend.adapters.ingestors.docx_ingestor import DocxIngestor
    from backend.adapters.ingestors.pdf_ingestor import PdfIngestor

    return [
        CsvIngestor(),
        MarkdownIngestor(),
        DocxIngestor(),
        PdfIngestor(),
    ]



def _build_log_sink(settings: Settings) -> ILogSink:
    # MVP: JSON lines to stdout
    from backend.adapters.logging.stdout_log_sink import StdoutJsonLogSink
    return StdoutJsonLogSink()
