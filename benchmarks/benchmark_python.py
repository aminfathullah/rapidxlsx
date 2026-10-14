import os
import time
import tempfile
import polars as pl
import fastxlsx

def run_benchmark(num_rows: int = 1_000_000, num_cols: int = 20):
    print(f"Generating dataset: {num_rows:,} rows x {num_cols} columns...")
    t0 = time.perf_counter()
    data = {
        "id": list(range(1, num_rows + 1)),
        **{f"num_{i}": [float(r * i) for r in range(num_rows)] for i in range(1, num_cols - 2)},
        "flag": [r % 2 == 0 for r in range(num_rows)],
        "category": [f"group_{r % 10}" for r in range(num_rows)],
    }
    df = pl.DataFrame(data)
    print(f"Data generation: {time.perf_counter() - t0:.3f} s")

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        out_path = f.name

    try:
        print(f"Writing to {out_path} using fastxlsx.write()...")
        t_start = time.perf_counter()
        fastxlsx.write(out_path, df)
        t_elapsed = time.perf_counter() - t_start

        file_size_mb = os.path.getsize(out_path) / (1024 * 1024)
        throughput = num_rows / t_elapsed

        print(f"Result: {t_elapsed:.3f} s ({throughput:,.0f} rows/s, {file_size_mb:.2f} MB)")
        assert t_elapsed < 5.0, f"Write took {t_elapsed:.3f}s, exceeding 5.0s goal!"
        print("PASS: Completed under 5 seconds.")
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)

if __name__ == "__main__":
    run_benchmark()
