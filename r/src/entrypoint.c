#include <R.h>
#include <Rinternals.h>
#include <R_ext/Rdynload.h>

extern SEXP c_write_xlsx(SEXP path, SEXP sheet, SEXP df, SEXP comp);

static const R_CallMethodDef CallEntries[] = {
    {"c_write_xlsx", (DL_FUNC) &c_write_xlsx, 4},
    {NULL, NULL, 0}
};

void R_init_fastxlsx(DllInfo *dll) {
    R_registerRoutines(dll, NULL, CallEntries, NULL, NULL);
    R_useDynamicSymbols(dll, FALSE);
}
