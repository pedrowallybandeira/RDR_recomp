"""Procura trechos de texto em um ELF e mostra a string C completa e o deslocamento.

uso: str_peek.py <arquivo> <trecho> [<trecho> ...]
"""
import sys


def main():
    dados = open(sys.argv[1], 'rb').read()
    vistos = set()
    for trecho in sys.argv[2:]:
        alvo = trecho.encode()
        i = dados.find(alvo)
        while i >= 0:
            ini = i
            while ini > 0 and 0x20 <= dados[ini - 1] < 0x7F:
                ini -= 1
            fim = dados.find(b'\0', i)
            if ini not in vistos and fim - ini < 200:
                vistos.add(ini)
                print(f'0x{ini:08X}  {dados[ini:fim].decode("latin-1")}')
            i = dados.find(alvo, i + 1)


if __name__ == '__main__':
    main()
