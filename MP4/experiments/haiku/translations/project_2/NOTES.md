STATUS: BLOCKED

## Conflict

`cargo test` fails at `src/bin/test.rs:147` (`test_card_operations`, the seven-card hand section, first assertion after the first insert): expected `R9`, got `R2`.

The cause is in the benchmark, not the implementation. In `card_test.c`, every section starts with `srand48(3)` (lines 198, 218, 286, 305, 335), so each section expects a fresh seed-3 stream from offset 0. The Rust interface has no seeding function, and the Rust test has no reseed calls, so all sections draw from one process-wide generator.

- Process-wide generator (C's `lrand48` semantics, the design used here): only the first deck can start at offset 0. The first section's 50 deals already advance the stream, so the seven-card section sees a different stream. Its expected values need a seed-3 reset that the interface cannot express.
- Per-deck generator seeded with 3 at creation: I checked by hand against `SEED3_DEALING_ORDER` that the seven-card, one-card and head-removal sections would match. It fails the distribution section (every fresh deck would deal the same card, so 52,000 draws land on one bin) and makes every game in `simulate_razz_game` identical, so it is not a faithful design.
- The distribution section (`expected_card_count`) needs a process-wide stream that starts at seed-3 offset 0 and advances across decks. That contradicts the seven-card expectations under any design that does not reset the stream, so no honest design satisfies all sections.

Verified facts (scratch checks, since removed from the deliverable):
- A fresh process whose first deck deals 52 cards produces exactly `SEED3_DEALING_ORDER`.
- A fresh process running 52,000 fresh-deck single deals produces exactly `expected_card_count`.
- Both expectations agree with the C reference (`srand48(3)` then the same draws), and the seed-3 stream is `(seed << 16) | 0x330E` with the POSIX multiplier `0x5DEECE66D`, increment `0xB`, 48-bit mask, returning `state >> 17`.

Everything before line 147 passes, and the seven-card, one-card, head-removal, remove-and-break, capacity, and razz-simulation logic were exercised by scratch tests with explicit seed-3 cards.

## Design

- `src/lib.rs`: `#![forbid(unsafe_code)]` as the first line.
- `Card` keeps the C byte layout (suit bits in the top three bits, rank in the low five) and uses the public `*_BITS` constants through three private lookup tables: suits (bits, letter), ranks (bits, label), and `ALL_CARDS` in `CardSuitRank` order. Sentinels map to `INVALID_*`.
- `CardDeck` holds the cards still in the deck as a `Vec<CardSuitRank>` in `CardSuitRank` order. `deal_from_deck` removes index `lrand48() % len` (matching the C indexing), and `None` is returned without a draw when empty.
- The generator is a `static Mutex<Lrand48>` (process-wide, as C's `lrand48` state is), initialised to the `srand48(3)` state. Poisoned locks are recovered with `PoisonError::into_inner`.
- `CardCollection` is a sentinel-headed singly linked list with `Option<Box<_>>` links, plus an iterative `Drop`. Insertion calls the sorter with `None` for the head and tail, matching C's `NULL`. The hand walk visits by position, and removal happens through `unlink_at` after a shared lookup, so no borrow is held across a removal.
- `CardHand` keeps the stub fields; `len` only counts cards that were actually inserted.
- `razz_simulation`: `RAZZ_CARD_IN_HAND_COUNT`, `strip_deck`, `complete_hand`, and the Razz rank (drop duplicate ranks, keep five lowest, take the highest). The C `static prev_rank` in the duplicate remover is a `thread_local!` `Cell`, because iterator callbacks are plain function pointers.

## Hardest C constructs

- The circular doubly linked collection with `prev`/`next` and removal under an iterator. Safe Rust cannot hold a shared `prev` and an owned `next`, so the list is singly linked and removal is by position.
- The `static` `prev_rank` in the duplicate remover, moved to a `thread_local!`.
- The global `lrand48` state and its seeding, handled by the static `Mutex`.
- `NULL` sentinels (`before`/`after` in sorters, empty cards), mapped to `Option::None`.
- `strtocard` character arithmetic, mapped to byte-slice patterns with `to_ascii_uppercase`.

## Deliberate differences from C

- `insert_into_hand` ignores an absent card instead of inserting a `NULL` entry, and does not count a card the sorter rejects (C counted it and leaked it).
- `CardCollection::detach_from_collection` takes `&Option<Box<_>>` into the list it modifies, which safe code cannot produce while `&mut self` is held. It is implemented by identity and is a no-op in safe use. It is kept only because the public signature is fixed.
- Parameters `_before` and `_new` of `sort_card_after` are underscore-prefixed (names only, types unchanged).
- `#[allow(clippy::module_inception)]` on the nested `card::card` and `razz_simulation::razz_simulation` modules, which the benchmark's import paths depend on.
- C's debug printing (`#ifndef NDEBUG`) is not translated.

## Verification

- `cargo +nightly-2025-05-13 build --all-targets`: builds; warnings only in `src/bin/test.rs`, which I did not touch.
- `cargo +nightly-2025-05-13 test`: one failure, at `src/bin/test.rs:147` (see Conflict).
- Clippy (`correctness`, `style`, `complexity`, `perf`) with `--all-targets --all-features`: zero findings in `src/*.rs`.
- `unsafe_metrics.py`: every primary metric 0, `#![forbid(unsafe_code)]` present.
