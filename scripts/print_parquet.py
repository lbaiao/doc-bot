import argparse
import os
import sys
import datetime as dt
from typing import Any, Dict, List, Optional, Tuple
import pyarrow as pa
import pandas as pd

#!/usr/bin/env python3
"""
print_parquet.py

CLI to print the first N rows of a Parquet file along with useful metadata.

Usage:
    python print_parquet.py /path/to/file.parquet [-n 20] [--stats] [--no-data] [--columns col1,col2]

Requires:
    - pyarrow
    - pandas
"""


try:
        import pyarrow.parquet as pq
except ImportError as e:
        sys.stderr.write("This script requires 'pyarrow' and 'pandas'. Install them with:\n")
        sys.stderr.write("  pip install pyarrow pandas\n")
        sys.exit(1)


def human_bytes(n: int) -> str:
        if n is None:
                return "unknown"
        units = ["B", "KB", "MB", "GB", "TB", "PB"]
        i = 0
        f = float(n)
        while f >= 1024 and i < len(units) - 1:
                f /= 1024.0
                i += 1
        return f"{f:.2f} {units[i]}"


def safe_decode(b: Optional[bytes]) -> Optional[str]:
        if b is None:
                return None
        for enc in ("utf-8", "utf-16", "latin-1"):
                try:
                        return b.decode(enc)
                except Exception:
                        continue
        return repr(b)


def print_file_info(path: str) -> None:
        print(f"File: {path}")
        try:
                st = os.stat(path)
                print(f"  Size: {human_bytes(st.st_size)} ({st.st_size} bytes)")
                print(f"  Modified: {dt.datetime.fromtimestamp(st.st_mtime).isoformat()}")
                print(f"  Created:  {dt.datetime.fromtimestamp(st.st_ctime).isoformat()}")
        except Exception as e:
                print(f"  [!] Could not stat file: {e}")


def print_parquet_metadata(pf: pq.ParquetFile) -> None:
        meta = pf.metadata  # type: ignore[attr-defined]
        print("Parquet metadata:")
        print(f"  Num rows:      {meta.num_rows}")
        try:
                num_cols = meta.num_columns  # may not exist in some versions
        except Exception:
                # fall back to arrow schema
                num_cols = len(pf.schema_arrow)
        print(f"  Num columns:   {num_cols}")
        print(f"  Num row groups:{meta.num_row_groups}")
        created_by = getattr(meta, "created_by", None)
        if created_by:
                print(f"  Created by:    {created_by}")
        print(f"  Format ver.:   {getattr(meta, 'format_version', 'unknown')}")
        kv = getattr(meta, "metadata", None)
        if isinstance(kv, dict) and kv:
                print("  Key-Value metadata:")
                for k, v in kv.items():
                        k_s = safe_decode(k if isinstance(k, (bytes, bytearray)) else str(k).encode())
                        v_s = safe_decode(v if isinstance(v, (bytes, bytearray)) else str(v).encode())
                        print(f"    {k_s}: {v_s}")

        # Row group summary
        if meta.num_row_groups > 0:
                print("Row groups:")
                for i in range(meta.num_row_groups):
                        rg = meta.row_group(i)
                        rows = rg.num_rows
                        size = getattr(rg, "total_byte_size", None)
                        size_s = human_bytes(size) if size is not None else "unknown"
                        print(f"  - RG {i}: rows={rows}, size≈{size_s}")


def print_schema(pf: pq.ParquetFile, max_cols: int = 200) -> None:
        schema = pf.schema_arrow
        print("Schema (Arrow):")
        shown = 0
        for field in schema:
                nullable = "nullable" if field.nullable else "required"
                print(f"  - {field.name}: {field.type} ({nullable})")
                shown += 1
                if shown >= max_cols and len(schema) > shown:
                        print(f"  ... {len(schema) - shown} more columns")
                        break


def collect_compressions(pf: pq.ParquetFile) -> Dict[str, List[str]]:
        meta = pf.metadata
        result: Dict[str, List[str]] = {}
        try:
                for col_idx, name in enumerate(pf.schema_arrow.names):
                        algos = set()
                        for rg_i in range(meta.num_row_groups):
                                try:
                                        col = meta.row_group(rg_i).column(col_idx)
                                        algo = getattr(col, "compression", None)
                                        if algo is not None:
                                                algos.add(str(algo))
                                except Exception:
                                        pass
                        result[name] = sorted(algos) if algos else []
        except Exception:
                pass
        return result


def print_compressions(pf: pq.ParquetFile) -> None:
        comp = collect_compressions(pf)
        any_comp = any(v for v in comp.values())
        if not any_comp:
                return
        print("Column compression:")
        for name, algos in comp.items():
                if algos:
                        print(f"  - {name}: {', '.join(algos)}")


def aggregate_column_stats(
        pf: pq.ParquetFile, limit_cols: Optional[int] = 10
) -> List[Tuple[str, Any, Any, Optional[int]]]:
        meta = pf.metadata
        fields = pf.schema_arrow
        out: List[Tuple[str, Any, Any, Optional[int]]] = []
        num_cols = len(fields)
        cols_to_process = range(num_cols if limit_cols is None else min(num_cols, limit_cols))
        for col_idx in cols_to_process:
                name = fields[col_idx].name
                min_val = None
                max_val = None
                nulls: Optional[int] = 0
                any_stats = False
                for rg_i in range(meta.num_row_groups):
                        try:
                                col = meta.row_group(rg_i).column(col_idx)
                                stats = getattr(col, "statistics", None)
                                if stats is None:
                                        continue
                                any_stats = True
                                if stats.has_min_max:
                                        # pyarrow returns python scalars already
                                        cmin = stats.min
                                        cmax = stats.max
                                        if cmin is not None:
                                                min_val = cmin if min_val is None else (cmin if cmin < min_val else min_val)
                                        if cmax is not None:
                                                max_val = cmax if max_val is None else (cmax if cmax > max_val else max_val)
                                if hasattr(stats, "null_count") and stats.null_count is not None:
                                        nulls = (nulls or 0) + int(stats.null_count)
                        except Exception:
                                continue
                if any_stats:
                        out.append((name, min_val, max_val, nulls))
        return out


def format_value_for_print(v: Any, max_len: int = 120) -> str:
        s = repr(v)
        if len(s) > max_len:
                s = s[: max_len - 3] + "..."
        return s


def print_stats(pf: pq.ParquetFile, max_cols: int = 10) -> None:
        stats = aggregate_column_stats(pf, max_cols)
        if not stats:
                print("No column statistics available in metadata.")
                return
        print(f"Column stats (first {min(max_cols, len(stats))} columns with stats):")
        for name, mn, mx, nulls in stats:
                mn_s = format_value_for_print(mn)
                mx_s = format_value_for_print(mx)
                nulls_s = "unknown" if nulls is None else str(nulls)
                print(f"  - {name}: min={mn_s}, max={mx_s}, nulls={nulls_s}")


def read_head(pf: pq.ParquetFile, n: int, columns: Optional[List[str]] = None) -> pd.DataFrame:
        if n <= 0:
                return pd.DataFrame()
        remaining = n
        batches: List[pd.DataFrame] = []
        num_rgs = pf.metadata.num_row_groups
        for rg_i in range(num_rgs):
                table = pf.read_row_group(rg_i, columns=columns)
                if len(table) == 0:
                        continue
                if remaining < len(table):
                        table = table.slice(0, remaining)
                # Convert to pandas without losing types too much
                df = table.to_pandas(types_mapper=pd.ArrowDtype)
                batches.append(df)
                remaining -= len(df)
                if remaining <= 0:
                        break
        if not batches:
                return pd.DataFrame(columns=columns or pf.schema_arrow.names)
        df_all = pd.concat(batches, ignore_index=True)
        return df_all.head(n)


def print_dataframe_head(df: pd.DataFrame, max_cols: int = 50, display_width: int = 200) -> None:
        if df.empty:
                print("Data preview: [no rows]")
                return
        with pd.option_context(
                "display.max_rows", len(df),
                "display.max_columns", max_cols,
                "display.width", display_width,
                "display.max_colwidth", 100,
        ):
                print("Data preview (top rows):")
                print(df)


def main() -> None:
        ap = argparse.ArgumentParser(description="Print the first N rows and metadata from a Parquet file.")
        ap.add_argument("path", help="Path to a Parquet file")
        ap.add_argument("-n", "--rows", type=int, default=20, help="Number of rows to preview (default: 20)")
        ap.add_argument("--columns", type=str, default=None, help="Comma-separated list of columns to preview")
        ap.add_argument("--no-data", action="store_true", help="Do not print data, only metadata")
        ap.add_argument("--stats", action="store_true", help="Print column min/max/nulls from metadata (if available)")
        ap.add_argument("--max-stat-cols", type=int, default=10, help="Max columns to show stats for (default: 10)")
        ap.add_argument("--display-width", type=int, default=200, help="Max display width for data preview (default: 200)")
        args = ap.parse_args()

        path = args.path
        if not os.path.isfile(path):
                sys.stderr.write(f"Error: '{path}' is not a file.\n")
                sys.exit(2)

        print_file_info(path)

        try:
                pf = pq.ParquetFile(path)
        except Exception as e:
                sys.stderr.write(f"Error opening Parquet file: {e}\n")
                sys.exit(3)

        print_parquet_metadata(pf)
        print_schema(pf)
        print_compressions(pf)

        if args.stats:
                print_stats(pf, max_cols=args.max_stat_cols)

        if not args.no_data:
                cols = [c.strip() for c in args.columns.split(",")] if args.columns else None
                try:
                        df = read_head(pf, n=args.rows, columns=cols)
                except Exception as e:
                        sys.stderr.write(f"Error reading data: {e}\n")
                        sys.exit(4)
                print_dataframe_head(df, display_width=args.display_width)

        # Basic dtype summary for previewed data
        if not args.no_data and 'df' in locals() and not df.empty:
                print("Dtypes (pandas):")
                for name, dtype in df.dtypes.items():
                        print(f"  - {name}: {dtype}")

        # Done
        return


if __name__ == "__main__":
        main()