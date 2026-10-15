## Test environments
* local Ubuntu 24.04 LTS (x86_64), R 4.5.3

## R CMD check results

0 ERRORs | 0 WARNINGs | 1 NOTE

* Found the following (possibly) invalid URLs:
  URL: https://github.com/aminfathullah/rapidxlsx
  This is a new submission; the repository and issues will be public upon release.

* Found 'abort' in compiled code:
  The package is backed by Rust. The 'abort' entry point originates from the standard Rust runtime library panic handlers and cannot be reached during normal execution, as all serialization is wrapped in std::panic::catch_unwind.
