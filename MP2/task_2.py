import jsonlines
import sys
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

import ast
import importlib.util
import json
import os
import re
import subprocess
import xml.etree.ElementTree as ET

#####################################################
# Please finish all TODOs in this file for MP2;
#####################################################

MP2_DIR = os.path.dirname(os.path.abspath(__file__))
COVERAGE_DIR = os.path.join(MP2_DIR, "Coverage")
TESTS_DIR = os.path.join(MP2_DIR, "generated_tests")
PYTEST_TIMEOUT = 120
TEST_TIMEOUT = 10
SLOW_TEST_LIMIT = 15

VANILLA_TEMPLATE = '''Generate a pytest test suite for the following code.
Only write unit tests in the output and nothing else.
{program}'''

CRAFTED_TEMPLATE = '''You are an expert Python test engineer. Write a pytest test suite for the function `{entry_point}` below that achieves 100% statement and branch coverage, and whose tests all PASS against this exact implementation.

```python
{program}
```

The function is already implemented in a module named `{module}`. Start the test file with:
```python
import pytest
from {module} import *
```

Requirements:
1. Exercise every decision point of the implementation. Write at least one test that makes each of the following conditions True and at least one that makes it False:
{branches}
2. Cover edge cases: empty inputs, a single element, zero, negative numbers, boundary values, and the largest/smallest cases that the code treats specially. Keep inputs small (no values like 10**9 or 2147483647) so that every test runs in well under a second.
3. Include every example from the docstring as a test.
4. Compute each expected value by carefully tracing THIS implementation step by step (it is the ground truth; do not "fix" it). If you are not sure of an expected value, choose a simpler input instead.
5. Write each test case as its own top-level test function containing exactly ONE assert, so that one wrong case does not hide the others. Use `pytest.approx` for floating point results.
6. Do NOT re-implement or redefine `{entry_point}`, do not call the test functions yourself, do not define tests inside other functions, do not use mocks, files or user input.
7. Write between 10 and 20 test functions in total.

The test file must look like this example (for a different function `add`):
```python
import pytest
from module import *

def test_add_positive():
    assert add(2, 3) == 5

def test_add_negative():
    assert add(-2, -3) == -5

def test_add_invalid_type():
    with pytest.raises(TypeError):
        add(1, None)
```

Output a single ```python code block containing only the complete test file.'''

FEEDBACK_TEMPLATE = '''Your previous pytest test suite for the function `{entry_point}` did not execute the following lines of the implementation (line numbers refer to the listing below):
{missing}

```python
{numbered_program}
```

Write ADDITIONAL pytest test functions (new names, do not repeat earlier tests) with inputs chosen so that each of the lines above is executed. Trace the implementation carefully to compute the exact expected values so that the tests pass. Each test function must contain exactly one assert, and you must not call the test functions yourself. Use `from {module} import *` to import the function and output a single ```python code block.'''


def save_file(content, file_path):
    with open(file_path, 'w') as file:
        file.write(content)

def strip_docstrings(source):
    """Remove module/function/class docstrings while keeping the rest of the source untouched."""
    tree = ast.parse(source)
    drop = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                drop.update(range(first.lineno, first.end_lineno + 1))
    lines = source.split("\n")
    kept = [line for i, line in enumerate(lines, start=1) if i not in drop]
    return "\n".join(kept).strip("\n") + "\n"

def module_name(task_id):
    # HumanEval/60 -> HumanEval_60 (a valid, importable module name)
    return task_id.replace("/", "_")

def list_branches(source):
    """Describe every decision point of the program so the prompt can ask for both outcomes."""
    items = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.If, ast.While, ast.IfExp)):
            kind = {ast.If: "if", ast.While: "while", ast.IfExp: "conditional expression"}[type(node)]
            items.append((node.lineno, f"`{ast.get_source_segment(source, node.test)}` ({kind})"))
        elif isinstance(node, (ast.For, ast.comprehension)):
            iter_src = ast.get_source_segment(source, node.iter)
            items.append((getattr(node, "lineno", node.iter.lineno), f"`{iter_src}` is empty vs. non-empty (loop)"))
        elif isinstance(node, ast.BoolOp):
            op = "and" if isinstance(node.op, ast.And) else "or"
            items.append((node.lineno, f"each operand of `{ast.get_source_segment(source, node)}` (short-circuit `{op}`)"))
        elif isinstance(node, ast.Try):
            items.append((node.lineno, "the `try` block raises vs. does not raise"))
    items.sort()
    if not items:
        return "   - (no branches: just check the return value on several different inputs)"
    return "\n".join(f"   - {text}" for _, text in items)

def extract_code(response):
    blocks = re.findall(r"```(?:python|py)?[^\n]*\n(.*?)```", response, re.DOTALL)
    if not blocks:
        m = re.search(r"```(?:python|py)?[^\n]*\n(.*)", response, re.DOTALL)
        blocks = [m.group(1)] if m else [response]
    # Prefer the block(s) that actually contain tests
    test_blocks = [b for b in blocks if re.search(r"def test_", b)]
    return "\n\n".join(test_blocks) if test_blocks else blocks[0]

def make_parseable(code):
    """Drop trailing lines until the code parses (handles generations cut off by max_new_tokens)."""
    lines = code.rstrip().split("\n")
    while lines:
        try:
            ast.parse("\n".join(lines))
            return "\n".join(lines) + "\n"
        except SyntaxError:
            lines.pop()
    return ""

def clean_test_code(code, entry, module):
    """Turn the model's code into a test file that imports the program under test from `module`."""
    code = make_parseable(code)
    if not code:
        return f"import pytest\nfrom {module} import *\n"
    tree = ast.parse(code)
    lines = code.split("\n")
    replace = {}
    program_names = {entry["entry_point"]} | {
        n.name for n in ast.parse(entry["prompt"] + entry["canonical_solution"]).body
        if isinstance(n, (ast.FunctionDef, ast.ClassDef))
    }
    for node in tree.body:
        span = range(node.lineno - 1, node.end_lineno)
        # Top-level calls such as `test_x()` or `pytest.main()` run at import time and break collection
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            for i in span:
                replace[i] = ""
        # A re-implemented function would hide the real program from coverage
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in program_names:
            for i in span:
                replace[i] = ""
        # `from solution import f` / `import solution` -> point to the real module
        elif isinstance(node, ast.ImportFrom) and node.module and node.module != module:
            if importlib.util.find_spec(node.module.split(".")[0]) is None:
                for i in span:
                    replace[i] = ""
                replace[node.lineno - 1] = f"from {module} import *"
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name != module and importlib.util.find_spec(alias.name.split(".")[0]) is None:
                    for i in span:
                        replace[i] = ""
                    replace[node.lineno - 1] = f"import {module} as {alias.asname or alias.name}"
    lines = [replace.get(i, line) for i, line in enumerate(lines)]
    code = f"import pytest\nfrom {module} import *\n\n" + "\n".join(lines).strip("\n") + "\n"
    return split_asserts(code)

def contains_assert(node):
    if any(isinstance(n, ast.Assert) for n in ast.walk(node)):
        return True
    # `with pytest.raises(...)` blocks are test cases too
    return isinstance(node, ast.With) and "raises" in ast.unparse(node.items[0].context_expr)

def split_asserts(code):
    """Split a test function with several asserts into one test function per assert, so a single wrong
    expected value does not stop the remaining checks from running. Statements without asserts are kept
    as setup in front of every later test case."""
    tree = ast.parse(code)
    out = []
    for node in tree.body:
        is_plain_test = (isinstance(node, ast.FunctionDef) and node.name.startswith("test")
                         and not node.args.args and not node.decorator_list)
        units = [s for s in node.body if contains_assert(s)] if is_plain_test else []
        if len(units) <= 1:
            out.append(ast.unparse(node))
            continue
        setup, k = [], 0
        for stmt in node.body:
            if contains_assert(stmt):
                k += 1
                body = "\n".join(ast.unparse(s) for s in setup + [stmt])
                out.append(f"def {node.name}_{k}():\n" + "\n".join("    " + l for l in body.split("\n")))
            elif not isinstance(stmt, ast.FunctionDef):
                setup.append(stmt)
    return "\n\n".join(out) + "\n"

def collects(code, test_dir, module):
    path = os.path.join(test_dir, f"{module}_collect_test.py")
    save_file(code, path)
    try:
        proc = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider",
                               os.path.basename(path)], cwd=test_dir, capture_output=True, text=True, timeout=60)
        return proc.returncode in (0, 5)
    except subprocess.TimeoutExpired:
        return False
    finally:
        os.remove(path)

def repair_collection(code, test_dir, module):
    """If pytest cannot even collect the file (e.g. a malformed parametrize), keep only the top-level
    statements that collect, instead of losing the whole suite."""
    if collects(code, test_dir, module):
        return code
    tree = ast.parse(code)
    kept = [ast.unparse(n) for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        candidate = kept + [ast.unparse(node)]
        if collects("\n\n".join(candidate) + "\n", test_dir, module):
            kept = candidate
        else:
            print(f"Dropped a statement that breaks test collection:\n{ast.unparse(node)[:300]}")
    return "\n\n".join(kept) + "\n"

def run_tests(module, test_dir, vanilla):
    """Run pytest with coverage on {ID}_test.py and return coverage, test counts and missing lines."""
    mode = "vanilla" if vanilla else "crafted"
    cov_report = os.path.join(COVERAGE_DIR, f"{module}_test_{mode}.json")
    junit = os.path.join(test_dir, f"{module}_junit.xml")
    for f in (cov_report, junit):
        if os.path.exists(f):
            os.remove(f)
    cmd = [sys.executable, "-m", "pytest", f"{module}_test.py", "--cov", module,
           "--cov-report", f"json:{cov_report}", f"--junitxml={junit}", "-q", "-p", "no:cacheprovider"]
    if importlib.util.find_spec("pytest_timeout"):
        # A single test with a huge input must not stop the whole report from being written
        cmd.append(f"--timeout={TEST_TIMEOUT}")
    print("Running:", " ".join(cmd))
    slow = []
    try:
        proc = subprocess.run(cmd, cwd=test_dir, capture_output=True, text=True, timeout=PYTEST_TIMEOUT)
        print(proc.stdout[-3000:])
        print(proc.stderr[-1000:])
    except subprocess.TimeoutExpired:
        # pytest-timeout cannot interrupt long C-level calls such as sum(range(2**31)),
        # so find those tests, deselect them (they count as failed) and run the rest again
        print(f"pytest timed out after {PYTEST_TIMEOUT}s, looking for slow tests")
        slow = find_slow_tests(module, test_dir)
        print("Deselected slow tests:", slow)
        cmd += [arg for node_id in slow for arg in ("--deselect", node_id)]
        try:
            proc = subprocess.run(cmd, cwd=test_dir, capture_output=True, text=True, timeout=PYTEST_TIMEOUT)
            print(proc.stdout[-3000:])
        except subprocess.TimeoutExpired:
            print(f"pytest timed out again after {PYTEST_TIMEOUT}s")

    stats = {"coverage": 0.0, "missing_lines": [], "num_tests": 0, "num_passed": 0, "num_failed": 0}
    if os.path.exists(cov_report):
        with open(cov_report) as f:
            report = json.load(f)
        stats["coverage"] = round(report["totals"]["percent_covered"], 2)
        for path, data in report["files"].items():
            if os.path.basename(path) == f"{module}.py":
                stats["missing_lines"] = data["missing_lines"]
    if os.path.exists(junit):
        root = ET.parse(junit).getroot()
        suite = root if root.tag == "testsuite" else root.find("testsuite")
        total = int(suite.get("tests", 0))
        failed = int(suite.get("failures", 0)) + int(suite.get("errors", 0))
        skipped = int(suite.get("skipped", 0))
        stats["num_tests"] = total + len(slow)
        stats["num_failed"] = failed + len(slow)
        stats["num_passed"] = total - failed - skipped
    return stats

def find_slow_tests(module, test_dir):
    proc = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider",
                           f"{module}_test.py"], cwd=test_dir, capture_output=True, text=True, timeout=60)
    node_ids = [line.strip() for line in proc.stdout.splitlines() if "::" in line]
    slow = []
    for node_id in node_ids:
        try:
            subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", node_id],
                           cwd=test_dir, capture_output=True, text=True, timeout=SLOW_TEST_LIMIT)
        except subprocess.TimeoutExpired:
            slow.append(node_id)
    return slow

def rename_tests(code, suffix):
    return re.sub(r"^(\s*)(def|class) ((?:test_|Test)\w*)", rf"\1\2 \3{suffix}", code, flags=re.MULTILINE)

def generate(model, tokenizer, instruction, max_new_tokens):
    prompt = tokenizer.apply_chat_template(
        [{"role": "user", "content": instruction}], add_generation_prompt=True, tokenize=False
    )
    input_ids = tokenizer(prompt, return_tensors="pt", add_special_tokens=False).input_ids.to(model.device)
    with torch.no_grad():
        outputs = model.generate(
            input_ids,
            attention_mask=torch.ones_like(input_ids),
            max_new_tokens=max_new_tokens,
            do_sample=False,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.eos_token_id,
        )
    return prompt, tokenizer.decode(outputs[0][input_ids.shape[1]:], skip_special_tokens=True)

def prompt_model(dataset, model_name = "deepseek-ai/deepseek-coder-6.7b-instruct", vanilla = True):
    print(f"Working with {model_name} prompt type {vanilla}...")

    # TODO: download the model
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    # TODO: load the model with quantization
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
    )

    os.makedirs(COVERAGE_DIR, exist_ok=True)
    test_dir = os.path.join(TESTS_DIR, "vanilla" if vanilla else "crafted")
    os.makedirs(test_dir, exist_ok=True)

    results = []
    for entry in dataset:
        # TODO: create prompt for the model
        # Tip : Use can use any data from the dataset to create
        #       the prompt including prompt, canonical_solution, test, etc.
        module = module_name(entry["task_id"])
        full_program = entry["prompt"] + entry["canonical_solution"]
        save_file(full_program, os.path.join(test_dir, f"{module}.py"))
        if vanilla:
            instruction = VANILLA_TEMPLATE.format(program=strip_docstrings(full_program))
        else:
            instruction = CRAFTED_TEMPLATE.format(
                entry_point=entry["entry_point"], program=full_program.strip("\n"),
                module=module, branches=list_branches(full_program),
            )

        # TODO: prompt the model and get the response
        prompt, response = generate(model, tokenizer, instruction, 1024 if vanilla else 1536)

        # TODO: process the response, generate coverage and save it to results
        test_code = repair_collection(clean_test_code(extract_code(response), entry, module), test_dir, module)
        save_file(test_code, os.path.join(test_dir, f"{module}_test.py"))
        stats = run_tests(module, test_dir, vanilla)

        feedback_prompt, feedback_response = "", ""
        if not vanilla and stats["missing_lines"]:
            # Coverage-guided refinement: show the model exactly which lines it missed
            numbered = "\n".join(f"{i:3d} | {line}" for i, line in enumerate(full_program.split("\n"), start=1))
            missing = "\n".join(f"   - line {n}: `{full_program.split(chr(10))[n - 1].strip()}`" for n in stats["missing_lines"])
            feedback_instruction = FEEDBACK_TEMPLATE.format(
                entry_point=entry["entry_point"], missing=missing,
                numbered_program=numbered, module=module,
            )
            feedback_prompt, feedback_response = generate(model, tokenizer, feedback_instruction, 1024)
            extra = clean_test_code(extract_code(feedback_response), entry, module)
            merged = test_code + "\n\n# ---- additional tests from coverage feedback ----\n" + rename_tests(extra, "_extra")
            test_code = repair_collection(merged, test_dir, module)
            save_file(test_code, os.path.join(test_dir, f"{module}_test.py"))
            stats = run_tests(module, test_dir, vanilla)
        coverage = stats["coverage"]

        print(f"Task_ID {entry['task_id']}:\nprompt:\n{prompt}\nresponse:\n{response}\ncoverage:\n{coverage}")
        if feedback_prompt:
            print(f"feedback prompt:\n{feedback_prompt}\nfeedback response:\n{feedback_response}")
        print(f"tests: {stats['num_tests']}, passed: {stats['num_passed']}, failed: {stats['num_failed']}\n")
        results.append({
            "task_id": entry["task_id"],
            "prompt": prompt,
            "response": response,
            "coverage": coverage,
            "feedback_prompt": feedback_prompt,
            "feedback_response": feedback_response,
            "test_code": test_code,
            "num_tests": stats["num_tests"],
            "num_passed": stats["num_passed"],
            "num_failed": stats["num_failed"],
            "missing_lines": stats["missing_lines"],
        })

    return results

def read_jsonl(file_path):
    dataset = []
    with jsonlines.open(file_path) as reader:
        for line in reader:
            dataset.append(line)
    return dataset

def write_jsonl(results, file_path):
    with jsonlines.open(file_path, "w") as f:
        for item in results:
            f.write_all([item])

if __name__ == "__main__":
    """
    This Python script is to run prompt LLMs for code synthesis.
    Usage:
    `python3 task_2.py <input_dataset> <model> <output_file> <if_vanilla>`|& tee prompt.log

    Inputs:
    - <input_dataset>: A `.jsonl` file, which should be your team's dataset containing 20 HumanEval problems.
    - <model>: Specify the model to use. Options are "deepseek-ai/deepseek-coder-6.7b-base" or "deepseek-ai/deepseek-coder-6.7b-instruct".
    - <output_file>: A `.jsonl` file where the results will be saved.
    - <if_vanilla>: Set to 'True' or 'False' to enable vanilla prompt

    Outputs:
    - You can check <output_file> for detailed information.
    """
    args = sys.argv[1:]
    input_dataset = args[0]
    model = args[1]
    output_file = args[2]
    if_vanilla = args[3] # True or False

    if not input_dataset.endswith(".jsonl"):
        raise ValueError(f"{input_dataset} should be a `.jsonl` file!")

    if not output_file.endswith(".jsonl"):
        raise ValueError(f"{output_file} should be a `.jsonl` file!")

    vanilla = True if if_vanilla == "True" else False

    dataset = read_jsonl(input_dataset)
    results = prompt_model(dataset, model, vanilla)
    write_jsonl(results, output_file)
