"""MP3 Task 2: ask DeepSeekCoder to detect HumanEvalPack bugs."""

import json
import os
import re
import sys

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")


MAX_NEW_TOKENS = 1536

VANILLA_TEMPLATE = """{program}

Is the above code buggy or correct? Please explain your step by step reasoning.
The prediction should be enclosed within <start> and <end> tags.
For example: <start>Buggy<end>"""

CRAFTED_TEMPLATE = """You are reviewing a Python implementation for semantic bugs. Decide whether the implementation satisfies the supplied specification and tests. Do not assume that plausible-looking code is correct or claim an assertion passes without calculating its actual value.

Here are two demonstrations of the required method and output format.

BUGGY DEMONSTRATION
Specification: Return whether the absolute distance between a and b is below limit.
Implementation: `def close(a, b, limit): return a - b < limit`
Test: `assert close(1, 10, 2) == False`
Analysis: On the test, the implementation evaluates 1 - 10 < 2, which is True, but the expected value is False. It omitted `abs`, so this is a semantic defect.
Verdict: <start>Buggy<end>

CORRECT DEMONSTRATION
Specification: Return the number of even integers in values.
Implementation: `def count_even(values): return sum(1 for x in values if x % 2 == 0)`
Tests: `assert count_even([1, 2, 4]) == 2`; `assert count_even([]) == 0`
Analysis: Direct evaluation produces 2 and 0 respectively, matching both assertions and the specification.
Verdict: <start>Correct<end>

Specification and implementation:
```python
{program}
```

Behavioral tests supplied with the task:
```python
{tests}
```

The name `candidate` in a test means the implementation under review. Analyze the target as follows:
1. Compare exact operators, loop bounds, branches, and return values with the specification.
2. Manually evaluate assertions one at a time until you find the first mismatch. Never merely state that tests pass.
3. Also check nearby boundary cases, Python negative-number behavior, mutation, ordering, and duplicates when relevant.
4. If one mismatch exists, the verdict is Buggy. Only use Correct after obtaining the expected result for every supplied assertion.

Your FIRST line must be exactly `<start>Buggy<end>` or `<start>Correct<end>`. Use the remaining response for a concise natural-language justification of at most 250 words. Emit exactly one tagged verdict."""


def read_jsonl(file_path):
    with open(file_path, encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def write_jsonl(results, file_path):
    with open(file_path, "w", encoding="utf-8") as file:
        for item in results:
            file.write(json.dumps(item, ensure_ascii=False) + "\n")


def complete_program(entry):
    """Construct the code under review without revealing the canonical solution."""
    prefix = entry.get("prompt") or entry.get("declaration", "")
    imports = entry.get("import", "")
    setup = entry.get("test_setup", "")
    return "\n".join(part.rstrip() for part in (imports, setup, prefix + entry["buggy_solution"]) if part).strip()


def build_instruction(entry, vanilla):
    program = complete_program(entry)
    if vanilla:
        return VANILLA_TEMPLATE.format(program=program)
    return CRAFTED_TEMPLATE.format(program=program, tests=entry.get("test", "").strip())


def extract_verdict(response):
    """Return Buggy/Correct only when the response contains one unambiguous tagged label."""
    matches = re.findall(r"<start>\s*(buggy|correct)\s*<end>", response, re.IGNORECASE)
    labels = {match.capitalize() for match in matches}
    if len(labels) == 1:
        return labels.pop()
    return None


def score_response(response):
    prediction = extract_verdict(response)
    if prediction is None:
        return False, "parse_error", None
    if prediction == "Buggy":
        return True, "correct_buggy_prediction", prediction
    return False, "predicted_correct", prediction


def load_model(model_name):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    if not torch.cuda.is_available():
        raise RuntimeError(
            "DeepSeekCoder-6.7B 4-bit inference requires an NVIDIA GPU. "
            "In Colab choose Runtime > Change runtime type > T4 GPU."
        )
    capability_major, _ = torch.cuda.get_device_capability()
    compute_dtype = (
        torch.bfloat16
        if capability_major >= 8 and torch.cuda.is_bf16_supported()
        else torch.float16
    )
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"4-bit compute dtype: {compute_dtype}")
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    quantization = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=compute_dtype,
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=quantization,
        device_map="auto",
        torch_dtype=compute_dtype,
        low_cpu_mem_usage=True,
        trust_remote_code=True,
    )
    model.eval()
    return tokenizer, model


def generate_response(model, tokenizer, instruction):
    import torch

    prompt = tokenizer.apply_chat_template(
        [{"role": "user", "content": instruction}],
        add_generation_prompt=True,
        tokenize=False,
    )
    inputs = tokenizer(prompt, return_tensors="pt", add_special_tokens=False).to(model.device)
    with torch.inference_mode():
        outputs = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.eos_token_id,
        )
    response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    del outputs, inputs
    torch.cuda.empty_cache()
    return prompt, response


def prompt_model(
    dataset,
    model_name="deepseek-ai/deepseek-coder-6.7b-instruct",
    vanilla=True,
    output_file=None,
):
    print(f"Working with {model_name}; vanilla={vanilla}")
    tokenizer, model = load_model(model_name)
    resume = os.environ.get("MP3_RESUME") == "1"
    completed = {}
    if resume and output_file and os.path.exists(output_file):
        completed_rows = read_jsonl(output_file)
        completed = {row["task_id"]: row for row in completed_rows}
        if len(completed) != len(completed_rows):
            raise ValueError(f"Cannot resume because {output_file} contains duplicate task IDs")
        print(f"Resuming from {len(completed)} completed Task 2 entries in {output_file}")
    results = []
    for entry in dataset:
        if entry["task_id"] in completed:
            print(f"Skipping completed Task_ID {entry['task_id']}")
            results.append(completed[entry["task_id"]])
            continue
        instruction = build_instruction(entry, vanilla)
        prompt, response = generate_response(model, tokenizer, instruction)
        is_correct, outcome, prediction = score_response(response)

        print(f"\nTask_ID {entry['task_id']}")
        print(f"prompt:\n{prompt}\nresponse:\n{response}")
        print(f"prediction: {prediction}")
        print(f"is_correct: {is_correct}")
        print(f"outcome: {outcome}")

        results.append(
            {
                "task_id": entry["task_id"],
                "prompt": prompt,
                "response": response,
                "is_correct": is_correct,
                "prediction": prediction,
                "outcome": outcome,
            }
        )
        if output_file:
            write_jsonl(results, output_file)
    return results


def main(args):
    if len(args) != 4:
        raise SystemExit(
            "Usage: python3 task_2.py <dataset.jsonl> <model> <output.jsonl> <True|False>"
        )
    input_dataset, model_name, output_file, vanilla_text = args
    if not input_dataset.endswith(".jsonl") or not output_file.endswith(".jsonl"):
        raise ValueError("Input and output files must use the .jsonl extension.")
    if vanilla_text not in {"True", "False"}:
        raise ValueError("<if_vanilla> must be exactly True or False.")
    dataset = read_jsonl(input_dataset)
    if len(dataset) != 20:
        raise ValueError("Task 2 requires exactly 20 HumanEvalPack entries.")
    results = prompt_model(
        dataset,
        model_name,
        vanilla_text == "True",
        output_file=output_file,
    )
    write_jsonl(results, output_file)


if __name__ == "__main__":
    main(sys.argv[1:])
