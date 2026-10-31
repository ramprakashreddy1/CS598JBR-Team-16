"""Fast local tests for MP3 response processing (no model or GPU required)."""

import os
import tempfile
import unittest

import task_1
import task_2
import analyze


class Task1Tests(unittest.TestCase):
    def test_extracts_marked_java(self):
        response = "Explanation\n[Java Start]\nclass Solution { int f(){return 1;} }\n[Java End]"
        self.assertEqual(task_1.extract_java(response), "class Solution { int f(){return 1;} }")

    def test_extracts_fenced_java_without_markers(self):
        response = "Here it is:\n```java\nclass Solution { boolean f(){return true;} }\n```"
        self.assertIn("class Solution", task_1.extract_java(response))

    def test_wraps_method_only_answer(self):
        normalized = task_1.normalize_solution("public int f() { return 3; }")
        self.assertTrue(normalized.startswith("class Solution {"))
        self.assertIn("public int f()", normalized)

    def test_renames_generated_wrapper_class(self):
        normalized = task_1.normalize_solution("public class Main { int f() { return 3; } }")
        self.assertTrue(normalized.startswith("class Solution"))
        self.assertNotIn("class Main", normalized)

    def test_extracts_balanced_class_with_braces_in_strings_and_comments(self):
        code = '''public class Solution {
            String f() { return "}"; } // }
            /* { */ int g() { return 2; }
        }
        class Extra {}'''
        normalized = task_1.normalize_solution(code)
        self.assertTrue(normalized.endswith("}"))
        self.assertNotIn("class Extra", normalized)
        self.assertEqual(normalized.count("int g()"), 1)

    def test_derives_paired_java_dataset(self):
        path = task_1.derive_java_dataset_path("/tmp/selected_humanevalx_python_123.jsonl")
        self.assertEqual(path, "/tmp/selected_humanevalx_java_123.jsonl")

    def test_jsonl_round_trip(self):
        data = [{"task_id": "HumanEval/1", "is_correct": True}]
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "result.jsonl")
            task_1.write_jsonl(data, path)
            self.assertEqual(task_1.read_jsonl(path), data)


class Task2Tests(unittest.TestCase):
    def test_parses_case_insensitive_verdict(self):
        self.assertEqual(task_2.extract_verdict("Reasoning\n<start> buggy <end>"), "Buggy")

    def test_rejects_conflicting_verdicts(self):
        response = "<start>Correct<end>\nActually, <start>Buggy<end>"
        self.assertIsNone(task_2.extract_verdict(response))

    def test_rejects_missing_tags(self):
        self.assertIsNone(task_2.extract_verdict("The code is buggy."))

    def test_scores_expected_buggy_label(self):
        self.assertEqual(
            task_2.score_response("analysis\n<start>Buggy<end>"),
            (True, "correct_buggy_prediction", "Buggy"),
        )

    def test_crafted_prompt_does_not_reveal_canonical_solution(self):
        entry = {
            "prompt": "def f(x):\n",
            "buggy_solution": "    return x + 1\n",
            "canonical_solution": "    return x\n",
            "test": "assert candidate(1) == 1",
        }
        prompt = task_2.build_instruction(entry, vanilla=False)
        self.assertIn("return x + 1", prompt)
        self.assertNotIn("return x\n", prompt)
        self.assertIn("BUGGY DEMONSTRATION", prompt)
        self.assertIn("CORRECT DEMONSTRATION", prompt)
        self.assertIn("Your FIRST line", prompt)


class AnalysisTests(unittest.TestCase):
    def test_task_1_compilation_label_matches_rubric(self):
        row = {"is_correct": False, "failure_type": "compilation_error"}
        self.assertEqual(analyze.task_1_label(row), "False (compilation issue)")

    def test_percentage_uses_twenty_program_denominator(self):
        rows = {str(i): {"is_correct": i < 7} for i in range(20)}
        self.assertEqual(analyze.percent(rows), 35.0)

    def test_improvement_status_tracks_rubric_threshold(self):
        self.assertIn("NEEDS ITERATION", analyze.improvement_status(10.0, 25.0))
        self.assertIn("MEETS EXPECTATION", analyze.improvement_status(10.0, 30.0))
        self.assertIn("MEETS MINIMUM", analyze.improvement_status(10.0, 75.0))


if __name__ == "__main__":
    unittest.main()
