from __future__ import annotations

import os
from typing import Any, Mapping, Sequence

from fastxlsx._fastxlsx import write_xlsx

__all__ = ["write", "FastXlsxWriter"]


def _process_numpy_column(arr: Any) -> tuple[str, Any] | tuple[str, Any, Any] | list[Any]:
    import numpy as np

    if not isinstance(arr, np.ndarray):
        arr = np.asarray(arr)

    if arr.ndim != 1:
        arr = arr.ravel()

    dtype = arr.dtype
    if np.issubdtype(dtype, np.floating):
        if dtype == np.float64:
            return ("f64", arr.tobytes())
        elif dtype == np.float32:
            return ("f32", arr.tobytes())
        else:
            return ("f64", arr.astype(np.float64).tobytes())

    if np.issubdtype(dtype, np.integer):
        if dtype == np.int64:
            return ("i64", arr.tobytes())
        elif dtype == np.int32:
            return ("i32", arr.tobytes())
        elif dtype in (np.int16, np.int8):
            return ("i32", arr.astype(np.int32).tobytes())
        elif dtype == np.uint64:
            return ("i64", arr.astype(np.int64).tobytes())
        else:
            return ("i32", arr.astype(np.int32).tobytes())

    if dtype == np.bool_:
        return ("bool", arr.tobytes())

    return arr.tolist()


def _process_polars_series(series: Any) -> tuple[str, Any] | tuple[str, Any, Any] | list[Any]:
    dtype_str = str(series.dtype)
    null_count = series.null_count()

    if "Float" in dtype_str:
        if null_count == 0:
            np_arr = series.to_numpy()
            if series.dtype.is_float() and str(series.dtype) == "Float32":
                return ("f32", np_arr.tobytes())
            return ("f64", np_arr.astype("float64", copy=False).tobytes())
        else:
            np_arr = series.fill_null(0.0).to_numpy()
            mask_arr = series.is_null().to_numpy().astype("uint8")
            return ("f64", np_arr.astype("float64", copy=False).tobytes(), mask_arr.tobytes())

    if "Int" in dtype_str or "UInt" in dtype_str:
        if null_count == 0:
            np_arr = series.to_numpy()
            if "32" in dtype_str or "16" in dtype_str or "8" in dtype_str:
                return ("i32", np_arr.astype("int32", copy=False).tobytes())
            return ("i64", np_arr.astype("int64", copy=False).tobytes())
        else:
            np_arr = series.fill_null(0).to_numpy()
            mask_arr = series.is_null().to_numpy().astype("uint8")
            return ("i64", np_arr.astype("int64", copy=False).tobytes(), mask_arr.tobytes())

    if "Boolean" in dtype_str or "Bool" in dtype_str:
        if null_count == 0:
            np_arr = series.to_numpy().astype("uint8")
            return ("bool", np_arr.tobytes())
        else:
            np_arr = series.fill_null(False).to_numpy().astype("uint8")
            mask_arr = series.is_null().to_numpy().astype("uint8")
            return ("bool", np_arr.tobytes(), mask_arr.tobytes())

    if "String" in dtype_str or "Utf8" in dtype_str or "Categorical" in dtype_str:
        if null_count == 0:
            return ("str", series.to_list())
        return ("str_opt", series.to_list())

    return series.to_list()


def _normalize_data(data: Any, column_names: Sequence[str] | None = None) -> tuple[list[str], list[Any]]:
    type_name = type(data).__name__
    module_name = getattr(type(data), "__module__", "")

    if "polars" in module_name or type_name == "DataFrame":
        try:
            import polars as pl
            if isinstance(data, pl.DataFrame):
                headers = list(data.columns) if column_names is None else list(column_names)
                columns = [_process_polars_series(data.get_column(c)) for c in data.columns]
                return headers, columns
        except ImportError:
            pass

    if "pandas" in module_name or type_name == "DataFrame":
        try:
            import pandas as pd
            if isinstance(data, pd.DataFrame):
                headers = [str(c) for c in data.columns] if column_names is None else list(column_names)
                columns = []
                for c in data.columns:
                    col_series = data[c]
                    if hasattr(col_series, "to_numpy"):
                        columns.append(_process_numpy_column(col_series.to_numpy()))
                    else:
                        columns.append(col_series.tolist())
                return headers, columns
        except ImportError:
            pass

    if "pyarrow" in module_name or type_name in ("Table", "RecordBatch"):
        try:
            import pyarrow as pa
            if isinstance(data, (pa.Table, pa.RecordBatch)):
                headers = list(data.column_names) if column_names is None else list(column_names)
                columns = []
                for c in data.column_names:
                    col_chunk = data[c]
                    try:
                        np_arr = col_chunk.to_numpy(zero_copy_only=False)
                        columns.append(_process_numpy_column(np_arr))
                    except Exception:
                        columns.append(col_chunk.to_pylist())
                return headers, columns
        except ImportError:
            pass

    if isinstance(data, Mapping):
        headers = [str(k) for k in data.keys()] if column_names is None else list(column_names)
        columns = []
        for v in data.values():
            if hasattr(v, "to_numpy"):
                columns.append(_process_numpy_column(v.to_numpy()))
            elif isinstance(v, (list, tuple)):
                columns.append(list(v))
            else:
                try:
                    import numpy as np
                    if isinstance(v, np.ndarray):
                        columns.append(_process_numpy_column(v))
                    else:
                        columns.append(list(v))
                except ImportError:
                    columns.append(list(v))
        return headers, columns

    try:
        import numpy as np
        if isinstance(data, np.ndarray) and data.ndim == 2:
            num_rows, num_cols = data.shape
            headers = [f"Col_{c}" for c in range(num_cols)] if column_names is None else list(column_names)
            columns = [_process_numpy_column(data[:, c]) for c in range(num_cols)]
            return headers, columns
    except ImportError:
        pass

    if isinstance(data, (list, tuple)):
        if len(data) == 0:
            headers = list(column_names) if column_names else []
            return headers, []

        first = data[0]
        if isinstance(first, Mapping):
            keys = list(first.keys())
            headers = [str(k) for k in keys] if column_names is None else list(column_names)
            columns = [[row.get(k) for row in data] for k in keys]
            return headers, columns

        if isinstance(first, (list, tuple)):
            num_cols = max(len(row) for row in data)
            headers = [f"Col_{c}" for c in range(num_cols)] if column_names is None else list(column_names)
            columns = [
                [row[c] if c < len(row) else None for row in data]
                for c in range(num_cols)
            ]
            return headers, columns

    raise TypeError(f"Unsupported data type for fastxlsx: {type(data)}")


def write(
    path: str | os.PathLike[str],
    data: Any,
    sheet_name: str = "Sheet1",
    column_names: Sequence[str] | None = None,
    compression_level: int = 1,
) -> None:
    headers, columns = _normalize_data(data, column_names=column_names)
    target_path = os.fspath(path)
    write_xlsx(
        target_path,
        sheet_name,
        headers,
        columns,
        compression_level=compression_level,
    )


class FastXlsxWriter:
    def __init__(
        self,
        path: str | os.PathLike[str],
        sheet_name: str = "Sheet1",
        compression_level: int = 1,
    ) -> None:
        self.path = os.fspath(path)
        self.sheet_name = sheet_name
        self.compression_level = compression_level

    def __enter__(self) -> FastXlsxWriter:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    def write(self, data: Any, column_names: Sequence[str] | None = None) -> None:
        write(
            self.path,
            data,
            sheet_name=self.sheet_name,
            column_names=column_names,
            compression_level=self.compression_level,
        )
