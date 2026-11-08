"""Resume um boot: mensagens do jogo, imports nao resolvidos, SPU pedido."""
import hashlib
import json
import os
import re
import struct
import sys

ROOT = os.environ.get("RDR_ROOT", os.getcwd())
sys.path.insert(0, os.path.join(ROOT, "referencias", "ps3recomp-v0.18.0", "tools"))
import nid_database  # noqa: E402

tag = sys.argv[1]
B = os.path.join(ROOT, "build_rdr2", "work_v3", "boots")
out = open(os.path.join(B, tag + ".out"), encoding="latin1").read().splitlines()
err = open(os.path.join(B, tag + ".err"), encoding="latin1").read().splitlines()
ruido = re.compile(r"^\[(cellSysmodule|D3D12|VPVB|VPCB|sem\]|rsx)")
print("linhas stdout:", len(out), "stderr:", len(err))
print("--- stdout sem ruido")
vistos = 0
for ln in out:
    if ruido.match(ln) or not ln.strip():
        continue
    vistos += 1
    if vistos <= 60:
        print(ln[:150])
print("total:", vistos)
imp = json.load(open(os.path.join(ROOT, "relatorios", "evidencias", "etapa2_auditoria", "RDR2.imports.json")))
lib = {int(i["nid"], 16): i["library"] for i in imp}
db = nid_database.get_default_db()
nids = sorted(set(int(x, 16) for x in re.findall(r"unresolved NID 0x([0-9A-Fa-f]{8})", "\n".join(err))))
print("--- imports nao resolvidos chamados")
for n in nids:
    k = db.lookup_nid(n)
    print(f"  0x{n:08X} {lib.get(n)} {k[1] if k else '?'}")
print("--- SPU")
for ln in err:
    if "spu_workload" in ln or ln.startswith("[SPU]") or "[spu" in ln:
        print(" ", ln[:200])
d = open(os.path.join(ROOT, "build_rdr2", "baseline_v1", "entradas", "RDR2.elf"), "rb").read()
isa = json.load(open(os.path.join(ROOT, "relatorios", "evidencias", "etapa2_auditoria", "RDR2.isa.json")))
for s in isa["spu_elfs"][:10]:
    o = int(s["file_off"], 16)
    ph, = struct.unpack_from(">I", d, o + 28)
    n = struct.unpack_from(">H", d, o + 44)[0]
    mx = 0
    for k in range(n):
        t, of, va, pa, fs, ms, fl, al = struct.unpack_from(">8I", d, o + ph + k * 32)
        if t == 1:
            mx = max(mx, va + ms)
    i = d[o:o + 26580].find(b"SPUNAME")
    print(f"  {s['file_off']} extent={s['extent']} loadend={mx} ({mx:#x})")
