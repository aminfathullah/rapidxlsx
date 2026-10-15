use pyo3::buffer::PyBuffer;
use pyo3::exceptions::{PyIOError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyBytes, PyFloat, PyInt, PyList, PySequence, PyString, PyTuple};

use rapidxlsx_core::{write_xlsx_file, ColumnData};

fn extract_column<'py>(obj: &Bound<'py, PyAny>) -> PyResult<ColumnData<'static>> {
    let py = obj.py();

    if let Ok(tuple) = obj.downcast::<PyTuple>() {
        if tuple.len() == 2 {
            let tag: String = tuple.get_item(0)?.extract()?;
            let val = tuple.get_item(1)?;
            return extract_tagged_column(&tag, &val);
        }
        if tuple.len() == 3 {
            let tag: String = tuple.get_item(0)?.extract()?;
            let val = tuple.get_item(1)?;
            let mask = tuple.get_item(2)?;
            return extract_masked_column(&tag, &val, &mask);
        }
    }

    if let Ok(buf) = PyBuffer::<f64>::get(obj) {
        let vals: Vec<f64> = buf.to_vec(py)?;
        return Ok(ColumnData::Float64(vals));
    }
    if let Ok(buf) = PyBuffer::<i64>::get(obj) {
        let vals: Vec<i64> = buf.to_vec(py)?;
        return Ok(ColumnData::Int64(vals));
    }
    if let Ok(buf) = PyBuffer::<i32>::get(obj) {
        let vals: Vec<i32> = buf.to_vec(py)?;
        return Ok(ColumnData::Int32(vals));
    }
    if let Ok(buf) = PyBuffer::<f32>::get(obj) {
        let vals: Vec<f32> = buf.to_vec(py)?;
        return Ok(ColumnData::Float32(vals));
    }
    if let Ok(buf) = PyBuffer::<u8>::get(obj) {
        let raw: Vec<u8> = buf.to_vec(py)?;
        let bools: Vec<bool> = raw.into_iter().map(|b| b != 0).collect();
        return Ok(ColumnData::Bool(bools));
    }

    if let Ok(list) = obj.downcast::<PyList>() {
        return extract_from_list(list);
    }

    if let Ok(seq) = obj.downcast::<PySequence>() {
        let len: usize = seq.len()?;
        let mut first_non_none = None;
        for i in 0..len.min(100) {
            let item = seq.get_item(i)?;
            if !item.is_none() {
                first_non_none = Some(item);
                break;
            }
        }

        let Some(first) = first_non_none else {
            return Ok(ColumnData::Empty(len));
        };

        if first.is_instance_of::<PyBool>() {
            let mut res = Vec::with_capacity(len);
            for i in 0..len {
                let item = seq.get_item(i)?;
                res.push(if item.is_none() {
                    None
                } else {
                    Some(item.extract::<bool>()?)
                });
            }
            return Ok(ColumnData::BoolOpt(res));
        }

        if first.is_instance_of::<PyInt>() {
            let mut res = Vec::with_capacity(len);
            for i in 0..len {
                let item = seq.get_item(i)?;
                res.push(if item.is_none() {
                    None
                } else {
                    Some(item.extract::<i64>()?)
                });
            }
            return Ok(ColumnData::Int64Opt(res));
        }

        if first.is_instance_of::<PyFloat>() {
            let mut res = Vec::with_capacity(len);
            for i in 0..len {
                let item = seq.get_item(i)?;
                res.push(if item.is_none() {
                    None
                } else {
                    Some(item.extract::<f64>()?)
                });
            }
            return Ok(ColumnData::Float64Opt(res));
        }

        let mut res = Vec::with_capacity(len);
        for i in 0..len {
            let item = seq.get_item(i)?;
            if item.is_none() {
                res.push(None);
            } else if let Ok(s) = item.downcast::<PyString>() {
                let s_str: &str = s.to_str()?;
                res.push(Some(s_str.to_string()));
            } else {
                let s_obj = item.str()?;
                let s_str: &str = s_obj.to_str()?;
                res.push(Some(s_str.to_string()));
            }
        }
        return Ok(ColumnData::StringOpt(res));
    }

    Ok(ColumnData::Empty(0))
}

fn extract_tagged_column<'py>(tag: &str, val: &Bound<'py, PyAny>) -> PyResult<ColumnData<'static>> {
    match tag {
        "f64" => {
            if let Ok(bytes) = val.downcast::<PyBytes>() {
                let b = bytes.as_bytes();
                let count = b.len() / 8;
                let mut vec = vec![0.0f64; count];
                unsafe {
                    std::ptr::copy_nonoverlapping(
                        b.as_ptr(),
                        vec.as_mut_ptr() as *mut u8,
                        count * 8,
                    );
                }
                return Ok(ColumnData::Float64(vec));
            }
        }
        "i64" => {
            if let Ok(bytes) = val.downcast::<PyBytes>() {
                let b = bytes.as_bytes();
                let count = b.len() / 8;
                let mut vec = vec![0i64; count];
                unsafe {
                    std::ptr::copy_nonoverlapping(
                        b.as_ptr(),
                        vec.as_mut_ptr() as *mut u8,
                        count * 8,
                    );
                }
                return Ok(ColumnData::Int64(vec));
            }
        }
        "i32" => {
            if let Ok(bytes) = val.downcast::<PyBytes>() {
                let b = bytes.as_bytes();
                let count = b.len() / 4;
                let mut vec = vec![0i32; count];
                unsafe {
                    std::ptr::copy_nonoverlapping(
                        b.as_ptr(),
                        vec.as_mut_ptr() as *mut u8,
                        count * 4,
                    );
                }
                return Ok(ColumnData::Int32(vec));
            }
        }
        "f32" => {
            if let Ok(bytes) = val.downcast::<PyBytes>() {
                let b = bytes.as_bytes();
                let count = b.len() / 4;
                let mut vec = vec![0.0f32; count];
                unsafe {
                    std::ptr::copy_nonoverlapping(
                        b.as_ptr(),
                        vec.as_mut_ptr() as *mut u8,
                        count * 4,
                    );
                }
                return Ok(ColumnData::Float32(vec));
            }
        }
        "bool" => {
            if let Ok(bytes) = val.downcast::<PyBytes>() {
                let b = bytes.as_bytes();
                let bools = b.iter().map(|&x| x != 0).collect();
                return Ok(ColumnData::Bool(bools));
            }
        }
        "str" => {
            if let Ok(list) = val.downcast::<PyList>() {
                let mut res = Vec::with_capacity(list.len());
                for item in list.iter() {
                    let s: &str = item.extract()?;
                    res.push(s.to_string());
                }
                return Ok(ColumnData::StringDense(res));
            }
        }
        "str_opt" => {
            if let Ok(list) = val.downcast::<PyList>() {
                let mut res = Vec::with_capacity(list.len());
                for item in list.iter() {
                    let s: Option<String> = item.extract()?;
                    res.push(s);
                }
                return Ok(ColumnData::StringOpt(res));
            }
        }
        _ => {}
    }
    extract_column(val)
}

fn extract_masked_column<'py>(
    tag: &str,
    val: &Bound<'py, PyAny>,
    mask: &Bound<'py, PyAny>,
) -> PyResult<ColumnData<'static>> {
    let mask_bytes = mask.downcast::<PyBytes>()?.as_bytes();
    match tag {
        "f64" => {
            let val_bytes = val.downcast::<PyBytes>()?.as_bytes();
            let count = val_bytes.len() / 8;
            let mut raw = vec![0.0f64; count];
            unsafe {
                std::ptr::copy_nonoverlapping(
                    val_bytes.as_ptr(),
                    raw.as_mut_ptr() as *mut u8,
                    count * 8,
                );
            }
            let mut res = Vec::with_capacity(count);
            for i in 0..count {
                let is_null = mask_bytes.get(i).copied().unwrap_or(0) != 0;
                res.push(if is_null { None } else { Some(raw[i]) });
            }
            Ok(ColumnData::Float64Opt(res))
        }
        "i64" => {
            let val_bytes = val.downcast::<PyBytes>()?.as_bytes();
            let count = val_bytes.len() / 8;
            let mut raw = vec![0i64; count];
            unsafe {
                std::ptr::copy_nonoverlapping(
                    val_bytes.as_ptr(),
                    raw.as_mut_ptr() as *mut u8,
                    count * 8,
                );
            }
            let mut res = Vec::with_capacity(count);
            for i in 0..count {
                let is_null = mask_bytes.get(i).copied().unwrap_or(0) != 0;
                res.push(if is_null { None } else { Some(raw[i]) });
            }
            Ok(ColumnData::Int64Opt(res))
        }
        "bool" => {
            let val_bytes = val.downcast::<PyBytes>()?.as_bytes();
            let count = val_bytes.len();
            let mut res = Vec::with_capacity(count);
            for i in 0..count {
                let is_null = mask_bytes.get(i).copied().unwrap_or(0) != 0;
                res.push(if is_null {
                    None
                } else {
                    Some(val_bytes[i] != 0)
                });
            }
            Ok(ColumnData::BoolOpt(res))
        }
        _ => extract_tagged_column(tag, val),
    }
}

fn extract_from_list(list: &Bound<'_, PyList>) -> PyResult<ColumnData<'static>> {
    let len = list.len();
    if len == 0 {
        return Ok(ColumnData::Empty(0));
    }

    let mut first_non_none = None;
    for item in list.iter() {
        if !item.is_none() {
            first_non_none = Some(item);
            break;
        }
    }

    let Some(first) = first_non_none else {
        return Ok(ColumnData::Empty(len));
    };

    if first.is_instance_of::<PyBool>() {
        let mut has_none = false;
        let mut res_opt = Vec::with_capacity(len);
        for item in list.iter() {
            if item.is_none() {
                has_none = true;
                res_opt.push(None);
            } else {
                res_opt.push(Some(item.extract::<bool>()?));
            }
        }
        if !has_none {
            let dense: Vec<bool> = res_opt.into_iter().map(|x| x.unwrap()).collect();
            return Ok(ColumnData::Bool(dense));
        }
        return Ok(ColumnData::BoolOpt(res_opt));
    }

    if first.is_instance_of::<PyInt>() {
        let mut has_none = false;
        let mut res_opt = Vec::with_capacity(len);
        for item in list.iter() {
            if item.is_none() {
                has_none = true;
                res_opt.push(None);
            } else {
                res_opt.push(Some(item.extract::<i64>()?));
            }
        }
        if !has_none {
            let dense: Vec<i64> = res_opt.into_iter().map(|x| x.unwrap()).collect();
            return Ok(ColumnData::Int64(dense));
        }
        return Ok(ColumnData::Int64Opt(res_opt));
    }

    if first.is_instance_of::<PyFloat>() {
        let mut has_none = false;
        let mut res_opt = Vec::with_capacity(len);
        for item in list.iter() {
            if item.is_none() {
                has_none = true;
                res_opt.push(None);
            } else {
                res_opt.push(Some(item.extract::<f64>()?));
            }
        }
        if !has_none {
            let dense: Vec<f64> = res_opt.into_iter().map(|x| x.unwrap()).collect();
            return Ok(ColumnData::Float64(dense));
        }
        return Ok(ColumnData::Float64Opt(res_opt));
    }

    let mut has_none = false;
    let mut res_opt = Vec::with_capacity(len);
    for item in list.iter() {
        if item.is_none() {
            has_none = true;
            res_opt.push(None);
        } else if let Ok(s) = item.downcast::<PyString>() {
            let s_str: &str = s.to_str()?;
            res_opt.push(Some(s_str.to_string()));
        } else {
            let s_obj = item.str()?;
            let s_str: &str = s_obj.to_str()?;
            res_opt.push(Some(s_str.to_string()));
        }
    }
    if !has_none {
        let dense: Vec<String> = res_opt.into_iter().map(|x| x.unwrap()).collect();
        return Ok(ColumnData::StringDense(dense));
    }
    Ok(ColumnData::StringOpt(res_opt))
}

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
    let mut cols_data: Vec<ColumnData<'static>> = Vec::with_capacity(columns.len());
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
fn _rapidxlsx(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(write_xlsx, m)?)?;
    Ok(())
}
