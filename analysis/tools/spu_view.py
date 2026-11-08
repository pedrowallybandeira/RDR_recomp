"""Mostra trechos de um SPU embarcado no RDR2.elf. So leitura.
Uso: spu_view.py <offset_arquivo> <ini>-<fim> [<ini>-<fim> ...]"""
import os
import struct
import sys

ROOT = os.environ.get("RDR_ROOT", os.getcwd())
sys.path.insert(0, os.path.join(ROOT, "referencias", "ps3recomp-v0.18.0", "tools"))
import spu_disasm  # noqa: E402

d = open(os.path.join(ROOT, "build_rdr2", "baseline_v1", "entradas", "RDR2.elf"), "rb").read()
o = int(sys.argv[1], 0)
ident = d[o:o + 16]
entry, phoff = struct.unpack_from(">II", d, o + 24)
phent, phnum = struct.unpack_from(">HH", d, o + 42)
print(f"ELF SPU entry={entry:#x} phnum={phnum}")
loads = []
for k in range(phnum):
    t, of, va, pa, fs, ms, fl, al = struct.unpack_from(">8I", d, o + phoff + k * phent)
    print(f"  PH{k} type={t:#x} off={of:#x} va={va:#x} fs={fs:#x} ms={ms:#x} fl={fl:#x}")
    if t == 1:
        loads.append((va, of, fs))


def rd(a):
    for va, of, fs in loads:
        if va <= a < va + fs:
            return struct.unpack_from(">I", d, o + of + a - va)[0]
    return None


dec = spu_disasm.spu_decode
for r in sys.argv[2:]:
    a, b = [int(x, 16) for x in r.split("-")]
    print(f"--- {a:#x}..{b:#x}")
    for x in range(a, b, 4):
        w = rd(x)
        if w is None:
            print(f"  {x:#07x} <fora>")
            continue
        try:
            i = dec(w, x)
            txt = f"{getattr(i, 'mnemonic', i)} {getattr(i, 'operands', '')}"
        except Exception as e:
            txt = f"? {e}"
        print(f"  {x:#07x} {w:08X} {txt}")
