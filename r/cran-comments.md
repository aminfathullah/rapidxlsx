## Test environments
* local Ubuntu 24.04 LTS (x86_64), R 4.5.3
* win-builder (devel and release)
* Debian Linux (r-devel)

## R CMD check results

0 ERRORs | 0 WARNINGs | 1 NOTE

* Maintainer: 'Amin Fathullah <amin_fathullah@yahoo.com>'
  New submission.

## Resubmission Notes

* Resolved "~/.cargo" creation:
  `CARGO_HOME` is now redirected to a local directory within the package build directory (`$(CURDIR)/.cargo`) during compilation and immediately removed along with extracted vendor files and target build directories upon completion. Cargo does not write to or leave behind any files in `$HOME/.cargo`, strictly complying with CRAN policy.

* Offline compilation:
  All Rust dependencies are bundled in src/rust/vendor.tar.xz and compiled with `cargo build -j 2 --offline --release`.

* Portable Makefiles:
  All Makefiles (Makevars, Makevars.win, Makevars.ucrt) use strictly portable POSIX syntax without GNU extensions.
