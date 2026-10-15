## Test environments
* local Ubuntu 24.04 LTS (x86_64), R 4.5.3
* win-builder (devel and release)
* Debian Linux (r-devel)

## R CMD check results

0 ERRORs | 0 WARNINGs | 1 NOTE

* Maintainer: 'Amin Fathullah <amin_fathullah@yahoo.com>'
  New submission.

* Offline compilation:
  All Rust crate dependencies are bundled offline in src/rust/vendor.tar.xz and unpacked during package installation, strictly adhering to CRAN policy prohibiting network access during build and install.
