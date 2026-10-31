"""Create rubric-ready MP3 comparison tables from the four result JSONL files."""

import json
import os
import sys
from collections import Counter


def read_jsonl(path):
    with open(path, encoding="utf-8") as file:
        rows = [json.loads(line) for line in file if line.strip()]
    if len(rows) != 20:
        raise ValueError(f"{path} has {len(rows)} entries; expected 20")
    indexed = {row["task_id"]: row for row in rows}
    if len(indexed) != 20:
        raise ValueError(f"{path} contains duplicate task IDs")
    return indexed


def percent(rows):
    return 100.0 * sum(bool(row.get("is_correct")) for row in rows.values()) / 20


def success_count(rows):
    return sum(bool(row.get("is_correct")) for row in rows.values())


def improvement_status(vanilla_rate, crafted_rate):
    improvement = crafted_rate - vanilla_rate
    if improvement < 20:
        return "NEEDS ITERATION - below the rubric's expected 20-point minimum"
    if improvement <= 50:
        return "MEETS EXPECTATION - within the expected 20-50 point range"
    return "MEETS MINIMUM - above the typical 20-50 point range; document the methodology"


def outcome_summary(rows, field):
    counts = Counter(str(row.get(field, "missing")) for row in rows.values())
    return ", ".join(f"{label}: {count}" for label, count in sorted(counts.items()))


def task_1_label(row):
    if row.get("is_correct"):
        return "True"
    failure = row.get("failure_type", "unknown failure").replace("_", " ")
    if failure.startswith("compilation"):
        return "False (compilation issue)"
    return f"False ({failure})"


def task_2_label(row):
    return "True" if row.get("is_correct") else "False"


def require_same_ids(left, right, label):
    if set(left) != set(right):
        missing_left = sorted(set(right) - set(left))
        missing_right = sorted(set(left) - set(right))
        raise ValueError(
            f"{label} task IDs do not match; missing from vanilla={missing_left}, "
            f"missing from crafted={missing_right}"
        )


def comparison_table(vanilla, crafted, formatter, include_failure=False):
    require_same_ids(vanilla, crafted, "Comparison")
    if include_failure:
        lines = [
            "| Task ID | Vanilla | Crafted | Vanilla category | Crafted category |",
            "|---|---:|---:|---|---|",
        ]
        for task_id in vanilla:
            v = vanilla[task_id]
            c = crafted[task_id]
            lines.append(
                f"| {task_id} | {formatter(v)} | {formatter(c)} | "
                f"{v.get('failure_type', 'unknown')} | {c.get('failure_type', 'unknown')} |"
            )
        return "\n".join(lines)

    lines = ["| Task ID | Vanilla | Crafted |", "|---|---:|---:|"]
    for task_id in vanilla:
        lines.append(f"| {task_id} | {formatter(vanilla[task_id])} | {formatter(crafted[task_id])} |")
    return "\n".join(lines)


def build_report(seed, directory="."):
    paths = {
        "t1v": os.path.join(directory, f"task_1_{seed}_vanilla.jsonl"),
        "t1c": os.path.join(directory, f"task_1_{seed}_crafted.jsonl"),
        "t2v": os.path.join(directory, f"task_2_{seed}_vanilla.jsonl"),
        "t2c": os.path.join(directory, f"task_2_{seed}_crafted.jsonl"),
    }
    data = {key: read_jsonl(path) for key, path in paths.items()}
    require_same_ids(data["t1v"], data["t1c"], "Task 1")
    require_same_ids(data["t2v"], data["t2c"], "Task 2")

    t1v_rate, t1c_rate = percent(data["t1v"]), percent(data["t1c"])
    t2v_rate, t2c_rate = percent(data["t2v"]), percent(data["t2c"])
    t1v_count, t1c_count = success_count(data["t1v"]), success_count(data["t1c"])
    t2v_count, t2c_count = success_count(data["t2v"]), success_count(data["t2c"])
    return "\n".join(
        [
            "# MP3 experiment summary",
            "",
            "## Task 1 - Code translation",
            "",
            f"- Vanilla success rate: {t1v_rate:.1f}% ({t1v_count}/20)",
            f"- Crafted success rate: {t1c_rate:.1f}% ({t1c_count}/20)",
            f"- Absolute improvement: {t1c_rate - t1v_rate:+.1f} percentage points",
            f"- Rubric check: **{improvement_status(t1v_rate, t1c_rate)}**",
            f"- Vanilla outcomes: {outcome_summary(data['t1v'], 'failure_type')}",
            f"- Crafted outcomes: {outcome_summary(data['t1c'], 'failure_type')}",
            "",
            comparison_table(data["t1v"], data["t1c"], task_1_label, include_failure=True),
            "",
            "## Task 2 - Bug detection",
            "",
            f"- Vanilla success rate: {t2v_rate:.1f}% ({t2v_count}/20)",
            f"- Crafted success rate: {t2c_rate:.1f}% ({t2c_count}/20)",
            f"- Absolute improvement: {t2c_rate - t2v_rate:+.1f} percentage points",
            f"- Rubric check: **{improvement_status(t2v_rate, t2c_rate)}**",
            f"- Vanilla outcomes: {outcome_summary(data['t2v'], 'outcome')}",
            f"- Crafted outcomes: {outcome_summary(data['t2c'], 'outcome')}",
            "",
            comparison_table(data["t2v"], data["t2c"], task_2_label),
            "",
        ]
    )


def main(args):
    if len(args) not in {1, 2}:
        raise SystemExit("Usage: python3 analyze.py <seed> [output.md]")
    seed = args[0]
    output = args[1] if len(args) == 2 else "analysis.md"
    report = build_report(seed)
    with open(output, "w", encoding="utf-8") as file:
        file.write(report)
    print(report)


if __name__ == "__main__":
    main(sys.argv[1:])
