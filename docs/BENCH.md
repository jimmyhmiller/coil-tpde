# Scorecard

Host: Apple Silicon (arm64) macOS, coil 0.1.0 (ffb39bda2e77). Reference TPDE
9779acf built with LLVM 21.1.8, Release with assertions (`ref/README.md`).

## Correctness gates

| Gate | Status | How |
|---|---|---|
| TIR parser parity | ✅ 7/7 TPDE `tir/` tests | `scripts/parity.py` |
| Analyzer parity | ✅ 4/4 TPDE `analyzer/` tests, 500/500 random CFGs, 6/6 scale inputs | `scripts/parity.py --fuzz 500` |
| Codegen differential | not started (M2) | |
| TIR execution | not started (M2) | |
| Coil corpus lane | not started (M3) | |
| C ABI | not started (M3) | |
| Self-host | not started (M4) | |

## Port quality: ours vs C++ `tpde_test` (2026-10-24)

Median of 15 runs. "analysis" is the time the analyzer adds over parsing alone
(`--run-until=analyzer` minus `--run-until=ir`).

| Input (`gen_tir.py scale …`) | C++ parse | ours parse | C++ analysis | ours analysis |
|---|---|---|---|---|
| many-values 200000 | 53.6 ms | 69.1 ms | 3.3 ms | 2.3 ms |
| many-blocks 50000 | 27.1 ms | 35.6 ms | 3.2 ms | 4.2 ms |
| many-funcs 50000 | 29.8 ms | 34.5 ms | 5.5 ms | 3.4 ms |
| loop-nest 2000 | 3.9 ms | 4.8 ms | 14.0 ms | 12.0 ms |
| switch 20000 | 10.7 ms | 14.9 ms | 2.1 ms | 1.6 ms |
| random (5000 funcs × ≤40 blocks) | 92.1 ms | 101.1 ms | 20.8 ms | 20.4 ms |

Analysis is at parity with C++ (0.7–1.3×); the gate is ≤2×. The TIR parser is
1.1–1.4× slower than C++, but it is a test front end, not part of Coil's path.
`loop-nest` is super-linear in both implementations; that is TPDE's
lowest-common-loop walk (`Analyzer.hpp`, noted O(n²) worst case in a TODO there).

## Baseline: LLVM -O0 (M0, 2026-10-24)

### Backend compile time, the Coil compiler (`src/compiler/main_a64.coil`)

`coil build … --timings`, one run each.

| Backend | Backend spans | Total wall | Max RSS |
|---|---|---|---|
| LLVM -O0 | 1747 ms (lower 269 + optimize 62 + object-emit 1416) | 4.60 s | 2.33 GB |
| naive arm64 (`--backend arm64`, DWARF on) | 328 ms | 2.97 s | 2.31 GB |
| **tpde target (≥10× vs -O0)** | **≤ 175 ms** | | |

### Generated code speed, `coil/src/benchmarks` (hyperfine median of 5)

| Program | LLVM -O0 | naive arm64 | LLVM -O3 | tpde target (≤ -O0) |
|---|---|---|---|---|
| fib | 435.0 ms | 786.7 ms | 290.6 ms | ≤ 435 ms |
| tak | 4.5 ms | 6.8 ms | 3.8 ms | ≤ 4.5 ms |
| loop | 373.1 ms | 1231.3 ms | 295.2 ms | ≤ 373 ms |
| float | 734.7 ms | 1162.3 ms | 187.6 ms | ≤ 735 ms |
| genreduce | 280.6 ms | 735.8 ms | 95.7 ms | ≤ 281 ms |
| memory | ✓ | crash (no tail calls) | ✓ | |
| structcall | ✓ | crash (no tail calls) | ✓ | |
| slicesum | crash (stack) | ✓ | ✓ | |

`memory` and `structcall` recurse ~200M deep through calls Coil guarantees to be
tail calls (scalar/pointer signatures are emitted `musttail` even at -O0), so a
backend without tail calls overflows the stack. `slicesum` passes a slice, which
is not a guaranteed tail call, so it needs LLVM's optimizer. **tpde must
implement Coil's guaranteed tail calls**; TPDE itself has none.
