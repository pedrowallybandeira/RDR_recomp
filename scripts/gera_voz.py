"""Copia experimental de ppu_recomp_023.cpp com uma sonda no laco de func_0066BEA8.

Depois de 100 mil voltas, numero impossivel numa lista de vozes, registra o estado e
sai do laco. Sem efeito nas chamadas normais.

O resultado e codigo do jogo traduzido: fica so na sua pasta local (o CMake do
port o usa se existir em PORT_OVERLAY_DIR). Nunca publicar.

Writes a copy of YOUR lifted ppu_recomp_023.cpp with the [t54] probe that breaks
the voice-list loop in func_0066BEA8 after 100,000 laps. The output is lifted
game code: keep it local, never commit it.

uso: gera_voz.py <lift>/ppu_recomp_023.cpp <local>/overlay/ppu_recomp_023.cpp
"""
import sys

if len(sys.argv) != 3:
    sys.exit(__doc__)
ORIG, SAIDA = sys.argv[1], sys.argv[2]
s = open(ORIG, encoding="latin-1", newline="").read()
a = s.index("void func_0066BEA8(ppu_context* ctx) {")
b = s.index("loc_0066BF80:", a)
nl = "\r\n" if "\r\n" in s[a:b] else "\n"
novo = ("{ extern void rdr2_t54_zera(void); rdr2_t54_zera(); }" + nl +
        "loc_0066BF80:" + nl +
        "        { extern int rdr2_t54_voz(ppu_context*); if (rdr2_t54_voz(ctx)) goto loc_0066C0E8; }")
s = s[:b] + novo + s[b + len("loc_0066BF80:"):]
s += r"""

#include <stdio.h>
static thread_local unsigned long long t54_n;
static unsigned t54_vezes;
void rdr2_t54_zera(void) { t54_n = 0; }
int rdr2_t54_voz(ppu_context* ctx)
{
    if (++t54_n < 100000ull) return 0;
    ppu_context* c = ctx;
    PPU_MM_SNAP
    if (t54_vezes++ < 6) {
        const uint32_t r7 = (uint32_t)c->gpr[7], r27 = (uint32_t)c->gpr[27], r28 = (uint32_t)c->gpr[28], r29 = (uint32_t)c->gpr[29];
        const uint32_t base = vm_read32(r29 + 0x50);
        fprintf(stderr, "[t54] laco preso #%u lr=0x%08X r7=0x%08X r26=%llX r27=0x%08X r28=0x%08X r29=0x%08X r30=%llX r31=%llX base=0x%08X grupos=0x%08X\n",
                t54_vezes, (uint32_t)c->lr, r7, (unsigned long long)c->gpr[26], r27, r28, r29,
                (unsigned long long)c->gpr[30], (unsigned long long)c->gpr[31], base, vm_read32(r29 + 0x68));
        fprintf(stderr, "[t54] r28+:");
        for (uint32_t o = 0; o < 0x40; o += 4) fprintf(stderr, " %08X", vm_read32(r28 + o));
        fprintf(stderr, "\n[t54] r27+:");
        for (uint32_t o = 0; o < 0x40; o += 4) fprintf(stderr, " %08X", vm_read32(r27 + o));
        fprintf(stderr, "\n[t54] lista a partir de r7:");
        uint32_t i = vm_read16(r7);
        for (int k = 0; k < 40 && i != 0xFFFFu; k++) {
            const uint32_t n = base + (i << 5);
            uint32_t pri = vm_read32(n + 0xC);
            fprintf(stderr, " %u(prox=%u f1A=%04X p=%08X)", i, vm_read16(n + 0x18), vm_read16(n + 0x1A), pri);
            i = vm_read16(n + 0x18);
        }
        fprintf(stderr, "\n");
        fflush(stderr);
    }
    return 1;
}
"""
open(SAIDA, "w", encoding="latin-1", newline="").write(s)
print("gerado", len(s))
