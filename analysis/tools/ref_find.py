"""Acha referencias a enderecos: lis+addi/addic/ori no .text e ponteiros nos dados. So leitura.

uso: ref_find.py <addr> [<addr> ...]
"""
import os
import struct
import sys

ROOT = os.environ.get("RDR_ROOT", os.getcwd())
d = open(os.path.join(ROOT, "build_rdr2", "baseline_v1", "entradas", "RDR2.elf"), "rb").read()
phoff = struct.unpack_from(">Q", d, 32)[0]
segs = []
for k in range(struct.unpack_from(">H", d, 56)[0]):
    t, fl, o, va, _, fs = struct.unpack_from(">IIQQQQ", d, phoff + k * 56)
    if t == 1:
        segs.append((va, o, fs, fl))
tva, tof, tfs, _ = segs[0]
n = tfs // 4
W = struct.unpack(">%dI" % n, d[tof:tof + n * 4])

for arg in sys.argv[1:]:
    alvo = int(arg, 16)
    print(f"== {alvo:#x}")
    for i in range(n):
        w = W[i]
        if (w >> 26) != 15 or ((w >> 16) & 31):
            continue
        rt = (w >> 21) & 31
        hi = (w & 0xFFFF) << 16
        for j in range(i + 1, min(i + 12, n)):
            b = W[j]
            if (b >> 26) in (12, 13, 14) and ((b >> 16) & 31) == rt:
                lo = b & 0xFFFF
                lo = lo - 0x10000 if lo & 0x8000 else lo
                if (hi + lo) & 0xFFFFFFFF == alvo:
                    print(f"  codigo {tva + j * 4:#x}")
                    break
    p = struct.pack(">I", alvo)
    for va, so, fs, fl in segs:
        o = d.find(p, so, so + fs)
        while o >= 0:
            if o % 4 == 0:
                print(f"  ponteiro em {va + o - so:#x}")
            o = d.find(p, o + 1, so + fs)
