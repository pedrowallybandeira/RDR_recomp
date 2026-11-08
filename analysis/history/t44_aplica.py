"""Liga a observacao da tentativa 44 no fonte traduzido do job 7639.

uso: t44_aplica.py <spu_recomp.c do 7639>
Desligar e copiar o arquivo de volta da baseline.
"""
import re
import sys

CAB = '#include "spu_helpers.h"\n'
NOVO = (CAB +
        "/* TEMP attempt 44 */\n"
        "extern void rdr2_t44_wrch(spu_context* ctx, uint32_t ch, u128 v);\n"
        "extern void rdr2_t44_call(spu_context* ctx, uint32_t stage, uint32_t ret);\n"
        "#define spu_wrch(c, ch, v) do { rdr2_t44_wrch((c), (ch), (v)); (spu_wrch)((c), (ch), (v)); } while (0)\n")
CHAMADA = re.compile(r"ctx->pc = _tg; ctx->host_depth\+\+; spu_indirect_branch\(ctx\); spu_drain_call\(ctx, (0x[0-9A-F]+)\);")


def troca(m):
    r = m.group(1)
    return (f"ctx->pc = _tg; rdr2_t44_call(ctx, 1, {r}); ctx->host_depth++; spu_indirect_branch(ctx); "
            f"rdr2_t44_call(ctx, 2, {r}); spu_drain_call(ctx, {r}); rdr2_t44_call(ctx, 3, {r});")


def main():
    p = sys.argv[1]
    t = open(p, encoding="utf-8", newline="").read()
    if t.count(CAB) != 1:
        sys.exit("cabecalho nao encontrado")
    t = t.replace(CAB, NOVO)
    t, n = CHAMADA.subn(troca, t)
    if n != 2:
        sys.exit(f"esperava 2 chamadas, achei {n}")
    open(p, "w", encoding="utf-8", newline="").write(t)
    print("aplicado:", n, "chamadas")


if __name__ == "__main__":
    main()
