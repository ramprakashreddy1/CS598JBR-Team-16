# Pipeline summary: project_1 (libbase122)

- Framework: Claude Code 2.1.321 (headless CLI (claude -p, --output-format stream-json), one fresh session per controller iteration)
- Model: claude-haiku-5-5
- Toolchain: nightly-2025-05-13
- Iterations: 1
- Stop reason: success: all tests pass, clippy clean, unsafe metrics zero, forbid(unsafe_code) present
- Total agent cost: $0.09; total agent wall time: 3.7 min

| Iter | Agent turns | Tool calls | Cost ($) | Build | Tests passed/total | Clippy (generated) | Unsafe primary | unimplemented! left | forbid(unsafe_code) |
|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| 1 | 32 | 31 | 0.09 | ok | 6/6 | 0 (c0 s0 x0 p0 o0 r0) | 0 | 0 | yes |
