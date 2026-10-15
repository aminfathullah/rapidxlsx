from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np
import polars as pl

import rapidxlsx


def run_benchmark(
    num_rows: int = 1_000_000,
    num_cols: int = 20,
    compare_openpyxl: bool = False,
    output_path: str = "benchmark_output.xlsx",
) -> None:
    print("=" * 70)
    print(f"RAPIDXLSX BENCHMARK: {num_rows:,} rows x {num_cols} columns ({num_rows * num_cols:,} cells)")
    print("=" * 70)

    print("Generating dataset...")
    t0 = time.perf_counter()
    cols = {}
    for c in range(num_cols):
        col_name = f"Col_{c:02d}"
        mod = c % 4
        if mod == 0:
            cols[col_name] = np.random.randn(num_rows)
        elif mod == 1:
            cols[col_name] = np.random.randint(-1_000_000, 1_000_000, size=num_rows, dtype=np.int64)
        elif mod == 2:
            cols[col_name] = [f"Item_{i % 500}" for i in range(num_rows)]
        else:
            cols[col_name] = (np.arange(num_rows) % 2 == 0)

    df = pl.DataFrame(cols)
    gen_time = time.perf_counter() - t0
    print(f"Dataset generated in {gen_time:.2f}s (DataFrame shape: {df.shape})")

    print("\nRunning rapidxlsx...")
    t_start = time.perf_counter()
    rapidxlsx.write(output_path, df)
    fast_time = time.perf_counter() - t_start

    file_size_bytes = os.path.getsize(output_path)
    file_size_mb = file_size_bytes / (1024 * 1024)
    rows_per_sec = num_rows / fast_time
    cells_per_sec = (num_rows * num_cols) / fast_time
    throughput_mb_sec = file_size_mb / fast_time

    print(f"rapidxlsx completed in: {fast_time:.3f} seconds")
    print(f"Generated file size   : {file_size_mb:.2f} MB")
    print(f"Throughput (rows/sec) : {rows_per_sec:,.0f} rows/s")
    print(f"Throughput (cells/sec): {cells_per_sec:,.0f} cells/s")
    print(f"I/O speed             : {throughput_mb_sec:.2f} MB/s compressed")

    if os.path.exists(output_path):
        os.remove(output_path)

    if compare_openpyxl and num_rows <= 100_000:
        print("\nRunning openpyxl comparison (sampled on smaller slice if large)...")
        sample_rows = min(num_rows, 50_000)
        sample_df = df.slice(0, sample_rows)
        import openpyxl

        t_opx_start = time.perf_counter()
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(list(sample_df.columns))
        for row in sample_df.iter_rows():
            ws.append(list(row))
        wb.save("openpyxl_temp.xlsx")
        opx_time = time.perf_counter() - t_opx_start
        print(f"openpyxl ({sample_rows:,} rows) took: {opx_time:.3f} seconds")
        speedup = (opx_time / sample_rows) / (fast_time / num_rows)
        print(f"rapidxlsx speedup vs openpyxl: {speedup:.1f}x faster")
        if os.path.exists("openpyxl_temp.xlsx"):
            os.remove("openpyxl_temp.xlsx")

    print("\n" + "=" * 70)
    if fast_time < 5.0:
        print(f"SUCCESS: 1M rows written in {fast_time:.3f}s (well below 5s target)")
    else:
        print(f"RESULT: 1M rows written in {fast_time:.3f}s")
    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(description="rapidxlsx Performance Benchmark")
    parser.add_argument("--rows", type=int, default=1_000_000, help="Number of rows")
    parser.add_argument("--cols", type=int, default=20, help="Number of columns")
    parser.add_argument("--compare-openpyxl", action="store_true", help="Compare with openpyxl")
    parser.add_argument("--output", type=str, default="bench_out.xlsx", help="Output file path")
    args = parser.parse_args()

    run_benchmark(
        num_rows=args.rows,
        num_cols=args.cols,
        compare_openpyxl=args.compare_openpyxl,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
