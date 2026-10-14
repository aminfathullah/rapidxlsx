#![allow(unsafe_op_in_unsafe_fn)]

use std::ffi::{c_char, c_int, c_void, CStr};
use fastxlsx_core::{write_xlsx_file, ColumnData};

type SEXP = *mut c_void;

const LGLSXP: c_int = 10;
const INTSXP: c_int = 13;
const REALSXP: c_int = 14;
const STRSXP: c_int = 16;
const VECSXP: c_int = 19;

unsafe extern "C" {
    fn Rf_xlength(x: SEXP) -> isize;
    fn TYPEOF(x: SEXP) -> c_int;
    fn VECTOR_ELT(x: SEXP, i: isize) -> SEXP;
    fn STRING_ELT(x: SEXP, i: isize) -> SEXP;
    fn R_CHAR(x: SEXP) -> *const c_char;
    fn REAL_RO(x: SEXP) -> *const f64;
    fn INTEGER_RO(x: SEXP) -> *const i32;
    fn LOGICAL_RO(x: SEXP) -> *const i32;
    fn Rf_getAttrib(x: SEXP, symbol: SEXP) -> SEXP;
    fn Rf_isFactor(x: SEXP) -> c_int;
    fn Rf_error(fmt: *const c_char, ...) -> !;

    static R_NamesSymbol: SEXP;
    static R_LevelsSymbol: SEXP;
    static R_NilValue: SEXP;
    static R_NaString: SEXP;
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn c_write_xlsx(
    path_sxp: SEXP,
    sheet_sxp: SEXP,
    df_sxp: SEXP,
    comp_sxp: SEXP,
) -> SEXP {
    if path_sxp == R_NilValue || Rf_xlength(path_sxp) == 0 {
        let msg = CStr::from_bytes_with_nul_unchecked(b"invalid path\0");
        Rf_error(b"%s\0".as_ptr() as *const c_char, msg.as_ptr());
    }
    let path_elt = STRING_ELT(path_sxp, 0);
    let path_cstr = CStr::from_ptr(R_CHAR(path_elt));
    let path_str = match path_cstr.to_str() {
        Ok(s) => s,
        Err(_) => {
            let msg = CStr::from_bytes_with_nul_unchecked(b"path must be valid UTF-8\0");
            Rf_error(b"%s\0".as_ptr() as *const c_char, msg.as_ptr());
        }
    };

    let sheet_str = if sheet_sxp != R_NilValue && Rf_xlength(sheet_sxp) > 0 {
        let elt = STRING_ELT(sheet_sxp, 0);
        CStr::from_ptr(R_CHAR(elt)).to_str().unwrap_or("Sheet1")
    } else {
        "Sheet1"
    };

    if TYPEOF(df_sxp) != VECSXP {
        let msg = CStr::from_bytes_with_nul_unchecked(b"data must be a data.frame or list\0");
        Rf_error(b"%s\0".as_ptr() as *const c_char, msg.as_ptr());
    }

    let num_cols = Rf_xlength(df_sxp) as usize;
    let mut headers = Vec::with_capacity(num_cols);

    let names_sxp = Rf_getAttrib(df_sxp, R_NamesSymbol);
    if names_sxp != R_NilValue {
        for c in 0..num_cols {
            let elt = STRING_ELT(names_sxp, c as isize);
            let name_str = CStr::from_ptr(R_CHAR(elt)).to_str().unwrap_or("");
            headers.push(name_str.to_string());
        }
    } else {
        for c in 0..num_cols {
            headers.push(format!("Col_{}", c + 1));
        }
    }

    let mut columns: Vec<ColumnData> = Vec::with_capacity(num_cols);

    for c in 0..num_cols {
        let col_sxp = VECTOR_ELT(df_sxp, c as isize);
        let col_len = Rf_xlength(col_sxp) as usize;
        let col_type = TYPEOF(col_sxp);

        let col_data = if col_type == REALSXP {
            let ptr = REAL_RO(col_sxp);
            let slice = std::slice::from_raw_parts(ptr, col_len);
            ColumnData::Float64Slice(slice)
        } else if col_type == INTSXP {
            let ptr = INTEGER_RO(col_sxp);
            if Rf_isFactor(col_sxp) != 0 {
                let levels_sxp = Rf_getAttrib(col_sxp, R_LevelsSymbol);
                let num_levels = Rf_xlength(levels_sxp) as usize;
                let mut levels: Vec<String> = Vec::with_capacity(num_levels);
                for l in 0..num_levels {
                    let s_elt = STRING_ELT(levels_sxp, l as isize);
                    let level_str = CStr::from_ptr(R_CHAR(s_elt)).to_str().unwrap_or("");
                    levels.push(level_str.to_string());
                }
                let int_slice = std::slice::from_raw_parts(ptr, col_len);
                let mut str_opt = Vec::with_capacity(col_len);
                for &idx in int_slice {
                    if idx == i32::MIN || idx <= 0 || (idx as usize) > num_levels {
                        str_opt.push(None);
                    } else {
                        str_opt.push(Some(levels[(idx - 1) as usize].clone()));
                    }
                }
                ColumnData::StringOpt(str_opt)
            } else {
                let slice = std::slice::from_raw_parts(ptr, col_len);
                ColumnData::Int32RNullable(slice)
            }
        } else if col_type == LGLSXP {
            let ptr = LOGICAL_RO(col_sxp);
            let slice = std::slice::from_raw_parts(ptr, col_len);
            ColumnData::Int32RLogical(slice)
        } else if col_type == STRSXP {
            let mut str_opt = Vec::with_capacity(col_len);
            for r in 0..col_len {
                let elt = STRING_ELT(col_sxp, r as isize);
                if elt == R_NaString {
                    str_opt.push(None);
                } else {
                    let cstr = CStr::from_ptr(R_CHAR(elt));
                    let s = cstr.to_str().unwrap_or("");
                    str_opt.push(Some(s.to_string()));
                }
            }
            ColumnData::StringOpt(str_opt)
        } else {
            ColumnData::Empty(col_len)
        };

        columns.push(col_data);
    }

    let comp_level = if comp_sxp != R_NilValue && TYPEOF(comp_sxp) == INTSXP && Rf_xlength(comp_sxp) > 0 {
        let val = *INTEGER_RO(comp_sxp);
        if val > 0 { val as u32 } else { 1 }
    } else {
        1
    };

    if let Err(e) = write_xlsx_file(path_str, sheet_str, &headers, &columns, comp_level) {
        let err_msg = format!("fastxlsx write error: {}\0", e);
        Rf_error(b"%s\0".as_ptr() as *const c_char, err_msg.as_ptr() as *const c_char);
    }

    R_NilValue
}
