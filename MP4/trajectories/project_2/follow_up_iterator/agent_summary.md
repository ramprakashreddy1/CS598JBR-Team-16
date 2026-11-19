Repaired [src/card.rs](src/card.rs) with shared, safe traversal semantics. Head removal ends traversal; non-head removal continues at the shifted position.

Both C probes confirmed:
- `[0,3,6]`: one callback, leaving `[3,6]`.
- `[SpadeAce,SpadeAce,Spade2]`: removal leaves `[SpadeAce,Spade2]`.

Added 8 [supplemental tests](tests/hand_traversal.rs) covering all actions, removal positions, duplicates, and empty/singleton hands:
- Old implementation: **4 passed, 4 failed**.
- Repaired implementation: **8 passed**.
- Independent audit: **445/505 → 505/505 matching**, including 32,384 simulated games.

Using `nightly-2025-05-13`, build and all-target clippy passed. Full `cargo test` still fails at benchmark line 147 (`R2` versus `R9`), as expected from omitted seed resets. Existing benchmark warnings remain.

Public APIs, manifests, lockfile, benchmark, module wiring, and `forbid(unsafe_code)` were preserved. Evidence is in `/tmp/razz-repair-evidence`.
