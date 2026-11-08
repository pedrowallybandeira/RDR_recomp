"""Limita a lista de funcoes do RDR2 ao fim do codigo, sem tocar no ELF.

O ppu_loader.py do ps3recomp termina a ultima funcao muito depois do .text, o que
traduziria ~2,4 MB de dados (inclusive os programas SPU). Este script corta cada
fim no limite do .text ou do .sceStub.text e grava RDR2.functions.clamped.json.

Clamps the function list written by ps3recomp's ppu_loader.py so that no function
runs past .text / .sceStub.text (the loader's last function swallowed .rodata).
The constants are the section bounds of the BLUS30418 executable used here.

uso: prep_lift.py <pasta com RDR2.functions.json e RDR2.imports.json>
"""
import json
import os
import sys

if len(sys.argv) != 2:
    sys.exit(__doc__)
OUT = sys.argv[1]
TEXT_END = 0x10230 + 0x10F244C
STUB_START = 0x11026A0
STUB_END = STUB_START + 19432
fn = json.load(open(os.path.join(OUT, "RDR2.functions.json")))
starts = [int(f["start"], 16) for f in fn]
print("funcoes:", len(fn), "primeira", hex(min(starts)), "ultima", hex(max(starts)))
print("fim .text", hex(TEXT_END), ".sceStub", hex(STUB_START), hex(STUB_END))
fora = [f for f in fn if int(f["start"], 16) >= STUB_END]
print("comecam depois do codigo:", len(fora))
stub = [f for f in fn if STUB_START <= int(f["start"], 16) < STUB_END]
print("dentro de .sceStub.text:", len(stub))
clamped = 0
for f in fn:
    s, e = int(f["start"], 16), int(f["end"], 16)
    lim = TEXT_END if s < TEXT_END else STUB_START
    if e > lim:
        f["end"] = hex(lim)
        clamped += 1
print("fins limitados:", clamped)
json.dump([f for f in fn if int(f["start"], 16) < STUB_END],
          open(os.path.join(OUT, "RDR2.functions.clamped.json"), "w"), indent=1)
imp = json.load(open(os.path.join(OUT, "RDR2.imports.json")))
st = sorted(int(i["stub"], 16) for i in imp)
print("stubs de import:", len(st), hex(st[0]), hex(st[-1]))
