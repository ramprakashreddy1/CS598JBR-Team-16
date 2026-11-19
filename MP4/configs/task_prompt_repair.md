# Task: repair the Rust translation of `<<PROJECT_NAME>>` (pipeline iteration <<ITERATION>> of at most <<MAX_ITERATIONS>>)

A previous iteration of this pipeline translated the C project to Rust. The controller then re-verified the result independently with the pinned toolchain; the findings are below. Your job in this iteration is to fix everything that is still not green while keeping all rules (no `unsafe`, no edits to `Cargo.toml` or `src/bin/*.rs`, public signatures unchanged, no hard-coded test answers).

## Locations

- C project (read-only): `<<C_DIR>>`
- Rust project (your working directory): `<<RUST_DIR>>`
- Unsafe-metrics scan: `python3 <<MP4_DIR>>/src/unsafe_metrics.py .`

### C files
```
<<C_FILES>>
```

### Rust files
```
<<RUST_FILES>>
```

## Project-specific context supplied by the pipeline

<<PROJECT_CONTEXT>>

<<FEEDBACK>>

## What to do

1. Read `NOTES.md` (if present) and the current Rust sources to understand the existing design; read the relevant C code again where behaviour is in doubt.
2. Reproduce each reported problem locally (`cargo +<<TOOLCHAIN>> test`, `<<CLIPPY_CMD>>`, the unsafe scan), diagnose the root cause in the implementation, and repair it. Prefer fixing the design over patching symptoms; prefer safe abstractions (slices, `Vec`, `Option`, `Result`, iterators) over anything pointer-like.
3. Re-run build, tests, Clippy and the unsafe scan until all are green.
4. Update `NOTES.md` (`STATUS: DONE`, or `STATUS: BLOCKED` with the exact conflicting expectations if an honest implementation cannot satisfy the specification) and finish with a short summary of the final state.
