# MP4: Agentic C-to-Rust Translation (Team 16)

Group 16 projects from CRUST-Bench: **project_1 = `libbase122`** (a Base-122 binary-to-text codec: 2 C source files, 1 header of bit helpers, C tests) and **project_2 = `razz_simulation`** (a playing-card library with a linked card collection, hands, a deck, and a Razz poker simulator: 4 C source files, 2 headers, C tests).

```
MP4/
├── README.md
├── src/                 pipeline code: controller, verifier, unsafe-metrics scan, launch scripts
├── configs/             agent/model configuration, system prompt, task-prompt templates, per-project context
├── trajectories/        complete execution logs, one folder per project and per controller iteration
├── translations/        final generated Rust (Cargo projects; graded with nightly-2025-05-13)
├── subjects/            original C projects exactly as shipped in CRUST-Bench (CBench), unchanged
├── specs/               pristine CRUST-Bench Rust interfaces + tests (RBench) used to initialise translations/
│                        and to detect edits to protected files            (minor addition to the required layout)
├── official_checks/     official NewMetrics (unsafe-metrics) results, course structure-validator log, readiness audit   (minor addition)
├── tests/               unit tests for the verifier: python3 -m unittest discover -s tests   (minor addition)
└── experiments/         razz_spec_check/: evidence for the project_2 test contradiction and a C-faithful harness
                         haiku/: the same pipeline run with claude-haiku-5-5 (ablation)   (minor addition)
```

## 1. Models, frameworks and tools used

| Component | Choice |
|---|---|
| Agentic framework | **Claude Code 2.1.321**, headless mode (`claude -p --output-format stream-json --verbose`), launched and supervised by our own controller `src/pipeline.py` |
| Model | **`claude-sonnet-5-5`** produced the initial translations through Claude Code. **`claude-haiku-5-5`** ran the comparison experiment. Logged Codex CLI 0.167.0-alpha.4.1 follow-ups (`codex exec --json`, sandbox `workspace-write`) with OpenAI **`gpt-6.1-sol`** and medium reasoning repaired the Base122 bit writer (2026-11-17) and Razz hand traversal (2026-11-18); prompts, streams, diffs and verification are in `trajectories/project_*/follow_up_*/`. Each session uses one agent. |
| Inference settings | Claude Code defaults for decoding (temperature is not user-configurable in Claude Code); `--max-turns 300` and `--max-budget-usd 15` per controller iteration; at most 4 controller iterations and $45 per project; 90-minute wall-clock limit per iteration |
| Rust toolchain | `rustup` with **`nightly-2025-05-13`**: rustc 1.89.0-nightly (8405332bd 2025-05-12), cargo 1.89.0-nightly, clippy 0.1.88, rustfmt 1.8.0-nightly. Exported as `RUSTUP_TOOLCHAIN` for the agent and used explicitly (`cargo +nightly-2025-05-13 …`) by the verifier |
| OS / runtime | macOS 26.6.2 (Darwin 25.6.0), Apple Silicon (arm64); Python 3.11.15 (standard library only); Apple clang 17.0.0 available to the agent for compiling the original C |
| Tools available to the agent | Claude Code built-ins `Read`, `Glob`, `Grep`, `Edit`, `Write`, `MultiEdit`, `TodoWrite`, and `Bash` restricted by an allow-list (`configs/pipeline.json`) to `cargo`, `rustc`, `rustfmt`, `rustup`, `gcc`/`cc`/`clang`, `make`, `cmake`, `python3` (for `src/unsafe_metrics.py`), running locally built binaries, and read-only shell utilities (`ls`, `cat`, `head`, `tail`, `wc`, `grep`, `rg`, `find`, `diff`, `sed -n`, `awk`, `sort`, `uniq`, `tr`, `echo`, `printf`, `pwd`, `cd`, `mkdir`, `timeout`). `WebFetch`, `WebSearch`, `Agent`, `Task`, `NotebookEdit` are disabled, so the agent cannot look up existing Rust translations. Claude Code's own command-safety checks additionally refused a few compound shell commands (multiple `cd`, heredocs with quotes, `rm`); the agent then used the file tools. Every refusal is recorded in `agent_result.json` (`permission_denials`) |
| Unsafe-metrics tool | The agent controller used the local lexical scanner `src/unsafe_metrics.py` during translation. The final Task 4 safety results come from the course's NewMetrics tool. Both libraries compile with `#![forbid(unsafe_code)]`. |

## 2. Pipeline

```
            ┌───────────────────────── controller  src/pipeline.py ──────────────────────────┐
 specs/ ────┤ init workspace ─► prompt ─► Claude Code agent (headless) ─► verify.py ─► stop? ├─► SUMMARY.md
            │  interfaces→src/*.rs   configs/   │ Read/Grep C + Rust spec      cargo build       │   run_summary.json
            │  tests→src/bin/        system +   │ Write/Edit Rust              cargo test        │
            │  Cargo.toml            task       │ cargo build/test/clippy      clippy (4 groups) │
            │                        prompt     │ unsafe_metrics.py            unsafe scan       │
            │                                   ▼ (inner repair loop)          guards (tests,    │
            │                          translations/project_N  ◄── restore     Cargo.toml, API)  │
            │                                                                        │           │
            │     next iteration: repair prompt = build errors + failed tests + clippy items +    │
            │                     unsafe metrics + guard violations  ◄──────────────┘  (if !stop)│
            └──────────────────────────────────────────────────────────────────────────────────┘
```

**Agent (inner loop).** One `claude -p` session per controller iteration, started in `translations/project_N` with read access to `subjects/project_N`. The appended system prompt (`configs/system_prompt.md`) fixes the role, the specification precedence (Rust interface and tests over the C code), the hard rules (no `unsafe`, no FFI, no dependencies, no edits to tests or `Cargo.toml`, no hard-coded answers, pinned toolchain) and the working method. The task prompt (`configs/task_prompt_initial.md`) lists the C and Rust files and the automatically supplied project context (`configs/project_context/<project>.md`: facts about the C project and the tests, nothing about how to implement). The agent reads the C sources and the stubs/tests, writes the implementation, and itself runs `cargo build`, `cargo test`, the four-category Clippy command and the unsafe scan, repairing until green, or until it is certain that the remaining failure is a contradiction in the specification (then it writes `NOTES.md` with `STATUS: BLOCKED`).

**Controller (outer loop).** After the agent exits, `src/verify.py` independently re-runs, with the pinned toolchain, `cargo build --all-targets`, `cargo test`, `cargo clippy --all-targets --all-features -- -W clippy::correctness -W clippy::style -W clippy::complexity -W clippy::perf` (each diagnostic attributed to its lint group via `cargo clippy -- -W help`), and the unsafe scan. The controller restores protected files the agent changed (`Cargo.toml`, `Cargo.lock`, `src/bin/*.rs`) and requires another clean verification. The standalone evaluator reports changes by default. The verifier also checks that every public signature of the CRUST-Bench interface is still present (parameter names excluded). The results are rendered into the repair prompt (`configs/task_prompt_repair.md`) for the next iteration.

**How feedback reaches the agent.** Twice. Inside an iteration the agent sees the raw output of the cargo, Clippy and scan commands it runs (e.g. `error[E0506]: cannot assign to ... because it is borrowed`, `panicked at src/bin/test.rs:147`, `warning: this map_or can be simplified`). Between iterations, the controller's structured summary (build errors, failed tests with panic output, every Clippy finding in generated code with category/file/line, unsafe metrics, number of remaining `unimplemented!()`, guard violations) is embedded in the next prompt.

**Stopping condition** (`configs/pipeline.json`, evaluated by the controller after every iteration):

1. success: build ok, every benchmark test passes, all supplemental tests pass, Clippy exits successfully with zero findings in generated code, the local scan reports zero primary unsafe metrics, `#![forbid(unsafe_code)]` is present, no unfinished stubs remain, and the protected files and interface checks pass; or
2. `max_iterations` (4) reached; or
3. no improvement of the progress score (build, tests passed, stubs left, unsafe total, clippy total) for `patience` (2) consecutive iterations; or
4. cumulative agent cost ≥ $45 for the project; or
5. the agent reports `STATUS: BLOCKED` in `NOTES.md` and everything except the tests is green (a specification conflict that cannot be satisfied without hard-coding).

**Reusability.** The same code, prompts and configuration ran on both projects (and, unchanged, with a different model for the ablation). The only project-specific inputs are `specs/project_N`, `subjects/project_N` and the context file `configs/project_context/<project>.md`. Nothing in the pipeline hard-codes an implementation.

**Manual interventions.** All Rust implementation changes came from the logged agents. During follow-up verification we restored Project 2's upstream Cargo.lock format (version 3) after the new lockfile guard flagged a version 4 rewrite with identical package entries. The diff is in `trajectories/project_2/follow_up_verification/lockfile_restoration.diff`.

## 3. Installation and how to run

```bash
# Rust toolchain pinned by the handout
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain none
export PATH="$HOME/.cargo/bin:$PATH"
rustup toolchain install nightly-2025-05-13 --profile minimal -c clippy -c rustfmt

# Agent: Claude Code (https://docs.claude.com/en/docs/claude-code), logged in. If `claude` is not on PATH,
# the controller also looks for the binary bundled with the VS Code extension, or honours CLAUDE_BIN=/path/to/claude.
npm install -g @anthropic-ai/claude-code && claude      # log in once

# Python 3.9+ (standard library only); a C compiler is optional (lets the agent build the original C tests)
```

```bash
cd MP4
./src/run_pipeline.sh 1            # translate project_1 (libbase122); resumes if a run exists
./src/run_pipeline.sh 2 --fresh --work-dir experiments/reproduction/translations \
                         --trajectory-dir experiments/reproduction/trajectories
./src/run_pipeline.sh 1 --model claude-haiku-5-5 --work-dir experiments/haiku/translations \
                         --trajectory-dir experiments/haiku/trajectories --fresh     # ablation run
./src/evaluate.sh 1                # build/test/clippy/unsafe on the final translation; prints the report tables
python3 src/unsafe_metrics.py translations/project_2       # unsafe-metrics scan only
bash experiments/razz_spec_check/run_harness.sh            # C-faithful differential test for project_2 (Section 6)
```

From the `MP4/` directory, run the build and benchmark directly:

```bash
(cd translations/project_1 && cargo +nightly-2025-05-13 build --locked && cargo +nightly-2025-05-13 test --locked --bins)
(cd translations/project_2 && cargo +nightly-2025-05-13 build --locked && cargo +nightly-2025-05-13 test --locked --bins)
# Clippy: the required command (all targets) and the library-only variant suggested by course staff (forum #435)
(cd translations/project_1 && cargo +nightly-2025-05-13 clippy --all-targets --all-features -- -W clippy::correctness -W clippy::style -W clippy::complexity -W clippy::perf)
(cd translations/project_1 && cargo +nightly-2025-05-13 clippy --lib --all-features -- -W clippy::correctness -W clippy::style -W clippy::complexity -W clippy::perf)
# Safety: the official NewMetrics tool, see official_checks/README.md for installation and the exact commands
```

For the macOS host used in the follow-up, the installed linker required
`export SDKROOT=/Library/Developer/CommandLineTools/SDKs/MacOSX15.2.sdk`
before running Cargo. Other hosts can use their normal SDK and linker.
Run the verifier regressions with `python3 -m unittest discover -s tests -v`.
The evaluator checks benchmark binaries separately from the complete Cargo test
run, so supplemental tests do not inflate the benchmark pass rate. Its safety
numbers come from the local scanner. The official NewMetrics results and the
course structure validator log are saved in [`official_checks/`](official_checks/README.md).

### Trajectory contents (`trajectories/project_N/`)

| File | Content |
|---|---|
| `pipeline.log` | controller log with the full verification report after every iteration (it also keeps the two earlier runs made on 2026-11-09 while the controller was being finished; the final run is the last block) |
| `run_summary.json`, `SUMMARY.md` | per-iteration metrics (agent turns, tool calls, cost, build, tests, Clippy by category, unsafe metrics), stop reason |
| `iteration_XX/prompt.md` | the exact prompt sent to the agent (initial or repair, including the controller feedback) |
| `iteration_XX/agent_command.txt` | the exact `claude` command line (model, limits, allow/deny lists) |
| `iteration_XX/agent_stream.jsonl` | the complete raw Claude Code event stream: every model message, tool call, tool result, permission refusal, token usage and cost |
| `iteration_XX/agent_transcript.md` | the same stream rendered for reading |
| `iteration_XX/agent_result.json` | final result event: turns, tool calls, cost, duration, permission refusals |
| `iteration_XX/cargo_build.log`, `cargo_test.log`, `cargo_clippy.log`, `unsafe_metrics.json`, `verify.json`, `verify_report.md` | the controller's independent verification |
| `iteration_XX/src_snapshot/` | the Rust sources after the iteration |

No credentials appear anywhere: the agent authenticates through the local Claude Code login and the stream contains no tokens (checked with a pattern scan before committing).

## 4. Results (initial Sonnet runs and follow-up verification)

| Project | Compiles | Tests passed | Total tests | Pass rate | Agent iterations (controller) | Agent turns / tool calls | Cost | Wall time |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| libbase122 (project_1) | yes | 6 | 6 (+1 `#[ignore]` in the benchmark) | 100% | 1 | 11 / 10 | $0.25 | 1.3 min |
| razz_simulation (project_2) | yes | 0 | 1 | 0% (see Section 6) | 1 | 22 / 21 | $0.63 | 3.5 min |

The table records the original Sonnet sessions and the active benchmark counts.
On November 17 a separate Codex CLI 0.167.0-alpha.4.1 session using OpenAI
`gpt-6.1-sol` with medium reasoning repaired the Base122 bit writer. The initial
Rust writer left unused bits in prefilled output bytes. Writing one zero bit to
`0xff` yielded `0x7f` in Rust and `0x00` in C. The agent reproduced three failing
cases, updated the write path, and reran the tests. The final Base122 translation
passes six active benchmark tests and six supplemental regression tests, with
one benchmark test still marked ignored by default. The repair prompt, agent
trace, diff and independent checks are in
[`trajectories/project_1/follow_up_bitwriter/`](trajectories/project_1/follow_up_bitwriter/).
The original Claude Code session and snapshot remain in `iteration_01/`.

Safety (local scanner used during translation, generated code only):

| Project | Unsafe lines | Unsafe calls | Unsafe casts | Pointer arithmetic | unsafe blocks / unsafe fn | raw-pointer types | FFI | transmute | manual alloc | `#![forbid(unsafe_code)]` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| libbase122 | 0 | 0 | 0 | 0 | 0 / 0 | 0 | 0 | 0 | 0 | yes |
| razz_simulation | 0 | 0 | 0 | 0 | 0 / 0 | 0 | 0 | 0 | 0 | yes |

Final [official NewMetrics results](official_checks/README.md) also recorded
zero unsafe lines, unsafe calls, unsafe casts, and pointer arithmetic for both
projects. Raw analyzer logs and the course aggregator summaries are included.

Idiomaticity (Clippy, generated code / whole crate including the benchmark test file):

| Project | Correctness | Style | Complexity | Performance | rustc warnings | generated LOC | unwrap / expect / panic! / clone |
|---|---:|---:|---:|---:|---:|---:|---|
| libbase122 | 0 / 0 | 0 / 5 | 0 / 0 | 0 / 0 | 0 / 3 | 244 | 0 / 0 / 0 / 0 |
| razz_simulation | 0 / 0 | 0 / 1 | 0 / 0 | 0 / 0 | 0 / 13 | 403 | 0 / 0 / 0 / 0 |

The whole-crate findings are all inside the benchmark's own `src/bin/*.rs` (five `uninlined_format_args`, one `assertions_on_constants`, unused imports/variables), which we may not modify. Per course staff (forum #435) these do not count toward the idiomaticity score. The library-only command they suggested, `cargo +nightly-2025-05-13 clippy --lib --all-features -- -W clippy::correctness -W clippy::style -W clippy::complexity -W clippy::perf`, reports 0 findings for both projects (verified 2026-11-18), and the supplemental `tests/` targets of both projects are covered by the `--all-targets` run with 0 findings.

The follow-up checks for the current saved sources are in
[`project_1/follow_up_bitwriter/verification/`](trajectories/project_1/follow_up_bitwriter/verification/)
and [`project_2/follow_up_iterator/verification/`](trajectories/project_2/follow_up_iterator/verification/).
The [MP4 progress report section](report/mp4_report_section.tex) can be included
in the team report or compiled through [the standalone entry point](report/mp4_progress_report.tex).
From `report/`, run `latexmk -pdf mp4_progress_report.tex` with a TeX installation that includes TikZ.

Ablation (`experiments/haiku/`, identical pipeline, `claude-haiku-5-5`): project_1 6/6 tests, 0 Clippy, 0 unsafe in 1 iteration (32 turns, $0.09, 3.7 min); project_2 0/1 tests, 0 Clippy, 0 unsafe in 1 iteration (57 turns, $0.59, 10.5 min), also `STATUS: BLOCKED` with the same analysis. Its inner loop is where most of the visible repair happened: three borrow-checker errors (`E0506`, then `E0502`) on a `Box`-linked list were repaired in three rounds by moving to index-based traversal; see the progress report.

## 5. API and usage limits that affected the experiment

- Model access went through the Claude Code login (no API key in the environment). Rate-limit events were reported by the CLI at session start but never throttled a run; the per-iteration budget ($15) and turn limit (300) were never reached (max observed: 57 turns, $0.63).
- Claude Code's built-in command-safety checks refused some compound shell commands (several `cd`s in one command, heredocs containing quotes, `rm`, running freshly compiled binaries). The agent adapted by using `Read`/`Write`/`Edit` and simple single commands, at the cost of a few extra turns (3 refusals per final run).
- `cargo` is not on the user's default PATH on this machine; the controller prepends `~/.cargo/bin` and sets `RUSTUP_TOOLCHAIN=nightly-2025-05-13` for the agent so that every `cargo` call uses the graded toolchain.

## 6. Supplied Razz benchmark discrepancy and supplemental evidence

A broader [C-versus-Rust audit](experiments/razz_behavior_audit/README.md)
subsequently found two real translation differences in hand removal: traversal
continued after removing the head, and named removal deleted too many duplicate
cards. A [logged Codex repair](trajectories/project_2/follow_up_iterator/)
restored the C behavior. Before repair, 445/505 cases matched; afterward,
**505/505 matched**, including 32,384 simulation games. All eight new hand
regression tests pass; four failed before repair. These comparisons cover the
documented valid inputs and do not prove correctness for every execution.
The original benchmark failure below remains a separate harness discrepancy.

Course staff advised us to follow the original C behavior, preserve the supplied
tests, and report scratch results separately. The supplied Rust benchmark
scores **0/1** at line 147 (actual `R2`, expected `R9`). The supplemental
scratch harness scores **1/1**. The supplied test bundles its assertions in
one test function.

1. **Seeding.** The hand sections expect every freshly created deck to deal the `srand48(3)` sequence (Heart 9, Spade Ace, Heart 10, …), while the last section expects the first card of 52,000 freshly created decks to follow the distribution of one continuous `lrand48` stream seeded once. In the C test both hold because `card_test.c` calls `srand48(3)` before each section; the Rust interface has no seeding function. We verified analytically that the expected counts match the POSIX `lrand48` stream seeded with 3 at offset 0. None of the seven other offsets checked matched (`experiments/razz_spec_check/lrand48_check.py`).
2. **Dropped statement.** In the 3-card-hand section the C test calls `remove_from_hand (h, SPADE_ACE)` before iterating; the Rust test omitted it but kept the assertions that depend on it (`[Heart9, Heart10]`, count 2).

The agent reached conclusion 1 on its own in every run (Sonnet and Haiku) and conclusion 2 in one run; it chose the C-faithful design (one process-wide generator seeded like `srand48(3)`), did not special-case anything, and reported `STATUS: BLOCKED` (`translations/project_2/NOTES.md`). To check the affected behavior against the original C test, `experiments/razz_spec_check/run_harness.sh` builds a scratch copy of the translation with a harness-only `seed_rng` hook and runs `test_c_faithful.rs`, which is the benchmark test plus the five `srand48(3)` calls the C test performs and the one omitted `remove_from_hand` call: **every assertion passes, including the 52,000-deck distribution** (`experiments/razz_spec_check/results.txt`). The original C card test also passed natively with assertions enabled and `-include string.h` for its missing declaration of `strcmp`. The submitted `translations/project_2` is untouched by the harness.
