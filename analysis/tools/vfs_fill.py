"""Copia dados do dump para o VFS, com SHA-256 da origem e da copia.

uso: vfs_fill.py <dir_origem> <dir_destino> <manifesto.json> <nome>|<origem=destino> ...
"""
import hashlib, json, os, sys, time

BLOCO = 16 * 1024 * 1024


def copiar(origem, destino):
    h = hashlib.sha256()
    temp = destino + '.parcial'
    with open(origem, 'rb') as e, open(temp, 'wb') as s:
        while True:
            b = e.read(BLOCO)
            if not b:
                break
            h.update(b)
            s.write(b)
    os.replace(temp, destino)
    return h.hexdigest()


def hash_de(caminho):
    h = hashlib.sha256()
    with open(caminho, 'rb') as e:
        while True:
            b = e.read(BLOCO)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main():
    dir_origem, dir_destino, manifesto = sys.argv[1:4]
    saida = []
    for item in sys.argv[4:]:
        nome_origem, _, nome = item.rpartition('=')
        origem = os.path.join(dir_origem, nome_origem or nome)
        destino = os.path.join(dir_destino, nome)
        t = time.time()
        h_origem = copiar(origem, destino)
        t_copia = time.time() - t
        t = time.time()
        h_destino = hash_de(destino)
        igual = h_origem == h_destino
        tam = os.path.getsize(destino)
        print(f'{nome}: {tam} B, copia {t_copia:.0f}s, verificacao {time.time() - t:.0f}s, '
              f'sha256 {h_destino}, {"IGUAL" if igual else "DIFERENTE"}', flush=True)
        saida.append({'nome': nome, 'bytes': tam, 'sha256': h_destino, 'origem_igual_copia': igual})
        if not igual:
            sys.exit(2)
    os.makedirs(os.path.dirname(manifesto), exist_ok=True)
    with open(manifesto, 'w', encoding='utf-8') as f:
        json.dump(saida, f, indent=2)


if __name__ == '__main__':
    main()
