library(rapidxlsx)

args <- commandArgs(trailingOnly = TRUE)
compare <- "--compare" %in% args || "--writexl" %in% args

num_rows <- 1000000L
num_cols <- 20L

cat(sprintf("Generating dataset: %s rows x %d columns in R...\n", format(num_rows, big.mark = ","), num_cols))
t0 <- proc.time()

cols <- list(id = seq_len(num_rows))
for (i in seq_len(num_cols - 3L)) {
  cols[[sprintf("num_%d", i)]] <- seq(0.1 * i, 100.0 * i, length.out = num_rows)
}
cols[["flag"]] <- rep(c(TRUE, FALSE), length.out = num_rows)
cols[["category"]] <- rep(c("group_A", "group_B", "group_C", "group_D"), length.out = num_rows)

df <- as.data.frame(cols, stringsAsFactors = FALSE)
cat(sprintf("Data generation: %.3f s\n\n", (proc.time() - t0)["elapsed"]))

out_path <- tempfile(fileext = ".xlsx")

tryCatch({
  cat("Writing XLSX using rapidxlsx::write_xlsx()...\n")
  t_start <- proc.time()
  write_xlsx(df, out_path, sheet_name = "Benchmark")
  t_elapsed <- (proc.time() - t_start)["elapsed"]

  file_size_mb <- file.size(out_path) / (1024 * 1024)
  throughput <- num_rows / t_elapsed

  cat(sprintf("rapidxlsx: %.3f s (%s rows/s, %.2f MB)\n",
              t_elapsed,
              format(round(throughput), big.mark = ","),
              file_size_mb))

  stopifnot(t_elapsed < 5.0)
  cat("PASS: Completed under 5 seconds.\n")

  if (compare && requireNamespace("writexl", quietly = TRUE)) {
    cat("\nWriting XLSX using writexl::write_xlsx()...\n")
    out_wxl <- tempfile(fileext = ".xlsx")
    t_wxl_start <- proc.time()
    writexl::write_xlsx(df, out_wxl)
    t_wxl_elapsed <- (proc.time() - t_wxl_start)["elapsed"]
    wxl_size_mb <- file.size(out_wxl) / (1024 * 1024)
    wxl_throughput <- num_rows / t_wxl_elapsed

    cat(sprintf("writexl  : %.3f s (%s rows/s, %.2f MB)\n",
                t_wxl_elapsed,
                format(round(wxl_throughput), big.mark = ","),
                wxl_size_mb))
    cat(sprintf("Speedup  : %.1fx faster than writexl\n", t_wxl_elapsed / t_elapsed))
    unlink(out_wxl)
  }
}, finally = {
  if (file.exists(out_path)) {
    unlink(out_path)
  }
})
