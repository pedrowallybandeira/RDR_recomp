"""Item 5 da tentativa 37: rotinas SPURS e strings nos jobs traduzidos. So leitura.

uso: t37_estatico.py <dir_dumps>
Procura os bytes exatos das rotinas do C895 e, por independer de posicao, os pares
ilhu 0x8041 / iohl <codigo> e as constantes de GETLLAR e PUTLLC.
"""
import glob
import os
import struct
import sys

ROTINAS = {"Notify": (0xF440, 0x30), "Kick": (0xF580, 0x30), "Run": (0xF678, 0x30),
           "TryWait": (0xECA8, 0x30), "Ready": (0xF738, 0x28), "Sinal": (0xF850, 0x2C)}
TEXTOS = [b"edge_jobs.cpp", b"edgegeom.cpp", b"cellSpursJobGuardNotify", b"cellSpursRunJobChain",
          b"cellSpursKickJobChain", b"cellSpursEventFlag", b"tryWaitRes", b"JOBCRT"]
CODIGOS = {0xA02: "INVAL", 0xA09: "PERM", 0xA0F: "STAT", 0xA10: "ALIGN", 0xA11: "NULL",
           0x90A: "BUSY", 0x902: "T_INVAL", 0x910: "T_ALIGN", 0x911: "T_NULL"}


def palavras(d):
    return struct.unpack(f">{len(d) // 4}I", d[:len(d) // 4 * 4])


def main():
    base = sys.argv[1]
    ref = open(os.path.join(base, "spujob_C895B508A51CD2A6_79376.bin"), "rb").read()
    print("job   tamanho  rotinas_exatas                       codigos_8041              getllar putllc  textos")
    for p in sorted(glob.glob(os.path.join(base, "spujob_*.bin"))):
        d = open(p, "rb").read()
        n = os.path.basename(p)[7:11]
        exatas = []
        for nome, (o, t) in ROTINAS.items():
            i = d.find(ref[o:o + t])
            if i >= 0:
                exatas.append(f"{nome}@{i:#x}")
        w = palavras(d)
        cod = {}
        ga = pu = 0
        for i, x in enumerate(w):
            op, imm, rt = x >> 23, (x >> 7) & 0xFFFF, x & 127
            if op == 0x081 and imm == 208:
                ga += 1
            if op == 0x081 and imm == 180:
                pu += 1
            if op == 0x0C1 and imm in CODIGOS:
                for y in w[max(0, i - 16):i]:
                    if y >> 23 == 0x082 and ((y >> 7) & 0xFFFF) == 0x8041 and (y & 127) == rt:
                        cod[CODIGOS[imm]] = cod.get(CODIGOS[imm], 0) + 1
                        break
        txt = [t.decode() for t in TEXTOS if t in d]
        c = " ".join(f"{k}x{v}" for k, v in sorted(cod.items()))
        print(f"{n}  {len(d):7d}  {' '.join(exatas) or '-':36s} {c or '-':25s} {ga:6d} {pu:6d}  {' '.join(txt) or '-'}")


if __name__ == "__main__":
    main()
