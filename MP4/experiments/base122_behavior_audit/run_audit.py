"""Compare independent C and Rust codec executables without changing the crate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out-dir', type=Path, default=HERE / 'evidence')
args = parser.parse_args()
out = args.out_dir.resolve()
out.mkdir(parents=True, exist_ok=True)
env = os.environ.copy()
env['PATH'] = str(Path.home() / '.cargo/bin') + os.pathsep + env['PATH']
sdk = Path('/Library/Developer/CommandLineTools/SDKs/MacOSX15.2.sdk')
if sdk.is_dir():
    env.setdefault('SDKROOT', str(sdk))
rng = random.Random(598)
samples = [b''] + [bytes([n]) for n in range(256)]
samples += [n.to_bytes(2, 'big') for n in range(65536)]
samples += [bytes(rng.randrange(256) for _ in range(rng.randrange(3, 1025))) for _ in range(1000)]
samples += [bytes([value]) * length for value in (0, 10, 13, 34, 38, 92, 127, 128, 255)
            for length in (3, 7, 8, 9, 63, 64, 65, 1024)]
cases = [(op, sample) for op in ('e', 'd') for sample in samples]
payload = ''.join(op + ' ' + sample.hex() + '\n' for op, sample in cases)
hashes = {}
for label, source in [('c', ROOT / 'subjects/project_1/src'), ('rust', ROOT / 'translations/project_1/src')]:
    hashes[label] = {p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(source.rglob('*')) if p.is_file() and p.suffix in ('.c', '.h', '.rs')}
(out / 'input_hashes.json').write_text(json.dumps(hashes, indent=2) + '\n')

def run(command, cwd, data=None):
    result = subprocess.run(list(map(str, command)), cwd=cwd, env=env, input=data,
                            text=True, capture_output=True, timeout=180)
    if result.returncode:
        raise RuntimeError(f'{command}: {result.returncode}\n{result.stdout[-2000:]}\n{result.stderr}')
    return result

with tempfile.TemporaryDirectory(prefix='base122-readiness-') as temporary:
    work = Path(temporary)
    rust = work / 'rust'
    shutil.copytree(ROOT / 'translations/project_1', rust, ignore=shutil.ignore_patterns('target'))
    shutil.copy2(HERE / 'probe.rs', rust / 'src/bin/behavior_probe.rs')
    env['CARGO_TARGET_DIR'] = str(work / 'target')
    c_sources = ROOT / 'subjects/project_1/src'
    result = run(['cc', '-O2', '-I', c_sources, HERE / 'probe.c', c_sources / 'base122.c', '-o', work / 'c-probe'], work)
    (out / 'compile_c.log').write_text(result.stdout + result.stderr)
    result = run(['cargo', '+nightly-2025-05-13', 'build', '--locked', '--bin', 'behavior_probe'], rust)
    (out / 'compile_rust.log').write_text(result.stdout + result.stderr)
    c_output = run([work / 'c-probe'], work, payload).stdout
    rust_output = run([work / 'target/debug/behavior_probe'], rust, payload).stdout
    c_lines, rust_lines = c_output.splitlines(), rust_output.splitlines()
    assert len(c_lines) == len(rust_lines) == len(cases)
    mismatches = [{'case': i, 'operation': op, 'input': sample.hex(), 'c': c_lines[i], 'rust': rust_lines[i]}
                  for i, (op, sample) in enumerate(cases) if c_lines[i] != rust_lines[i]]
    summary = {'cases': len(cases), 'encode_cases': len(samples), 'decode_cases': len(samples),
               'matched': len(cases) - len(mismatches), 'mismatch_count': len(mismatches),
               'c_output_sha256': hashlib.sha256(c_output.encode()).hexdigest(),
               'rust_output_sha256': hashlib.sha256(rust_output.encode()).hexdigest(),
               'scope': 'encode/decode bytes and exact error messages; every zero-, one-, and two-byte input; seeded longer inputs; every successful encode round-tripped in Rust'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (out / 'mismatches.json').write_text(json.dumps(mismatches, indent=2) + '\n')
    print(json.dumps(summary, indent=2))
    raise SystemExit(bool(mismatches))
