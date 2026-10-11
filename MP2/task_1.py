import jsonlines
import sys
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

import ast
import math
import random
import re

#####################################################
# Please finish all TODOs in this file for MP2;
#####################################################

# Fixed seed so vanilla and crafted runs pick the same assertion per problem
SELECTION_SEED = 598

# Self-consistency: besides the greedy answer, sample this many extra reasoning paths and take a majority vote
SC_SAMPLES = 4

FEW_SHOT_EXAMPLE = '''Here are two examples of how to solve this kind of task.

Example 1:
```python
def f(n):
    for d in reversed(range(2, n)):
        if n % d == 0:
            return d
    return 1
```
Function call: f(21)

Step-by-step execution:
1. Bind the arguments: n = 21
2. `range(2, 21)` is 2, 3, ..., 20 (21 is excluded), so `reversed(range(2, 21))` is 20, 19, ..., 2
3. d=20: 21 % 20 = 1, `1 == 0` -> False
4. d=19: 21 % 19 = 2, `2 == 0` -> False
5. d=18: 21 % 18 = 3 -> False
6. d=17: 21 % 17 = 4 -> False
7. d=16: 21 % 16 = 5 -> False
8. d=15: 21 % 15 = 6 -> False
9. d=14: 21 % 14 = 7 -> False
10. d=13: 21 % 13 = 8 -> False
11. d=12: 21 % 12 = 9 -> False
12. d=11: 21 % 11 = 10 -> False
13. d=10: 21 % 10 = 1 -> False
14. d=9: 21 % 9 = 3 -> False
15. d=8: 21 % 8 = 5 -> False
16. d=7: 21 % 7 = 0, `0 == 0` -> True, so `return d` returns 7 immediately
[Output]7[/Output]

Example 2:
```python
def g(s, words):
    nums = [int(t) for t in s.split() if t.isdigit()]
    ranked = sorted(words, key=lambda w: (len(w), w))
    return ranked[:2] + [sum(nums)]
```
Function call: g("3 cats and 12 dogs", ["pear", "fig", "apple", "kiwi"])

Step-by-step execution:
1. Bind the arguments: s = "3 cats and 12 dogs", words = ["pear", "fig", "apple", "kiwi"]
2. s.split() = ['3', 'cats', 'and', '12', 'dogs']
3. '3'.isdigit() -> True, 'cats'.isdigit() -> False, 'and'.isdigit() -> False, '12'.isdigit() -> True, 'dogs'.isdigit() -> False
4. nums = [3, 12]
5. Sort keys: "pear" -> (4, 'pear'), "fig" -> (3, 'fig'), "apple" -> (5, 'apple'), "kiwi" -> (4, 'kiwi')
6. Ascending by key: (3, 'fig') < (4, 'kiwi') < (4, 'pear') < (5, 'apple'), so ranked = ['fig', 'kiwi', 'pear', 'apple']
7. ranked[:2] = ['fig', 'kiwi'], sum(nums) = 3 + 12 = 15
8. `return ranked[:2] + [sum(nums)]` concatenates two lists, so it returns the list ['fig', 'kiwi', 15] (square brackets, because it is a list)
[Output]['fig', 'kiwi', 15][/Output]
'''

CRAFTED_TEMPLATE = '''You are an expert Python interpreter. Your job is to simulate the execution of a Python function on a concrete input, exactly as CPython would, and report the value it returns.

Rules:
1. Start by binding every parameter to its argument value.
2. Execute the code statement by statement. Never summarize a loop ("loop through the list..."): write one line per iteration with the concrete values of the loop variable(s) and of every variable that changes. For every `if`/`while` condition, substitute the concrete values and evaluate it to True or False before choosing a branch.
3. When a `return` statement executes, the function stops immediately.
4. If a loop has too many iterations to list (for example nested loops over range(2, 101)), do not guess: work out which iteration first makes the condition true and show why.
5. Be careful with Python semantics: `range(a, b)` excludes `b`, indexing starts at 0, negative indices count from the end, `//` floors, `%` with negatives, `sorted()`/`sort()` order and `key=` functions (ties keep their original order), string methods such as `split()` and `isdigit()`, integer vs float results, and tuples vs lists.
6. Base your answer ONLY on what the code actually does, not on the function name or the docstring (the docstring is only a hint).
7. Keep the exact type of the return value: a list (from `[...]`, `append`, list comprehensions, slicing a list, `sorted()`) must be written with square brackets [1, 2]; only a real tuple (e.g. `return a, b`) is written with parentheses (1, 2).
8. After the trace, write the exact return value as a Python literal (for example 5, 2.5, 'abc', [1, 2], (3, None), True) between [Output] and [/Output] tags, then stop. Write the value itself, not the function call. Solve only this one task.

{example}
Now solve the following task.

```python
{program}
```
Function call: {call}

Step-by-step execution:'''

VANILLA_TEMPLATE = '''If the input is {inputs}, what will the following code return?
The return value prediction must be enclosed between [Output] and [/Output] tags. For example : [Output]prediction[/Output].
{program}'''


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

def select_test(entry):
    """Pick one `assert candidate(...) == expected` from the HumanEval tests (deterministically at random)
    and compute its ground-truth output by running the canonical solution."""
    test_src = entry["test"]
    full_program = entry["prompt"] + entry["canonical_solution"]
    namespace = {}
    exec(full_program, namespace)
    namespace["candidate"] = namespace[entry["entry_point"]]

    candidates = []
    for node in ast.walk(ast.parse(test_src)):
        if not isinstance(node, ast.Assert) or not isinstance(node.test, ast.Compare):
            continue
        cmp = node.test
        if len(cmp.ops) != 1 or not isinstance(cmp.ops[0], ast.Eq):
            continue
        call = cmp.left
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "candidate"):
            continue
        args = [ast.get_source_segment(test_src, a) for a in call.args]
        args += [f"{k.arg}={ast.get_source_segment(test_src, k.value)}" for k in call.keywords]
        inputs = ", ".join(args)
        try:
            expected = eval(ast.get_source_segment(test_src, cmp.comparators[0]), namespace)
            actual = eval(f"candidate({inputs})", namespace)
        except Exception:
            continue
        if actual == expected:
            candidates.append((inputs, expected))

    rng = random.Random(f"{SELECTION_SEED}-{entry['task_id']}")
    return rng.choice(candidates)

def extract_prediction(response):
    """Return the text inside the first [Output]...[/Output] block (tolerating [\\Output] and missing close tags).
    The first block is the answer; anything after it is the model running on into made-up follow-up tasks."""
    matches = re.findall(r"\[Output\](.*?)\[[/\\]Output\]", response, re.DOTALL | re.IGNORECASE)
    if matches:
        return matches[0].strip()
    tail = re.split(r"\[Output\]", response, flags=re.IGNORECASE)
    if len(tail) > 1:
        return tail[-1].strip().split("\n")[0].strip()
    return response.strip().split("\n")[-1].strip() if response.strip() else ""

def values_equal(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) == type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-9)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return type(a) == type(b) and len(a) == len(b) and all(values_equal(x, y) for x, y in zip(a, b))
    return a == b

def check_prediction(prediction, expected):
    pred = prediction.strip().strip("`").strip()
    pred = re.sub(r"^(python\s+)", "", pred)
    try:
        value = ast.literal_eval(pred)
    except Exception:
        # Unquoted strings such as [Output]db1111db[/Output]
        return isinstance(expected, str) and pred.strip("'\"") == expected
    if values_equal(value, expected):
        return True
    # Accept a string answer written without the right quoting style
    return isinstance(expected, str) and str(value) == expected

def normalize_prediction(prediction):
    pred = prediction.strip().strip("`").strip()
    try:
        return repr(ast.literal_eval(pred))
    except Exception:
        return pred.strip("'\"")

def majority_vote(responses):
    """Pick the most common predicted value; ties go to the earliest response (the greedy one)."""
    predictions = [extract_prediction(r) for r in responses]
    keys = [normalize_prediction(p) for p in predictions]
    counts = {}
    for k in keys:
        counts[k] = counts.get(k, 0) + 1
    winner = max(counts, key=lambda k: (counts[k], -keys.index(k)))
    i = keys.index(winner)
    return responses[i], predictions[i], counts

def build_prompt(entry, inputs, vanilla):
    if vanilla:
        program = strip_docstrings(entry["prompt"] + entry["canonical_solution"])
        return VANILLA_TEMPLATE.format(inputs=inputs, program=program)
    program = (entry["prompt"] + entry["canonical_solution"]).strip("\n")
    call = f"{entry['entry_point']}({inputs})"
    return CRAFTED_TEMPLATE.format(example=FEW_SHOT_EXAMPLE, program=program, call=call)

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

    results = []
    for entry in dataset:
        # TODO: create prompt for the model
        # Tip : Use can use any data from the dataset to create
        #       the prompt including prompt, canonical_solution, test, etc.
        inputs, expected = select_test(entry)
        instruction = build_prompt(entry, inputs, vanilla)
        # The chat template adds the DeepSeek system prompt and the ### Instruction / ### Response markers
        prompt = tokenizer.apply_chat_template(
            [{"role": "user", "content": instruction}], add_generation_prompt=True, tokenize=False
        )

        # TODO: prompt the model and get the response
        input_ids = tokenizer(prompt, return_tensors="pt", add_special_tokens=False).input_ids.to(model.device)
        gen_kwargs = dict(
            attention_mask=torch.ones_like(input_ids),
            max_new_tokens=512 if vanilla else 1536,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.eos_token_id,
            stop_strings=["[/Output]"],
            tokenizer=tokenizer,
        )
        with torch.no_grad():
            outputs = model.generate(input_ids, do_sample=False, **gen_kwargs)
            if not vanilla and SC_SAMPLES:
                sampled = model.generate(input_ids, do_sample=True, temperature=0.6, top_p=0.95,
                                         num_return_sequences=SC_SAMPLES, **gen_kwargs)
        responses = [tokenizer.decode(outputs[0][input_ids.shape[1]:], skip_special_tokens=True)]
        if not vanilla and SC_SAMPLES:
            responses += [tokenizer.decode(s[input_ids.shape[1]:], skip_special_tokens=True) for s in sampled]

        # TODO: process the response and save it to results
        if vanilla:
            response, prediction, votes = responses[0], extract_prediction(responses[0]), {}
        else:
            response, prediction, votes = majority_vote(responses)
        verdict = check_prediction(prediction, expected)

        print(f"Task_ID {entry['task_id']}:\nprompt:\n{prompt}\nresponse:\n{response}\nis_correct:\n{verdict}")
        print(f"input: {inputs}\nexpected: {expected!r}\nprediction: {prediction}\nvotes: {votes}\n")
        results.append({
            "task_id": entry["task_id"],
            "prompt": prompt,
            "response": response,
            "is_correct": verdict,
            "input": inputs,
            "expected_output": repr(expected),
            "prediction": prediction,
            "votes": votes,
            "all_responses": responses,
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
    `python3 Task_1.py <input_dataset> <model> <output_file> <if_vanilla>`|& tee prompt.log

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
