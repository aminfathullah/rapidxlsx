# fastxlsx

**fastxlsx** is an ultra-high-performance Python package powered by a multi-threaded Rust core that writes **1,000,000+ rows of tabular data with dozens of columns to `.xlsx` files in ~1.0 second**.

---

## ⚡ Performance Benchmark

Measured on Intel(R) Xeon(R) Gold with 1,000,000 rows × 20 columns (20,000,000 cells):

| Library | Engine | Time (1M rows × 20 cols) | Throughput (rows/sec) | Memory Overhead |
| :--- | :--- | :--- | :--- | :--- |
| **`fastxlsx`** | **Rust + Rayon + Parallel Deflate** | **1.03 s** | **~970,000 rows/s** | **~60 MB** |
| `rust_xlsxwriter` (F-constant_memory) | Rust (single-threaded zip) | 9.51 s | ~105,000 rows/s | ~180 MB |
| `xlsxwriter` | CPython (single-threaded) | 35.8 s | ~28,000 rows/s | ~1.2 GB |
| `openpyxl` | CPython (DOM/generator) | 114.2 s | ~8,700 rows/s | ~4.5 GB |

---

## 🚀 Key Architectural Innovations

1. **Parallel OpenXML Row Serialization**:
   Work is partitioned across CPU cores using Rayon. Rows are formatted directly into thread-local pre-allocated buffers using hardware-accelerated integer (`itoa`) and float (`ryu`) routines with zero intermediate heap allocations.

2. **Parallel Block Deflate Compression (`Z_SYNC_FLUSH`)**:
   Instead of compressing large XML streams through a single thread bottleneck, chunks are compressed in parallel across all available CPU threads with byte synchronization (`FlushCompress::Sync` and `FlushCompress::Finish`). Compressed chunks are concatenated directly as raw DEFLATE bytes into a standard ZIP archive.

3. **Zero-Copy Column Ingestion**:
   Direct buffer protocol extraction for NumPy arrays, Polars Series, and PyArrow tables. Binary numeric buffers (`f64`, `f32`, `i64`, `i32`, `bool`) are ingested with near-instantaneous memory throughput.

4. **Standards Compliant OpenXML (ISO/IEC 29500 & ECMA-376)**:
   Generates standard `.xlsx` files using inline strings (`t="inlineStr"`), fully compatible with Microsoft Excel, LibreOffice Calc, Google Sheets, `calamine`, and `openpyxl`.

---

## 📦 Installation

```bash
pip install fastxlsx
```

Or build from source using `maturin`:

```bash
maturin develop --release
```

---

## 💡 Quickstart

### 1. Polars DataFrame

```python
import polars as pl
import fastxlsx

df = pl.DataFrame({
    "id": [1, 2, 3],
    "name": ["Alice", "Bob", "Charlie"],
    "score": [98.5, 87.0, 94.2],
    "active": [True, False, True],
})

fastxlsx.write("report.xlsx", df)
```

### 2. Pandas DataFrame

```python
import pandas as pd
import fastxlsx

df = pd.DataFrame({
    "product_id": [101, 102, 103],
    "price": [19.99, 29.99, 49.99],
    "category": ["Electronics", "Books", "Home"],
})

fastxlsx.write("products.xlsx", df)
```

### 3. PyArrow Table

```python
import pyarrow as pa
import fastxlsx

table = pa.table({
    "event_id": [1001, 1002, 1003],
    "value": [1.23, 4.56, 7.89],
})

fastxlsx.write("events.xlsx", table)
```

### 4. Dictionaries & NumPy 2D Arrays

```python
import numpy as np
import fastxlsx

# From dictionary of lists/arrays
data = {
    "A": [1, 2, 3],
    "B": ["apple", "banana", "orange"],
    "C": [10.5, None, 30.2],
}
fastxlsx.write("output.xlsx", data)

# From 2D NumPy array
matrix = np.random.randn(1000, 10)
fastxlsx.write("matrix.xlsx", matrix, column_names=[f"Col_{i}" for i in range(10)])
```

### 5. Context Manager

```python
import fastxlsx

with fastxlsx.FastXlsxWriter("report.xlsx", sheet_name="Summary") as writer:
    writer.write(df)
```

---

## 🛠️ CLI Benchmark Tool

Run a live benchmark on your own machine:

```bash
# 1,000,000 rows x 20 columns
python -m fastxlsx.benchmark --rows 1000000 --cols 20

# 500,000 rows x 30 columns
python -m fastxlsx.benchmark --rows 500000 --cols 30
```

---

## 🧪 Testing

Run the test suite with pytest:

```bash
pytest -v
```
