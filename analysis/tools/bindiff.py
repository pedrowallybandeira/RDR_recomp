"""Compara dois binarios e situa as diferencas no PE. So leitura.

uso: bindiff.py <a> <b>
"""
import struct
import sys

a = open(sys.argv[1], "rb").read()
b = open(sys.argv[2], "rb").read()
print(f"tamanhos: {len(a)} {len(b)}")
n = min(len(a), len(b))
dif = []
pos = 0
while pos < n:
    fim = min(pos + (1 << 20), n)
    if a[pos:fim] != b[pos:fim]:
        dif += [i for i in range(pos, fim) if a[i] != b[i]]
    pos = fim
print(f"bytes diferentes: {len(dif)}")
pe = struct.unpack_from("<I", a, 0x3C)[0]
nsec = struct.unpack_from("<H", a, pe + 6)[0]
opt = struct.unpack_from("<H", a, pe + 20)[0]
print(f"campo TimeDateStamp em {pe + 8:#x}")
secs = []
for i in range(nsec):
    o = pe + 24 + opt + i * 40
    nome = a[o:o + 8].rstrip(b"\0").decode("ascii", "replace")
    raw_sz, raw_off = struct.unpack_from("<II", a, o + 16)
    secs.append((raw_off, raw_off + raw_sz, nome))
faixas = []
for i in dif:
    if faixas and i - faixas[-1][1] <= 16:
        faixas[-1][1] = i
    else:
        faixas.append([i, i])
print(f"faixas: {len(faixas)}")
for x, y in faixas[:24]:
    s = next((nm for ini, fim, nm in secs if ini <= x < fim), "cabecalho")
    print(f"  {x:#010x}-{y:#010x} ({y - x + 1} B) secao={s} a={a[x:x + 8].hex()} b={b[x:x + 8].hex()}")
