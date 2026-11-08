"""Resolve RVAs do executavel para simbolos, usando a saida de llvm-nm.

uso: rva2sym.py <nm.txt> <base_hex> <rva_hex> [<rva_hex> ...]
"""
import bisect
import sys


def main():
    base = int(sys.argv[2], 16)
    ends, nomes = [], []
    for linha in open(sys.argv[1], encoding="utf-8", errors="ignore"):
        p = linha.split()
        if len(p) >= 3 and p[1] in "tT":
            ends.append(int(p[0], 16))
            nomes.append(p[2])
    pares = sorted(zip(ends, nomes))
    ends = [a for a, _ in pares]
    for r in sys.argv[3:]:
        a = base + int(r, 16)
        i = bisect.bisect_right(ends, a) - 1
        print(f"{r}: {pares[i][1]}+0x{a - ends[i]:X}" if i >= 0 else f"{r}: ?")


if __name__ == "__main__":
    main()
