# Official MP4 checks

We ran NewMetrics and the course structure checks from course repository commit
[`5f9213ad24e4debbfe0cfee5a8c3c0ba0fb9fef1`](https://github.com/Intelligent-CAT-Lab/CS598JBR-Team-0/tree/5f9213ad24e4debbfe0cfee5a8c3c0ba0fb9fef1/MP4).

| Project | Unsafe lines | Unsafe calls | Unsafe casts | Pointer arithmetic |
| --- | ---: | ---: | ---: | ---: |
| [libbase122](project_1/summary.json) | 0 | 0 | 0 | 0 |
| [razz_simulation](project_2/summary.json) | 0 | 0 | 0 | 0 |

Both analyzer invocations exited successfully and reported nonzero total spans.
NewMetrics runs on build targets independently of the benchmark test results.
The JSON files are from the course's `aggregate.py`.

To reproduce, install `rustc-dev` and `llvm-tools-preview` for
`nightly-2025-05-13` and install NewMetrics using the course tool README.
From each translated project, with the analyzer binaries on PATH, run the
following and aggregate the log after the first command succeeds. We used
temporary project copies because NewMetrics cleans Cargo build artifacts.

```sh
cargo +nightly-2025-05-13 newmetrics --locked > newmetrics.log 2>&1
python3 /path/to/course/MP4/newmetrics/aggregate.py newmetrics.log --out summary.json
```

Reproduced on a second machine on 2026-11-18 from the same course commit
(`rustup component add --toolchain nightly-2025-05-13 rustc-dev llvm-tools-preview`,
`cargo install --debug --locked --path . --force`, then the commands above on
temporary copies of `translations/`): both `summary.json` files were byte-identical
to the ones saved here (17,654 and 30,789 total spans, all four metrics 0).

The [structure log](structure_validator.log) records the official validator's
repository-name and file-layout checks on a temporary candidate with this
package at the repository root as `MP4/`. Run the validator's clone-based CLI
against the team's submission URL and branch once that layout is pushed.
