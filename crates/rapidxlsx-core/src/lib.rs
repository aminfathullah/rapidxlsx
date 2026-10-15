pub mod columns;
pub mod writer;
pub mod xml;
pub mod zip;

pub use columns::ColumnData;
pub use writer::write_xlsx_file;
pub use zip::ZipPackage;

#[cfg(test)]
mod tests {
    use super::*;
    use crate::xml::{append_escaped_xml, col_name};

    #[test]
    fn test_col_names() {
        assert_eq!(col_name(0), "A");
        assert_eq!(col_name(25), "Z");
        assert_eq!(col_name(26), "AA");
        assert_eq!(col_name(27), "AB");
        assert_eq!(col_name(701), "ZZ");
        assert_eq!(col_name(702), "AAA");
        assert_eq!(col_name(16383), "XFD");
    }

    #[test]
    fn test_xml_escaping() {
        let mut buf = Vec::new();
        append_escaped_xml(&mut buf, "A & B < C > D \"quotes\" 'apos' \x00control\x1f");
        assert_eq!(
            String::from_utf8(buf).unwrap(),
            "A &amp; B &lt; C &gt; D &quot;quotes&quot; &apos;apos&apos; control"
        );
    }

    #[test]
    fn test_write_xlsx_roundtrip() {
        let dir = std::env::temp_dir();
        let path = dir.join("test_core_write.xlsx");

        let headers = vec!["ColA".to_string(), "ColB".to_string(), "ColC".to_string()];
        let cols = vec![
            ColumnData::Int64(vec![1, 2, 3]),
            ColumnData::Float64(vec![1.5, 2.5, f64::NAN]),
            ColumnData::Bool(vec![true, false, true]),
        ];

        let res = write_xlsx_file(&path, "TestSheet", &headers, &cols, 1);
        assert!(res.is_ok());
        assert!(path.exists());
        assert!(std::fs::metadata(&path).unwrap().len() > 0);

        let _ = std::fs::remove_file(path);
    }
}

