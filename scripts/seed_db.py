#!/usr/bin/env python3
"""
scripts/seed_db.py
───────────────────
Seeds the ChromaDB vector store with initial knowledge base documents.
Run once after standing up the stack: `make seed`
"""

import asyncio
import json
from pathlib import Path

from src.core.logging import configure_logging, get_logger
from src.utils.chunker import chunk_documents
from src.utils.embeddings import EmbeddingService

logger = get_logger(__name__)

SEED_DOCUMENTS = [
    {
        "id": "intro-nexus",
        "text": (
            "AI engineering combines software engineering best practices with machine learning "
            "to build production-grade AI systems. Key concerns include reliability, observability, "
            "latency, cost management, and safety. Unlike research ML, production AI demands "
            "robust error handling, fallback strategies, and continuous evaluation pipelines."
        ),
        "metadata": {"category": "fundamentals", "source": "seed"},
    },
    {
        "id": "mcp-protocol",
        "text": (
            "The Model Context Protocol (MCP) is an open standard by Anthropic that enables "
            "AI models to securely connect to external data sources and tools. MCP servers expose "
            "resources, tools, and prompts via JSON-RPC over stdio or HTTP+SSE transport. "
            "Clients (like Claude Desktop) discover and invoke these capabilities dynamically."
        ),
        "metadata": {"category": "mcp", "source": "seed"},
    },
    {
        "id": "rag-overview",
        "text": (
            "Retrieval-Augmented Generation (RAG) grounds LLM responses in external knowledge. "
            "The pipeline: (1) chunk documents into fixed-token segments with overlap, "
            "(2) embed chunks into a vector space, (3) at query time, embed the user question "
            "and retrieve the top-k most similar chunks via cosine similarity, "
            "(4) inject retrieved chunks into the LLM context. This reduces hallucination "
            "and allows the model to cite specific sources."
        ),
        "metadata": {"category": "rag", "source": "seed"},
    },
    {
        "id": "tool-use-patterns",
        "text": (
            "Effective tool use patterns for LLMs: (1) define precise JSON schemas so the model "
            "generates valid inputs, (2) return structured data, not prose, from tools, "
            "(3) handle tool errors gracefully and return error info back to the model, "
            "(4) set iteration limits on the agentic loop to prevent infinite cycles, "
            "(5) log every tool invocation with inputs and outputs for debugging and auditing."
        ),
        "metadata": {"category": "tools", "source": "seed"},
    },
]


async def main() -> None:
    configure_logging()
    svc = EmbeddingService()

    logger.info("seeding_start", documents=len(SEED_DOCUMENTS))
    chunks = chunk_documents(SEED_DOCUMENTS, chunk_size=256, chunk_overlap=32)
    logger.info("chunks_created", count=len(chunks))

    await svc.upsert(chunks)
    logger.info("seeding_complete", chunks_upserted=len(chunks))
    print(f"✅ Seeded {len(chunks)} chunks from {len(SEED_DOCUMENTS)} documents.")


if __name__ == "__main__":
    asyncio.run(main())
