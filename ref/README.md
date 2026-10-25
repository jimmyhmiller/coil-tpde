# TPDE reference oracle build

Source: `/Users/jimmyhmiller/Documents/Code/open-source/tpde` (commit 9779acf), submodules initialized, no tracked files modified.
LLVM: Homebrew `llvm@21` (21.1.8). TPDE lists 21.1 as its "primary" version, meaning every test passes without XFAILs.
Host compiler: Apple clang (default). lit: 18.1.8 from PyPI, installed in `ref/venv`. PyPI has no 21.x release. FileCheck, not and llvm-objdump come from llvm@21 and are picked up automatically through `LLVM_TOOLS_BINARY_DIR`.

## Build

`./build.sh` reproduces everything. It runs these commands:

```sh
git -C /Users/jimmyhmiller/Documents/Code/open-source/tpde submodule update --init
python3 -m venv venv && venv/bin/pip install 'lit==18.1.8'
cmake -S /Users/jimmyhmiller/Documents/Code/open-source/tpde -B build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DTPDE_ENABLE_ASSERTIONS=ON \
  -DLLVM_DIR=/opt/homebrew/opt/llvm@21/lib/cmake/llvm -DLIT=$PWD/venv/bin/lit
ninja -C build
```

## Binaries (under `ref/build/`)

- `tpde/tpde_test`: the TIR test driver. It only links libc++ and libSystem, not LLVM.
- `tpde-llvm/tpde-llc`: compiles LLVM IR (.ll/.bc) to an ELF object.
- `tpde-llvm/tpde-lli`: a JIT runner.
- `tpde-encodegen/tpde_encodegen`

## tpde_test CLI (source: tpde/src/test/test_main.cpp)

```
tpde_test [options] [ir_path]        # reads stdin if no path is given
  --target=/--arch= x64|x86_64|a64|aarch64   (default x64)
  -o, --obj-out=PATH     write the ELF object here (default, or "-": stdout)
  --run-until=ir|analyzer|full   (default full)
  --print-ir             print the parsed TIR and exit
  --print-rpo / --print-layout / --print-loops / --print-liveness
                         analyzer dumps; they only take effect with --run-until=analyzer
  --no-fixed-assignments  (the codegen tests use this)
  -l, --log-level=N       0 none .. 5+ trace (only if built with TPDE_LOGGING)
```

Examples:

```sh
T=/Users/jimmyhmiller/Documents/Code/open-source/tpde/tpde/test/filetest
build/tpde/tpde_test --run-until=analyzer --print-rpo --print-layout --print-loops --print-liveness $T/analyzer/condbr.tir
build/tpde/tpde_test --target=aarch64 -o out.o $T/codegen/add.tir
build/tpde/tpde_test --target=x86_64 --no-fixed-assignments $T/codegen/add.tir \
  | /opt/homebrew/opt/llvm@21/bin/llvm-objdump -d -r --no-show-raw-insn --symbolize-operands --no-addresses --x86-asm-syntax=intel -
```

## tpde-llc

```sh
build/tpde-llvm/tpde-llc --target=aarch64-unknown-linux-gnu -o add.a64.o sanity/add.ll
build/tpde-llvm/tpde-llc --target=x86_64-unknown-linux-gnu  -o add.x64.o sanity/add.ll
```

Both commands produce valid ELF relocatables. `sanity/` holds the test input and the outputs. The assertions build compiles each input twice by default and compares the two outputs (`--compile-twice`).

## Tests

```sh
venv/bin/lit -sv build/tpde/test/filetest   # core: 22/22 passed (analyzer 4, codegen 11, tir 7)
venv/bin/lit -s  build/tpde-llvm/test       # 238 passed, 13 unsupported, 1 XFAIL, 0 failed
```

`ninja -C build check-tpde` runs both suites.

## Problems / notes

- PyPI has no lit 21, so lit 18.1.8 is used. It works without problems.
- When linking you may see `ld: warning: search path '.../mamba/target/debug/' not found`. This comes from a `LIBRARY_PATH` setting in the shell environment and does no harm.
- macOS ld lacks `--gc-sections`, so CMake skips that flag automatically.
