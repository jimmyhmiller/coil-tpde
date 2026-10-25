#!/bin/sh
/opt/homebrew/opt/llvm/bin/llvm-objdump -d --no-show-raw-insn --symbolize-operands --no-addresses "$1" | grep -v "file format\|Disassembly of" | grep -v -E '^[[:space:]]*\.\.\.[[:space:]]*$|udf[[:space:]]+#0x0|^$' | sed -e 's/^<_/</' -e 's/[[:space:]]*\/\/.*$//' -e 's/<_/</g'
