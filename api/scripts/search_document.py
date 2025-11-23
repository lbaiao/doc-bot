#!/usr/bin/env python3
import argparse
import sys
import os
from typing import Optional

# Ensure project root is on sys.path when running as a script (python scripts/xxx.py)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
	sys.path.insert(0, PROJECT_ROOT)

from analyzer.schemas import DocumentTypes
from analyzer.woosh_searcher import WooshSearcher


def _read_preview(path: Optional[str], max_chars: int = 100) -> Optional[str]:
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
		description="Query the Whoosh index for a given PDF (by name without extension) using SwooshSearcher."
	)
	ap.add_argument("file_name", help="PDF file name without extension (folder under extraction/)")
	ap.add_argument("query", help="Lexical query string (Whoosh syntax supported)")
	ap.add_argument(
		"--type",
		dest="doc_type",
		default="any",
		choices=["any", DocumentTypes.CHUNK, DocumentTypes.IMAGE_CAPTION],
		help="Filter results by document type (default: any)",
	)
	ap.add_argument("--limit", type=int, default=10, help="Max results to return (default: 10)")
	ap.add_argument("--show-text", action="store_true", help="Show a short preview from the file when possible")
	ap.add_argument("--max-chars", type=int, default=240, help="Max preview characters (default: 240)")
	args = ap.parse_args(argv)

	try:
		with WooshSearcher(pdf_name=args.file_name) as s:
			# Fetch previews sized according to user preference when --show-text is set,
			# else keep them lightweight (100 chars) and we will also print a fixed content100.
			preview_len = args.max_chars if args.show_text else 100
			hits = s.search(
				args.query,
				doc_type=args.doc_type,
				limit=args.limit,
				return_preview=True,
				max_preview_chars=preview_len,
			)
	except FileNotFoundError as e:
		sys.stderr.write(str(e) + "\n")
		return 2
	except Exception as e:
		sys.stderr.write(f"Error: {e}\n")
		return 1

	if not hits:
		print("No results.")
		return 0

	print(f"Top {len(hits)} results:")
	for i, r in enumerate(hits, start=1):
		rid = r.get("id")
		rtype = r.get("type")
		order = r.get("order")
		page_index = r.get("page_index")
		path = r.get("path")
		score = r.get("score")
		header = f"[{i:02d}] score={score:.4f} id={rid} type={rtype}"
		metas = []
		if order is not None:
			metas.append(f"order={order}")
		if page_index is not None:
			metas.append(f"page_index={page_index}")
		if path:
			metas.append(f"path={path}")
		if metas:
			header += "  (" + ", ".join(metas) + ")"
		print(header)
		# Always print up to 100 chars of content from the underlying file when available
		# Prefer the preview we already fetched (slice to 100), otherwise read from disk.
		prev = r.get("preview")
		snippet = (prev[:100] if isinstance(prev, str) and prev else None) or _read_preview(path, max_chars=100)
		if snippet:
			print("    content100: " + snippet)
		# Optionally print a longer preview if requested by the user (up to --max-chars)
		if args.show_text:
			long_prev = prev if isinstance(prev, str) and prev else _read_preview(path, max_chars=args.max_chars)
			if long_prev:
				print("    preview:    " + long_prev)

	return 0


if __name__ == "__main__":
	raise SystemExit(main())

