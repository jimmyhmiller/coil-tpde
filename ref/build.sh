#!/usr/bin/env bash
# Reproduce the TPDE reference-oracle build (macOS arm64).
set -euo pipefail

REF="$(cd "$(dirname "$0")" && pwd)"
TPDE_SRC="${TPDE_SRC:-/Users/jimmyhmiller/Documents/Code/open-source/tpde}"
LLVM="${LLVM:-/opt/homebrew/opt/llvm@21}"   # TPDE's primary supported LLVM is 21.1

# 1. Submodules (spdlog, args, fadec, disarm, doxygen-awesome-css)
git -C "$TPDE_SRC" submodule update --init

# 2. lit in a local venv (PyPI has no lit 21.x; 18.1.8 works fine)
if [ ! -x "$REF/venv/bin/lit" ]; then
  python3 -m venv "$REF/venv"
  "$REF/venv/bin/pip" install -q 'lit==18.1.8'
fi

# 3. Configure + build (Release + assertions; Debug would enable ASan by default)
cmake -S "$TPDE_SRC" -B "$REF/build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DTPDE_ENABLE_ASSERTIONS=ON \
  -DLLVM_DIR="$LLVM/lib/cmake/llvm" \
  -DLIT="$REF/venv/bin/lit"
ninja -C "$REF/build"

# 4. Tests
"$REF/venv/bin/lit" -sv "$REF/build/tpde/test/filetest"   # core TIR tests
"$REF/venv/bin/lit" -s  "$REF/build/tpde-llvm/test"       # tpde-llvm tests
