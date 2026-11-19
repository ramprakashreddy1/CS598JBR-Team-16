# Submission readiness audit — November 18, 2026

Audited candidate: this `MP4/` package. No production Rust logic was changed in this audit.
Fresh checks used `nightly-2025-05-13`, temporary build targets, and the installed
macOS 15.2 SDK. No new model calls were made.

## Fresh results

| Check | libbase122 | razz_simulation |
| --- | --- | --- |
| Build, all targets | Pass | Pass |
| Supplied active tests | 6/6; 1 supplied ignore | 0/1 |
| Supplemental regression tests | 6/6 | 8/8 |
| Generated-code Clippy: correctness/style/complexity/performance | 0/0/0/0 | 0/0/0/0 |
| Whole-crate Clippy: correctness/style/complexity/performance | 0/5/0/0 | 0/1/0/0 |
| Whole-crate rustc warnings | 3 | 13 |
| Official NewMetrics: unsafe lines/calls/casts/pointer arithmetic | 0/0/0/0 | 0/0/0/0 |
| Official NewMetrics total spans | 17,654 | 30,789 |
| Protected Cargo and benchmark changes | None | None |
| Missing required public signatures, local guard | None | None |
| Library differences from logged repair snapshot | None | None |
| Independent C-versus-Rust comparisons | 133,730/133,730 | 505/505 |

The Razz comparisons include 32,384 simulation games. Its separate C-faithful
scratch benchmark was also rerun: 1/1, including the 52,000-deck distribution.
The supplied benchmark still fails at `src/bin/test.rs:147`, actual `R2`, expected
`R9`. The scratch result does not replace or alter the supplied result.

Both verifier infrastructure regressions passed. The official validator's
repository-name and layout functions passed against a temporary local candidate
exposing this package as top-level `MP4/`. The clone-based remote CLI was not run.
Credential-pattern scanning found no matches; this is a bounded pattern scan,
not a guarantee that arbitrary sensitive text cannot exist.

## Remaining findings

1. **Razz correctness grading risk.** The missing test reseeds and omitted card
   removal remain documented under the TA's guidance. The visible suite is
   still 0/1. Supplemental C agreement supports the translation but does not
   establish the staff's grading decision or hidden-test outcome. The literal
   visible-suite formula yields zero of the project's 40 correctness points.
2. **Cumulative report.** The team's progress report must carry the current MP4
   section (`report/mp4_report_section.tex`), the Section 1 link to this `MP4/`
   folder, and the safety numbers above.
