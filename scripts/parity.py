#!/usr/bin/env python3
"""Differential test against the C++ reference.

For every TPDE filetest whose RUN line only invokes `tpde_test` (the parser and
analyzer tests), run that command with the C++ `tpde_test` and with ours, and
require identical stdout and exit status. Codegen tests (RUN lines that pipe an
object into objdump) are compared by `--codegen` once codegen exists.

usage: scripts/parity.py [--ours build/tpde-test] [--ref ref/build/tpde/tpde_test]
                         [--tests DIR]... [-v]
"""
import argparse
import os
import re
import shlex
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPDE = os.path.expanduser("~/Documents/Code/open-source/tpde")
DEFAULT_DIRS = [
    os.path.join(TPDE, "tpde/test/filetest/analyzer"),
    os.path.join(TPDE, "tpde/test/filetest/tir"),
    os.path.join(ROOT, "tests/tir"),
]


def run_lines(path):
    out = []
    with open(path) as f:
        for line in f:
            m = re.match(r"\s*;\s*RUN:\s*(.*)$", line)
            if m:
                out.append(m.group(1).strip())
    return out


def analyzer_args(run, path):
    """The tpde_test argv of a RUN line, or None if it does more than that."""
    cmd = run.split("|")[0].strip()
    expect_fail = False
    if cmd.startswith("not "):
        expect_fail = True
        cmd = cmd[4:].strip()
    words = shlex.split(cmd)
    if not words or words[0] not in ("%tpde_test", "tpde_test"):
        return None
    args = [path if w == "%s" else w for w in words[1:]]
    if not any(a.startswith("--run-until=") and a != "--run-until=full" for a in args) \
            and "--print-ir" not in args:
        return None  # codegen
    return args, expect_fail


def run(binary, args):
    p = subprocess.run([binary] + args, capture_output=True)
    return p.returncode, p.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ours", default=os.path.join(ROOT, "build/tpde-test"))
    ap.add_argument("--ref", default=os.path.join(ROOT, "ref/build/tpde/tpde_test"))
    ap.add_argument("--tests", action="append")
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--fuzz", type=int, default=0,
                    help="also compare N random programs from gen_tir.py")
    o = ap.parse_args()

    dirs = o.tests or DEFAULT_DIRS
    files = []
    for d in dirs:
        if os.path.isdir(d):
            files += sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith(".tir"))

    passed = failed = skipped = 0
    for path in files:
        rel = os.path.relpath(path, TPDE) if path.startswith(TPDE) else os.path.relpath(path, ROOT)
        cases = [c for c in (analyzer_args(r, path) for r in run_lines(path)) if c]
        if not cases:
            skipped += 1
            continue
        for args, expect_fail in cases:
            rc_ref, out_ref = run(o.ref, args)
            rc_ours, out_ours = run(o.ours, args)
            same_status = (rc_ref == 0) == (rc_ours == 0)
            # a failing run's output is the reference's timestamped log; only
            # the status is compared
            if same_status and (rc_ref != 0 or out_ref == out_ours):
                passed += 1
                if o.verbose:
                    print(f"PASS {rel} {' '.join(a for a in args if a != path)}")
            else:
                failed += 1
                print(f"FAIL {rel} {' '.join(a for a in args if a != path)}")
                print(f"  exit: ref {rc_ref}, ours {rc_ours}")
                if out_ref != out_ours:
                    ref_lines = out_ref.decode(errors="replace").splitlines()
                    our_lines = out_ours.decode(errors="replace").splitlines()
                    for i in range(max(len(ref_lines), len(our_lines))):
                        a = ref_lines[i] if i < len(ref_lines) else "<eof>"
                        b = our_lines[i] if i < len(our_lines) else "<eof>"
                        if a != b:
                            print(f"  line {i + 1}:\n    ref:  {a}\n    ours: {b}")
                            break
    print(f"parity: {passed} passed, {failed} failed, {skipped} files without analyzer RUN lines")
    if o.fuzz:
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import gen_tir
        import tempfile
        fz_fail = 0
        flags = ["--run-until=analyzer", "--print-rpo", "--print-layout", "--print-loops", "--print-liveness"]
        with tempfile.TemporaryDirectory() as tmp:
            for seed in range(o.fuzz):
                blocks = [3, 6, 12, 30, 80][seed % 5]
                path = os.path.join(tmp, f"fuzz{seed}.tir")
                with open(path, "w") as f:
                    f.write(gen_tir.gen_random(seed, 10, blocks))
                ref = run(o.ref, flags + [path])
                ours = run(o.ours, flags + [path])
                if ref != ours:
                    fz_fail += 1
                    keep = os.path.join(ROOT, "build", f"fuzz-fail-{seed}.tir")
                    os.replace(path, keep)
                    print(f"FUZZ FAIL seed {seed} (exit ref {ref[0]}, ours {ours[0]}); kept {keep}")
        print(f"fuzz: {o.fuzz - fz_fail} passed, {fz_fail} failed")
        failed += fz_fail
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
