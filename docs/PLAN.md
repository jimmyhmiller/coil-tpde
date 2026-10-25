# coil-tpde plan

A port of [TPDE](https://github.com/tpde2/tpde) (`~/Documents/Code/open-source/tpde`)
to Coil: a fast, single-pass, -O0-quality compiler back-end that is generic over
the IR it compiles, and then the backend for the Coil compiler itself
(`coil build --backend tpde`).

## Decisions (2026-10-24)

| Question | Decision |
|---|---|
| Who owns encoders and object writers? | **Do what TPDE does.** The package owns its assembler/object writers (TPDE's `AssemblerElf`; we add Mach-O) and its instruction encoders live in their own namespaces, the way TPDE uses fadec/disarm as separate libraries. The package never depends on Coil compiler internals. No encodegen: instruction selection is hand-written, as TPDE's own TIR compilers do. |
| What is the performance bar? | **LLVM -O0**, on both compile time and the speed of the generated code (`coil build -O0`, which runs LLVM's `default<O0>`). |
| How does Coil's tree become SSA? | **Braun et al.**, "Simple and Efficient Construction of SSA Form" (CC 2013), done on the fly while lowering the expression tree. Locals whose address is never taken become SSA values; address-taken ones become static allocas. |

## Architecture

TPDE's layering, with C++ templates/CRTP replaced by Coil traits plus
monomorphization (same zero-cost specialization):

```
IR adaptor (trait)          ← TIR (test IR), Coil SSA, any other IR
  │
Analyzer                    RPO, loop tree, block layout, liveness
  │
CompilerBase                value assignments, register file, spilling,
  │                         PHI moves, calling-convention plumbing
Arch compiler (trait)       arm64 (AAPCS64 / Apple), x86-64 (SysV)
  │
Assembler                   sections, symbols, relocations, labels/fixups
  └─ object writers         Mach-O (first), ELF; in-memory JIT mapping
```

- `IRAdaptor.hpp` → a Coil `deftrait` with dense per-function value indices,
  block successors/instructions/phis, and two per-block scratch slots.
- The compiler core is generic over the adaptor; arch-specific hooks are a second
  trait (the C++ `derived()->…` calls).
- **TIR**, TPDE's toy text IR (`tpde/src/test/`), is ported first. It is the
  first adaptor, lets the core be tested and benchmarked without Coil's
  frontend, and lets us diff our output against the C++ reference on identical
  inputs.

## Using it in Coil

1. A lowering from Coil's monomorphized expression tree (`ast.coil` `Expr`) to a
   small SSA IR using Braun's algorithm, plus the adaptor for that IR.
2. `--backend tpde` in the driver's backend dispatch (`driver.coil`).
3. Apple arm64 ABI first (host): stack-only varargs, naturally packed stack args,
   caller-extended small ints, x18 reserved, `char*` `va_list`. Then x86-64 ELF.
4. `llvm-ir` bodies: reuse the subset the arm64 backend already lowers.
5. **Guaranteed tail calls.** Coil emits calls in tail position with scalar or
   pointer signatures as `musttail` even at -O0, and programs rely on it (the
   `memory` and `structcall` benchmarks recurse ~200M deep). TPDE has no tail
   calls, so this is new work in the call lowering (`codegen.coil`
   `tail-call-ok` defines which calls qualify).

## Port notes

- Adaptor handles are `u32` (TPDE allows any 8-byte handle). Ranges are a count
  plus an indexed accessor.
- A `println` written directly in a loop body grows the stack each iteration
  (Coil bug, filed in the `coil-bugs` pad), so printing code calls a function
  per line.

## How we know we're done

### Correctness gates

| Gate | Passes when |
|---|---|
| Analyzer parity | TPDE's `tpde/test/filetest/analyzer/*.tir` produce identical RPO / layout / loop / liveness dumps |
| Codegen differential | Same TIR through C++ TPDE and through ours gives the same instruction sequence (modulo relocations and object format) |
| TIR execution | TIR programs run in-process (JIT) with expected results |
| Coil corpus | a `tpde` lane in `scripts/oracle.py` matches the LLVM reference on all of `tests/corpus` |
| C ABI | `scripts/tests/c-abi.py` passes with `--backend tpde` |
| Self-host | the Coil compiler built with `--backend tpde` passes `dev.py test fast` |

### Performance gates (vs LLVM -O0)

| Metric | Measured with | Target |
|---|---|---|
| Backend compile time | `--timings` / `COIL_TRACE` spans: LLVM's `llvm-lower`+`llvm-optimize`+`object-emit` vs ours | ≥10× faster (TPDE's claim is 10–20×) |
| Generated code speed | `dev.py benchmark runtime` built `-O0` vs `--backend tpde` | ≤1.0× LLVM -O0 runtime (Braun SSA should beat -O0) |
| Code size | text section size | ≤1.3× LLVM -O0 |
| Scaling | TPDE's `tpde-llvm/test/benchmark` generators (many-values, switch, irreducible loops, many-funcs, call-chain) rewritten for TIR / Coil | linear |
| Port quality | our TIR compile vs C++ `tpde_test` on the same large inputs | within 2× of C++ throughput |

Numbers live in [BENCH.md](BENCH.md): baseline, target and current value for
each row.

## Milestones

- **M0** Baselines: C++ TPDE reference built (`ref/`), LLVM -O0 numbers recorded, bench harness.
- **M1** Generic core: adaptor trait, TIR parser, Analyzer; analyzer parity gate green.
- **M2** arm64 codegen over TIR: register file, value assignments, CompilerBase,
  CompilerA64, Mach-O writer, Apple ABI; JIT execution tests and the C++ differential.
- **M3** Coil: tree → SSA (Braun) lowering, adaptor, `--backend tpde`; corpus lane green.
- **M4** Performance gates and self-host.
- **M5** x86-64 ELF.
