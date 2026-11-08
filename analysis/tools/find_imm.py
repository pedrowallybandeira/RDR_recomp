"""Procura imediatos ligados ao fim de segmento do FIFO no PPU e nos jobs SPU. So leitura.

uso: find_imm.py <valor_hex> [<valor_hex> ...]
Testa addi/addic/cmpwi/li no PPU e il/ai no SPU, com o valor e seu negativo.
"""
import glob
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
vals = [int(x, 16) for x in sys.argv[1:]]
imm = set()
for v in vals:
    imm.add(v & 0xFFFF)
    imm.add((-v) & 0xFFFF)
for i, w in enumerate(W):
    if (w >> 26) in (11, 12, 13, 14, 7, 10, 24, 28) and (w & 0xFFFF) in imm:
        ins = ppu_disasm.decode(w, va + i * 4)
        print(f"PPU {va + i * 4:#010x} {ins.mnemonic} {ins.operands}")

# SPU: il (0x81 << 23 com I16 em 7..22) e ai (0x1C << 24 com I10), nos jobs capturados
for caminho in sorted(glob.glob(os.path.join(ROOT, "build_rdr2", "spu_dumps", "*.bin"))):
    b = open(caminho, "rb").read()
    for a in range(0, len(b) - 3, 4):
        w = struct.unpack_from(">I", b, a)[0]
        if (w >> 23) in (0x81, 0x83, 0x82):
            i16 = (w >> 7) & 0xFFFF
            if i16 in imm:
                print(f"SPU {os.path.basename(caminho)[7:23]} {a:#07x} op={w >> 23:#x} i16={i16:#x} rt={w & 127}")
