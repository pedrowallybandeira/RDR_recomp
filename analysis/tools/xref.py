"""Acha referencias a uma string no ELF e mostra o codigo em volta. So leitura."""
import os
import struct
import sys

ROOT = os.environ.get("RDR_ROOT", os.getcwd())
sys.path.insert(0, os.path.join(ROOT, "referencias", "ps3recomp-v0.18.0", "tools"))
import ppu_disasm  # noqa: E402

d = open(os.path.join(ROOT, "build_rdr2", "baseline_v1", "entradas", "RDR2.elf"), "rb").read()
TOC = 0x13D1E30
shoff = struct.unpack_from(">Q", d, 40)[0]
_, _, _, addr, off, size = struct.unpack_from(">IIQQQQ", d, shoff + 2 * 64)
n = size // 4
W = struct.unpack(">%dI" % n, d[off:off + n * 4])
phoff = struct.unpack_from(">Q", d, 32)[0]
segs = []
for k in (0, 1):
    _, _, o, va, _, fs = struct.unpack_from(">IIQQQQ", d, phoff + k * 56)
    segs.append((va, o, fs))


def f2v(o):
    for va, so, fs in segs:
        if so <= o < so + fs:
            return va + o - so


def show(i, a=-46, b=22):
    for k in range(max(i + a, 0), min(i + b, n)):
        ins = ppu_disasm.decode(W[k], addr + k * 4)
        mark = " <==" if k == i else ""
        print(f"  {addr + k * 4:#010x} {W[k]:08X} {ins.mnemonic} {ins.operands}{mark}")


for s in sys.argv[1:]:
    o = d.find(s.encode())
    if o < 0:
        print("string nao achada:", s)
        continue
    v = f2v(o)
    print(f"== {s!r} em {v:#x}")
    achou = 0
    for i in range(n - 1):
        w = W[i]
        if (w >> 26) == 15 and ((w >> 16) & 0x1F) == 0:
            hi = (w & 0xFFFF) << 16
            rt = (w >> 21) & 0x1F
            for j in range(i + 1, min(i + 8, n)):
                b = W[j]
                if (b >> 26) in (12, 14) and ((b >> 16) & 0x1F) == rt:
                    lo = b & 0xFFFF
                    lo = lo - 0x10000 if lo & 0x8000 else lo
                    if (hi + lo) & 0xFFFFFFFF == v:
                        print(f"-- referencia lis+addi em {addr + j * 4:#x}")
                        show(j)
                        achou += 1
                    break
    if not achou:
        print("sem lis+addi; procurando no TOC")
        for va, so, fs in segs[1:]:
            for k in range(fs // 4):
                if struct.unpack_from(">I", d, so + k * 4)[0] == v:
                    print("  slot", hex(va + k * 4), "disp", hex(va + k * 4 - TOC))
