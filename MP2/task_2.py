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
2. Cover edge cases: empty inputs, a single element, zero, negative numbers, boundary values, and the largest/smallest cases that the code treats specially.
3. Include every example from the docstring as a test.
4. Compute each expected value by carefully tracing THIS implementation step by step (it is the ground truth; do not "fix" it). If you are not sure of an expected value, choose a simpler input instead.
5. Prefer `@pytest.mark.parametrize` with many (input, expected) pairs so that one wrong case does not hide the others. Use `pytest.approx` for floating point results.
6. Do NOT re-implement or redefine `{entry_point}`, do not use mocks, do not read files or user input.
7. Write between 10 and 20 test cases in total.

Output a single ```python code block containing only the complete test file.'''

FEEDBACK_TEMPLATE = '''Your previous pytest test suite for the function `{entry_point}` did not execute the following lines of the implementation (line numbers refer to the listing below):
{missing}

```python
{numbered_program}
```

Write ADDITIONAL pytest test functions (new names, do not repeat earlier tests) with inputs chosen so that each of the lines above is executed. Trace the implementation carefully to compute the exact expected values so that the tests pass. Use `from {module} import *` to import the function and output a single ```python code block.'''


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
        # A re-implemented function would hide the real program from coverage
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in program_names:
            for i in span:
                replace[i] = ""
        # Generated test files sometimes invoke test functions directly at
        # module scope. Pytest already discovers these functions; executing
        # them during import turns an ordinary failed assertion into a
        # collection error and prevents pytest-cov from writing a report.
        elif (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id.startswith("test_")
        ):
            for i in span:
                replace[i] = ""
        # Likewise, discard a generated `if __name__ == "__main__"` runner.
        elif (
            isinstance(node, ast.If)
            and isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name)
            and node.test.left.id == "__name__"
        ):
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
    return f"import pytest\nfrom {module} import *\n\n" + "\n".join(lines).strip("\n") + "\n"

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
    print("Running:", " ".join(cmd))
    try:
        proc = subprocess.run(cmd, cwd=test_dir, capture_output=True, text=True, timeout=PYTEST_TIMEOUT)
        print(proc.stdout[-3000:])
        print(proc.stderr[-1000:])
    except subprocess.TimeoutExpired:
        print(f"pytest timed out after {PYTEST_TIMEOUT}s")

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
        stats["num_tests"] = total
        stats["num_failed"] = failed
        stats["num_passed"] = total - failed - skipped
    return stats

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

def prompt_model(dataset, model_name = "deepseek-ai/deepseek-coder-6.7b-instruct", vanilla = True, output_file = None):
    print(f"Working with {model_name} prompt type {vanilla}...")

    if not torch.cuda.is_available():
        raise RuntimeError(
            "DeepSeekCoder-6.7B 4-bit inference requires an NVIDIA GPU. "
            "In Colab select Runtime > Change runtime type > T4 GPU, "
            "restart the runtime, and rerun all cells."
        )

    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"PyTorch CUDA: {torch.version.cuda}")
    print(f"4-bit compute dtype: {compute_dtype}")

    # TODO: download the model
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    # TODO: load the model with quantization
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=compute_dtype,
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=compute_dtype,
        low_cpu_mem_usage=True,
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
        test_code = clean_test_code(extract_code(response), entry, module)
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
            test_code = test_code + "\n\n# ---- additional tests from coverage feedback ----\n" + rename_tests(extra, "_extra")
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
        # Checkpoint after every problem so a long crafted run survives a
        # Colab interruption with its completed records intact.
        if output_file:
            write_jsonl(results, output_file)

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
    results = prompt_model(dataset, model, vanilla, output_file)
    write_jsonl(results, output_file)
