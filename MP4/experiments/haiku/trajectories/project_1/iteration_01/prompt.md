# Task: translate the C project `libbase122` to safe, idiomatic Rust (pipeline iteration 1 of at most 4)

## Locations

- C project (read-only): `/Users/ram/Desktop/UIUC/Fall 2026/CS598_LLM/CS598JBR-Team-16/MP4/subjects/project_1`
- Rust project you are completing (your working directory): `experiments/haiku/translations/project_1`
- Pipeline tools: `/Users/ram/Desktop/UIUC/Fall 2026/CS598_LLM/CS598JBR-Team-16/MP4/src/unsafe_metrics.py` (unsafe-metrics scan; run it as `python3 /Users/ram/Desktop/UIUC/Fall 2026/CS598_LLM/CS598JBR-Team-16/MP4/src/unsafe_metrics.py .`)

### C files
```
  CMakeLists.txt                                         58 lines
  README.md                                              62 lines
  src/base122.c                                         248 lines
  src/base122.h                                          46 lines
  src/util.h                                            154 lines
  test/assertions.c                                     109 lines
  test/assertions.h                                      87 lines
  test/fuzz.c                                            48 lines
  test/test.c                                           503 lines
  test/testconsumer/CMakeLists.txt                       31 lines
  test/testconsumer/testconsumer.c                       19 lines
```

### Rust files (interface stubs with `unimplemented!()` bodies, and the benchmark tests under `src/bin/`)
```
  Cargo.toml                                              6 lines
  src/base122.rs                                        103 lines
  src/bin/tests.rs                                      222 lines
  src/lib.rs                                              1 lines
```

## Project-specific context supplied by the pipeline

Project context for `libbase122` (facts gathered by the pipeline from the C project and the Rust specification; no implementation is prescribed):

- The C library (`src/base122.c`, helpers in `src/util.h`) implements a binary-to-text encoding that packs 7 bits per output byte and escapes six illegal byte values (null, newline, carriage return, double quote, ampersand, backslash) as two-byte sequences. `test/test.c` holds the C test vectors and the exact error-message strings; `test/fuzz.c` is a fuzz harness that is not part of the Rust specification.
- The C API `base122_encode/decode(in, in_len, out, out_len, out_written, error)` treats `out == NULL` as a size-only pass. The Rust interface mirrors this with `BitWriter { output: Option<&mut [u8]>, len, cur_bit, count_only }`, `BitWriter::new(output: Option<&mut [u8]>, len)` and `encode_internal(input, output: Option<&mut [u8]>, out_written)`, while the public `encode`/`decode` return `Result<Vec<u8>, Base122Error>`.
- The Rust tests check `error.message.contains("<text>")` with substrings taken verbatim from the messages the C code writes into `error->msg`; reproduce those messages exactly.
- `src/lib.rs` is `pub mod base122;` and the tests import `libbase122::base122::{BitReader, BitWriter, decode, encode}`. `BitReader::read(nbits)` returns `(bits_read, value)`; `BitWriter::write(nbits, value)` returns `Ok(bytes_used_so_far)` or an error when the output is full.


## What to do

1. Inspect the C project thoroughly (headers, implementation, C tests). Understand the data structures, the algorithm, all error paths and the exact strings or numeric conventions that the tests depend on.
2. Read every Rust stub and every benchmark test in `src/bin/`. The tests are part of the specification; the public signatures in the stubs must stay exactly as they are.
3. Implement every `unimplemented!()` in `src/*.rs` with safe, idiomatic Rust. Add `#![forbid(unsafe_code)]` as the first line of `src/lib.rs`.
4. Verify and repair until green, in this order:
   - `cargo +nightly-2025-05-13 build --all-targets`
   - `cargo +nightly-2025-05-13 test`
   - `cargo +nightly-2025-05-13 clippy --all-targets --all-features -- -W clippy::correctness -W clippy::style -W clippy::complexity -W clippy::perf` (target: zero findings in `src/*.rs`; findings inside `src/bin/` are in benchmark files you must not touch)
   - `python3 /Users/ram/Desktop/UIUC/Fall 2026/CS598_LLM/CS598JBR-Team-16/MP4/src/unsafe_metrics.py .` (target: every metric zero, forbid attribute present)
5. Write `NOTES.md` (first line `STATUS: DONE` or `STATUS: BLOCKED`, then the design notes described in your instructions) and finish with a short summary of the final state: build, tests, clippy, unsafe metrics, and anything still failing with the reason.

Remember: do not edit `Cargo.toml` or `src/bin/*.rs`; do not use `unsafe`, raw pointers, FFI or dependencies; do not hard-code test outputs. The controller will independently re-run build, tests, clippy and the unsafe scan after you finish and will start a repair iteration if anything is not green.
