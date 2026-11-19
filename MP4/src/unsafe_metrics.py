#!/usr/bin/env python3
"""Stand-in unsafe-metrics scanner for MP4.

The course promised an official unsafe-metrics tool. Until it is published, this
script reports the four primary metrics defined in the handout plus the
auxiliary counts, computed on the generated Rust code only (``src/**/*.rs``
excluding the benchmark tests under ``src/bin/``).

Primary metrics (handout section 3.3):
  unsafe_lines        non-empty, non-comment lines inside ``unsafe { }`` blocks
                      or ``unsafe fn`` bodies
  unsafe_calls        call expressions inside those unsafe regions
  unsafe_casts        ``x as *const T`` / ``x as *mut T`` / ``transmute``
  pointer_arithmetic  ``.add(`` ``.sub(`` ``.offset(`` ``.byte_add(`` ... on pointers

Auxiliary: unsafe blocks, unsafe fn declarations, raw-pointer type mentions,
``extern "C"`` blocks, transmute uses, manual allocation calls, and whether
``#![forbid(unsafe_code)]`` is present in ``src/lib.rs``.  It also reports a few
idiom indicators (``unwrap``, ``expect``, ``panic!``, ``clone``, ``unimplemented!``)
that the pipeline feeds back to the agent.

The scan is lexical: comments and string literals are blanked first, so a word
``unsafe`` inside a comment or a message string is not counted.

Usage:  python3 unsafe_metrics.py <rust_project_dir> [--json] [--include-tests]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

KEYWORDS = {
    "if", "while", "for", "match", "return", "loop", "unsafe", "fn", "let", "as",
    "in", "else", "break", "continue", "move", "ref", "mut", "where", "impl",
    "pub", "use", "mod", "struct", "enum", "type", "const", "static", "trait",
}

PRIMARY = ("unsafe_lines", "unsafe_calls", "unsafe_casts", "pointer_arithmetic")


def strip_comments_and_strings(src: str) -> str:
    """Blank out comments, string literals and char literals, keeping newlines."""
    out: list[str] = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if src.startswith("//", i):
            j = src.find("\n", i)
            j = n if j == -1 else j
            out.append(" " * (j - i))
            i = j
            continue
        if src.startswith("/*", i):
            depth, j = 1, i + 2
            while j < n and depth:
                if src.startswith("/*", j):
                    depth += 1
                    j += 2
                elif src.startswith("*/", j):
                    depth -= 1
                    j += 2
                else:
                    j += 1
            out.append(re.sub(r"[^\n]", " ", src[i:j]))
            i = j
            continue
        m = re.match(r'b?r(#*)"', src[i:])
        if m:
            end_tok = '"' + m.group(1)
            j = src.find(end_tok, i + len(m.group(0)))
            j = n if j == -1 else j + len(end_tok)
            out.append(re.sub(r"[^\n]", " ", src[i:j]))
            i = j
            continue
        if c == '"' or (c == "b" and i + 1 < n and src[i + 1] == '"'):
            j = i + (2 if c == "b" else 1)
            while j < n and src[j] != '"':
                j += 2 if src[j] == "\\" else 1
            j = min(j + 1, n)
            out.append(re.sub(r"[^\n]", " ", src[i:j]))
            i = j
            continue
        if c == "'":
            m2 = re.match(r"'(\\u\{[0-9a-fA-F]+\}|\\.|[^'\\])'", src[i:])
            if m2:
                out.append(" " * len(m2.group(0)))
                i += len(m2.group(0))
                continue
        out.append(c)
        i += 1
    return "".join(out)


def brace_span(code: str, open_idx: int) -> int:
    depth = 0
    for j in range(open_idx, len(code)):
        if code[j] == "{":
            depth += 1
        elif code[j] == "}":
            depth -= 1
            if depth == 0:
                return j + 1
    return len(code)


def unsafe_regions(code: str) -> list[tuple[int, int, str]]:
    """Return (start, end, kind) spans for unsafe blocks, unsafe fn bodies, etc."""
    regions: list[tuple[int, int, str]] = []
    for m in re.finditer(r"\bunsafe\b", code):
        rest = code[m.end():]
        k = re.match(r"\s*(fn|impl|trait|extern)\b", rest)
        if k:
            kind = k.group(1)
            if kind in ("fn", "extern"):
                ob = code.find("{", m.end())
                semi = code.find(";", m.end())
                if kind == "fn" and semi != -1 and (ob == -1 or semi < ob):
                    regions.append((m.start(), semi, "unsafe_fn_decl"))
                    continue
                if ob == -1:
                    continue
                regions.append((ob, brace_span(code, ob), "unsafe_" + kind))
            else:
                regions.append((m.start(), m.end(), "unsafe_" + kind))
            continue
        ob = code.find("{", m.end())
        if ob != -1 and code[m.end():ob].strip() == "":
            regions.append((ob, brace_span(code, ob), "unsafe_block"))
    return regions


def analyze_source(raw: str, is_lib_rs: bool = False) -> dict:
    code = strip_comments_and_strings(raw)
    regions = unsafe_regions(code)
    unsafe_lines: set[int] = set()
    unsafe_calls = 0
    for start, end, kind in regions:
        if kind not in ("unsafe_block", "unsafe_fn", "unsafe_extern"):
            continue
        body = code[start:end]
        first_line = code.count("\n", 0, start)
        for offset, line in enumerate(body.split("\n")):
            stripped = line.strip()
            if stripped and stripped not in ("{", "}", "};", "});"):
                unsafe_lines.add(first_line + offset)
        unsafe_calls += sum(
            1
            for call in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", body)
            if call.group(1) not in KEYWORDS
        )
    raw_ptr_types = len(re.findall(r"\*\s*(?:const|mut)\b", code))
    transmutes = len(re.findall(r"\btransmute(?:_copy)?\b", code))
    unsafe_casts = len(re.findall(r"\bas\s*\*\s*(?:const|mut)\b", code)) + transmutes
    ptr_arith = len(
        re.findall(
            r"\.\s*(?:offset|byte_add|byte_sub|byte_offset|offset_from|byte_offset_from|wrapping_offset)\s*\(",
            code,
        )
    )
    if raw_ptr_types:
        # `.add(` / `.sub(` are only treated as pointer arithmetic when the file
        # mentions raw pointer types at all; otherwise they are trait methods.
        ptr_arith += len(re.findall(r"\.\s*(?:add|sub|wrapping_add|wrapping_sub)\s*\(", code))
    manual_alloc = len(
        re.findall(
            r"\b(?:std::alloc::|alloc::alloc\b|dealloc\s*\(|realloc\s*\(|Box::into_raw|Box::from_raw|mem::forget|ManuallyDrop)",
            code,
        )
    )
    result = {
        "unsafe_lines": len(unsafe_lines),
        "unsafe_calls": unsafe_calls,
        "unsafe_casts": unsafe_casts,
        "pointer_arithmetic": ptr_arith,
        "unsafe_blocks": sum(1 for r in regions if r[2] == "unsafe_block"),
        "unsafe_fns": sum(1 for r in regions if r[2] in ("unsafe_fn", "unsafe_fn_decl")),
        "unsafe_impls_or_traits": sum(1 for r in regions if r[2] in ("unsafe_impl", "unsafe_trait")),
        "raw_pointer_types": raw_ptr_types,
        "ffi_extern_blocks": len(re.findall(r'\bextern\s+"C"', code)),
        "transmutes": transmutes,
        "manual_alloc": manual_alloc,
        "unwrap_calls": len(re.findall(r"\.unwrap\s*\(", code)),
        "expect_calls": len(re.findall(r"\.expect\s*\(", code)),
        "panic_macros": len(re.findall(r"\bpanic!\s*\(", code)),
        "clone_calls": len(re.findall(r"\.clone\s*\(", code)),
        "unimplemented_or_todo": len(re.findall(r"\b(?:unimplemented|todo)!\s*\(", code)),
        "loc": sum(1 for line in code.split("\n") if line.strip()),
    }
    if is_lib_rs:
        result["forbid_unsafe_code"] = bool(re.search(r"#!\[\s*forbid\s*\(\s*unsafe_code\s*\)\s*\]", code))
        result["deny_unsafe_code"] = bool(re.search(r"#!\[\s*deny\s*\(\s*unsafe_code\s*\)\s*\]", code))
    return result


def generated_files(project_dir: Path, include_tests: bool = False) -> list[Path]:
    src = project_dir / "src"
    files = sorted(p for p in src.rglob("*.rs") if include_tests or "bin" not in p.relative_to(src).parts)
    return files


def analyze_project(project_dir: Path, include_tests: bool = False) -> dict:
    project_dir = Path(project_dir)
    per_file: dict[str, dict] = {}
    totals: dict[str, int] = {}
    forbid = False
    for path in generated_files(project_dir, include_tests):
        rel = str(path.relative_to(project_dir))
        metrics = analyze_source(path.read_text(encoding="utf-8", errors="replace"), is_lib_rs=(rel == "src/lib.rs"))
        if rel == "src/lib.rs":
            forbid = metrics.get("forbid_unsafe_code", False)
        per_file[rel] = metrics
        for key, value in metrics.items():
            if isinstance(value, bool):
                continue
            totals[key] = totals.get(key, 0) + value
    totals["forbid_unsafe_code"] = forbid
    totals["primary_total"] = sum(totals.get(k, 0) for k in PRIMARY)
    totals["files"] = list(per_file)
    return {"project": str(project_dir), "totals": totals, "per_file": per_file}


def format_table(report: dict) -> str:
    t = report["totals"]
    lines = [
        f"Unsafe metrics for {report['project']} (generated code only: {', '.join(t['files'])})",
        "",
        "| Metric | Count |",
        "|---|---:|",
        f"| Unsafe lines | {t['unsafe_lines']} |",
        f"| Unsafe calls | {t['unsafe_calls']} |",
        f"| Unsafe casts | {t['unsafe_casts']} |",
        f"| Pointer arithmetic | {t['pointer_arithmetic']} |",
        f"| unsafe blocks / unsafe fn / unsafe impl | {t['unsafe_blocks']} / {t['unsafe_fns']} / {t['unsafe_impls_or_traits']} |",
        f"| Raw pointer types (*const/*mut) | {t['raw_pointer_types']} |",
        f"| extern \"C\" blocks | {t['ffi_extern_blocks']} |",
        f"| transmute uses | {t['transmutes']} |",
        f"| Manual allocation ops | {t['manual_alloc']} |",
        f"| #![forbid(unsafe_code)] in src/lib.rs | {'yes' if t['forbid_unsafe_code'] else 'NO'} |",
        "",
        f"Idiom indicators: unwrap={t['unwrap_calls']} expect={t['expect_calls']} panic!={t['panic_macros']} "
        f"clone={t['clone_calls']} unimplemented!/todo!={t['unimplemented_or_todo']} loc={t['loc']}",
        f"PRIMARY TOTAL = {t['primary_total']} (target 0)",
    ]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project_dir", help="Rust project directory (contains Cargo.toml and src/)")
    parser.add_argument("--json", action="store_true", help="print JSON instead of a table")
    parser.add_argument("--include-tests", action="store_true", help="also scan src/bin/ (benchmark tests)")
    args = parser.parse_args(argv)
    report = analyze_project(Path(args.project_dir), include_tests=args.include_tests)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(format_table(report))
    return 0 if report["totals"]["primary_total"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
