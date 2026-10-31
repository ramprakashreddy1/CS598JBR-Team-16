###################################################################
# This is a list of all commands you need to run for MP3 on Colab.
###################################################################

# Clone the team repository in a fresh Colab runtime.
! git clone https://github.com/ramprakashreddy1/CS598JBR-Team-16.git
%cd CS598JBR-Team-16/MP3

# Seed generated in MP1.
seed = "148118091928943694313340081131652963687"

humaneval_input_dataset = "selected_humaneval_" + seed + ".jsonl"
humaneval_source_dataset = "../MP1/" + humaneval_input_dataset

# MP3/validate.py requires the original selected dataset inside MP3 as well.
! cp {humaneval_source_dataset} {humaneval_input_dataset}

# Set up requirements for dataset generation
! bash -x setup_dataset.sh

# Set up requirements for model prompting
! bash -x setup_models.sh

# Task 1 compiles and runs generated Java programs. Colab normally includes a JDK.
! javac -version
! java -version

# Task 1

# The {humaneval_input_dataset} is the JSON file consisting of 20 unique programs for your group that you generated in MP1 (selected_humaneval_[seed].jsonl)
! python3 humanevalx_dataset_generation.py {humaneval_input_dataset} |& tee humanevalx_dataset_generation.log

input_python_dataset = "selected_humanevalx_python_" + seed + ".jsonl"
input_java_dataset = "selected_humanevalx_java_" + seed + ".jsonl"

task_1_vanilla_jsonl = "task_1_" + seed + "_vanilla.jsonl"
task_1_crafted_jsonl = "task_1_" + seed + "_crafted.jsonl"

! python3 task_1.py {input_python_dataset} "deepseek-ai/deepseek-coder-6.7b-instruct" {task_1_vanilla_jsonl} "True" |& tee task_1_vanilla.log
! python3 task_1.py {input_python_dataset} "deepseek-ai/deepseek-coder-6.7b-instruct" {task_1_crafted_jsonl} "False" |& tee task_1_crafted.log

# Task 2
humaneval_input_dataset = "selected_humaneval_" + seed + ".jsonl"

# The {humaneval_input_dataset} is the JSON file consisting of 20 unique programs for your group that you generated in MP1 (selected_humaneval_[seed].jsonl)
! python3 humanevalpack_dataset_generation.py {humaneval_input_dataset} |& tee humanevalpack_dataset_generation.log

task_2_vanilla_jsonl = "task_2_" + seed + "_vanilla.jsonl"
task_2_crafted_jsonl = "task_2_" + seed + "_crafted.jsonl"
humanevalpack_input_dataset = "selected_humanevalpack_" + seed + ".jsonl"

! python3 task_2.py {humanevalpack_input_dataset} "deepseek-ai/deepseek-coder-6.7b-instruct" {task_2_vanilla_jsonl} "True" |& tee task_2_vanilla.log
! python3 task_2.py {humanevalpack_input_dataset} "deepseek-ai/deepseek-coder-6.7b-instruct" {task_2_crafted_jsonl} "False" |& tee task_2_crafted.log

# Generate pairwise tables and success-rate calculations for the progress report.
! python3 analyze.py {seed} analysis.md |& tee analysis.log

%cd ..

# git push all nessacery files (e.g., *jsonl, *log) to your GitHub repository
