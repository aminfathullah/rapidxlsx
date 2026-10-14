pub mod columns;
pub mod writer;
pub mod xml;
pub mod zip;

use pyo3::exceptions::{PyIOError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyList;

use crate::columns::{extract_column, ColumnData};
use crate::writer::write_xlsx_file;

#[pyfunction]
#[pyo3(signature = (path, sheet_name, headers, columns, compression_level = 1))]
fn write_xlsx(
    py: Python<'_>,
    path: String,
    sheet_name: String,
    headers: Vec<String>,
    columns: &Bound<'_, PyList>,
    compression_level: u32,
) -> PyResult<()> {
    let mut cols_data: Vec<ColumnData> = Vec::with_capacity(columns.len());
    for item in columns.iter() {
        let col = extract_column(&item)?;
        cols_data.push(col);
    }

    py.allow_threads(|| {
        write_xlsx_file(&path, &sheet_name, &headers, &cols_data, compression_level)
            .map_err(|e| match e.kind() {
                std::io::ErrorKind::InvalidInput => PyValueError::new_err(e.to_string()),
                _ => PyIOError::new_err(e.to_string()),
            })
    })?;

    Ok(())
}

#[pymodule]
fn _fastxlsx(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(write_xlsx, m)?)?;
    Ok(())
}
