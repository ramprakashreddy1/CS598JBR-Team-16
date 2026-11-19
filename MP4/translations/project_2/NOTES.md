STATUS: BLOCKED

## Design
- `Card` is a `Copy` wrapper over the same bit encoding as C. Lookup tables (`ALL_CARDS`, `ALL_RANKS`, ...) replace C's big `switch` statements and integer-to-enum casts, so no `transmute` is needed.
- `CardCollection` (private fields changed) is a `Vec<Card>` instead of a circular doubly linked list. It keeps the C sorter protocol: `sorter(before, new, after)` is tried at each gap from the front to the back. `CardHand` stores `max`, `sorter` and the collection, and its length is the Vec length.
- `iterate_hand` walks by index and honours `ItrAction` (Continue/Break/Remove*). The reported position stays correct after removals, as in C.
- `CardDeck` keeps a `[bool; 52]` presence table. As in C, `deal_from_deck` picks the n-th remaining card in `CardSuitRank` order with `lrand48() % card_count`.
- `lrand48` is the POSIX 48-bit LCG in safe integer arithmetic, kept in a process-wide `AtomicU64` initialised like `srand48(3)`.
- `razz_simulation`: C's stateful `duplicated_rank_remover` and `length_trimmer` are replaced by a `pub(crate) CardHand::ranks()` iterator. The Razz rank is the 5th distinct rank of the sorted hand, or `InvalidRank` if there are fewer than five.
- No unsafe code, `#![forbid(unsafe_code)]` is set, Clippy shows zero findings in `src/*.rs`, and the unsafe metrics are all zero. The module-inception lint is allowed because the required module layout forces it.

## Hardest parts
Translating the pointer-ring collection and the removal-during-iteration protocol, and the global `lrand48` state.

## Why BLOCKED
`cargo test` builds and runs; `test_card_operations` fails at `src/bin/test.rs:147` (first card of a new deck was R2, expected R9). The test's expectations about the random generator contradict each other.
- The deal order `SEED3_DEALING_ORDER`, with `Heart9` first, is asserted on freshly created decks after earlier decks have already dealt cards (hand section, 1-card hand section, 3-card hand section). That only holds if every `create_shuffled_deck()` restarts the generator at seed 3.
- `expected_card_count` is the first-card distribution over 52,000 freshly created decks after a single `srand48(3)`, so the generator must keep advancing across `create_shuffled_deck()` calls. With a per-deck seed, all 52,000 first cards would be `Heart9`.
- The interface has no seeding function. No honest rule (a per-deck or a process-wide generator) satisfies both, and I did not special-case call counts.
- I chose the process-wide generator seeded once with 3, which is what the C program does (global `lrand48`). With it the test passes the deck section and fails at the first hand assertion. I only checked the per-deck alternative by analysis, not by running it: it would pass up to the distribution check and fail there.
