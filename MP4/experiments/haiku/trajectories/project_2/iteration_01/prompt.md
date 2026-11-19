# Task: translate the C project `razz_simulation` to safe, idiomatic Rust (pipeline iteration 1 of at most 4)

## Locations

- C project (read-only): `/Users/ram/Desktop/UIUC/Fall 2026/CS598_LLM/CS598JBR-Team-16/MP4/subjects/project_2`
- Rust project you are completing (your working directory): `experiments/haiku/translations/project_2`
- Pipeline tools: `/Users/ram/Desktop/UIUC/Fall 2026/CS598_LLM/CS598JBR-Team-16/MP4/src/unsafe_metrics.py` (unsafe-metrics scan; run it as `python3 /Users/ram/Desktop/UIUC/Fall 2026/CS598_LLM/CS598JBR-Team-16/MP4/src/unsafe_metrics.py .`)

### C files
```
  card.c                                                964 lines
  card.h                                                417 lines
  card_test.c                                           353 lines
  razz.c                                                211 lines
  razz_simulation.c                                     215 lines
  razz_simulation.h                                      72 lines
```

### Rust files (interface stubs with `unimplemented!()` bodies, and the benchmark tests under `src/bin/`)
```
  Cargo.toml                                              6 lines
  src/bin/test.rs                                       238 lines
  src/card.rs                                           170 lines
  src/lib.rs                                              2 lines
  src/razz_simulation.rs                                 20 lines
```

## Project-specific context supplied by the pipeline

Project context for `razz_simulation` (facts gathered by the pipeline from the C project and the Rust specification; no implementation is prescribed):

- Files: `card.h`/`card.c` (cards, a doubly linked card collection, hands with a pluggable sorter callback, a deck), `razz_simulation.h`/`razz_simulation.c` (the simulation engine with a rank-listener callback), `razz.c` (a command-line driver, not part of the Rust specification), `card_test.c` (the C tests, the source of the Rust test's expectations). `doc/` is generated Doxygen output.
- Randomness: the C code uses the POSIX 48-bit linear congruential generator. `card_test.c` calls `srand48(3)` before each test section and `deal_from_deck` in `card.c` chooses the dealt card with `lrand48() % d->card_count`. `create_shuffled_deck` does not shuffle anything: it only marks all 52 cards as present; the randomness is applied at deal time by indexing the remaining cards in `CardSuitRank` order.
- POSIX definition: X(n+1) = (0x5DEECE66D * X(n) + 0xB) mod 2^48; `srand48(s)` sets X = (s << 16) | 0x330E; `lrand48()` advances X and returns its top 31 bits (X >> 17). The grading environment has no dependencies, so a faithful translation implements this generator itself with safe integer arithmetic.
- The Rust test `src/bin/test.rs` embeds `SEED3_DEALING_ORDER` (the first 52 cards dealt after `srand48(3)`) and `expected_card_count` (the first-card distribution over 52,000 freshly created decks after one `srand48(3)`). The Rust interface has no seeding function, so the translation has to decide where the generator state lives and when it is seeded. Check which expectations a per-deck generator seeded with 3 satisfies, which a single process-wide generator seeded once satisfies, and whether any honest design satisfies all of them. Do not special-case call counts or inputs. If the expectations are mutually inconsistent, pick the most faithful deterministic design, state the exact conflict in `NOTES.md` with `STATUS: BLOCKED`, and stop.
- `CardHand::iterate_hand` takes a `CardIterator` callback that returns `ItrAction` (continue, break, remove-and-continue, remove-and-break), mirroring the C iterator protocol; `CardSorter` callbacks decide the insertion position (`sort_card_after`, `sort_card_by_rank`). The `CardCollection` fields are private, so a safe ownership design (for example a boxed singly linked list or a `Vec`-backed collection) is acceptable as long as every public signature stays unchanged.


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
