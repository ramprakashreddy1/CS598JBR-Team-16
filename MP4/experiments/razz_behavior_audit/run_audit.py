"""Compare original C and submitted Rust in independent subprocesses."""
from collections import Counter
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('mp4_root', nargs='?', type=Path, default=HERE.parents[1])
parser.add_argument('--rust-dir', type=Path, help='Alternative Rust candidate to audit')
parser.add_argument('--out-dir', type=Path, default=HERE/'evidence')
args = parser.parse_args()
ROOT = args.mp4_root.resolve()
env = os.environ.copy()
sdk = Path('/Library/Developer/CommandLineTools/SDKs/MacOSX15.2.sdk')
if sys.platform == 'darwin' and sdk.is_dir():
    env.setdefault('SDKROOT', str(sdk))
env['PATH'] = str(Path.home() / '.cargo/bin') + os.pathsep + env['PATH']
output = args.out_dir.resolve()
output.mkdir(parents=True, exist_ok=True)


def run(argv, cwd):
    result = subprocess.run(list(map(str, argv)), cwd=cwd, env=env,
                            text=True, capture_output=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f'{argv} exited {result.returncode}\n{result.stdout}\n{result.stderr}')
    return result


seeds = [0, 1, 3, 17, 42, 1234567, 4294967295, -17]
rng = random.Random(598)
cases = []
strings = ['', 'A', 'ace', '1', '10', '100', '0', 'J', 'j', 'Qx', 'K', '2', '9',
           'T', 'S10', '10suffix', '-1', 'S1', 'sA', 'H9', 'Ck', 'dQ']
strings += [s + r for s in 'SHDCshdcX' for r in 'A23456789TJQK1?']
cases.append(['parse', *strings])
for seed in seeds:
    for scenario in range(3):
        cases.append(['deck', str(seed), str(scenario)])
sequences = [[], list(range(52)), list(reversed(range(52))), [0]*10,
             [0, 13, 26, 39, 1, 14, 27, 40], [rng.randrange(52) for _ in range(80)]]
for cap in [0, 1, 3, 7, 52, 255]:
    for sorter in range(2):
        for mode in range(4):
            for cards in sequences:
                cases.append(['hand', str(cap), str(sorter), str(mode), *map(str, cards)])
for seed in seeds:
    for scenario in range(8):
        for rounds in [1, 5, 500]:
            cases.append(['simulate', str(seed), str(scenario), str(rounds)])

with tempfile.TemporaryDirectory(prefix='razz-c-rust-oracle-') as tmp:
    tmp = Path(tmp)
    rust = tmp / 'rust'
    candidate = args.rust_dir or ROOT / 'translations/project_2'
    hashes = {
        'c': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted((ROOT/'subjects/project_2').iterdir()) if p.suffix in ('.c', '.h')},
        'rust': {p.relative_to(candidate).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(Path(candidate).rglob('*.rs')) if 'target' not in p.relative_to(candidate).parts},
    }
    (output/'input_hashes.json').write_text(json.dumps(hashes, indent=2)+'\n')
    env['CARGO_TARGET_DIR'] = str(tmp/'target')
    shutil.copytree(candidate, rust,
                    ignore=shutil.ignore_patterns('target', '__pycache__', '.DS_Store'))
    hook = ROOT / 'experiments/razz_spec_check/seed_rng_harness_hook.diff'
    result = subprocess.run(['patch', '-s', str(rust/'src/card.rs')], input=hook.read_text(),
                            text=True, capture_output=True, env=env)
    if result.returncode:
        raise RuntimeError(result.stderr + result.stdout)
    shutil.copy2(HERE/'probe.rs', rust/'src/bin/behavior_probe.rs')
    c = tmp / 'c-probe'
    compile_c = run(['cc', '-O2', '-DNDEBUG', '-I', ROOT/'subjects/project_2',
                     HERE/'probe.c', '-o', c], tmp)
    (output/'compile_c.log').write_text(compile_c.stdout + compile_c.stderr)
    compile_rust = run(['cargo', '+nightly-2025-05-13', 'build', '--locked', '--bin', 'behavior_probe'], rust)
    (output/'compile_rust.log').write_text(compile_rust.stdout + compile_rust.stderr)
    binary = tmp/'target/debug/behavior_probe'
    counts = Counter()
    transcript = []
    mismatches = []
    for index, args in enumerate(cases):
        original = run([c, *args], tmp).stdout
        translated = run([binary, *args], rust).stdout
        matched = original == translated
        counts[args[0]] += 1
        transcript.append({'case': index, 'argv': args, 'matched': matched,
                           'c_sha256': hashlib.sha256(original.encode()).hexdigest(),
                           'rust_sha256': hashlib.sha256(translated.encode()).hexdigest()})
        if not matched:
            difference = ''.join(difflib.unified_diff(original.splitlines(True), translated.splitlines(True),
                                                    fromfile='C', tofile='Rust'))
            mismatches.append({'case': index, 'argv': args, 'diff': difference})
    summary = {'cases': len(cases), 'by_operation': dict(counts), 'matched': len(cases)-len(mismatches),
               'simulation_games': sum(int(c[3]) for c in cases if c[0]=='simulate'),
               'mismatches': mismatches, 'scope': 'Valid cards, seeded serial dealing, supported hand sorters, all iterator actions, valid decided-card arrays'}
    (output/'cases.json').write_text(json.dumps(transcript, indent=2)+'\n')
    (output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='mismatches'}, indent=2))
    print('Mismatching cases:', len(mismatches))
    for entry in mismatches[:2]:
        print('Case',entry['case'], entry['argv'][:5])
        print(entry['diff'])
    raise SystemExit(1 if mismatches else 0)
