#!/usr/bin/env python3
"""Generate TIR programs for differential testing and benchmarking.

  gen_tir.py random --seed S [--funcs N] [--blocks B]   random CFGs: loops,
      irreducible regions, unreachable blocks, PHIs; SSA-valid (a value is used
      only in its own block, or comes from an argument or the entry block)
  gen_tir.py scale KIND N                                TPDE-style scaling inputs:
      many-values, many-blocks, loop-nest, many-funcs, switch
"""
import random
import sys


def random_func(rng, name, max_blocks):
    nargs = rng.randint(0, 4)
    args = [f"a{i}" for i in range(nargs)]
    nblocks = rng.randint(1, max_blocks)
    blocks = [f"b{i}" for i in range(nblocks)]
    lines = [f"{name}({', '.join('%' + a for a in args)}) {{"]
    # successors: never the entry; sometimes none (a return)
    succs = []
    for i in range(nblocks):
        r = rng.random()
        if nblocks == 1 or r < 0.15:
            succs.append([])
        else:
            k = rng.choice([1, 1, 2, 2, 2, 3, 5])
            succs.append([rng.randint(1, nblocks - 1) for _ in range(k)])
    preds = [[] for _ in range(nblocks)]
    for i, ss in enumerate(succs):
        for s in ss:
            if i not in preds[s]:
                preds[s].append(i)
    global_vals = list(args)
    local_out = {}  # block -> a value defined in it
    counter = [0]

    def fresh():
        counter[0] += 1
        return f"v{counter[0]}"

    body = []
    for i, b in enumerate(blocks):
        out = [f"{b}:"]
        local = []
        # phis, taking from global values or each pred's own value
        if i > 0 and preds[i] and rng.random() < 0.6:
            for _ in range(rng.randint(1, 3)):
                v = fresh()
                inc = []
                for p in preds[i]:
                    src = f"lv{p}" if rng.random() < 0.5 else (rng.choice(global_vals) if global_vals else f"lv{p}")
                    inc.append(f"[^{blocks[p]}, %{src}]")
                out.append(f"  %{v} = phi {', '.join(inc)}")
                local.append(v)
        # every block defines lv<i> so PHIs in successors can name it
        ops = local + (global_vals if True else [])
        uses = rng.sample(ops, min(len(ops), rng.randint(0, 3))) if ops else []
        out.append(f"  %lv{i} = {', '.join('%' + u for u in uses)}".rstrip())
        local.append(f"lv{i}")
        for _ in range(rng.randint(0, 4)):
            v = fresh()
            pool = local + global_vals
            uses = rng.sample(pool, min(len(pool), rng.randint(0, 3)))
            if rng.random() < 0.15 and i == 0:
                out.append(f"  %{v} = alloca {rng.choice([1, 8, 16])}, {rng.choice([1, 8])}")
            else:
                out.append(f"  %{v} = {', '.join('%' + u for u in uses)}".rstrip())
                local.append(v)
        if i == 0:
            global_vals += [v for v in local]
        ss = succs[i]
        if not ss:
            out.append(rng.choice(["  terminate", f"  ret %{rng.choice(local)}"]))
        elif len(ss) == 1 and rng.random() < 0.5:
            out.append(f"  br ^{blocks[ss[0]]}")
        else:
            out.append(f"  jump {', '.join('^' + blocks[s] for s in ss)}")
        body += out
    lines += body
    lines.append("}")
    return "\n".join(lines)


def gen_random(seed, funcs, max_blocks):
    rng = random.Random(seed)
    return "\n\n".join(random_func(rng, f"f{i}", max_blocks) for i in range(funcs)) + "\n"


def gen_scale(kind, n):
    out = []
    if kind == "many-values":
        out.append("f(%a) {\nentry:")
        prev = "a"
        for i in range(n):
            out.append(f"  %v{i} = add %{prev}, %a")
            prev = f"v{i}"
        out.append(f"  ret %{prev}\n}}")
    elif kind == "many-blocks":
        out.append("f(%a) {")
        for i in range(n):
            out.append(f"b{i}:\n  %v{i} = add %a, %a")
            out.append(f"  condbr %v{i}, ^b{i + 1}, ^b{n}" if i + 1 < n else f"  br ^b{n}")
        out.append(f"b{n}:\n  ret %a\n}}")
    elif kind == "loop-nest":
        out.append("f(%a) {\nentry:\n  br ^h0")
        for i in range(n):
            out.append(f"h{i}:\n  %p{i} = phi [^{'entry' if i == 0 else f'h{i-1}'}, %a], [^l{i}, %q{i}]")
            out.append(f"  %q{i} = add %p{i}, %a")
            out.append(f"  condbr %q{i}, ^{'h' + str(i + 1) if i + 1 < n else 'inner'}, ^l{i}")
        out.append("inner:\n  %x = add %a, %a\n  br ^l" + str(n - 1))
        for i in reversed(range(n)):
            nxt = f"h{i}"
            out.append(f"l{i}:\n  condbr %a, ^{nxt}, ^{'l' + str(i - 1) if i > 0 else 'exit'}")
        out.append("exit:\n  ret %a\n}")
    elif kind == "many-funcs":
        for i in range(n):
            out.append(f"f{i}(%a, %b) {{\nentry:\n  %c = add %a, %b\n  %d = sub %c, %a\n  ret %d\n}}")
    elif kind == "switch":
        out.append("f(%a) {\nentry:\n  jump " + ", ".join(f"^c{i}" for i in range(n)) + ", ^exit")
        for i in range(n):
            out.append(f"c{i}:\n  %v{i} = add %a, %a\n  br ^exit")
        out.append("exit:\n  %r = phi " + ", ".join(f"[^c{i}, %v{i}]" for i in range(n)) + ", [^entry, %a]")
        out.append("  ret %r\n}")
    else:
        raise SystemExit(f"unknown kind {kind}")
    return "\n".join(out) + "\n"


def main():
    a = sys.argv[1:]
    if a and a[0] == "random":
        seed, funcs, blocks = 0, 20, 12
        i = 1
        while i < len(a):
            if a[i] == "--seed": seed = int(a[i + 1]); i += 2
            elif a[i] == "--funcs": funcs = int(a[i + 1]); i += 2
            elif a[i] == "--blocks": blocks = int(a[i + 1]); i += 2
            else: raise SystemExit(f"bad arg {a[i]}")
        sys.stdout.write(gen_random(seed, funcs, blocks))
    elif a and a[0] == "scale":
        sys.stdout.write(gen_scale(a[1], int(a[2])))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
