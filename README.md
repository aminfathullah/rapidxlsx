# fastxlsx

High-performance Excel (`.xlsx`) spreadsheet writer for Python and R, powered by a multi-threaded Rust engine with parallel OpenXML row formatting and parallel block Deflate compression.

Writes 1,000,000 rows across 20 to 30 columns in under 1 second.

## Performance Benchmark

Measured on Intel Xeon Gold (1,000,000 rows x 20 columns, 20,000,000 cells):

| Language / Tool | Backend Engine | Write Time (1M x 20) | Throughput | Output Size |
| :--- | :--- | :--- | :--- | :--- |
| **`fastxlsx` (R)** | **Rust + Rayon + Sync Deflate** | **0.47 s** | **~2,145,000 rows/s** | 209 MB |
| **`fastxlsx` (Python)** | **Rust + Rayon + Sync Deflate** | **0.72 s** | **~1,390,000 rows/s** | 138 MB |
| `rust_xlsxwriter` | Single-threaded Rust zip | 9.51 s | ~105,000 rows/s | 180 MB |
| `writexl` (R) | libxlsxwriter C | 14.80 s | ~67,500 rows/s | 175 MB |
| `xlsxwriter` (Python) | Single-threaded Python | 35.80 s | ~28,000 rows/s | 170 MB |
| `openpyxl` (Python) | Python DOM / generator | 114.20 s | ~8,700 rows/s | 190 MB |

## Architecture

The project is structured as a Cargo workspace with distinct layers:

```
fastxlsx/
├── crates/
│   ├── fastxlsx-core/       # Pure Rust engine: XML formatting, parallel sync deflate, ZIP packaging
│   └── fastxlsx-python/     # PyO3 CPython extension module
├── python/
│   └── fastxlsx/            # Python package with zero-copy buffer protocol ingestion
├── r/
│   ├── R/                   # R package functions (write_xlsx)
│   ├── src/                 # C entrypoint registering native routines
│   └── src/rust/            # Rust static library crate wrapping fastxlsx-core
├── benchmarks/              # Reproducible 1M row benchmarks for Python and R
└── tests/                   # Python integration and regression tests
```

### Key Technical Mechanisms

1. **Parallel OpenXML Serialization**: Rayon distributes rows across CPU threads. Cell coordinates, numbers (`ryu` for floats, `itoa` for integers), and strings are written directly into pre-allocated memory buffers without heap thrashing.
2. **Parallel Block Deflate (`Z_SYNC_FLUSH`)**: XML row streams are partitioned into chunks and compressed simultaneously across threads with byte synchronization. Compressed segments are combined directly into the ZIP archive, removing the single-threaded compression bottleneck.
3. **Zero-Copy Ingestion**: Python buffer protocol and R internal vector pointers (`REAL_RO`, `INTEGER_RO`, `LOGICAL_RO`) feed contiguous numerical slices directly to Rust without intermediate copying.
4. **Standards Compliant OpenXML**: Produces standard ISO/IEC 29500 and ECMA-376 spreadsheets using inline strings (`t="inlineStr"`), fully compatible with Microsoft Excel, LibreOffice Calc, Google Sheets, `python-calamine`, and `openpyxl`.

## Python Package

### Installation

```bash
pip install fastxlsx
```

To build from source:

```bash
maturin develop --release
```

### Quickstart

#### Polars DataFrame

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

#### Pandas DataFrame

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

#### PyArrow Table

```python
import pyarrow as pa
import fastxlsx

table = pa.table({
    "event_id": [1001, 1002, 1003],
    "value": [1.23, 4.56, 7.89],
})

fastxlsx.write("events.xlsx", table)
```

#### NumPy 2D Array or Python Dictionary

```python
import numpy as np
import fastxlsx

# 2D numeric matrix
matrix = np.random.randn(1000, 10)
fastxlsx.write("matrix.xlsx", matrix, column_names=[f"Col_{i}" for i in range(10)])

# Dictionary of lists or arrays
data = {
    "A": [1, 2, 3],
    "B": ["apple", "banana", "orange"],
    "C": [10.5, None, 30.2],
}
fastxlsx.write("dict_output.xlsx", data)
```

#### Context Manager

```python
import fastxlsx

with fastxlsx.FastXlsxWriter("report.xlsx", sheet_name="Data") as writer:
    writer.write(df)
```

## R Package

### Installation

Install directly from source directory:

```bash
R CMD INSTALL r
```

Or using `remotes` / `devtools` in R:

```r
remotes::install_local("r")
```

### Quickstart

```r
library(fastxlsx)

df <- data.frame(
  id = 1:5,
  name = c("Alice", "Bob", "Charlie", "David", "Eva"),
  score = c(95.5, 82.0, 91.5, 78.0, 88.5),
  active = c(TRUE, FALSE, TRUE, TRUE, FALSE),
  category = factor(c("A", "B", "A", "C", "B")),
  stringsAsFactors = FALSE
)

# Write to Excel
write_xlsx(df, "output.xlsx", sheet_name = "Summary")
```

### Supported R Column Types

- Numeric (`double` / `real`): Zero-copy contiguous memory mapping.
- Integer: 32-bit integer conversion with `NA_integer_` mapped to blank cells.
- Logical: Boolean conversion with `NA` mapped to blank cells.
- Character: UTF-8 string encoding with automatic XML character escaping.
- Factors: Level vector lookup mapping to string cells.

## Benchmarks

Run the benchmark scripts to measure performance on your local system:

```bash
# Python benchmark (1,000,000 rows x 20 columns)
python benchmarks/benchmark_python.py

# R benchmark (1,000,000 rows x 20 columns)
Rscript benchmarks/benchmark_r.R
```

## Testing

```bash
# Run Rust workspace unit tests
cargo test --workspace

# Run Python test suite
pytest -v

# Run R test suite
Rscript r/tests/test_fastxlsx.R
```

## License

MIT License. See [LICENSE](LICENSE) for details.
