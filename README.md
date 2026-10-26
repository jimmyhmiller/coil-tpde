# coil-tpde

[TPDE](https://tpde.org) — a fast single-pass compiler back-end — ported to
[Coil](../coil), generic over the IR it compiles, and the Coil compiler's
`--backend tpde` (arm64 and x86-64, Mach-O).

TPDE is by Contributors to TPDE (Alexis Engelke, T0b1) and is licensed under
Apache-2.0 WITH LLVM-exception; so is this port. See [NOTICE](NOTICE) and
[LICENSE](LICENSE).

## Using it

The backend is part of the Coil compiler, which takes this package as a path
dependency. In `../coil`:

```sh
scripts/dev.py build candidate                    # build/bin/coil-candidate
build/bin/coil-candidate build hello.coil -o hello --backend tpde
build/bin/coil-candidate build hello.coil -o hello --backend tpde \
    --target x86_64-apple-macosx11.0.0            # x86-64, runs under Rosetta
build/bin/coil-candidate run hello.coil --backend tpde
build/bin/coil-candidate emit-obj hello.coil -o hello.o --backend tpde
```

As a JIT for your own IR (see `tpde.jit` in [docs/PLAN.md](docs/PLAN.md#jit)):

```coil
(match (jit/jit-load asm false (jit/no-resolver))   ; arm64; true for x86-64
  (Ok [image] (let [(mut img) image
                    f (primitive/cast (fnptr (cc/C) [i64] i64)
                                      (jit/jit-find (cast (ptr JitImage) (mut img)) asm "f"))]
                (call-ptr f 41)))
  (Err [msg] ...))
```

Coil's REPL can compile with it: `coil repl --backend tpde`.

Package tools, built with any Coil compiler from this directory:

```sh
coil build src/tools/tpde_test.coil  -o build/tpde-test   # TPDE's tpde_test CLI over TIR
coil build src/tools/tpde_check.coil -o build/tpde-check  # build/tpde-check all
coil build src/tools/tpde_bench.coil -o build/tpde-bench  # gates vs LLVM -O0
```

[docs/PLAN.md](docs/PLAN.md) has the design and decisions;
[docs/BENCH.md](docs/BENCH.md) the numbers.
