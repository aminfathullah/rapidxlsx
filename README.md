# rapidxlsx

High-performance Excel (`.xlsx`) spreadsheet writer for Python and R, powered by a multi-threaded Rust engine with parallel OpenXML row formatting and parallel block Deflate compression.

Writes 1,000,000 rows across 20 to 30 columns in under 1 second.

## Performance Benchmark

Measured on Intel Xeon Gold 6526Y (32 cores, 1,000,000 rows x 20 columns, 20,000,000 cells):

| Language / Tool | Backend Engine | Write Time (1M x 20) | Throughput | Output Size |
| :--- | :--- | :--- | :--- | :--- |
| **`rapidxlsx` (R)** | **Rust + Rayon + Sync Deflate** | **0.47 s** | **~2,100,000 rows/s** | 209 MB |
| **`rapidxlsx` (Python)** | **Rust + Rayon + Sync Deflate** | **0.73 s** | **~1,370,000 rows/s** | 138 MB |
| `rust_xlsxwriter` | Rust (`Workbook::new`) | 17.06 s | ~58,600 rows/s | 116 MB |
| `writexl` (R) | libxlsxwriter C | 32.44 s | ~30,800 rows/s | 138 MB |
| `xlsxwriter` (Python) | Python (`constant_memory`) | 64.55 s | ~15,500 rows/s | 111 MB |
| `openpyxl` (Python) | Standard DOM generator | 111.58 s | ~8,960 rows/s | 107 MB |

## Architecture

The project is structured as a Cargo workspace with distinct layers:

```
rapidxlsx/
├── crates/
│   ├── rapidxlsx-core/       # Pure Rust engine: XML formatting, parallel sync deflate, ZIP packaging
│   └── rapidxlsx-python/     # PyO3 CPython extension module
├── python/
│   └── rapidxlsx/            # Python package with zero-copy buffer protocol ingestion
├── r/
│   ├── R/                    # R package functions (write_xlsx)
│   ├── src/                  # C entrypoint registering native routines
│   └── src/rust/             # Rust static library crate wrapping rapidxlsx-core
├── benchmarks/               # Reproducible 1M row benchmarks for Python and R
└── tests/                    # Python integration and regression tests
```

### Key Technical Mechanisms

1. **Parallel OpenXML Serialization**: Rayon distributes rows across CPU threads. Cell coordinates, numbers (`ryu` for floats, `itoa` for integers), and strings are written directly into pre-allocated memory buffers without heap thrashing.
2. **Parallel Block Deflate (`Z_SYNC_FLUSH`)**: XML row streams are partitioned into chunks and compressed simultaneously across threads with byte synchronization. Compressed segments are combined directly into the ZIP archive, removing the single-threaded compression bottleneck.
3. **Zero-Copy Ingestion**: Python buffer protocol and R internal vector pointers (`REAL_RO`, `INTEGER_RO`, `LOGICAL_RO`) feed contiguous numerical slices directly to Rust without intermediate copying.
4. **Standards Compliant OpenXML**: Produces standard ISO/IEC 29500 and ECMA-376 spreadsheets using inline strings (`t="inlineStr"`), fully compatible with Microsoft Excel, LibreOffice Calc, Google Sheets, `python-calamine`, and `openpyxl`.

## Python Package

### Installation

```bash
pip install rapidxlsx
```

To build from source:

```bash
maturin develop --release
```

### Quickstart

#### Polars DataFrame

```python
import polars as pl
import rapidxlsx

df = pl.DataFrame({
    "id": [1, 2, 3],
    "name": ["Alice", "Bob", "Charlie"],
    "score": [98.5, 87.0, 94.2],
    "active": [True, False, True],
})

rapidxlsx.write("report.xlsx", df)
```

#### Pandas DataFrame

```python
import pandas as pd
import rapidxlsx

df = pd.DataFrame({
    "product_id": [101, 102, 103],
    "price": [19.99, 29.99, 49.99],
    "category": ["Electronics", "Books", "Home"],
})

rapidxlsx.write("products.xlsx", df)
```

#### PyArrow Table

```python
import pyarrow as pa
import rapidxlsx

table = pa.table({
    "event_id": [1001, 1002, 1003],
    "value": [1.23, 4.56, 7.89],
})

rapidxlsx.write("events.xlsx", table)
```

#### NumPy 2D Array or Python Dictionary

```python
import numpy as np
import rapidxlsx

# 2D numeric matrix
matrix = np.random.randn(1000, 10)
rapidxlsx.write("matrix.xlsx", matrix, column_names=[f"Col_{i}" for i in range(10)])

# Dictionary of lists or arrays
data = {
    "A": [1, 2, 3],
    "B": ["apple", "banana", "orange"],
    "C": [10.5, None, 30.2],
}
rapidxlsx.write("dict_output.xlsx", data)
```

#### Context Manager

```python
import rapidxlsx

with rapidxlsx.RapidXlsxWriter("report.xlsx", sheet_name="Data") as writer:
    writer.write(df)
```

## R Package

### Installation

#### Option 1: Pre-compiled Binaries (Recommended, No Rust or C toolchain required)

Install pre-compiled platform binaries directly from GitHub Releases:

```r
# Windows (.zip)
install.packages("https://github.com/aminfathullah/rapidxlsx/releases/download/v0.1.0/rapidxlsx_0.1.0.zip", repos = NULL)

# macOS (.tgz)
install.packages("https://github.com/aminfathullah/rapidxlsx/releases/download/v0.1.0/rapidxlsx_0.1.0.tgz", repos = NULL)

# Linux (.tar.gz)
install.packages("https://github.com/aminfathullah/rapidxlsx/releases/download/v0.1.0/rapidxlsx_0.1.0_linux.tar.gz", repos = NULL)

# Or via remotes / devtools:
remotes::install_url("https://github.com/aminfathullah/rapidxlsx/releases/download/v0.1.0/rapidxlsx_0.1.0.zip")
```

#### Option 2: R-universe (Automatic Cloud Binaries)

```r
install.packages("rapidxlsx", repos = c("https://aminfathullah.r-universe.dev", "https://cloud.r-project.org"))
```

#### Option 3: Install from Source (Requires Rust/Cargo toolchain)

```r
# From GitHub using remotes / devtools
remotes::install_github("aminfathullah/rapidxlsx/r")
```

Or from local source directory:

```bash
R CMD INSTALL r
```

### Quickstart

```r
library(rapidxlsx)

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

Run the benchmark scripts to measure and compare performance on your local system:

```bash
# Python benchmark (rapidxlsx vs xlsxwriter vs openpyxl)
python benchmarks/benchmark_python.py --compare

# R benchmark (rapidxlsx vs writexl)
Rscript benchmarks/benchmark_r.R --compare
```

## Testing

```bash
# Run Rust workspace unit tests
cargo test --workspace

# Run Python test suite
pytest -v

# Run R test suite
Rscript r/tests/test_rapidxlsx.R
```

## License

MIT License. See [LICENSE](LICENSE) for details.
