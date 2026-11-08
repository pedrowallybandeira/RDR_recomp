"""Lista instrucoes oris/addis com um imediato no .text do RDR2.elf. So leitura.

uso: find_oris.py <imediato_hex> [antes] [depois]
"""
import os
import struct
import sys

ROOT = os.environ.get("RDR_ROOT", os.getcwd())
sys.path.insert(0, os.path.join(ROOT, "referencias", "ps3recomp-v0.18.0", "tools"))
import ppu_disasm  # noqa: E402

d = open(os.path.join(ROOT, "build_rdr2", "baseline_v1", "entradas", "RDR2.elf"), "rb").read()
phoff = struct.unpack_from(">Q", d, 32)[0]
_, _, o, va, _, fs = struct.unpack_from(">IIQQQQ", d, phoff)
n = fs // 4
W = struct.unpack(">%dI" % n, d[o:o + n * 4])
alvo = int(sys.argv[1], 16)
antes = int(sys.argv[2]) if len(sys.argv) > 2 else 8
depois = int(sys.argv[3]) if len(sys.argv) > 3 else 8
for i, w in enumerate(W):
    op = w >> 26
    if (w & 0xFFFF) == alvo and op in (25, 15):
        print(f"== {va + i * 4:#x}")
        for k in range(max(0, i - antes), min(n, i + depois + 1)):
            ins = ppu_disasm.decode(W[k], va + k * 4)
            print(f"  {va + k * 4:#010x} {ins.mnemonic} {ins.operands}{' <==' if k == i else ''}")
