# Razz C-to-Rust behavior audit

This supplemental audit runs the original C implementation and the current Rust
translation in separate executable processes with identical inputs. It compares
the complete outputs for 505 cases, including 32,384 simulated games.

| Operation | Cases |
| --- | ---: |
| ASCII parser and enum conversion batch | 1 |
| Seeded decks, stripping, exhaustion, and interleaved decks | 24 |
| Hand sorting, capacities, duplicates, resets, and all iterator actions | 288 |
| Positive-length simulations and decided-card scenarios | 192 |

Run from the `MP4/` directory with the pinned Rust toolchain and a C
compiler available. The script selects the installed macOS 15.2 SDK on this host.

```sh
python3 experiments/razz_behavior_audit/run_audit.py
```

The tool compiles unmodified original C source through `probe.c`. It copies the
Rust crate into a temporary directory, adds the existing harness-only seeding
hook, and builds `probe.rs` there. Production code implements its own behavior.
The comparator saves input hashes, command diagnostics, per-case output hashes,
and complete mismatch diffs. It exits with status 1 if any case differs.

`before/` records 60 mismatching hand cases before the follow-up repair. The C
iterator stops a traversal after removing the head, because its predecessor
advances to the new head and reaches the iterator's termination check. The initial
Rust port continued after that removal. Its `remove_from_hand` also removed all
matching cards, while the C walk stops after removing a matching head.

`after/` records 505 matching cases after a logged Codex repair. All 24 deck
cases and all 192 simulation scenarios matched before and after the repair.
Eight focused Rust regressions are included in `translations/project_2/tests/`.
Four of those tests failed on the original Rust port; all eight pass after the
repair. The generated edits and tool feedback are archived under
`trajectories/project_2/follow_up_iterator/`.

The probes exercise valid card values, supported sorters, bounded decided-card
counts, and nonoverlapping decided cards. They cover serial RNG use with explicit
seeds. Zero-game C simulations are excluded because the original C cleanup reads
an uninitialized deck pointer on that path. Private collection helpers, allocation
failures, concurrent schedules, and arbitrary malformed inputs are outside the
comparison. The existing supplied benchmark and its separate scratch harness
have their own results under `experiments/razz_spec_check/`.
