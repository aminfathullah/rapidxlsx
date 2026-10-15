from __future__ import annotations

import os
import subprocess
import numpy as np
import polars as pl
import pandas as pd
import pyarrow as pa
import pytest

import rapidxlsx


def test_basic_dict(tmp_path):
    out = str(tmp_path / "basic.xlsx")
    data = {
        "A": [1, 2, 3],
        "B": ["foo", "bar", "baz"],
        "C": [1.1, 2.2, 3.3],
        "D": [True, False, True],
    }
    rapidxlsx.write(out, data)

    res = pl.read_excel(out, engine="calamine")
    assert res.shape == (3, 4)
    assert list(res.columns) == ["A", "B", "C", "D"]
    assert res["A"].to_list() == [1, 2, 3]
    assert res["B"].to_list() == ["foo", "bar", "baz"]
    assert res["C"].to_list() == [1.1, 2.2, 3.3]
    assert res["D"].to_list() == [True, False, True]


def test_polars_dataframe(tmp_path):
    out = str(tmp_path / "polars.xlsx")
    df = pl.DataFrame({
        "id": [101, 102, 103],
        "name": ["Alice", "Bob", "Charlie"],
        "score": [98.5, None, 75.0],
        "passed": [True, False, True],
    })
    rapidxlsx.write(out, df)

    res = pl.read_excel(out, engine="calamine")
    assert res.shape == (3, 4)
    assert res["id"].to_list() == [101, 102, 103]
    assert res["name"].to_list() == ["Alice", "Bob", "Charlie"]
    assert res["score"].to_list() == [98.5, None, 75.0]
    assert res["passed"].to_list() == [True, False, True]


def test_pandas_dataframe(tmp_path):
    out = str(tmp_path / "pandas.xlsx")
    df = pd.DataFrame({
        "x": [10, 20, 30],
        "y": ["alpha", "beta", "gamma"],
        "z": [0.5, 1.5, 2.5],
    })
    rapidxlsx.write(out, df)

    res = pl.read_excel(out, engine="calamine")
    assert res.shape == (3, 3)
    assert res["x"].to_list() == [10, 20, 30]
    assert res["y"].to_list() == ["alpha", "beta", "gamma"]
    assert res["z"].to_list() == [0.5, 1.5, 2.5]


def test_pyarrow_table(tmp_path):
    out = str(tmp_path / "pyarrow.xlsx")
    table = pa.table({
        "col_a": [1, 2, 3, 4],
        "col_b": ["w", "x", "y", "z"],
    })
    rapidxlsx.write(out, table)

    res = pl.read_excel(out, engine="calamine")
    assert res.shape == (4, 2)
    assert res["col_a"].to_list() == [1, 2, 3, 4]
    assert res["col_b"].to_list() == ["w", "x", "y", "z"]


def test_numpy_2d(tmp_path):
    out = str(tmp_path / "numpy.xlsx")
    arr = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]], dtype=np.float64)
    rapidxlsx.write(out, arr, column_names=["First", "Second"])

    res = pl.read_excel(out, engine="calamine")
    assert res.shape == (3, 2)
    assert list(res.columns) == ["First", "Second"]
    assert res["First"].to_list() == [1.0, 3.0, 5.0]
    assert res["Second"].to_list() == [2.0, 4.0, 6.0]


def test_list_of_lists(tmp_path):
    out = str(tmp_path / "lol.xlsx")
    data = [
        [1, "apple", True],
        [2, "banana", False],
    ]
    rapidxlsx.write(out, data, column_names=["ID", "Fruit", "Available"])

    res = pl.read_excel(out, engine="calamine")
    assert res.shape == (2, 3)
    assert res["ID"].to_list() == [1, 2]
    assert res["Fruit"].to_list() == ["apple", "banana"]
    assert res["Available"].to_list() == [True, False]


def test_list_of_dicts(tmp_path):
    out = str(tmp_path / "lod.xlsx")
    data = [
        {"city": "Paris", "pop": 2161000},
        {"city": "Tokyo", "pop": 13960000},
    ]
    rapidxlsx.write(out, data)

    res = pl.read_excel(out, engine="calamine")
    assert res.shape == (2, 2)
    assert res["city"].to_list() == ["Paris", "Tokyo"]
    assert res["pop"].to_list() == [2161000, 13960000]


def test_xml_escaping(tmp_path):
    out = str(tmp_path / "escape.xlsx")
    tricky_strings = [
        "<tag>value</tag>",
        "AT&T & Verizon",
        "Quote: \"Hello\"",
        "Apostrophe: 'World'",
        "Mixed: <a href=\"x&y\">'link'</a>",
        "  leading & trailing  ",
        "Control \x01\x02 characters \x1f stripped",
    ]
    rapidxlsx.write(out, {"Text": tricky_strings})

    res = pl.read_excel(out, engine="calamine")
    read_vals = res["Text"].to_list()
    assert read_vals[0] == "<tag>value</tag>"
    assert read_vals[1] == "AT&T & Verizon"
    assert read_vals[2] == "Quote: \"Hello\""
    assert read_vals[3] == "Apostrophe: 'World'"
    assert read_vals[4] == "Mixed: <a href=\"x&y\">'link'</a>"
    assert read_vals[5] == "  leading & trailing  "
    assert read_vals[6] == "Control  characters  stripped"


def test_nan_and_inf_handling(tmp_path):
    out = str(tmp_path / "special_floats.xlsx")
    data = {
        "id": [1, 2, 3, 4, 5],
        "Floats": [1.0, float("nan"), float("inf"), float("-inf"), 2.5],
    }
    rapidxlsx.write(out, data)

    import openpyxl
    wb = openpyxl.load_workbook(out)
    ws = wb.active
    values = [cell.value for cell in ws["B"][1:]]
    assert values[0] == 1.0
    assert values[1] is None
    assert values[2] == "#DIV/0!"
    assert values[3] == "#DIV/0!"
    assert values[4] == 2.5


def test_context_manager(tmp_path):
    out = str(tmp_path / "context.xlsx")
    with rapidxlsx.RapidXlsxWriter(out, sheet_name="DataSheet") as writer:
        writer.write({"Col1": [10, 20]})

    res = pl.read_excel(out, sheet_name="DataSheet", engine="calamine")
    assert res.shape == (2, 1)
    assert res["Col1"].to_list() == [10, 20]


def test_excel_limits(tmp_path):
    out = str(tmp_path / "limits.xlsx")
    with pytest.raises(Exception):
        rapidxlsx.write(out, {"Col": [0] * 1_048_576})


def test_unsupported_type(tmp_path):
    out = str(tmp_path / "err.xlsx")
    with pytest.raises(TypeError):
        rapidxlsx.write(out, 12345)


def test_zip_integrity(tmp_path):
    out = str(tmp_path / "integrity.xlsx")
    rapidxlsx.write(out, {"A": list(range(1000))})
    ret = subprocess.run(["unzip", "-t", out], capture_output=True, text=True)
    assert ret.returncode == 0


def test_scale_100k(tmp_path):
    out = str(tmp_path / "scale_100k.xlsx")
    n = 100_000
    df = pl.DataFrame({
        "int_col": np.arange(n, dtype=np.int64),
        "float_col": np.random.randn(n),
        "bool_col": np.arange(n) % 2 == 0,
    })
    rapidxlsx.write(out, df)
    res = pl.read_excel(out, engine="calamine")
    assert res.shape == (n, 3)
