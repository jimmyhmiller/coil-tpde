# Scorecard

Host: Apple Silicon (arm64) macOS. Reference TPDE 9779acf built with LLVM
21.1.8, Release with assertions (`ref/README.md`). Coil numbers are for the
compiler built by `scripts/dev.py build candidate` in `../coil` (branch
`tpde-backend`), 2026-10-25.

All checks are Coil programs in `src/tools/`:

- `build/tpde-check all` — parser/analyzer parity, fuzzing, the codegen
  differential, the encoder check, TIR and CIR execution (package level).
- `build/tpde-bench compile-time|examples|runtime COIL …` — the Coil-level
  gates, run against a Coil compiler binary.

## Correctness gates

| Gate | Status | How |
|---|---|---|
| TIR parser parity | ✅ 7/7 TPDE `tir/` tests | `tpde-check parity` |
| Analyzer parity | ✅ 4/4 TPDE `analyzer/` tests, 500/500 random CFGs | `tpde-check parity --fuzz 500` |
| Encoder | ✅ 160/160 encodings disassemble (llvm-mc) to the expected text | `tpde-check enc` |
| Codegen differential | ✅ 9/10 aarch64 runs identical to C++ TPDE; `tbz.tir` differs only in veneer placement | `tpde-check codegen` |
| TIR execution | ✅ `tests/tir/exec1` | `tpde-check exec` |
| CIR builder (Braun SSA) | ✅ `tests/cir_test` | `tpde-check exec` |
| Coil corpus lane | ✅ 9/9 `tests/corpus` on the `tpde` lane | `scripts/oracle.py corpus tpde` |
| Coil examples | ✅ 45/45 `src/examples` print the same as LLVM -O0 (2 skipped: their LLVM build fails) | `tpde-bench examples` |
| Coil stdlib suites | ✅ 171/171 (parsers 13, serde 41, system 38, text 34, threads 7, traits 38) | `coil test tests/stdlib/…_test.coil --backend tpde` |
| C ABI | ✅ tpde, tpde program + LLVM lib, LLVM program + tpde lib | `scripts/tests/c-abi.py` |
| Self-host | ✅ the compiler built by tpde builds itself with tpde; stage2 and stage3 are identical but for LC_UUID and the code signature; stage2 passes the corpus on the tpde and llvm lanes | see below |

Self-host:

```
coil-candidate build src/compiler/main_a64.coil -o coil-selftpde --backend tpde
coil-selftpde  build src/compiler/main_a64.coil -o coil-stage2 --backend tpde
coil-stage2    build src/compiler/main_a64.coil -o coil-stage3 --backend tpde
```

## Compile time: backend vs LLVM -O0 (gate: ≥10×)

The Coil compiler (`src/compiler/main_a64.coil`, 16.5k functions, 594k CIR
instructions, 6.4 MB of text). `tpde-bench compile-time`, median of 7, the
`--timings` spans: tpde's `backend.tpde-object` (module setup, lowering,
compiling, merge, Mach-O writing) against LLVM's `backend.llvm-lower` +
`backend.llvm-optimize` + `backend.object-emit`.

| Backend | Median backend time | vs LLVM -O0 |
|---|---|---|
| LLVM -O0 | 1699 ms | 1× |
| naive arm64 (`--backend arm64`) | ~290 ms | 5.9× |
| **tpde (pipelined, default)** | **121 ms** | **14.0×** ✅ |
| tpde, one thread (`COIL_TPDE_SERIAL=1`) | ~165 ms | 10.3× |

Breakdown (serial, `COIL_TPDE_STATS=1`): lowering AST→CIR ~80 ms (of which the
promotion scan ~8 ms), compiling CIR→arm64 ~60 ms (analyzer ~17 ms), module
setup (codegen_a64's signatures, layouts, statics) ~10 ms, merge ~2.5 ms,
Mach-O writing ~5 ms. The pipeline overlaps lowering and compiling.

## Generated code speed vs LLVM -O0 (gate: ≤1.0×)

`tpde-bench runtime build/bin/coil-candidate src/benchmarks 5`, median wall time.

| Program | LLVM -O0 | tpde | tpde / LLVM |
|---|---|---|---|
| fib | 417 ms | 416 ms | 1.00 |
| float | 678 ms | 180 ms | 0.27 |
| genreduce | 271 ms | 214 ms | 0.79 |
| loop | 358 ms | 342 ms | 0.96 |
| memory | 61 ms | 53 ms | 0.87 |
| prop_bench | 8714 ms | 6610 ms | 0.76 |
| regex_literal | 26 ms | 20 ms | 0.77 |
| regex_nfa | 26 ms | 20 ms | 0.77 |
| structcall | 172 ms | 169 ms | 0.98 |
| tak | 4 ms | 4 ms | ≈1 |
| slicesum | crash (stack) | crash (stack) | same: a slice argument is not a guaranteed tail call |
| json_tape | needs an input file | | |

The largest program: the Coil compiler built by tpde compiles itself in
18.3–18.4 s; built by LLVM -O0, in 18.5–18.6 s.

Code size: 6.41 MB of text against LLVM -O0's 5.80 MB (1.11×; gate ≤1.3×).

## Port quality: ours vs C++ `tpde_test` (2026-10-24)

Median of 15 runs. "analysis" is the time the analyzer adds over parsing alone
(`--run-until=analyzer` minus `--run-until=ir`). Inputs from
`tpde-check gen scale …` (then `gen_tir.py`).

| Input | C++ parse | ours parse | C++ analysis | ours analysis |
|---|---|---|---|---|
| many-values 200000 | 53.6 ms | 69.1 ms | 3.3 ms | 2.3 ms |
| many-blocks 50000 | 27.1 ms | 35.6 ms | 3.2 ms | 4.2 ms |
| many-funcs 50000 | 29.8 ms | 34.5 ms | 5.5 ms | 3.4 ms |
| loop-nest 2000 | 3.9 ms | 4.8 ms | 14.0 ms | 12.0 ms |
| switch 20000 | 10.7 ms | 14.9 ms | 2.1 ms | 1.6 ms |
| random (5000 funcs × ≤40 blocks) | 92.1 ms | 101.1 ms | 20.8 ms | 20.4 ms |

Analysis is at parity with C++ (0.7–1.3×); the gate is ≤2×. `loop-nest` is
super-linear in both implementations; that is TPDE's lowest-common-loop walk
(`Analyzer.hpp`, noted O(n²) worst case in a TODO there).

## History

- 2026-10-24 baseline: LLVM -O0 1747 ms; first working tpde backend 249 ms (7×).
- 2026-10-25: 165 ms serial (quadratic string interning, per-function table
  clears, lazy promotion scan, memoized lookups, shared small constants), then
  121 ms with the lowering/compiling pipeline. Run time brought under -O0 by
  four register-allocation changes (see PLAN.md, "Where we differ from TPDE").
