"""Resume a pilha dominante de cada thread: chamada HLE/syscall e as funcoes guest logo acima."""
import bisect, collections, os, re, sys
nmf = sys.argv[2]
base = 0x140000000
o = []
for l in open(nmf, encoding="utf-8", errors="ignore"):
    p = l.split()
    if len(p) >= 3 and p[1] in "tT":
        o.append((int(p[0], 16), p[2]))
o.sort()
ends = [a for a, _ in o]; nomes = [b for _, b in o]
def sym(r):
    i = bisect.bisect_right(ends, base + r) - 1
    return nomes[i] if i >= 0 else "?"
txt = open(sys.argv[1], encoding="utf-8", errors="replace").read()
grupos = collections.Counter()
for s in txt.split("\n=== thread ")[1:]:
    blocos = re.split(r"\n--- ", "\n" + s.split("\n", 1)[1])[1:]
    if not blocos:
        continue
    ls = blocos[0].strip().split("\n")
    fr = []
    for x in ls[1:]:
        m = re.match(r"\s*MyGameRecomp\+0x([0-9A-F]+)", x)
        fr.append(sym(int(m.group(1), 16)) if m else None)
    fr = [f for f in fr if f]
    fr = [re.sub(r"^_Z\d+|P11ppu_context$|^_ZL\d+", "", f) for f in fr]
    fr = [f for f in fr if "indirect_call" not in f]
    grupos[" < ".join(f[:30] for f in fr[:6])] += 1
for k, v in grupos.most_common(40):
    print(f"{v:3d}x {k}")
