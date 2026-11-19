# Pipeline summary: project_2 (razz_simulation)

- Framework: Claude Code 2.1.321 (headless CLI (claude -p, --output-format stream-json), one fresh session per controller iteration)
- Model: claude-sonnet-5-5
- Toolchain: nightly-2025-05-13
- Iterations: 1
- Stop reason: agent reported STATUS: BLOCKED in NOTES.md (specification conflict it cannot resolve honestly); everything except the tests is green
- Total agent cost: $0.63; total agent wall time: 3.5 min

| Iter | Agent turns | Tool calls | Cost ($) | Build | Tests passed/total | Clippy (generated) | Unsafe primary | unimplemented! left | forbid(unsafe_code) |
|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| 1 | 22 | 21 | 0.63 | ok | 0/1 | 0 (c0 s0 x0 p0 o0 r0) | 0 | 0 | yes |
