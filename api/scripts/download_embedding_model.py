#!/usr/bin/env python
"""
Download an embeddings model from Hugging Face to a local directory.

Usage:
  python scripts/download_embedding_model.py --model google/embeddinggemma-300m
  HF_TOKEN=... python scripts/download_embedding_model.py
"""

import argparse
import os
from pathlib import Path

from huggingface_hub import snapshot_download

from analyzer.config import default_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download HF embeddings model")
    parser.add_argument(
        "--model",
        default=default_config.FAISS_EMBEDDING_MODEL,
        help="Hugging Face model repo id",
    )
    parser.add_argument(
        "--output-dir",
        default="models",
        help="Directory to place the downloaded model",
    )
    parser.add_argument(
        "--hf-token",
        default=os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN"),
        help="HF token for restricted models (env HF_TOKEN also works)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_id = args.model

    target_root = Path(args.output_dir)
    target_root.mkdir(parents=True, exist_ok=True)
    # Keep each model in its own folder, e.g., google__embeddinggemma-300m
    safe_name = repo_id.replace("/", "__")
    dest_dir = target_root / safe_name
    dest_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading '{repo_id}' to '{dest_dir}'")
    if args.hf_token:
        print("Using provided HF token (via flag/env)")
    else:
        print("No HF token provided; this will only work for fully public models.")

    snapshot_download(
        repo_id=repo_id,
        local_dir=str(dest_dir),
        local_dir_use_symlinks=False,
        token=args.hf_token,
        resume_download=True,
    )
    print("✅ Download complete")
    print(f"Files stored under: {dest_dir}")


if __name__ == "__main__":
    main()
