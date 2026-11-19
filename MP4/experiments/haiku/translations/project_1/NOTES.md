STATUS: DONE

## Design

- `src/lib.rs` carries `#![forbid(unsafe_code)]` and `pub mod base122;`.
- `BitReader` keeps its public fields (`input`, `byte_pos`, `bit_pos`). `read` consumes up to 8 bits MSB-first and returns a right-aligned value with zero padding. `remaining_bits` is a private helper.
- `BitWriter` keeps its public fields (`output`, `len`, `cur_bit`, `count_only`). `new` sets `count_only` when there is no output buffer. `write` checks capacity before writing anything, so a failed write leaves no partial output. In count-only mode it only advances the bit position. `write` returns the number of bytes touched so far (`div_ceil(8)`).
- `encode` and `decode` mirror the C two-pass API. The first pass calls `*_internal` with no buffer to measure the output and surface all input errors. The second pass fills an exactly sized `Vec<u8>`. This avoids any growth logic and keeps the internal functions' signatures as specified.
- `Base122Error` implements `Display` and `std::error::Error`. Every message is copied verbatim from `test/test.c` and `src/base122.c`.

## Hardest C constructs

- The shortened two-byte form (illegal index 7): the illegal value itself travels in the 7 payload bits, and the sequence must be the final unit of the input.
- The last-byte rules in `write_last_7`: pad to a byte boundary, reject a leftover byte boundary exactly at 0 bits ("not a byte multiple"), and reject non-zero padding bits ("Last byte has extra data").
- Bit-level packing: the C code uses `unsigned short` shifting over two bytes. The Rust version writes and reads one bit at a time with explicit masks, which is simpler to verify.

## Unsafe patterns replaced

- Raw `unsigned char *` plus length pairs became `&[u8]` slices and `Option<&mut [u8]>`.
- The C `out == NULL` size-only mode became `Option::None` and `count_only`.
- The `goto`-like error reporting into `error->msg` became `Result<_, Base122Error>` with `?`.
- The C `assert` on `get_illegal_index` became a total function (`Option` + `unwrap_or`).
- Sentinel loops (`while ((nbits = read(...)) > 0)`) became `loop` with an explicit break on zero bits. Byte iteration uses `split_first` instead of index arithmetic.

## Signature note

- `write_last_7` (private) no longer takes the unused `error: &mut Base122Error` parameter. Its error is returned through `Result`, which is the only path the code needs. No public item changed.

## Verification

- `cargo +nightly-2025-05-13 build --all-targets`: builds. Remaining warnings are in `src/bin/tests.rs` (unused imports, dead code), which I cannot modify.
- `cargo +nightly-2025-05-13 test`: 6 passed, 1 ignored (`test_encode_file`, needs external data files).
- Clippy with the required groups: zero findings in `src/base122.rs` and `src/lib.rs`. All findings are in `src/bin/tests.rs`.
- `unsafe_metrics.py`: every metric is 0 and the forbid attribute is present.
- Extra check: 20,000 random round-trips (`decode(encode(x)) == x`) all pass. Every random input that decodes successfully re-encodes and decodes back to the same bytes.

## Notes for the reviewer

- A temporary scratch example at `examples/b122_diff_tmp.rs` (replaced by a no-op `fn main() {}`) and its `examples/` directory remain because deleting them needed approval. They are not part of the solution and should be removed.

## Summary

The Base122 encoder and decoder are fully implemented in safe Rust. Public signatures match the stubs exactly. The build succeeds. All active benchmark tests pass. The generated code has zero Clippy findings and zero unsafe metrics. The only remaining warnings come from the benchmark file, which I was not allowed to edit.

The design follows the C semantics: exact error strings, the shortened two-byte form, and two-pass sizing. The C reference was checked by reading the code and by the benchmark vectors. A direct C-vs-Rust differential run was not completed, because executing the compiled C harness needed approval in this session.
