#!/usr/bin/env bash
# Reproduce the MP4 agentic translation pipeline on one assigned project.
#
#   ./src/run_pipeline.sh 1            # project_1 = libbase122
#   ./src/run_pipeline.sh 2 --fresh --work-dir experiments/reproduction/translations \
#                                  --trajectory-dir experiments/reproduction/trajectories
#   ./src/run_pipeline.sh 1 --max-iterations 2 --model claude-sonnet-5-5
#
# Requirements (see README.md): rustup with nightly-2025-05-13 (+clippy), Python 3.9+,
# Claude Code >= 2.1 logged in (or CLAUDE_BIN pointing at the binary), a C compiler.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$HOME/.cargo/bin:$PATH"
export RUSTUP_TOOLCHAIN="${RUSTUP_TOOLCHAIN:-nightly-2025-05-13}"
command -v cargo >/dev/null || { echo "cargo not found: install rustup and run 'rustup toolchain install nightly-2025-05-13 -c clippy'" >&2; exit 1; }
cargo "+$RUSTUP_TOOLCHAIN" --version >/dev/null
exec python3 "$HERE/pipeline.py" "$@"
