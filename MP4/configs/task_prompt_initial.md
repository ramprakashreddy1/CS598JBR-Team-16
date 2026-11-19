# Task: translate the C project `<<PROJECT_NAME>>` to safe, idiomatic Rust (pipeline iteration <<ITERATION>> of at most <<MAX_ITERATIONS>>)

## Locations

- C project (read-only): `<<C_DIR>>`
- Rust project you are completing (your working directory): `<<RUST_DIR>>`
- Pipeline tools: `<<MP4_DIR>>/src/unsafe_metrics.py` (unsafe-metrics scan; run it as `python3 <<MP4_DIR>>/src/unsafe_metrics.py .`)

### C files
```
<<C_FILES>>
```

### Rust files (interface stubs with `unimplemented!()` bodies, and the benchmark tests under `src/bin/`)
```
<<RUST_FILES>>
```

## Project-specific context supplied by the pipeline

<<PROJECT_CONTEXT>>

## What to do

1. Inspect the C project thoroughly (headers, implementation, C tests). Understand the data structures, the algorithm, all error paths and the exact strings or numeric conventions that the tests depend on.
2. Read every Rust stub and every benchmark test in `src/bin/`. The tests are part of the specification; the public signatures in the stubs must stay exactly as they are.
3. Implement every `unimplemented!()` in `src/*.rs` with safe, idiomatic Rust. Add `#![forbid(unsafe_code)]` as the first line of `src/lib.rs`.
4. Verify and repair until green, in this order:
   - `cargo +<<TOOLCHAIN>> build --all-targets`
   - `cargo +<<TOOLCHAIN>> test`
   - `<<CLIPPY_CMD>>` (target: zero findings in `src/*.rs`; findings inside `src/bin/` are in benchmark files you must not touch)
   - `python3 <<MP4_DIR>>/src/unsafe_metrics.py .` (target: every metric zero, forbid attribute present)
5. Write `NOTES.md` (first line `STATUS: DONE` or `STATUS: BLOCKED`, then the design notes described in your instructions) and finish with a short summary of the final state: build, tests, clippy, unsafe metrics, and anything still failing with the reason.

Remember: do not edit `Cargo.toml` or `src/bin/*.rs`; do not use `unsafe`, raw pointers, FFI or dependencies; do not hard-code test outputs. The controller will independently re-run build, tests, clippy and the unsafe scan after you finish and will start a repair iteration if anything is not green.
