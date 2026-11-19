# Base122 behavior audit

This supplemental audit builds the unchanged C encoder/decoder and a temporary
copy of the submitted Rust crate as independent executables. It compares
encoded bytes, decoded bytes, and exact error messages. It also checks that each
successful Rust encoding decodes to the original input. Production Rust files
and supplied tests are not changed.

From the `MP4/` directory:

```sh
python3 experiments/base122_behavior_audit/run_audit.py
```

The deterministic input corpus includes every byte string of length zero, one,
or two; 1,000 longer samples generated with Python seed 598; and 72 repeated-byte
samples. Each input is independently encoded and decoded, giving 133,730
comparisons. On November 18, 2026, all comparisons matched. Retained results are
in `official_checks/readiness_2026-11-18/base122_audit/`.

The script retains source hashes, compiler diagnostics, output hashes, summary,
and any mismatches. It requires a C compiler and `nightly-2025-05-13`; it selects
the installed macOS 15.2 SDK on this host. It uses no model calls.

This audit exercises codec APIs, not arbitrary mutations of the public reader
or writer fields, allocation failure, or every possible long input. The existing
six supplemental bit-writer tests cover the earlier prefilled-buffer repair.
