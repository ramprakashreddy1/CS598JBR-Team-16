#!/usr/bin/env bash
# Evaluate a final translation exactly the way the pipeline does (no agent involved):
# cargo build, cargo test, the four-category clippy run and the unsafe-metrics scan.
#
#   ./src/evaluate.sh 1          # report for translations/project_1
#   ./src/evaluate.sh 2 --json   # machine-readable
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$HOME/.cargo/bin:$PATH"
exec python3 "$HERE/verify.py" "$@"
