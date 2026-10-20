import argparse
import os
import tempfile
import time
import polars as pl
import rapidxlsx

def run_benchmark(num_rows: int = 1_000_000, num_cols: int = 20, compare: bool = False):
    print(f"Generating dataset: {num_rows:,} rows x {num_cols} columns...")
    t0 = time.perf_counter()
    data = {
        "id": list(range(1, num_rows + 1)),
        **{f"num_{i}": [float(r * i) for r in range(num_rows)] for i in range(1, num_cols - 2)},
        "flag": [r % 2 == 0 for r in range(num_rows)],
        "category": [f"group_{r % 10}" for r in range(num_rows)],
    }
    df = pl.DataFrame(data)
    print(f"Data generation: {time.perf_counter() - t0:.3f} s\n")

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        out_path = f.name

    try:
        print("Writing XLSX using rapidxlsx.write()...")
        t_start = time.perf_counter()
        rapidxlsx.write(out_path, df)
        t_elapsed = time.perf_counter() - t_start

        file_size_mb = os.path.getsize(out_path) / (1024 * 1024)
        throughput = num_rows / t_elapsed

        print(f"rapidxlsx : {t_elapsed:.3f} s ({throughput:,.0f} rows/s, {file_size_mb:.2f} MB)")
        assert t_elapsed < 5.0, f"Write took {t_elapsed:.3f}s, exceeding 5.0s goal!"
        print("PASS: Completed under 5 seconds.")

        if compare:
            try:
                import xlsxwriter

                print("\nWriting XLSX using xlsxwriter (constant_memory)...")
                with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f_xw:
                    out_xw = f_xw.name
                try:
                    t_xw0 = time.perf_counter()
                    wb = xlsxwriter.Workbook(out_xw, {"constant_memory": True})
                    ws = wb.add_worksheet()
                    ws.write_row(0, 0, df.columns)
                    for r_idx, row in enumerate(df.iter_rows(), start=1):
                        ws.write_row(r_idx, 0, row)
                    wb.close()
                    t_xw = time.perf_counter() - t_xw0
                    xw_mb = os.path.getsize(out_xw) / (1024 * 1024)
                    print(f"xlsxwriter: {t_xw:.3f} s ({num_rows / t_xw:,.0f} rows/s, {xw_mb:.2f} MB)")
                    print(f"Speedup   : {t_xw / t_elapsed:.1f}x faster than xlsxwriter")
                finally:
                    if os.path.exists(out_xw):
                        os.remove(out_xw)
            except ImportError:
                pass

            try:
                import openpyxl

                sample_rows = min(num_rows, 50_000)
                print(f"\nWriting XLSX using openpyxl (sampled {sample_rows:,} rows)...")
                with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f_opx:
                    out_opx = f_opx.name
                try:
                    t_opx0 = time.perf_counter()
                    wb = openpyxl.Workbook()
                    ws = wb.active
                    ws.append(df.columns)
                    sample_df = df.slice(0, sample_rows)
                    for row in sample_df.iter_rows():
                        ws.append(list(row))
                    wb.save(out_opx)
                    t_opx = time.perf_counter() - t_opx0
                    projected_1m = (t_opx / sample_rows) * num_rows
                    print(f"openpyxl  : {t_opx:.3f} s for {sample_rows:,} rows (projected 1M: {projected_1m:.1f} s)")
                    print(f"Speedup   : {projected_1m / t_elapsed:.1f}x faster than openpyxl")
                finally:
                    if os.path.exists(out_opx):
                        os.remove(out_opx)
            except ImportError:
                pass

    finally:
        if os.path.exists(out_path):
            os.remove(out_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=1_000_000)
    parser.add_argument("--cols", type=int, default=20)
    parser.add_argument("--compare", action="store_true")
    args = parser.parse_args()
    run_benchmark(num_rows=args.rows, num_cols=args.cols, compare=args.compare)
