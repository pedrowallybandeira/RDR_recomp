"""Converte um PPM P6 em PNG, sem dependencias.

uso: ppm2png.py <entrada.ppm> <saida.png>
"""
import struct
import sys
import zlib


def main():
    d = open(sys.argv[1], "rb").read()
    campos, pos = [], 0
    while len(campos) < 4:
        while d[pos] in b" \t\r\n":
            pos += 1
        ini = pos
        while d[pos] not in b" \t\r\n":
            pos += 1
        campos.append(d[ini:pos])
    pos += 1
    w, h = int(campos[1]), int(campos[2])
    linhas = b"".join(b"\0" + d[pos + y * w * 3:pos + (y + 1) * w * 3] for y in range(h))

    def bloco(t, c):
        return struct.pack(">I", len(c)) + t + c + struct.pack(">I", zlib.crc32(t + c))

    saida = b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    saida += bloco(b"IDAT", zlib.compress(linhas, 6)) + bloco(b"IEND", b"")
    open(sys.argv[2], "wb").write(saida)


if __name__ == "__main__":
    main()
