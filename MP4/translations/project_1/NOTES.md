STATUS: DONE

Design: `BitReader`/`BitWriter` operate bit by bit on slices (no index/pointer arithmetic). `encode`/`decode` mirror the C "size-only pass" by running the internal routine once with `output = None` to count, then again into a zeroed `Vec<u8>`. Errors are `Base122Error` (with `Display`/`Error`) carrying the exact C messages; `?` propagates them.

Hardest parts: the C macros (`OUTPUT_BYTE`, `WRITE_7`) with early `return -1` became the `emit` and `write_7` helpers returning `Result`; the shortened trailing two-byte sequence and "last byte" bit-boundary checks were kept as in C. `write_last_7` and `get_illegal_index` signatures were adjusted (private) to drop the out-parameter error and use `Option`.

Unsafe: the C code had no real pointer tricks beyond buffer indexing; all of it is now bounds-checked slice access. `#![forbid(unsafe_code)]` is set; unsafe metrics are all zero.
