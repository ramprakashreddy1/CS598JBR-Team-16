# MP4: Agentic C-to-Rust Translation (Team 16)

We implemented a reusable agentic pipeline for translating two assigned CRUST-Bench C projects into safe, idiomatic Rust:

- **Project 1 — `libbase122`:** Base-122 binary-to-text codec.
- **Project 2 — `razz_simulation`:** Playing-card collections, hands, decks, and Razz simulation.

The supplied C sources and Rust benchmark tests are preserved. We report the supplied `razz_simulation` benchmark result separately from our supplemental C-equivalence evidence.

## Environment

- **Agent framework and version:** Claude Code **2.1.321**, invoked headlessly using `claude -p --output-format stream-json --verbose`, orchestrated by the team's Python controller `src/pipeline.py`. Logged follow-up repairs used Codex CLI **0.167.0-alpha.4.1**.
- **Model(s) and provider/runtime:** Anthropic **`claude-sonnet-5-5`** for the initial translations; **`claude-haiku-5-5`** for a comparative ablation. Logged follow-up repairs used OpenAI **`gpt-6.1-sol`** through Codex CLI (medium reasoning). Each session used one agent.
- **Inference settings:** Claude Code's default decoding settings (temperature not user-configurable through the CLI); maximum **300 turns** and **$15** per controller iteration; at most **4 iterations**, **$45** cumulative agent spend per project, and a configured 90-minute timeout per iteration (timeout enforcement currently depends on receiving agent output). The Codex follow-ups used medium reasoning.
- **OS/runtime:** macOS **26.6.2** (Darwin 25.6.0), Apple Silicon (`arm64`); Python **3.11.15** (standard library only); Apple Clang **17.0.0**. Rust toolchain **`nightly-2025-05-13`**, including rustc **1.89.0-nightly**, Cargo, Clippy, and rustfmt.
- **Tools available to the agent:** Claude Code `Read`, `Glob`, `Grep`, `Edit`, `Write`, `MultiEdit`, `TodoWrite`, and restricted `Bash`; Rust compiler, Cargo (`build`, `test`, `clippy`), rustfmt, the local `src/unsafe_metrics.py` scanner, C compiler/build utilities, and read-only shell commands. Web access and subagent tools were disabled. The controller independently invokes `src/verify.py` for build, tests, Clippy, safety scanning, and protected-file/API checks.
- **API or usage limits:** Claude Code authenticated through a local login rather than an API key. The configured turn, cost, and time budgets were not exhausted. Some compound shell commands were refused by Claude Code's command-safety checks; these refusals and the agent's alternatives are captured in the trajectories. The pipeline explicitly selects the pinned Rust toolchain.

## Setup

The environment uses Python 3.9+ and Rust installed through rustup. The following commands reproduce the setup:

```bash
# Install rustup if needed (official installation script)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"

# Install the pinned grading toolchain and components
rustup toolchain install nightly-2025-05-13 --profile minimal -c clippy -c rustfmt

# Optional: required only to rerun the Claude agent, not to evaluate existing Rust
npm install -g @anthropic-ai/claude-code
claude  # complete interactive login once
```

A C compiler is used for the C-faithful supplemental harness. No third-party Python packages are required for the controller/verifier. From the repository root, run `cd MP4` once. All subsequent commands are run from that directory.

## Run

### Evaluate the submitted Rust translations

```bash
# Run from MP4/ (after cd MP4 in Setup)
bash ./src/evaluate.sh 1  # libbase122
bash ./src/evaluate.sh 2  # razz_simulation
```

The scripts can also be invoked directly as `./src/evaluate.sh 1` and `./src/evaluate.sh 2` when execution permissions permit. The verifier builds the crates, executes the supplied benchmarks, runs Clippy, reports local unsafe metrics, and checks protected files and public interfaces. The provided `razz_simulation` benchmark is expected to fail as documented in **Evaluation**; this is not hidden by supplemental tests.

### Agent pipeline reproduction

```bash
bash ./src/run_pipeline.sh 1 --fresh \
  --work-dir experiments/reproduction/translations \
  --trajectory-dir experiments/reproduction/trajectories
bash ./src/run_pipeline.sh 2 --fresh \
  --work-dir experiments/reproduction/translations \
  --trajectory-dir experiments/reproduction/trajectories
```

The reproduction command writes to separate experiment directories to preserve the submitted `translations/` and `trajectories/`. Reproduction requires an authenticated Claude Code installation.

### Supplemental and independent checks

```bash
# C-faithful comparison harness for the Razz benchmark discrepancy
bash experiments/razz_spec_check/run_harness.sh

# Verifier regression tests
python3 -m unittest discover -s tests -v

# Local safety scan (not a substitute for official NewMetrics)
python3 src/unsafe_metrics.py translations/project_2

# Direct Cargo benchmark runs
(cd translations/project_1 && cargo +nightly-2025-05-13 test --locked --bins)
(cd translations/project_2 && cargo +nightly-2025-05-13 test --locked --bins)

# Assignment Clippy command: all targets and all features (includes benchmark tests)
(cd translations/project_1 && cargo +nightly-2025-05-13 clippy --all-targets --all-features -- -W clippy::correctness -W clippy::style -W clippy::complexity -W clippy::perf)
(cd translations/project_2 && cargo +nightly-2025-05-13 clippy --all-targets --all-features -- -W clippy::correctness -W clippy::style -W clippy::complexity -W clippy::perf)

# Library-only Clippy variant (excludes protected benchmark test code)
(cd translations/project_1 && cargo +nightly-2025-05-13 clippy --lib --all-features -- -W clippy::correctness -W clippy::style -W clippy::complexity -W clippy::perf)
(cd translations/project_2 && cargo +nightly-2025-05-13 clippy --lib --all-features -- -W clippy::correctness -W clippy::style -W clippy::complexity -W clippy::perf)
```

The course's official NewMetrics and submission-structure validator outputs are retained under `official_checks/`; see `official_checks/README.md` for their setup and exact commands.

## Pipeline

The same controller, prompts, and verification procedure are used for both projects:

1. **Initialize:** Read the assigned C sources in `subjects/project_N/` and the supplied Rust interfaces/benchmarks in `specs/project_N/`; initialize `translations/project_N/`.
2. **Prompt the agent:** Load `configs/system_prompt.md`, the initial task prompt, and project context. Require safe Rust, no FFI, no extra dependencies, and no edits to supplied tests, `Cargo.toml`, or public interfaces.
3. **Translate and repair:** The agent reads C and Rust files, implements the Rust library, and uses compiler, tests, Clippy, and safety feedback to revise its code within the same session.
4. **Verify independently:** `src/verify.py` runs `cargo build --all-targets`, Cargo tests, Clippy correctness/style/complexity/performance checks, and the local unsafe scanner. It also checks protected benchmark files and required public signatures.
5. **Iterate or stop:** The controller feeds structured errors, failed assertions, Clippy findings, and unsafe metrics into the repair prompt. It stops on success, iteration/cost limits, lack of improvement, or a documented specification conflict (`STATUS: BLOCKED`).
6. **Preserve evidence:** Save prompts, complete agent streams, human-readable transcripts, tool outputs, source snapshots, summaries, and final translations.

The pipeline is reusable: only the project inputs and per-project context differ. Agent changes and follow-up repairs are recorded in `trajectories/`; the supplied tests remain unchanged.

## Outputs

| Path | Contents |
|---|---|
| `src/` | Agent controller, evaluator, safety scanner, and launch scripts |
| `configs/` | Model/pipeline configuration, system prompt, task templates, project contexts |
| `subjects/project_1/`, `subjects/project_2/` | Original C projects, retained unchanged |
| `specs/project_1/`, `specs/project_2/` | Supplied Rust interfaces and benchmark tests used as protected baselines |
| `translations/project_1/`, `translations/project_2/` | Final Rust Cargo projects |
| `trajectories/project_1/`, `trajectories/project_2/` | Iteration logs, prompts, raw agent event streams, transcripts, verification results, follow-up repair traces |
| `tests/` | Verifier unit tests |
| `experiments/` | Supplemental regression, C-versus-Rust behavior audits, C-faithful Razz harness, and Haiku ablation |
| `official_checks/` | Saved course NewMetrics, structure-validation, and readiness evidence |

The trajectory folders contain `run_summary.json`, `SUMMARY.md`, and `iteration_XX/` records with prompts, tool calls, outputs, costs, and stopping conditions. The MP4 evaluation and discussion are documented in the team progress report.

## Evaluation

### Compilation and functional correctness

| Result | Project 1: `libbase122` | Project 2: `razz_simulation` |
|---|---:|---:|
| Rust compilation | Pass | Pass |
| **Supplied benchmark tests** | **6/6 passed** (1 ignored) | **0/1 passed** |
| Supplied benchmark pass rate | **100%** | **0%** |
| Supplemental Rust regression tests | 6/6 passed | 8/8 passed |
| C-versus-Rust audit cases | 133,730/133,730 matched | 505/505 matched |

The supplied `razz_simulation` test `test_card_operations` fails at `src/bin/test.rs:147` (`actual R2`, `expected R9`). This result is **not** counted as a pass. The original C test resets the `srand48(3)` seed before several sections and removes a card from a three-card hand; the supplied Rust benchmark omits those operations while retaining expectations that depend on them. The Rust interface also has no seeding function. The separate scratch C-faithful harness restores the missing test operations **only in a scratch copy** and passes **1/1**, including the 52,000-deck distribution assertion. The submitted benchmark and original C source are not changed. Course staff advised implementing C-faithful behavior and documenting the discrepancy and supplemental results separately. See `experiments/razz_spec_check/`, `experiments/razz_behavior_audit/`, and `translations/project_2/NOTES.md`.

A logged follow-up agent repair corrected genuine Razz hand-removal behavior: differential comparisons improved from 445/505 to **505/505**; the audit also covers **32,384 simulation games**. These finite comparisons support, but cannot prove, full behavioral equivalence.

### Safety

Primary metrics below are zero for both projects in the saved **official NewMetrics** results; the local scanner independently reports zero for the same categories.

| Safety metric | `libbase122` | `razz_simulation` |
|---|---:|---:|
| Unsafe lines | 0 | 0 |
| Unsafe calls | 0 | 0 |
| Unsafe casts | 0 | 0 |
| Pointer arithmetic | 0 | 0 |
| Unsafe blocks / unsafe functions (local scan) | 0 / 0 | 0 / 0 |
| Raw-pointer types (local scan) | 0 | 0 |
| FFI / transmute / manual allocation (local scan) | 0 / 0 / 0 | 0 / 0 / 0 |
| `#![forbid(unsafe_code)]` | Yes | Yes |

### Idiomaticity (Clippy)

Each count is **generated Rust code / entire crate including protected benchmark tests**.

| Metric | `libbase122` | `razz_simulation` |
|---|---:|---:|
| Correctness | 0 / 0 | 0 / 0 |
| Style | 0 / 5 | 0 / 1 |
| Complexity | 0 / 0 | 0 / 0 |
| Performance | 0 / 0 | 0 / 0 |
| Rust compiler warnings | 0 / 3 | 0 / 13 |
| Generated library lines of code (excluding tests) | 244 | 403 |
| Library-only `unwrap()` / `expect()` / `panic!()` / `clone()` | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |

The whole-crate findings arise in the **supplied benchmark test files**, not the generated Rust libraries. The `cargo clippy --lib` check reports zero findings for both libraries. The team records course-staff clarification that benchmark-file warnings are excluded from idiomaticity grading. Clippy counts are findings (so **zero is desirable**), not a count of functionality implemented.

### Agent runs and comparison

| Initial Sonnet run | `libbase122` | `razz_simulation` |
|---|---:|---:|
| Outer controller iterations | 1 | 1 |
| Agent turns / tool calls | 11 / 10 | 22 / 21 |
| Reported cost | $0.25 | $0.63 |
| Wall time | 1.3 min | 3.5 min |

The Haiku ablation used the same pipeline: Project 1 passed 6/6 benchmarks and Project 2 passed 0/1; both recorded zero generated-code Clippy findings and zero primary unsafe metrics. The original Sonnet trajectories and subsequent logged Codex repairs are preserved separately so that the reported runs remain reproducible and auditable.

**Summary:** Both translations compile, and both have zero reported primary unsafe metrics and zero generated-library Clippy findings. Project 1 passes its supplied benchmark; Project 2 does **not**, despite passing separate C-faithful and differential checks. Supplemental evidence does not replace the supplied benchmark score. The team progress report provides the extended analysis, benchmark discrepancy discussion, and limitations.
