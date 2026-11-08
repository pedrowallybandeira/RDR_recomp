"""Mostra por 30 s o que cada porta XInput recebe, sem abrir o jogo.

uso: xinput_teste.py
"""
import os as _os
# Raiz da arvore de trabalho privada (layout original: build_rdr2/, referencias/).
ROOT = _os.environ.get("RDR_ROOT", _os.getcwd())
import ctypes
import time

SAIDA = ROOT + r"\build_rdr2\work_v3\boots\xinput_teste.txt"
NOMES = {0x0001: "CIMA", 0x0002: "BAIXO", 0x0004: "ESQUERDA", 0x0008: "DIREITA", 0x0010: "START", 0x0020: "BACK",
         0x0040: "L3", 0x0080: "R3", 0x0100: "LB", 0x0200: "RB", 0x1000: "A", 0x2000: "B", 0x4000: "X", 0x8000: "Y"}


class Gamepad(ctypes.Structure):
    _fields_ = [("botoes", ctypes.c_ushort), ("lt", ctypes.c_ubyte), ("rt", ctypes.c_ubyte), ("lx", ctypes.c_short),
                ("ly", ctypes.c_short), ("rx", ctypes.c_short), ("ry", ctypes.c_short)]


class Estado(ctypes.Structure):
    _fields_ = [("pacote", ctypes.c_ulong), ("g", Gamepad)]


def main():
    x = ctypes.WinDLL("XInput1_4")
    antes = {}
    mudancas = [0, 0, 0, 0]
    ligado = [False] * 4
    vistos = []
    print("Aperte START, A e X no controle, e mexa os analogicos, por 30 s...")
    fim = time.time() + 30
    while time.time() < fim:
        for i in range(4):
            e = Estado()
            if x.XInputGetState(i, ctypes.byref(e)) != 0:
                continue
            ligado[i] = True
            if antes.get(i) is not None and antes[i] != e.pacote:
                mudancas[i] += 1
                nomes = [n for b, n in NOMES.items() if e.g.botoes & b]
                if nomes:
                    vistos.append(f"  porta {i}: {' + '.join(nomes)}")
                    print(vistos[-1])
            antes[i] = e.pacote
        time.sleep(0.01)
    print()
    linhas = [f"porta {i}: {'conectada' if ligado[i] else 'vazia'}, {mudancas[i]} mudancas recebidas" for i in range(4)]
    print("\n".join(linhas))
    with open(SAIDA, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas + vistos) + "\n")
    input("\nResultado salvo. Aperte Enter para fechar.")


if __name__ == "__main__":
    main()
