"""Acha lwz/stw com lis+deslocamento para um global. So leitura.

uso: disp_find.py <addr> [<addr> ...]
"""
import os
import struct
import sys

ROOT = os.environ.get("RDR_ROOT", os.getcwd())
d = open(os.path.join(ROOT, "build_rdr2", "baseline_v1", "entradas", "RDR2.elf"), "rb").read()
phoff = struct.unpack_from(">Q", d, 32)[0]
phnum = struct.unpack_from(">H", d, 56)[0]
OPS = {0x80000000: "lwz", 0x90000000: "stw", 0xE8000000: "ld", 0xF8000000: "std"}


def segmentos():
    for i in range(phnum):
        t, fl, off, va, _, fsz = struct.unpack_from(">IIQQQQ", d, phoff + i * 56)
        if t == 1 and fl & 1:
            yield off, va, fsz


def main():
    for alvo in (int(a, 16) for a in sys.argv[1:]):
        baixo = alvo & 0xFFFF
        alto = ((alvo + 0x8000) >> 16) & 0xFFFF
        print(f"== {alvo:#x} (lis {alto:#x}, desloc {baixo:#x})")
        for off, va, fsz in segmentos():
            for i in range(0, fsz - 4, 4):
                w = struct.unpack_from(">I", d, off + i)[0]
                op = w & 0xFC000000
                if op not in OPS or (w & 0xFFFF) != baixo:
                    continue
                ra = (w >> 16) & 31
                achou = any(
                    struct.unpack_from(">I", d, off + j)[0] == (0x3C000000 | (r << 21) | alto)
                    for j in range(max(0, i - 64), i, 4)
                    for r in [ra]
                )
                if achou:
                    print(f"  {va + i:#010x} {OPS[op]} r{(w >> 21) & 31}")


if __name__ == "__main__":
    main()
