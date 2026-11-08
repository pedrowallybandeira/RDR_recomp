"""Desmonta faixas do .text do RDR2.elf e resolve strings carregadas com lis+addi. So leitura.

uso: ppu_view.py <ini>-<fim> [<ini>-<fim> ...]
"""
import os
import struct
import sys

ROOT = os.environ.get("RDR_ROOT", os.getcwd())
sys.path.insert(0, os.path.join(ROOT, "referencias", "ps3recomp-v0.18.0", "tools"))
import ppu_disasm  # noqa: E402

d = open(os.path.join(ROOT, "build_rdr2", "baseline_v1", "entradas", "RDR2.elf"), "rb").read()
phoff = struct.unpack_from(">Q", d, 32)[0]
segs = []
for k in range(struct.unpack_from(">H", d, 56)[0]):
    t, _, o, va, _, fs = struct.unpack_from(">IIQQQQ", d, phoff + k * 56)
    if t == 1:
        segs.append((va, o, fs))


def v2f(v):
    for va, so, fs in segs:
        if va <= v < va + fs:
            return so + v - va


def texto(v):
    o = v2f(v)
    if o is None:
        return None
    fim = d.find(b"\0", o, o + 120)
    s = d[o:fim]
    if len(s) >= 4 and all(0x20 <= c < 0x7F for c in s):
        return s.decode("latin-1")


for faixa in sys.argv[1:]:
    ini, fim = (int(x, 16) for x in faixa.split("-"))
    print(f"== {ini:#x}-{fim:#x}")
    his = {}
    for a in range(ini, fim, 4):
        w = struct.unpack_from(">I", d, v2f(a))[0]
        i = ppu_disasm.decode(w, a)
        nota = ""
        op = w >> 26
        rt, ra = (w >> 21) & 31, (w >> 16) & 31
        if op == 15 and ra == 0:
            his[rt] = (w & 0xFFFF) << 16
        elif op in (12, 14) and ra in his:
            lo = w & 0xFFFF
            lo = lo - 0x10000 if lo & 0x8000 else lo
            s = texto((his[ra] + lo) & 0xFFFFFFFF)
            if s:
                nota = f'  ; "{s}"'
        print(f"  {a:#010x} {i.mnemonic} {i.operands}{nota}")
