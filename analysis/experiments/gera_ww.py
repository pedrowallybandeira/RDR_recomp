"""Copia o ppu_loader.cpp da v0.19 para ppu_loader_ww.cpp com uma condicao a mais:
a pilha do jogo sai tambem quando a escrita vigiada vem da funcao PPU_WWATCH_STACKFN."""
import os as _os
# Raiz da arvore de trabalho privada (layout original: build_rdr2/, referencias/).
ROOT = _os.environ.get("RDR_ROOT", _os.getcwd())
src = ROOT + "/referencias/ps3recomp-v0.19.0/runtime/ppu/ppu_loader.cpp"
s = open(src, encoding="utf-8", newline="").read()
velho = 'if (_i == 1 && g_active_ctx) ppu_dump_guest_stack(g_active_ctx, "ww");'
assert s.count(velho) == 1
novo = ('{ static long s_fn = -2; static int s_k = 0;'
        ' if (s_fn == -2) { const char* e = getenv("PPU_WWATCH_STACKFN"); s_fn = e ? (long)strtoul(e, 0, 16) : -1; }'
        ' const int hit = s_fn >= 0 && ppu_prof_resolve_host(ra) == (uint32_t)s_fn && s_k < 6;'
        ' if (hit) { s_k++; fprintf(stderr, "[ww-fn] r3=0x%08X r4=0x%08X" "\\n", g_active_ctx ? (uint32_t)g_active_ctx->gpr[3] : 0u, g_active_ctx ? (uint32_t)g_active_ctx->gpr[4] : 0u); }'
        ' if ((_i == 1 || hit) && g_active_ctx) ppu_dump_guest_stack(g_active_ctx, "ww"); }')
open("ppu_loader_ww.cpp", "w", encoding="utf-8", newline="").write(s.replace(velho, novo))
print("gerado")
