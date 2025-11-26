#!/usr/bin/env python
"""
Recreate Qdrant collections for text/image/table embeddings with proper config.

This drops existing collections (if they exist) and recreates them with:
 - COSINE distance
 - size 768
 - text payload index on `text` for the text collection (for hybrid/lexical search)

Usage:
  DATABASE_URL env not required; uses Qdrant env vars:
    QDRANT_URL (default: http://localhost:6333)
    QDRANT_API_KEY (optional)

  python scripts/recreate_qdrant_collections.py
"""

import os
import sys

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, TextIndexParams, TokenizerType


COLLECTIONS = {
    "text_chunks": {
        "size": 768,
        "with_text_index": True,
    },
    "image_embeddings": {
        "size": 768,
        "with_text_index": False,
    },
    "table_embeddings": {
        "size": 768,
        "with_text_index": False,
    },
}


def recreate_collections():
    url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    api_key = os.environ.get("QDRANT_API_KEY")

    client = QdrantClient(url=url, api_key=api_key)

    for name, cfg in COLLECTIONS.items():
        print(f"Recreating collection: {name}")
        try:
            client.delete_collection(name)
            print(f" - Dropped existing collection {name}")
        except Exception as e:
            print(f" - No existing collection or failed to drop ({e})")

        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=cfg["size"], distance=Distance.COSINE),
        )
        print(f" - Created collection {name} (size={cfg['size']}, COSINE)")

        if cfg.get("with_text_index"):
            try:
                client.create_payload_index(
                    collection_name=name,
                    field_name="text",
                    field_schema=TextIndexParams(
                        tokenizer=TokenizerType.WORD,
                        min_token_len=2,
                        lowercase=True,
                    ),
                )
                print(" - Created text payload index on field 'text'")
            except Exception as e:
                print(f" - Failed to create text index: {e}")

    print("✅ Done. You should re-run ingestion to repopulate points.")


if __name__ == "__main__":
    try:
        recreate_collections()
    except Exception as exc:
        print(f"❌ Error: {exc}")
        sys.exit(1)
