#!/usr/bin/env python3
"""Verification harness for MP4 translations.

Runs, with the pinned toolchain, the same checks the instructional team will
run on a translated project and returns them as structured data:

  * ``cargo build --all-targets``
  * ``cargo test`` (per-test pass/fail, failure output)
  * ``cargo clippy --all-targets --all-features -- -W clippy::correctness
    -W clippy::style -W clippy::complexity -W clippy::perf`` with every
    diagnostic attributed to one of the four rubric categories
  * the unsafe-metrics scan (``unsafe_metrics.py``)
  * a guard that the benchmark tests and ``Cargo.toml`` are untouched and that
    every public signature of the CRUST-Bench interface is still present

``pipeline.py`` calls ``run_all`` after every agent iteration and turns the
result into the feedback for the next iteration.  ``evaluate.sh`` calls the
command-line entry point to print the final report tables.

Usage:  python3 verify.py <project_number|project_dir> [--json] [--out-dir DIR]
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unsafe_metrics  # noqa: E402

MP4_DIR = Path(__file__).resolve().parent.parent
DEFAULT_TOOLCHAIN = "nightly-2025-05-13"
DEFAULT_CLIPPY_ARGS = [
    "--all-targets", "--all-features", "--",
    "-W", "clippy::correctness", "-W", "clippy::style",
    "-W", "clippy::complexity", "-W", "clippy::perf",
]
RUBRIC_CATEGORIES = ("correctness", "style", "complexity", "perf")
_LINT_GROUPS: dict[str, str] | None = None


# --------------------------------------------------------------------------- helpers
def cargo_env(toolchain: str) -> dict[str, str]:
    env = os.environ.copy()
    env["PATH"] = str(Path.home() / ".cargo" / "bin") + os.pathsep + env.get("PATH", "")
    env["RUSTUP_TOOLCHAIN"] = toolchain
    env["CARGO_TERM_COLOR"] = "never"
    return env


def run(cmd: list[str], cwd: Path, env: dict[str, str], timeout: int) -> tuple[int, str, float]:
    start = time.time()
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True, timeout=timeout)
        rc, out = proc.returncode, proc.stdout + proc.stderr
    except subprocess.TimeoutExpired as exc:
        rc = -9
        out = (exc.stdout or "") + (exc.stderr or "") + f"\n[command timed out after {timeout}s]"
    return rc, out, time.time() - start


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- cargo build
def cargo_build(rust_dir: Path, toolchain: str, env: dict[str, str], timeout: int = 900) -> dict:
    rc, out, secs = run(["cargo", f"+{toolchain}", "build", "--locked", "--all-targets"], rust_dir, env, timeout)
    errors = len(re.findall(r"^error(?:\[E\d+\])?:", out, re.M))
    warnings = [
        line for line in out.splitlines()
        if line.startswith("warning:") and not re.match(r"^warning: `.*` \(.*\) generated \d+ warnings?", line)
    ]
    return {"ok": rc == 0, "returncode": rc, "errors": errors, "warnings": len(warnings), "seconds": round(secs, 1), "log": out}


# --------------------------------------------------------------------------- cargo test
def cargo_test(rust_dir: Path, toolchain: str, env: dict[str, str], timeout: int = 900,
               *, benchmark_only: bool = False) -> dict:
    targets = ["--bins"] if benchmark_only else []
    rc, out, secs = run(
        ["cargo", f"+{toolchain}", "test", "--locked", *targets, "--no-fail-fast", "--", "--test-threads=1"],
        rust_dir, env, timeout,
    )
    tests = {}
    for m in re.finditer(r"^test (\S+) \.\.\. (ok|FAILED|ignored\b.*)$", out, re.M):
        name, status = m.group(1), m.group(2)
        tests[name] = "passed" if status == "ok" else ("failed" if status == "FAILED" else "ignored")
    summaries = re.findall(r"test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored", out)
    passed = sum(int(s[1]) for s in summaries)
    failed = sum(int(s[2]) for s in summaries)
    ignored = sum(int(s[3]) for s in summaries)
    compile_failed = not summaries and rc != 0
    failure_output = ""
    if "failures:" in out:
        failure_output = out[out.index("failures:"):]
        failure_output = re.sub(r"\n\s*Running [^\n]*\n", "\n", failure_output)
    return {
        "ok": rc == 0 and not compile_failed and failed == 0,
        "returncode": rc,
        "compile_failed": compile_failed,
        "passed": passed,
        "failed": failed,
        "ignored": ignored,
        "total": passed + failed,
        "tests": tests,
        "failed_tests": sorted(n for n, s in tests.items() if s == "failed"),
        "failure_output": failure_output,
        "seconds": round(secs, 1),
        "log": out,
    }


# --------------------------------------------------------------------------- clippy
def lint_groups(rust_dir: Path, toolchain: str, env: dict[str, str]) -> dict[str, str]:
    """Map ``clippy::lint_name`` -> group using ``cargo clippy -- -W help``."""
    global _LINT_GROUPS
    if _LINT_GROUPS is not None:
        return _LINT_GROUPS
    _, out, _ = run(["cargo", f"+{toolchain}", "clippy", "--locked", "--", "-W", "help"], rust_dir, env, 300)
    groups: dict[str, str] = {}
    specific = ("correctness", "suspicious", "style", "complexity", "perf", "pedantic", "nursery", "restriction", "cargo")
    for m in re.finditer(r"^\s*clippy::(\w+)\s+(clippy::[^\n]+)$", out, re.M):
        group = m.group(1)
        if group not in specific:  # skip umbrella groups such as clippy::all
            continue
        for lint in m.group(2).split(","):
            lint = lint.strip().replace("-", "_")
            if lint:
                groups.setdefault(lint, group)
    _LINT_GROUPS = groups
    return groups


def cargo_clippy(rust_dir: Path, toolchain: str, env: dict[str, str], clippy_args: list[str], timeout: int = 900) -> dict:
    human_rc, human_out, secs = run(["cargo", f"+{toolchain}", "clippy", "--locked", *clippy_args], rust_dir, env, timeout)
    if "--" in clippy_args:
        split = clippy_args.index("--")
        json_args = clippy_args[:split] + ["--message-format=json"] + clippy_args[split:]
    else:
        json_args = clippy_args + ["--message-format=json"]
    json_rc, json_out, _ = run(["cargo", f"+{toolchain}", "clippy", "--locked", *json_args], rust_dir, env, timeout)
    groups = lint_groups(rust_dir, toolchain, env)

    seen = set()
    items = []
    for line in json_out.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("reason") != "compiler-message":
            continue
        msg = event["message"]
        code = (msg.get("code") or {}).get("code")
        level = msg.get("level")
        if level not in ("warning", "error") or code is None:
            continue
        spans = msg.get("spans") or []
        primary = next((s for s in spans if s.get("is_primary")), spans[0] if spans else {})
        file_name = primary.get("file_name", "")
        key = (code, file_name, primary.get("line_start"), primary.get("column_start"), msg["message"])
        if key in seen:
            continue
        seen.add(key)
        if code.startswith("clippy::"):
            group = groups.get(code, "other_clippy")
            category = group if group in RUBRIC_CATEGORIES else "other_clippy"
        else:
            category = "rustc"
        items.append({
            "code": code,
            "category": category,
            "level": level,
            "file": file_name,
            "line": primary.get("line_start"),
            "message": msg["message"],
            "generated": not file_name.replace("\\", "/").startswith("src/bin/"),
        })

    def tally(selected):
        counts = {c: 0 for c in (*RUBRIC_CATEGORIES, "other_clippy", "rustc")}
        for it in selected:
            counts[it["category"]] += 1
        counts["clippy_total"] = sum(counts[c] for c in RUBRIC_CATEGORIES) + counts["other_clippy"]
        counts["total"] = counts["clippy_total"] + counts["rustc"]
        return counts

    return {
        "ok": human_rc == 0 and json_rc == 0,
        "returncode": human_rc,
        "json_returncode": json_rc,
        "all": tally(items),
        "generated": tally([it for it in items if it["generated"]]),
        "benchmark_tests": tally([it for it in items if not it["generated"]]),
        "items": items,
        "seconds": round(secs, 1),
        "log": human_out,
    }


# --------------------------------------------------------------------------- guards
def protected_files(spec_dir: Path, patterns: list[str]) -> list[str]:
    rels = []
    for path in spec_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(spec_dir)).replace("\\", "/")
        if any(fnmatch.fnmatch(rel, pat) for pat in patterns):
            rels.append(rel)
    return sorted(rels)


def guard_protected(spec_dir: Path, rust_dir: Path, patterns: list[str], restore: bool = True) -> list[dict]:
    """Report (and optionally restore) benchmark files the agent must not change."""
    findings = []
    for rel in protected_files(spec_dir, patterns):
        spec_path, rust_path = spec_dir / rel, rust_dir / rel
        if not rust_path.exists():
            status = "missing"
        elif sha256(spec_path) != sha256(rust_path):
            status = "modified"
        else:
            continue
        if restore:
            rust_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(spec_path, rust_path)
        findings.append({"file": rel, "status": status, "restored": restore})
    return findings


_SIG_RE = re.compile(
    r"^\s*(?:pub(?:\([^)]*\))?\s+)(?:unsafe\s+)?(?:const\s+)?(?:async\s+)?"
    r"(?:fn|struct|enum|type|const|static|trait|mod)\b[^{;=]*|^\s*impl\b[^{]*|^\s*pub\s+[a-z_][a-z0-9_]*\s*:[^,]*",
)


def _normalize(text: str) -> str:
    text = re.sub(r"//[^\n]*", "", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*([(){}<>,:;&\[\]=\-])\s*", r"\1", text)
    return text.strip()


def _canonical(sig: str) -> str:
    """Canonical form of an item header: parameter names, `mut` on by-value
    parameters and trailing commas are not part of a Rust public API, so they
    are removed from `fn` headers before comparison."""
    if re.match(r"^(?:pub(?:\([^)]*\))?\s*)?(?:(?:unsafe|const|async)\s+)*fn\b", sig):
        head, _, rest = sig.partition("(")
        params, _, tail = rest.rpartition(")")
        params = re.sub(r"(?<!&)\bmut self\b", "self", params)  # by-value `mut self` only; `&mut self` is API
        params = re.sub(r"(?<![:\w])(?:mut )?[A-Za-z_]\w*:(?!:)", "", params)
        params = re.sub(r",+$", "", params)
        sig = f"{head}({params}){tail}"
    return sig


def _join_headers(text: str) -> str:
    """Join multi-line item headers (parameter lists split over lines) into one line."""
    text = re.sub(r"//[^\n]*", "", text)
    out, depth = [], 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        out.append(" " if ch == "\n" and depth > 0 else ch)
    return "".join(out)


def interface_signatures(spec_text: str) -> list[str]:
    """Canonical public item headers (fn/struct/enum/type/const/mod, impl headers, pub fields)."""
    sigs = []
    for line in _join_headers(spec_text).splitlines():
        m = _SIG_RE.match(line)
        if not m:
            continue
        norm = _canonical(_normalize(m.group(0)))
        if norm and norm not in sigs:
            sigs.append(norm)
    return sigs


def guard_interfaces(spec_dir: Path, rust_dir: Path) -> list[dict]:
    """Every public signature of each interface file must still appear in the translation."""
    findings = []
    for spec_file in sorted((spec_dir / "src" / "interfaces").glob("*.rs")):
        target = rust_dir / "src" / spec_file.name
        if not target.exists():
            findings.append({"file": f"src/{spec_file.name}", "missing": ["<file missing>"]})
            continue
        translated = set(interface_signatures(target.read_text(encoding="utf-8", errors="replace")))
        missing = [sig for sig in interface_signatures(spec_file.read_text(encoding="utf-8")) if sig not in translated]
        if missing:
            findings.append({"file": f"src/{spec_file.name}", "missing": missing})
    return findings


# --------------------------------------------------------------------------- all together
def checks_pass(results: dict, *, require_passing_tests: bool = True) -> bool:
    metrics = results["unsafe"]["totals"]
    return bool(
        results["build"]["ok"]
        and (not require_passing_tests or (
            results["benchmark_tests"]["ok"] and results["benchmark_tests"]["total"] > 0
            and results["tests"]["ok"]
        ))
        and results["clippy"]["ok"]
        and results["clippy"]["generated"]["total"] == 0
        and metrics["primary_total"] == 0
        and metrics["forbid_unsafe_code"]
        and metrics["unimplemented_or_todo"] == 0
        and not results.get("protected")
        and not results.get("interface")
    )


def run_all(rust_dir: Path, spec_dir: Path | None, toolchain: str = DEFAULT_TOOLCHAIN,
            out_dir: Path | None = None, clippy_args: list[str] | None = None,
            protected_patterns: list[str] | None = None, restore_protected: bool = True) -> dict:
    rust_dir = Path(rust_dir)
    env = cargo_env(toolchain)
    clippy_args = clippy_args or DEFAULT_CLIPPY_ARGS
    protected_patterns = protected_patterns or ["Cargo.toml", "Cargo.lock", "src/bin/*.rs"]

    results: dict = {"rust_dir": str(rust_dir), "toolchain": toolchain, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}
    if spec_dir is not None:
        results["protected"] = guard_protected(Path(spec_dir), rust_dir, protected_patterns, restore=restore_protected)
        results["interface"] = guard_interfaces(Path(spec_dir), rust_dir)
    results["build"] = cargo_build(rust_dir, toolchain, env)
    results["benchmark_tests"] = cargo_test(rust_dir, toolchain, env, benchmark_only=True)
    results["tests"] = cargo_test(rust_dir, toolchain, env)
    results["clippy"] = cargo_clippy(rust_dir, toolchain, env, clippy_args)
    results["unsafe"] = unsafe_metrics.analyze_project(rust_dir)
    results["success"] = checks_pass(results)

    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "cargo_build.log").write_text(results["build"]["log"])
        (out_dir / "cargo_test.log").write_text(results["tests"]["log"])
        (out_dir / "cargo_benchmark_test.log").write_text(results["benchmark_tests"]["log"])
        (out_dir / "cargo_clippy.log").write_text(results["clippy"]["log"])
        (out_dir / "unsafe_metrics.json").write_text(json.dumps(results["unsafe"], indent=2))
        slim = {k: v for k, v in results.items()}
        slim["build"] = {k: v for k, v in results["build"].items() if k != "log"}
        for name in ("tests", "benchmark_tests"):
            slim[name] = {k: v for k, v in results[name].items() if k != "log"}
        slim["clippy"] = {k: v for k, v in results["clippy"].items() if k != "log"}
        (out_dir / "verify.json").write_text(json.dumps(slim, indent=2))
    return results


def format_report(results: dict, project_label: str = "") -> str:
    b, t, c, u = results["build"], results["benchmark_tests"], results["clippy"], results["unsafe"]["totals"]
    g, a = c["generated"], c["all"]
    lines = [
        f"# Verification report {project_label}".rstrip(),
        "",
        f"Toolchain: {results['toolchain']}    Time: {results['timestamp']}",
        "",
        "| Compiles | Benchmark passed | Benchmark total | Pass rate | Ignored |",
        "|---|---:|---:|---:|---:|",
        f"| {'yes' if b['ok'] else 'NO (' + str(b['errors']) + ' errors)'} | {t['passed']} | {t['total']} | "
        f"{(100.0 * t['passed'] / t['total']) if t['total'] else 0:.1f}% | {t['ignored']} |",
        "",
        f"All tests: {results['tests']['passed']} passed, {results['tests']['failed']} failed, "
        f"{results['tests']['ignored']} ignored.",
        "",
        "Clippy (generated code / whole crate incl. benchmark tests):",
        "",
        "| Correctness | Style | Complexity | Performance | Other clippy | rustc warnings |",
        "|---:|---:|---:|---:|---:|---:|",
        f"| {g['correctness']} / {a['correctness']} | {g['style']} / {a['style']} | {g['complexity']} / {a['complexity']} | "
        f"{g['perf']} / {a['perf']} | {g['other_clippy']} / {a['other_clippy']} | {g['rustc']} / {a['rustc']} |",
        "",
        "| Unsafe lines | Unsafe calls | Unsafe casts | Pointer arithmetic | forbid(unsafe_code) |",
        "|---:|---:|---:|---:|---|",
        f"| {u['unsafe_lines']} | {u['unsafe_calls']} | {u['unsafe_casts']} | {u['pointer_arithmetic']} | {'yes' if u['forbid_unsafe_code'] else 'NO'} |",
        "",
        f"Remaining unimplemented!/todo!: {u['unimplemented_or_todo']}    unwrap: {u['unwrap_calls']}  expect: {u['expect_calls']}  "
        f"panic!: {u['panic_macros']}  clone: {u['clone_calls']}  generated LOC: {u['loc']}",
    ]
    if t["failed_tests"]:
        lines += ["", "Failed tests: " + ", ".join(results["tests"]["failed_tests"])]
    elif results["tests"]["failed_tests"]:
        lines += ["", "Failed supplemental tests: " + ", ".join(results["tests"]["failed_tests"])]
    if not c["ok"]:
        lines += ["", f"Clippy command failed (text exit {c['returncode']}, JSON exit {c['json_returncode']})."]
    if results.get("protected"):
        lines += ["", "Protected files touched: " + ", ".join(f"{p['file']} ({p['status']})" for p in results["protected"])]
    if results.get("interface"):
        lines += ["", "Interface signatures missing:"]
        for f in results["interface"]:
            for sig in f["missing"]:
                lines.append(f"  - {f['file']}: `{sig}`")
    lines += ["", "Safety counts above come from the local scanner.",
              f"Local verification: {'passed' if results['success'] else 'failed'}"]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project", help="project number (1 or 2) or path to a Rust project")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out-dir", default=None, help="where to write logs and verify.json")
    parser.add_argument("--toolchain", default=DEFAULT_TOOLCHAIN)
    restoration = parser.add_mutually_exclusive_group()
    restoration.add_argument("--restore", action="store_true", help="restore protected files from the benchmark")
    restoration.add_argument("--no-restore", action="store_true", help="report protected changes without restoring (default)")
    args = parser.parse_args(argv)

    if args.project.isdigit():
        rust_dir = MP4_DIR / "translations" / f"project_{args.project}"
        spec_dir = MP4_DIR / "specs" / f"project_{args.project}"
        label = f"project_{args.project} ({(spec_dir / 'PROJECT_NAME').read_text().strip()})"
    else:
        rust_dir, spec_dir, label = Path(args.project), None, args.project
    results = run_all(rust_dir, spec_dir, args.toolchain, Path(args.out_dir) if args.out_dir else None,
                      restore_protected=args.restore)
    if args.json:
        slim = dict(results)
        for key in ("build", "tests", "benchmark_tests", "clippy"):
            slim[key] = {k: v for k, v in results[key].items() if k != "log"}
        print(json.dumps(slim, indent=2))
    else:
        print(format_report(results, label))
    return 0 if results["success"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
