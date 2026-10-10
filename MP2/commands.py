###################################################################
# This is a list of all commands you need to run for MP2 on Colab.
###################################################################

# TODO: Clone your GitHub repository
! git clone https://github.com/ramprakashreddy1/CS598JBR-Team-16.git
%cd CS598JBR-Team-16/MP2

# TODO: Replace the file path of selected_humaneval_[seed].jsonl generated in MP1
input_dataset = "selected_humaneval_148118091928943694313340081131652963687.jsonl"

# Set up requirements for model prompting
! bash -x setup_models.sh

# TODO: add your seed generated in MP1
seed = "148118091928943694313340081131652963687"
task_1_vanilla_json = "task_1_" + seed + "_vanilla.jsonl"
task_1_crafted_json = "task_1_" + seed + "_crafted.jsonl"
task_2_vanilla_json = "task_2_" + seed + "_vanilla.jsonl"
task_2_crafted_json = "task_2_" + seed + "_crafted.jsonl"

# Prompt the models, you can modify `MP2/task_1.py, MP2/task_2.py`
# The {input_dataset} is the JSON file consisting of 20 unique programs for your group that you generated in MP1 (selected_humaneval_[seed].jsonl)
! python3 task_1.py {input_dataset} "deepseek-ai/deepseek-coder-6.7b-instruct" {task_1_vanilla_json} "True" |& tee task_1_vanilla.log
! python3 task_1.py {input_dataset} "deepseek-ai/deepseek-coder-6.7b-instruct" {task_1_crafted_json} "False" |& tee task_1_crafted.log
! python3 task_2.py {input_dataset} "deepseek-ai/deepseek-coder-6.7b-instruct" {task_2_vanilla_json} "True" |& tee task_2_vanilla.log
! python3 task_2.py {input_dataset} "deepseek-ai/deepseek-coder-6.7b-instruct" {task_2_crafted_json} "False" |& tee task_2_crafted.log

# Commands to generate coverage reports
# task_2.py saves {ID}.py and {ID}_test.py under MP2/generated_tests/{vanilla,crafted}/ and runs, for every problem,
#   pytest {ID}_test.py --cov {ID} --cov-report json:MP2/Coverage/{ID}_test_{vanilla/crafted}.json
# e.g. to re-run one of them by hand:
# %cd generated_tests/crafted
# ! pytest HumanEval_60_test.py --cov HumanEval_60 --cov-report json:../../Coverage/HumanEval_60_test_crafted.json
# %cd ../..

# Tables for the progress report
! python3 analyze.py {seed} |& tee analysis.md

%cd ..

# git push all nessacery files (e.g., *jsonl, *log) to your GitHub repository
# ! git config --global user.email "<your email>" && git config --global user.name "<your name>"
# ! git add MP2 && git commit -m "MP2 results" && git push https://<token>@github.com/ramprakashreddy1/CS598JBR-Team-16.git main
