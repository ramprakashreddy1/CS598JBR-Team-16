###################################################################
# This is a list of all commands you need to run for MP2 on Colab.
# Each "# %% Cell N" block below is one Colab cell (MP2/MP2.ipynb has them ready to upload).
###################################################################

# %% Cell 1: check that the GPU runtime is on
! nvidia-smi

# %% Cell 2: clone the repo (or pull the latest changes if it is already cloned)
# TODO: Clone your GitHub repository
import os
if not os.path.exists("/content/CS598JBR-Team-16"):
    ! git clone https://github.com/ramprakashreddy1/CS598JBR-Team-16.git /content/CS598JBR-Team-16
%cd /content/CS598JBR-Team-16/MP2
! git pull

# %% Cell 3: install requirements
# Set up requirements for model prompting
! bash -x setup_models.sh

# %% Cell 4: dataset, seed and output file names
input_dataset = "../MP1/selected_humaneval_148118091928943694313340081131652963687.jsonl"

# TODO: add your seed generated in MP1
seed = "148118091928943694313340081131652963687"
task_1_vanilla_json = "task_1_" + seed + "_vanilla.jsonl"
task_1_crafted_json = "task_1_" + seed + "_crafted.jsonl"
task_2_vanilla_json = "task_2_" + seed + "_vanilla.jsonl"
task_2_crafted_json = "task_2_" + seed + "_crafted.jsonl"

# Prompt the models, you can modify `MP2/task_1.py, MP2/task_2.py`
# The {input_dataset} is the JSON file consisting of 20 unique programs for your group that you generated in MP1 (selected_humaneval_[seed].jsonl)

# %% Cell 5: Task 1 vanilla
! python3 task_1.py {input_dataset} "deepseek-ai/deepseek-coder-6.7b-instruct" {task_1_vanilla_json} "True" |& tee task_1_vanilla.log

# %% Cell 6: Task 1 crafted
! python3 task_1.py {input_dataset} "deepseek-ai/deepseek-coder-6.7b-instruct" {task_1_crafted_json} "False" |& tee task_1_crafted.log

# %% Cell 7: Task 2 vanilla (also writes Coverage/{ID}_test_vanilla.json)
! python3 task_2.py {input_dataset} "deepseek-ai/deepseek-coder-6.7b-instruct" {task_2_vanilla_json} "True" |& tee task_2_vanilla.log

# %% Cell 8: Task 2 crafted (also writes Coverage/{ID}_test_crafted.json)
! python3 task_2.py {input_dataset} "deepseek-ai/deepseek-coder-6.7b-instruct" {task_2_crafted_json} "False" |& tee task_2_crafted.log

# %% Cell 9: coverage reports
# Commands to generate coverage reports
# task_2.py saves {ID}.py and {ID}_test.py under MP2/generated_tests/{vanilla,crafted}/ and runs, for every problem,
#   pytest {ID}_test.py --cov {ID} --cov-report json:MP2/Coverage/{ID}_test_{vanilla/crafted}.json
# e.g. to re-run one of them by hand:
# %cd generated_tests/crafted
# ! pytest HumanEval_60_test.py --cov HumanEval_60 --cov-report json:../../Coverage/HumanEval_60_test_crafted.json
# %cd ../..
! ls Coverage | wc -l

# %% Cell 10: tables for the progress report
! python3 analyze.py {seed} |& tee analysis.md

# %% Cell 11: push results to GitHub
# git push all nessacery files (e.g., *jsonl, *log) to your GitHub repository
%cd /content/CS598JBR-Team-16
token = ""  # TODO: paste a GitHub personal access token (do not commit it)
! git config --global user.email "rmotati2@illinois.edu" && git config --global user.name "Ram"
! git add MP2 && git commit -m "MP2 results"
! git push https://{token}@github.com/ramprakashreddy1/CS598JBR-Team-16.git main
