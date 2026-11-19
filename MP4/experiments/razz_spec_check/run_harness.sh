#!/usr/bin/env bash
# Rebuilds the C-faithful differential test for translations/project_2 in a scratch copy and runs it.
# The submission itself is NOT modified: the scratch copy gets (a) a harness-only `seed_rng` hook
# (seed_rng_harness_hook.diff) and (b) test_c_faithful.rs, the benchmark test with the five
# `srand48(3)` calls that card_test.c performs and the `remove_from_hand(SPADE_ACE)` call it contains.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MP4="$(cd "$HERE/../.." && pwd)"
export PATH="$HOME/.cargo/bin:$PATH"
WORK="$(mktemp -d)"
trap 'rm -rf -- "$WORK"' EXIT
rsync -a --exclude target "$MP4/translations/project_2/" "$WORK/"
patch -s "$WORK/src/card.rs" < "$HERE/seed_rng_harness_hook.diff"
cp "$HERE/test_c_faithful.rs" "$WORK/src/bin/test_c_faithful.rs"
cd "$WORK"
echo "== original benchmark test (src/bin/test.rs) =="
if cargo +nightly-2025-05-13 test --locked --bin test > original.log 2>&1; then
  grep -E "test result" original.log
elif grep -q '^test result: FAILED' original.log; then
  grep -E "panicked|left:|right:|test result" original.log
else
  cat original.log >&2
  exit 1
fi
echo "== C-faithful test (test_c_faithful.rs) =="
if ! cargo +nightly-2025-05-13 test --locked --bin test_c_faithful > faithful.log 2>&1; then
  cat faithful.log >&2
  exit 1
fi
grep -E "test result" faithful.log
