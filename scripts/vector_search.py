#!/usr/bin/env python3
import argparse
import sys
import os
from typing import Optional

# Ensure project root is on sys.path when running as a script (python scripts/xxx.py)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
	sys.path.insert(0, PROJECT_ROOT)

from analyzer.config import default_config
from analyzer.faiss_wrapper import FaissWrapper


def _read_preview(path: Optional[str], max_chars: int = 100) -> Optional[str]:
	"""Read a preview of text from a file path."""
	if not path or not os.path.isfile(path):
		return None
	try:
		with open(path, "r", encoding="utf-8") as f:
			text = f.read(max_chars * 4)
		text = text.replace("\n", " ").strip()
		if len(text) > max_chars:
			text = text[: max_chars - 3] + "..."
		return text
	except Exception:
		return None


def main(argv: Optional[list[str]] = None) -> int:
	ap = argparse.ArgumentParser(
		description="Query the FAISS vector index for a given PDF (by name without extension) using semantic similarity search."
	)
	ap.add_argument("file_name", help="PDF file name without extension (folder under extraction/)")
	ap.add_argument("query", help="Natural language query for semantic search")
	ap.add_argument("--limit", type=int, default=5, help="Max results to return (default: 5)")
	ap.add_argument("--show-text", action="store_true", help="Show a short preview from the chunk file when possible")
	ap.add_argument("--max-chars", type=int, default=240, help="Max preview characters (default: 240)")
	ap.add_argument("--force-rebuild", action="store_true", help="Force rebuilding the FAISS index even if it exists")
	ap.add_argument("--image-captions", action="store_true", help="Search image captions index instead of text chunks")
	args = ap.parse_args(argv)

	# Build extraction directory path
	extraction_dir = os.path.join(default_config.EXTRACTION_DIR, args.file_name)
	
	if not os.path.exists(extraction_dir):
		sys.stderr.write(f"Error: Extraction directory not found: {extraction_dir}\n")
		sys.stderr.write(f"Make sure the PDF '{args.file_name}' has been processed.\n")
		return 2

	try:
		# Initialize FAISS wrapper
		faiss_wrapper = FaissWrapper()
		
		# Load or create FAISS index (either text chunks or image captions)
		if args.image_captions:
			index_loaded = faiss_wrapper.index_image_captions(extraction_dir, force_rebuild=args.force_rebuild)
			index_type = "image captions"
		else:
			index_loaded = faiss_wrapper.index_extraction_directory(extraction_dir, force_rebuild=args.force_rebuild)
			index_type = "text chunks"
		
		if not index_loaded:
			sys.stderr.write(f"Error: Failed to load or create FAISS {index_type} index for '{args.file_name}'\n")
			return 1
		
		# Get index information
		index_info = faiss_wrapper.get_index_info()
		if index_info.get("status") == "loaded":
			print(f"Loaded FAISS {index_type} index: {index_info.get('total_documents', 0)} documents, "
			      f"{index_info.get('embedding_dimension', 0)}D embeddings")
			print(f"Model: {index_info.get('embedding_model', 'unknown')}")
			print(f"Distance strategy: {index_info.get('distance_strategy', 'unknown')}")
			print()
		
		# Perform semantic search
		results = faiss_wrapper.search(args.query, k=args.limit)
		
	except FileNotFoundError as e:
		sys.stderr.write(f"File not found: {e}\n")
		return 2
	except Exception as e:
		sys.stderr.write(f"Error: {e}\n")
		return 1

	if not results:
		print("No results found.")
		return 0

	print(f"Top {len(results)} semantic search results for: \"{args.query}\"")
	print("=" * 60)
	
	for i, (document, score) in enumerate(results, start=1):
		# Extract metadata
		metadata = document.metadata
		source_type = metadata.get("source", "")
		
		# Format header differently for image captions vs text chunks
		if source_type == "image_caption":
			page_idx = metadata.get("page_index", "unknown")
			image_idx = metadata.get("image_index", "unknown")
			image_path = metadata.get("image_path", "")
			header = f"[{i:02d}] similarity={score:.4f} page={page_idx} image={image_idx}"
		else:
			chunk_number = metadata.get("chunk_number", "unknown")
			filename = metadata.get("filename", "unknown")
			header = f"[{i:02d}] similarity={score:.4f} chunk={chunk_number}"
			if filename != "unknown":
				header += f" file={filename}"
		
		print(header)
		
		# Show document content preview (always show some content from the document)
		content = document.page_content.strip()
		if content:
			# Always show a short preview
			short_preview = content.replace("\n", " ")[:100]
			if len(content) > 100:
				short_preview += "..."
			print(f"    content100: {short_preview}")
			
			# Show longer preview if requested
			if args.show_text:
				long_preview = content.replace("\n", " ")[:args.max_chars]
				if len(content) > args.max_chars:
					long_preview += "..."
				print(f"    preview:    {long_preview}")
		
		# Show source file path if available
		if source_type == "image_caption":
			image_path = metadata.get("image_path", "")
			if image_path:
				print(f"    image:      {image_path}")
		else:
			source_path = metadata.get("source", "")
			if source_path:
				print(f"    source:     {source_path}")
		
		print()  # Add spacing between results

	return 0


if __name__ == "__main__":
	raise SystemExit(main())
