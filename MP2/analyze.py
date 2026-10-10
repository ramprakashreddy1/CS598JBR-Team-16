"""Builds the tables for the MP2 progress report from the four result files.

Usage: python3 analyze.py <seed>
"""
import json
import math
import sys


def read_jsonl(path):
    with open(path) as f:
        return {json.loads(line)["task_id"]: json.loads(line) for line in f if line.strip()}


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return sxy / (sx * sy) if sx and sy else float("nan")


def main(seed):
    t1v = read_jsonl(f"task_1_{seed}_vanilla.jsonl")
    t1c = read_jsonl(f"task_1_{seed}_crafted.jsonl")
    t2v = read_jsonl(f"task_2_{seed}_vanilla.jsonl")
    t2c = read_jsonl(f"task_2_{seed}_crafted.jsonl")
    ids = list(t1v)

    print("## MP2-Task1: is_correct per program\n")
    print("| Task ID | Input | Expected | Vanilla | Crafted |")
    print("|---|---|---|---|---|")
    for i in ids:
        print(f"| {i} | `{t1c[i].get('input', '')[:40]}` | `{t1c[i].get('expected_output', '')[:30]}` "
              f"| {t1v[i]['is_correct']} | {t1c[i]['is_correct']} |")
    v = sum(t1v[i]["is_correct"] for i in ids)
    c = sum(t1c[i]["is_correct"] for i in ids)
    n = len(ids)
    print(f"\nSuccess rate: vanilla {v}/{n} = {100 * v / n:.0f}%, crafted {c}/{n} = {100 * c / n:.0f}%, "
          f"absolute improvement {100 * (c - v) / n:+.0f} points\n")

    for name, res in (("vanilla", t2v), ("crafted", t2c)):
        print(f"## MP2-Task2: generated tests ({name})\n")
        print("| Task ID | Total tests | Passed | Failed | Pass % |")
        print("|---|---|---|---|---|")
        tot = pas = fai = 0
        for i in ids:
            r = res[i]
            pct = 100 * r["num_passed"] / r["num_tests"] if r["num_tests"] else 0
            print(f"| {i} | {r['num_tests']} | {r['num_passed']} | {r['num_failed']} | {pct:.0f}% |")
            tot, pas, fai = tot + r["num_tests"], pas + r["num_passed"], fai + r["num_failed"]
        print(f"| **Total** | {tot} | {pas} | {fai} | {100 * pas / tot if tot else 0:.1f}% |\n")

    print("## MP2-Task2: coverage per program\n")
    print("| Task ID | Vanilla coverage (%) | Crafted coverage (%) |")
    print("|---|---|---|")
    for i in ids:
        print(f"| {i} | {t2v[i]['coverage']} | {t2c[i]['coverage']} |")
    mv = sum(t2v[i]["coverage"] for i in ids) / n
    mc = sum(t2c[i]["coverage"] for i in ids) / n
    print(f"| **Average** | {mv:.2f} | {mc:.2f} |\n")

    print("## Correlation: code reasoning (Task 1) vs. passing tests (Task 2)\n")
    for name, t1, t2 in (("vanilla", t1v, t2v), ("crafted", t1c, t2c)):
        reason = [1.0 if t1[i]["is_correct"] else 0.0 for i in ids]
        pass_rate = [t2[i]["num_passed"] / t2[i]["num_tests"] if t2[i]["num_tests"] else 0.0 for i in ids]
        all_pass = [1.0 if t2[i]["num_tests"] and t2[i]["num_failed"] == 0 else 0.0 for i in ids]
        print(f"- {name}: point-biserial r(is_correct, test pass rate) = {pearson(reason, pass_rate):.3f}; "
              f"phi(is_correct, all tests pass) = {pearson(reason, all_pass):.3f}")


if __name__ == "__main__":
    main(sys.argv[1])
