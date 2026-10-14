import jsonlines
import sys
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

import ast
from collections import Counter
import math
import random
import re

#####################################################
# Please finish all TODOs in this file for MP2;
#####################################################

# Fixed seed so vanilla and crafted runs pick the same assertion per problem
SELECTION_SEED = 598
CRAFTED_SAMPLES = 5

FEW_SHOT_EXAMPLE = '''Here is an example of how to solve this kind of task.

```python
def f(nums):
    total = 0
    for i, x in enumerate(nums):
        if x % 2 == 0:
            total += x * i
    return total
```
Function call: f([3, 4, 6])

Step-by-step execution:
1. Bind the arguments: nums = [3, 4, 6]
2. total = 0
3. Loop iteration i=0, x=3: condition `3 % 2 == 0` -> 1 == 0 -> False, total stays 0
4. Loop iteration i=1, x=4: condition `4 % 2 == 0` -> 0 == 0 -> True, total = 0 + 4 * 1 = 4
5. Loop iteration i=2, x=6: condition `6 % 2 == 0` -> 0 == 0 -> True, total = 4 + 6 * 2 = 16
6. Loop ends. `return total` returns 16
[Output]16[/Output]
'''

TYPE_AND_CONTROL_FLOW_EXAMPLE = '''Here is a second example. It demonstrates early returns and preserving the exact return type.

```python
def g(values):
    result = []
    for value in values:
        if value < 0:
            return tuple(result)
        result.append(value // 2)
    return result
```
Function call: g([5, 2, -1, 8])

Step-by-step execution:
1. Bind the arguments: values = [5, 2, -1, 8]
2. result = []
3. value=5: `5 < 0` -> False; append `5 // 2`, so result = [2]
4. value=2: `2 < 0` -> False; append `2 // 2`, so result = [2, 1]
5. value=-1: `-1 < 0` -> True; execute `return tuple(result)` and stop immediately
6. The exact return value is the tuple (2, 1), not the list [2, 1]. The value 8 is never visited.
[Output](2, 1)[/Output]
'''

CRAFTED_TEMPLATE = '''You are an expert Python interpreter. Your job is to simulate the execution of a Python function on a concrete input, exactly as CPython would, and report the value it returns.

Rules:
1. Start by binding every parameter to its argument value.
2. Execute the code statement by statement. For every loop iteration write the loop variable(s) and every variable that changes. For every `if`/`while` condition, evaluate it explicitly to True or False before choosing a branch.
3. Be careful with Python semantics: `range(a, b)` excludes `b`, indexing starts at 0, negative indices count from the end, `//` floors, `%` with negatives, `sorted()`/`sort()` order and `key=` functions, string methods, and integer vs float results.
4. Preserve the exact return type. A list and tuple with the same elements are different answers; so are `True` and `1`.
5. A `return` stops the current function immediately. Never execute later statements, loop iterations, or branches after it. Re-evaluate conditions using the current variable values instead of assuming a branch runs.
6. Base your answer ONLY on the supplied function call and what the code actually does. Do not solve examples from the docstring, invent a second input, or continue with another task.
7. Check the final value once against your trace. Then write it as a Python literal (for example 5, 2.5, 'abc', [1, 2], (3, None), True) between [Output] and [/Output] tags.
8. Emit exactly one [Output] block as the final line, and stop generating immediately after `[/Output]`.

{examples}
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
    """Return the first answer block, ignoring any continuation the model invents afterward."""
    matches = re.findall(r"\[Output\](.*?)\[[/\\]Output\]", response, re.DOTALL | re.IGNORECASE)
    if matches:
        return matches[0].strip()
    tail = re.split(r"\[Output\]", response, flags=re.IGNORECASE)
    if len(tail) > 1:
        return tail[1].strip().split("\n")[0].strip()
    return response.strip().split("\n")[-1].strip() if response.strip() else ""

def prediction_vote_key(prediction):
    """Canonicalize a prediction so equivalent spellings share a majority vote."""
    pred = prediction.strip().strip("`").strip()
    pred = re.sub(r"^(python\s+)", "", pred)
    try:
        value = ast.literal_eval(pred)
    except Exception:
        # Treat an unquoted generated string like the corresponding string literal.
        return ("str", pred.strip("'\""))
    if isinstance(value, str):
        return ("str", value)
    return (type(value).__name__, repr(value))

def select_majority(predictions):
    """Return the earliest prediction in the largest equivalence class and its vote count."""
    if not predictions:
        return "", 0, 0
    keys = [prediction_vote_key(prediction) for prediction in predictions]
    counts = Counter(keys)
    winning_key = max(counts, key=lambda key: counts[key])
    winning_index = keys.index(winning_key)
    return predictions[winning_index], winning_index, counts[winning_key]

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

def build_prompt(entry, inputs, vanilla):
    if vanilla:
        program = strip_docstrings(entry["prompt"] + entry["canonical_solution"])
        return VANILLA_TEMPLATE.format(inputs=inputs, program=program)
    program = (entry["prompt"] + entry["canonical_solution"]).strip("\n")
    call = f"{entry['entry_point']}({inputs})"
    examples = FEW_SHOT_EXAMPLE + "\n" + TYPE_AND_CONTROL_FLOW_EXAMPLE
    return CRAFTED_TEMPLATE.format(examples=examples, program=program, call=call)

def generate_response(model, tokenizer, prompt, max_new_tokens, sample_seed=None):
    """Generate one response; separate calls keep self-consistency sampling memory-safe."""
    input_ids = tokenizer(prompt, return_tensors="pt", add_special_tokens=False).input_ids.to(model.device)
    generate_args = {
        "input_ids": input_ids,
        "attention_mask": torch.ones_like(input_ids),
        "max_new_tokens": max_new_tokens,
        "eos_token_id": tokenizer.eos_token_id,
        "pad_token_id": tokenizer.eos_token_id,
    }
    if sample_seed is None:
        generate_args["do_sample"] = False
    else:
        torch.manual_seed(sample_seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(sample_seed)
        generate_args.update(do_sample=True, temperature=0.25, top_p=0.9)
    with torch.no_grad():
        outputs = model.generate(**generate_args)
    response = tokenizer.decode(outputs[0][input_ids.shape[1]:], skip_special_tokens=True)
    del outputs, input_ids
    return response

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

        # Keep the vanilla baseline unchanged. For the crafted condition, generate
        # five samples sequentially and select the majority answer without looking
        # at the ground truth. Sequential generation avoids retaining five large
        # decoder outputs on the GPU at once.
        if vanilla:
            responses = [generate_response(model, tokenizer, prompt, 512)]
        else:
            task_seed = sum((i + 1) * ord(ch) for i, ch in enumerate(entry["task_id"]))
            responses = [
                generate_response(
                    model, tokenizer, prompt, 1536,
                    sample_seed=SELECTION_SEED * 10000 + task_seed + sample_index,
                )
                for sample_index in range(CRAFTED_SAMPLES)
            ]

        # TODO: process the response and save it to results
        predictions = [extract_prediction(response) for response in responses]
        prediction, chosen_index, vote_count = select_majority(predictions)
        response = responses[chosen_index]
        verdict = check_prediction(prediction, expected)

        print(f"Task_ID {entry['task_id']}:\nprompt:\n{prompt}\nresponse:\n{response}\nis_correct:\n{verdict}")
        print(f"input: {inputs}\nexpected: {expected!r}\npredictions: {predictions}")
        print(f"selected prediction: {prediction} ({vote_count}/{len(predictions)} votes)\n")
        results.append({
            "task_id": entry["task_id"],
            "prompt": prompt,
            "response": response,
            "is_correct": verdict,
            "input": inputs,
            "expected_output": repr(expected),
            "prediction": prediction,
            "sample_predictions": predictions,
            "sample_responses": responses,
            "majority_votes": vote_count,
        })
        # Checkpoint after every problem so a Colab interruption does not lose
        # all completed results. The final write in main remains as a safeguard.
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
    results = prompt_model(dataset, model, vanilla, output_file)
    write_jsonl(results, output_file)
