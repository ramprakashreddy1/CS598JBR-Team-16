#!/usr/bin/env python3
"""MP4 agentic C-to-Rust translation pipeline (controller).

One run of this controller translates one assigned CRUST-Bench project:

    inspect C project -> generate/modify Rust -> build -> test -> clippy ->
    unsafe metrics -> feedback -> repair -> ... until the stopping condition

The *agent* is Claude Code running headless (``claude -p``).  Inside one
iteration the agent reads the C sources and the Rust interface/tests, edits the
Rust files, and runs cargo itself.  The *controller* (this file) owns the outer
loop: it prepares the workspace from the pristine CRUST-Bench specification,
launches the agent with the prompts in ``configs/``, records the complete
trajectory, re-verifies the result independently (``verify.py``), restores any
benchmark file the agent touched, formats the diagnostics into the next repair
prompt, and applies the stopping condition from ``configs/pipeline.json``.

Trajectory layout (``trajectories/project_<N>/``):
    pipeline.log                 controller log
    run_summary.json             per-iteration metrics, cost, stop reason
    SUMMARY.md                   human-readable summary table
    iteration_XX/prompt.md       exact prompt sent to the agent
    iteration_XX/agent_stream.jsonl   raw Claude Code stream-json events
    iteration_XX/agent_transcript.md  readable transcript (tool calls + results)
    iteration_XX/agent_result.json    final result event (cost, turns, denials)
    iteration_XX/cargo_*.log, unsafe_metrics.json, verify.json
    iteration_XX/src_snapshot/   the Rust sources after this iteration

Usage:  python3 pipeline.py <1|2> [--fresh] [--max-iterations N] [--model M]
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify  # noqa: E402

MP4_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = MP4_DIR / "configs"


# --------------------------------------------------------------------------- utilities
def load_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def render(template: str, **values: str) -> str:
    for key, value in values.items():
        template = template.replace(f"<<{key}>>", str(value))
    return template


def find_claude(configured: str) -> str:
    if os.environ.get("CLAUDE_BIN"):
        return os.environ["CLAUDE_BIN"]
    found = shutil.which(configured)
    if found:
        return found
    candidates = sorted(glob.glob(str(Path.home() / ".vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude")))
    if candidates:
        return candidates[-1]
    raise SystemExit("Claude Code binary not found. Install Claude Code or set CLAUDE_BIN=/path/to/claude")


def file_listing(root: Path, exts: tuple[str, ...]) -> str:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix in exts and ".git" not in path.parts and "target" not in path.parts:
            try:
                lines = sum(1 for _ in open(path, encoding="utf-8", errors="replace"))
            except OSError:
                lines = 0
            rows.append(f"  {str(path.relative_to(root)):50s} {lines:6d} lines")
    return "\n".join(rows)


def truncate(text: str, max_lines: int, max_chars: int = 20000) -> str:
    lines = text.splitlines()
    if len(lines) > max_lines:
        text = "\n".join(lines[:max_lines]) + f"\n... [{len(lines) - max_lines} more lines truncated]"
    if len(text) > max_chars:
        text = text[:max_chars] + "\n... [truncated]"
    return text


# --------------------------------------------------------------------------- pipeline
class Pipeline:
    def __init__(self, project_no: int, cfg: dict, args: argparse.Namespace):
        self.n = project_no
        self.cfg = cfg
        self.args = args
        self.spec_dir = MP4_DIR / "specs" / f"project_{project_no}"
        self.c_dir = MP4_DIR / "subjects" / f"project_{project_no}"
        translations_root = Path(args.work_dir) if args.work_dir else MP4_DIR / "translations"
        trajectories_root = Path(args.trajectory_dir) if args.trajectory_dir else MP4_DIR / "trajectories"
        self.rust_dir = translations_root / f"project_{project_no}"
        self.traj_dir = trajectories_root / f"project_{project_no}"
        self.project_name = (self.spec_dir / "PROJECT_NAME").read_text().strip()
        self.toolchain = cfg["toolchain"]
        self.model = args.model or cfg["model"]
        self.max_iterations = args.max_iterations or cfg["max_iterations"]
        self.claude = find_claude(cfg.get("claude_binary", "claude"))
        self.traj_dir.mkdir(parents=True, exist_ok=True)
        self.log_fh = open(self.traj_dir / "pipeline.log", "w" if args.fresh else "a", encoding="utf-8")
        self.summary_path = self.traj_dir / "run_summary.json"
        self.summary = self._load_summary()

    # ----------------------------------------------------------------- logging
    def log(self, msg: str) -> None:
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
        print(line, flush=True)
        self.log_fh.write(line + "\n")
        self.log_fh.flush()

    def _load_summary(self) -> dict:
        if self.summary_path.exists() and not self.args.fresh:
            return json.loads(self.summary_path.read_text())
        return {
            "project": self.project_name,
            "project_number": self.n,
            "framework": self.cfg["framework"],
            "model": self.model,
            "toolchain": self.toolchain,
            "config": {k: v for k, v in self.cfg.items() if k not in ("framework",)},
            "iterations": [],
            "stop_reason": None,
            "total_cost_usd": 0.0,
            "total_agent_seconds": 0.0,
        }

    def _save_summary(self) -> None:
        self.summary_path.write_text(json.dumps(self.summary, indent=2))

    # ----------------------------------------------------------------- workspace
    def init_workspace(self) -> None:
        if self.args.fresh and self.rust_dir.exists():
            self.log(f"--fresh: removing {self.rust_dir}")
            shutil.rmtree(self.rust_dir)
            for old in self.traj_dir.glob("iteration_*"):
                shutil.rmtree(old)
            for old in ("run_summary.json", "SUMMARY.md"):
                if (self.traj_dir / old).exists():
                    (self.traj_dir / old).unlink()
            self.summary = self._load_summary()
        if self.rust_dir.exists():
            self.log(f"workspace exists, continuing from current state: {self.rust_dir}")
            return
        self.log(f"initialising workspace from CRUST-Bench spec {self.spec_dir}")
        (self.rust_dir / "src").mkdir(parents=True)
        for rel in ("Cargo.toml", "Cargo.lock", ".gitignore", "src/lib.rs"):
            if (self.spec_dir / rel).exists():
                shutil.copy2(self.spec_dir / rel, self.rust_dir / rel)
        for test in (self.spec_dir / "src" / "bin").glob("*.rs"):
            (self.rust_dir / "src" / "bin").mkdir(exist_ok=True)
            shutil.copy2(test, self.rust_dir / "src" / "bin" / test.name)
        for iface in (self.spec_dir / "src" / "interfaces").glob("*.rs"):
            shutil.copy2(iface, self.rust_dir / "src" / iface.name)
        self.log("copied Cargo.toml, src/lib.rs, src/bin/*.rs (tests) and src/interfaces/*.rs -> src/*.rs (stubs)")

    # ----------------------------------------------------------------- prompts
    def project_context(self) -> str:
        path = CONFIG_DIR / "project_context" / f"{self.project_name}.md"
        return path.read_text(encoding="utf-8") if path.exists() else "(no project-specific context supplied)"

    def common_fields(self, iteration: int) -> dict:
        return {
            "PROJECT_NAME": self.project_name,
            "PROJECT_NUMBER": str(self.n),
            "C_DIR": str(self.c_dir),
            "RUST_DIR": str(self.rust_dir),
            "MP4_DIR": str(MP4_DIR),
            "C_FILES": file_listing(self.c_dir, (".c", ".h", ".txt", ".md", "Makefile")),
            "RUST_FILES": file_listing(self.rust_dir, (".rs", ".toml")),
            "PROJECT_CONTEXT": self.project_context(),
            "TOOLCHAIN": self.toolchain,
            "CLIPPY_CMD": "cargo +" + self.toolchain + " clippy " + " ".join(self.cfg["clippy_args"]),
            "ITERATION": str(iteration),
            "MAX_ITERATIONS": str(self.max_iterations),
        }

    def build_prompt(self, iteration: int, feedback: str | None) -> str:
        name = "task_prompt_initial.md" if feedback is None else "task_prompt_repair.md"
        template = (CONFIG_DIR / name).read_text(encoding="utf-8")
        return render(template, FEEDBACK=feedback or "", **self.common_fields(iteration))

    # ----------------------------------------------------------------- agent
    def agent_env(self) -> dict[str, str]:
        env = os.environ.copy()
        for key in list(env):
            if key in ("CLAUDECODE", "CLAUDE_CODE_SSE_PORT", "ENABLE_IDE_INTEGRATION", "CLAUDE_CODE_ENTRYPOINT"):
                env.pop(key, None)
        env["PATH"] = str(Path.home() / ".cargo" / "bin") + os.pathsep + env.get("PATH", "")
        env["RUSTUP_TOOLCHAIN"] = self.toolchain
        env["CARGO_TERM_COLOR"] = "never"
        return env

    def run_agent(self, iteration: int, prompt: str, it_dir: Path) -> dict:
        (it_dir / "prompt.md").write_text(prompt, encoding="utf-8")
        cmd = [
            self.claude, "-p",
            "--output-format", "stream-json", "--verbose",
            "--model", self.model,
            "--max-turns", str(self.cfg["max_turns_per_iteration"]),
            "--max-budget-usd", str(self.cfg["max_budget_usd_per_iteration"]),
            "--append-system-prompt-file", str(CONFIG_DIR / "system_prompt.md"),
            "--add-dir", str(self.c_dir),
            "--allowedTools", *self.cfg["allowed_tools"],
            "--disallowedTools", *self.cfg["disallowed_tools"],
        ]
        if self.cfg.get("no_session_persistence", False):
            cmd.append("--no-session-persistence")
        (it_dir / "agent_command.txt").write_text(" ".join(cmd) + "\n(prompt supplied on stdin)\n")
        self.log(f"iteration {iteration}: launching agent ({self.model}, max {self.cfg['max_turns_per_iteration']} turns, "
                 f"budget ${self.cfg['max_budget_usd_per_iteration']})")

        stream_path = it_dir / "agent_stream.jsonl"
        transcript_path = it_dir / "agent_transcript.md"
        result_event: dict = {}
        tool_calls = 0
        start = time.time()
        with open(stream_path, "w", encoding="utf-8") as stream_fh, open(transcript_path, "w", encoding="utf-8") as tr:
            tr.write(f"# Agent transcript: {self.project_name}, iteration {iteration}\n\n")
            proc = subprocess.Popen(cmd, cwd=str(self.rust_dir), env=self.agent_env(), stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
            assert proc.stdin is not None and proc.stdout is not None
            proc.stdin.write(prompt)
            proc.stdin.close()
            timeout = self.cfg["iteration_timeout_seconds"]
            for line in proc.stdout:
                stream_fh.write(line)
                stream_fh.flush()
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                tool_calls += self._transcribe(event, tr)
                if event.get("type") == "result":
                    result_event = event
                if time.time() - start > timeout:
                    self.log(f"iteration {iteration}: timeout after {timeout}s, terminating agent")
                    proc.kill()
                    break
            stderr = proc.stderr.read() if proc.stderr else ""
            proc.wait()
            if stderr.strip():
                (it_dir / "agent_stderr.txt").write_text(stderr)
        elapsed = time.time() - start
        info = {
            "session_id": result_event.get("session_id"),
            "subtype": result_event.get("subtype"),
            "is_error": result_event.get("is_error"),
            "num_turns": result_event.get("num_turns"),
            "tool_calls": tool_calls,
            "cost_usd": result_event.get("total_cost_usd"),
            "duration_ms": result_event.get("duration_ms"),
            "permission_denials": result_event.get("permission_denials", []),
            "usage": result_event.get("usage"),
            "model_usage": result_event.get("modelUsage"),
            "final_message": result_event.get("result"),
            "wall_seconds": round(elapsed, 1),
            "exit_code": proc.returncode,
        }
        (it_dir / "agent_result.json").write_text(json.dumps(info, indent=2))
        self.log(f"iteration {iteration}: agent finished subtype={info['subtype']} turns={info['num_turns']} "
                 f"tool_calls={tool_calls} cost=${info['cost_usd']} wall={info['wall_seconds']}s")
        return info

    @staticmethod
    def _transcribe(event: dict, tr) -> int:
        """Append a readable rendering of a stream-json event; return number of tool calls."""
        calls = 0
        etype = event.get("type")
        if etype == "assistant":
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "text" and block["text"].strip():
                    tr.write(f"### Assistant\n\n{block['text'].strip()}\n\n")
                elif block.get("type") == "tool_use":
                    calls += 1
                    payload = json.dumps(block.get("input", {}), ensure_ascii=False)
                    tr.write(f"**Tool call: {block.get('name')}**\n\n```json\n{payload[:3000]}\n```\n\n")
        elif etype == "user":
            for block in event.get("message", {}).get("content", []):
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    content = block.get("content")
                    if isinstance(content, list):
                        content = "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
                    content = str(content or "")
                    if len(content) > 6000:
                        content = content[:6000] + f"\n... [{len(content) - 6000} more characters]"
                    tr.write(f"<details><summary>Tool result</summary>\n\n```\n{content}\n```\n\n</details>\n\n")
        elif etype == "result":
            tr.write(f"---\n**Result:** subtype={event.get('subtype')} turns={event.get('num_turns')} "
                     f"cost=${event.get('total_cost_usd')} duration={event.get('duration_ms')}ms\n")
        tr.flush()
        return calls

    # ----------------------------------------------------------------- verification + feedback
    def verify(self, it_dir: Path) -> dict:
        self.log("verifying: guard -> cargo build -> cargo test -> cargo clippy -> unsafe metrics")
        results = verify.run_all(
            self.rust_dir, self.spec_dir, self.toolchain, it_dir,
            clippy_args=self.cfg["clippy_args"], protected_patterns=self.cfg["protected_files"],
        )
        snapshot = it_dir / "src_snapshot"
        if snapshot.exists():
            shutil.rmtree(snapshot)
        shutil.copytree(self.rust_dir / "src", snapshot)
        report = verify.format_report(results, f"project_{self.n} ({self.project_name})")
        (it_dir / "verify_report.md").write_text(report)
        self.log("\n" + report)
        return results

    def feedback(self, iteration: int, results: dict) -> str:
        b, t, c, u = results["build"], results["tests"], results["clippy"], results["unsafe"]["totals"]
        benchmark = results["benchmark_tests"]
        parts = [f"## Independent verification by the pipeline controller after iteration {iteration}", ""]
        if results.get("protected"):
            parts.append("### Protected files")
            for p in results["protected"]:
                parts.append(f"- `{p['file']}` was {p['status']} and has been RESTORED from the benchmark. Never edit it.")
            parts.append("")
        if results.get("interface"):
            parts.append("### Interface signatures missing (restore them exactly)")
            for f in results["interface"]:
                for sig in f["missing"]:
                    parts.append(f"- {f['file']}: `{sig}`")
            parts.append("")
        parts.append(f"### cargo build --all-targets: {'OK' if b['ok'] else 'FAILED'} ({b['errors']} errors, {b['warnings']} warnings)")
        if not b["ok"]:
            parts += ["```", truncate(b["log"], 150), "```"]
        parts.append("")
        parts.append(f"Benchmark binaries: {benchmark['passed']}/{benchmark['total']} active tests passed.")
        if t["compile_failed"]:
            parts.append("### cargo test: did not compile")
        else:
            parts.append(f"### cargo test: {t['passed']} passed, {t['failed']} failed, {t['ignored']} ignored (total counted {t['total']})")
            if t["failed_tests"]:
                parts.append("Failed tests: " + ", ".join(t["failed_tests"]))
                parts += ["```", truncate(t["failure_output"], 200), "```"]
        parts.append("")
        g = c["generated"]
        if not c["ok"]:
            parts += ["### Clippy invocation failed", "```", truncate(c["log"], 100), "```"]
        parts.append(f"### clippy ({' '.join(self.cfg['clippy_args'])}) on generated code: "
                     f"{g['total']} findings (correctness {g['correctness']}, style {g['style']}, complexity {g['complexity']}, "
                     f"perf {g['perf']}, other clippy {g['other_clippy']}, rustc warnings {g['rustc']})")
        gen_items = [it for it in c["items"] if it["generated"]]
        for it in gen_items[:80]:
            parts.append(f"- [{it['category']}] {it['code']} at {it['file']}:{it['line']}: {it['message']}")
        if len(gen_items) > 80:
            parts.append(f"- ... {len(gen_items) - 80} more")
        bt = c["benchmark_tests"]["total"]
        if bt:
            parts.append(f"(Additionally {bt} findings are inside the benchmark test files under src/bin/, which you must not edit; ignore them.)")
        parts.append("")
        parts.append("### Unsafe metrics (generated code only)")
        parts.append(f"unsafe lines {u['unsafe_lines']}, unsafe calls {u['unsafe_calls']}, unsafe casts {u['unsafe_casts']}, "
                     f"pointer arithmetic {u['pointer_arithmetic']}, raw pointer types {u['raw_pointer_types']}, "
                     f"#![forbid(unsafe_code)] present: {'yes' if u['forbid_unsafe_code'] else 'NO'}")
        parts.append(f"Remaining unimplemented!/todo!: {u['unimplemented_or_todo']}; unwrap {u['unwrap_calls']}, expect {u['expect_calls']}, "
                     f"panic! {u['panic_macros']}, clone {u['clone_calls']}")
        parts.append("")
        todo = []
        if not b["ok"]:
            todo.append("make the crate build")
        if not benchmark["ok"] or benchmark["total"] == 0:
            todo.append("make every benchmark test pass")
        elif not t["ok"]:
            todo.append("repair supplemental test failures or test execution errors")
        if not c["ok"]:
            todo.append("resolve the Clippy invocation error")
        if g["total"]:
            todo.append("remove every clippy and rustc warning in the generated code")
        if u["primary_total"] or not u["forbid_unsafe_code"]:
            todo.append("remove all unsafe code and add #![forbid(unsafe_code)] to src/lib.rs")
        if u["unimplemented_or_todo"]:
            todo.append("implement the remaining unimplemented!()/todo!() bodies")
        if results.get("interface"):
            todo.append("restore the missing interface signatures")
        if results.get("protected"):
            todo.append("verify again with all protected files intact")
        parts.append("### Remaining goals: " + ("; ".join(todo) if todo else "none, all targets met"))
        return "\n".join(parts)

    # ----------------------------------------------------------------- stopping condition
    @staticmethod
    def score(results: dict) -> tuple:
        t, c, u = results["benchmark_tests"], results["clippy"]["generated"], results["unsafe"]["totals"]
        return (
            int(results["build"]["ok"]),
            t["passed"],
            -u["unimplemented_or_todo"],
            -u["primary_total"],
            -c["total"],
        )

    def agent_reported_blocked(self) -> str | None:
        notes = self.rust_dir / "NOTES.md"
        if notes.exists():
            text = notes.read_text(encoding="utf-8", errors="replace")
            if "STATUS: BLOCKED" in text:
                return text
        return None

    def decide_stop(self, iteration: int, results: dict) -> str | None:
        if results["success"]:
            return "success: all tests pass, clippy clean, unsafe metrics zero, forbid(unsafe_code) present"
        if iteration >= self.max_iterations:
            return f"max_iterations ({self.max_iterations}) reached"
        if self.summary["total_cost_usd"] >= self.cfg["max_total_budget_usd_per_project"]:
            return f"budget exhausted (${self.summary['total_cost_usd']:.2f} >= ${self.cfg['max_total_budget_usd_per_project']})"
        blocked = self.agent_reported_blocked()
        tests = results["benchmark_tests"]
        only_tests_remain = (
            tests["failed"] > 0 and not tests["compile_failed"]
            and not results["tests"]["compile_failed"]
            and results["tests"]["failed"] == tests["failed"]
            and verify.checks_pass(results, require_passing_tests=False)
        )
        if blocked and only_tests_remain:
            return "agent reported STATUS: BLOCKED in NOTES.md (specification conflict it cannot resolve honestly); everything except the tests is green"
        scores = [tuple(it["score"]) for it in self.summary["iterations"]]
        patience = self.cfg["patience"]
        if len(scores) > patience:
            best_before = max(scores[:-patience])
            if all(s <= best_before for s in scores[-patience:]):
                return f"no progress for {patience} consecutive iterations"
        return None

    # ----------------------------------------------------------------- main loop
    def run(self) -> None:
        self.log(f"=== MP4 pipeline: project_{self.n} = {self.project_name} | model {self.model} | toolchain {self.toolchain}")
        self.init_workspace()
        done = len(self.summary["iterations"])
        feedback = None
        if done and self.summary["iterations"][-1].get("feedback"):
            feedback = self.summary["iterations"][-1]["feedback"]
            self.log(f"resuming after {done} completed iteration(s)")
        if self.summary.get("stop_reason") and not self.args.force:
            self.log(f"run already finished: {self.summary['stop_reason']} (use --force or --fresh to continue)")
            return
        self.summary["stop_reason"] = None

        iteration = done
        while True:
            iteration += 1
            it_dir = self.traj_dir / f"iteration_{iteration:02d}"
            it_dir.mkdir(parents=True, exist_ok=True)
            prompt = self.build_prompt(iteration, feedback)
            agent = self.run_agent(iteration, prompt, it_dir)
            results = self.verify(it_dir)
            feedback = self.feedback(iteration, results)
            record = {
                "iteration": iteration,
                "agent": {k: v for k, v in agent.items() if k not in ("usage", "model_usage", "final_message")},
                "build_ok": results["build"]["ok"],
                "tests": {k: results["benchmark_tests"][k] for k in ("passed", "failed", "ignored", "total", "failed_tests")},
                "clippy_generated": results["clippy"]["generated"],
                "clippy_all": results["clippy"]["all"],
                "unsafe": {k: results["unsafe"]["totals"][k] for k in
                           ("unsafe_lines", "unsafe_calls", "unsafe_casts", "pointer_arithmetic", "primary_total",
                            "forbid_unsafe_code", "unimplemented_or_todo", "unwrap_calls", "expect_calls", "clone_calls", "loc")},
                "protected_violations": results.get("protected", []),
                "interface_missing": results.get("interface", []),
                "success": results["success"],
                "score": list(self.score(results)),
                "feedback": feedback,
            }
            self.summary["iterations"].append(record)
            self.summary["total_cost_usd"] += float(agent.get("cost_usd") or 0.0)
            self.summary["total_agent_seconds"] += float(agent.get("wall_seconds") or 0.0)
            stop = self.decide_stop(iteration, results)
            self.summary["stop_reason"] = stop
            self._save_summary()
            self.write_summary_md()
            if stop:
                self.log(f"STOP after iteration {iteration}: {stop}")
                break
            self.log(f"iteration {iteration} did not meet all targets; starting repair iteration {iteration + 1}")

    def write_summary_md(self) -> None:
        s = self.summary
        rows = [
            f"# Pipeline summary: project_{self.n} ({self.project_name})", "",
            f"- Framework: {s['framework']['name']} {s['framework']['version']} ({s['framework']['mode']})",
            f"- Model: {s['model']}", f"- Toolchain: {s['toolchain']}",
            f"- Iterations: {len(s['iterations'])}", f"- Stop reason: {s['stop_reason']}",
            f"- Total agent cost: ${s['total_cost_usd']:.2f}; total agent wall time: {s['total_agent_seconds'] / 60:.1f} min", "",
            "| Iter | Agent turns | Tool calls | Cost ($) | Build | Tests passed/total | Clippy (generated) | Unsafe primary | unimplemented! left | forbid(unsafe_code) |",
            "|---:|---:|---:|---:|---|---:|---:|---:|---:|---|",
        ]
        for it in s["iterations"]:
            a, t, c, u = it["agent"], it["tests"], it["clippy_generated"], it["unsafe"]
            rows.append(
                f"| {it['iteration']} | {a.get('num_turns')} | {a.get('tool_calls')} | {float(a.get('cost_usd') or 0):.2f} | "
                f"{'ok' if it['build_ok'] else 'FAIL'} | {t['passed']}/{t['total']} | {c['total']} "
                f"(c{c['correctness']} s{c['style']} x{c['complexity']} p{c['perf']} o{c['other_clippy']} r{c['rustc']}) | "
                f"{u['primary_total']} | {u['unimplemented_or_todo']} | {'yes' if u['forbid_unsafe_code'] else 'no'} |"
            )
        (self.traj_dir / "SUMMARY.md").write_text("\n".join(rows) + "\n")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project", type=int, choices=(1, 2), help="assigned project number")
    parser.add_argument("--fresh", action="store_true", help="discard the current translation and trajectory and start over")
    parser.add_argument("--force", action="store_true", help="continue iterating even if a previous run already stopped")
    parser.add_argument("--max-iterations", type=int, default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--config", default=str(CONFIG_DIR / "pipeline.json"))
    parser.add_argument("--work-dir", default=None,
                        help="root for the Rust working copies (default MP4/translations); used for ablation runs")
    parser.add_argument("--trajectory-dir", default=None,
                        help="root for trajectories (default MP4/trajectories); used for ablation runs")
    args = parser.parse_args(argv)
    cfg = load_config(Path(args.config))
    Pipeline(args.project, cfg, args).run()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
