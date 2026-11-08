"""Le o que spu_run_spurs_job deixou numa copia do LS: descritor, contexto e pilha.

uso: ls_inspect.py <probe_ls.bin> [dir_dumps]
"""
import glob
import os
import struct
import sys

LS = 0x40000
DESC = LS - 0x400
CTX = DESC - 0x40


def u32(d, o):
    return struct.unpack_from(">I", d, o)[0]


def u16(d, o):
    return struct.unpack_from(">H", d, o)[0]


def main():
    d = open(sys.argv[1], "rb").read()
    print(f"tamanho={len(d)}")
    print("--- descritor em LS", hex(DESC))
    for o in range(0, 0x40, 16):
        print(f"  +{o:02X}:", " ".join(f"{u32(d, DESC + o + i):08X}" for i in range(0, 16, 4)))
    ea_bin = u32(d, DESC + 4) & ~1
    size_bin = u16(d, DESC + 8) << 4
    print(f"  eaBinary={ea_bin:#010x} sizeBinary={size_bin}")
    print("--- contexto em LS", hex(CTX))
    for o in range(0, 0x40, 16):
        print(f"  +{o:02X}:", " ".join(f"{u32(d, CTX + o + i):08X}" for i in range(0, 16, 4)))

    if len(sys.argv) > 2:
        print("--- comparacao com os dumps, palavra a palavra, no tamanho de cada job")
        for c in sorted(glob.glob(os.path.join(sys.argv[2], "spujob_*.bin"))):
            b = open(c, "rb").read()
            n = len(b) // 4
            iguais = sum(1 for i in range(n) if d[i * 4:i * 4 + 4] == b[i * 4:i * 4 + 4])
            print(f"  {os.path.basename(c):44s} {100 * iguais / n:6.1f}%")

    # Enderecos de retorno do SPU ficam em quadwords da pilha, na palavra preferencial.
    print("--- ultimos dados nao nulos abaixo do contexto (provavel pilha)")
    candidatos = []
    for o in range(CTX - 16, 0x4000, -16):
        q = struct.unpack_from(">4I", d, o)
        if any(q):
            candidatos.append((o, q))
        if len(candidatos) >= 40:
            break
    for o, q in candidatos:
        print(f"  {o:#07x}: " + " ".join(f"{v:08X}" for v in q))


if __name__ == "__main__":
    main()
