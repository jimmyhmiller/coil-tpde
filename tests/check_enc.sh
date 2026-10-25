#!/bin/sh
# Encoder gate: every instruction tests/enc_a64.coil encodes must disassemble
# (llvm-mc) to the text written beside it.
set -e
cd "$(dirname "$0")/.."
MC="${LLVM_MC:-/opt/homebrew/opt/llvm/bin/llvm-mc}"
coil build tests/enc_a64.coil -o build/enc_a64 --quiet
build/enc_a64 > build/enc_a64.txt
fail=0
while IFS= read -r line; do
  bytes="${line%% ;*}"; want="${line#*; }"
  got=$(echo "$bytes" | "$MC" --disassemble -triple=aarch64 -mattr=+lse 2>&1 | grep -v '^\s*\.text' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*\/\/.*$//' | tr '\t' ' ' | head -1)
  if [ "$got" != "$want" ]; then echo "MISMATCH: want [$want] got [$got] ($bytes)"; fail=$((fail+1)); fi
done < build/enc_a64.txt
echo "encoder: $(wc -l < build/enc_a64.txt | tr -d ' ') checked, $fail mismatched"
[ "$fail" = 0 ]
