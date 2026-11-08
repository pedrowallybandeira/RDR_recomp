/* audit.c -- experimento (tentativa 65): onde o audio do Multistream vira zero, v16.
 *
 * Chamado no inicio de mfc_do_transfer para toda transferencia DMA. So age na imagem
 * SPU_AUDIT_IMG=<id decimal> (o Multistream e 517498422).
 *
 * SPU_AUDIT_TRACE=<lo hex>,<hi hex>[,<max>]: uma linha [atrace] por DMA com EA em
 *   [lo, hi): GET/PUT, EA, tamanho, LSA, pc e lr do SPU, e as 4 palavras de LS 0x36190
 *   (o destino que a leitura estatica aponta para a saida do decodificador). Ate <max>
 *   linhas (padrao 400).
 * SPU_AUDIT_WATCH=<lsa hex>: a cada DMA da imagem, compara os 16 bytes de LS nesse
 *   endereco com os da ultima vez neste contexto e registra [awatch] quando mudam
 *   (ate 300 linhas).
 * SPU_AUDIT_SUM=1: o resumo por regiao de 64 KB da tentativa 62 ([audit], a cada 5 s).
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>
#include "spu_context.h"

extern uint8_t* vm_base;
unsigned long long ps3_ms_now(void);

static uint32_t ls_be32(const spu_context* spu, uint32_t a)
{
    const uint8_t* p = spu->ls + (a & 0x3FFFCu);
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3];
}

/* ---- resumo por regiao (tentativa 62) ---- */
#define AUD_N 4096
typedef struct { uint32_t reg; long long get, get_nz, put, put_nz; unsigned n; } aud_slot;
static aud_slot s_slot[AUD_N];
static SRWLOCK s_lk = SRWLOCK_INIT;
static unsigned long long s_t0;

static uint32_t nz_count(const uint8_t* p, uint32_t n)
{
    uint32_t c = 0;
    for (uint32_t i = 0; i < n; i++) c += p[i] != 0;
    return c;
}

static int cmp(const void* a, const void* b)
{
    const aud_slot* x = a; const aud_slot* y = b;
    long long tx = x->get + x->put, ty = y->get + y->put;
    return tx < ty ? 1 : tx > ty ? -1 : 0;
}

static void sum(spu_context* spu, uint32_t lsa, uint32_t e32, uint32_t size, int put)
{
    const uint32_t nz = put ? nz_count(spu->ls + (lsa & 0x3FFF0u), size) : nz_count(vm_base + e32, size);
    const uint32_t reg = e32 >> 16;
    AcquireSRWLockExclusive(&s_lk);
    aud_slot* s = &s_slot[reg % AUD_N];
    if (s->n && s->reg != reg) { ReleaseSRWLockExclusive(&s_lk); return; }
    s->reg = reg; s->n++;
    if (put) { s->put += size; s->put_nz += nz; } else { s->get += size; s->get_nz += nz; }
    const unsigned long long now = ps3_ms_now();
    if (!s_t0) s_t0 = now;
    if (now - s_t0 >= 5000) {
        static aud_slot tmp[AUD_N];
        memcpy(tmp, s_slot, sizeof tmp);
        memset(s_slot, 0, sizeof s_slot);
        s_t0 = now;
        ReleaseSRWLockExclusive(&s_lk);
        qsort(tmp, AUD_N, sizeof tmp[0], cmp);
        for (int i = 0; i < 24 && (tmp[i].get + tmp[i].put); i++)
            fprintf(stderr, "[audit] ea=0x%08X get=%lld (nz %lld) put=%lld (nz %lld) n=%u\n",
                    tmp[i].reg << 16, tmp[i].get, tmp[i].get_nz, tmp[i].put, tmp[i].put_nz, tmp[i].n);
        return;
    }
    ReleaseSRWLockExclusive(&s_lk);
}

void exp_dma_audit(spu_context* spu, uint32_t lsa, uint64_t ea, uint32_t size, uint32_t cmd)
{
    static long s_img = -2;
    if (s_img == -2) { const char* e = getenv("SPU_AUDIT_IMG"); s_img = e ? atol(e) : -1; }
    if (s_img < 0 || !spu || spu->image_id != s_img || !size || size > 0x4000) return;
    const int put = (cmd & 0xF0) == 0x20, get = (cmd & 0xF0) == 0x40;
    if (!put && !get) return;
    const uint32_t e32 = (uint32_t)ea;

    /* Mudancas no bloco observado. */
    { static long s_w = -2; static int s_wn;
      static struct { const spu_context* ctx; uint8_t v[16]; } s_last[8];
      if (s_w == -2) { const char* w = getenv("SPU_AUDIT_WATCH"); s_w = w ? (long)strtoul(w, 0, 16) : -1; }
      if (s_w >= 0 && s_wn < 300) {
          const uint8_t* cur = spu->ls + ((uint32_t)s_w & 0x3FFF0u);
          int k = 0;
          while (k < 8 && s_last[k].ctx && s_last[k].ctx != spu) k++;
          if (k < 8) {
              if (!s_last[k].ctx || memcmp(s_last[k].v, cur, 16)) {
                  s_last[k].ctx = spu;
                  memcpy(s_last[k].v, cur, 16);
                  s_wn++;
                  fprintf(stderr, "[awatch] t=%llu ctx=%p pc=0x%05X LS[0x%05lX]=%08X %08X %08X %08X (no %s ea=0x%08X)\n",
                          ps3_ms_now(), (void*)spu, spu->pc, s_w,
                          ls_be32(spu, (uint32_t)s_w), ls_be32(spu, (uint32_t)s_w + 4),
                          ls_be32(spu, (uint32_t)s_w + 8), ls_be32(spu, (uint32_t)s_w + 12),
                          put ? "PUT" : "GET", e32);
              }
          }
      } }

    /* Rastreio por faixa de EA. */
    { static long long s_lo = -2; static uint32_t s_hi; static long s_max, s_n;
      if (s_lo == -2) { const char* t = getenv("SPU_AUDIT_TRACE"); s_lo = -1;
          if (t) { char* c; s_lo = (long long)strtoul(t, &c, 16);
                   s_hi = *c == ',' ? (uint32_t)strtoul(c + 1, &c, 16) : 0xFFFFFFFFu;
                   s_max = *c == ',' ? atol(c + 1) : 400; } }
      static long s_maxsz = -2;   /* SPU_AUDIT_TRACE_MAXSZ=<n>: so DMA ate n bytes */
      if (s_maxsz == -2) { const char* m = getenv("SPU_AUDIT_TRACE_MAXSZ"); s_maxsz = m ? atol(m) : 0x4000; }
      if (s_lo >= 0 && e32 >= (uint32_t)s_lo && e32 < s_hi && s_n < s_max && (long)size <= s_maxsz) {
          const uint8_t* d = put ? spu->ls + (lsa & 0x3FFF0u) : vm_base + e32;
          /* Deduplicado: as 4 primeiras de cada (tipo, EA, pc, tem dados). */
          { static struct { uint32_t ea, pc; uint8_t put, nz, n; } s_k[512]; static int s_kn;
            const uint8_t has = nz_count(d, size < 256 ? size : 256) != 0;
            int k = 0;
            for (; k < s_kn; k++)
                if (s_k[k].ea == e32 && s_k[k].pc == spu->pc && s_k[k].put == put && s_k[k].nz == has) break;
            if (k == s_kn) { if (s_kn == 512) return; s_k[s_kn].ea = e32; s_k[s_kn].pc = spu->pc;
                             s_k[s_kn].put = (uint8_t)put; s_k[s_kn].nz = has; s_k[s_kn].n = 0; s_kn++; }
            if (s_k[k].n >= 4) return;
            s_k[k].n++; }
          s_n++;
          fprintf(stderr, "[atrace] t=%llu %s ea=0x%08X size=%u lsa=0x%05X pc=0x%05X lr=0x%05X nz=%u "
                          "LS[0x36190]=%08X %08X %08X %08X\n",
                  ps3_ms_now(), put ? "PUT" : "GET", e32, size, lsa, spu->pc, spu->gpr[0]._u32[0],
                  nz_count(d, size), ls_be32(spu, 0x36190), ls_be32(spu, 0x36194),
                  ls_be32(spu, 0x36198), ls_be32(spu, 0x3619C));
      } }

    { static int s_sum = -1; if (s_sum < 0) s_sum = getenv("SPU_AUDIT_SUM") ? 1 : 0;
      if (s_sum) sum(spu, lsa, e32, size, put); }

    /* SPU_AUDIT_HEX=<ea hex>,<len hex>,<ms>: a cada <ms>, as linhas de 16 bytes nao
     * nulas da memoria principal [ea, ea+len), com o tempo; ate 40 despejos. */
    /* Varias regioes: SPU_AUDIT_HEX=<ea>,<len>,<ms>[;<ea>,<len>;...] (o periodo vem da primeira). */
    { static int s_nr = -1; static uint32_t s_ea[8], s_len[8], s_ms; static unsigned long long s_t; static int s_k;
      if (s_nr < 0) { const char* h = getenv("SPU_AUDIT_HEX"); s_nr = 0; s_ms = 5000;
          while (h && *h && s_nr < 8) { char* c;
              s_ea[s_nr] = (uint32_t)strtoul(h, &c, 16);
              s_len[s_nr] = *c == ',' ? (uint32_t)strtoul(c + 1, &c, 16) : 0x100;
              if (*c == ',') { const unsigned long ms = strtoul(c + 1, &c, 10); if (!s_nr) s_ms = (uint32_t)ms; }
              s_nr++;
              h = *c == ';' ? c + 1 : NULL; } }
      const unsigned long long now = ps3_ms_now();
      if (s_nr > 0 && s_k < 40 && now - s_t >= s_ms) {
          s_t = now; s_k++;
          fprintf(stderr, "[ahex] t=%llu\n", now);
          for (int r = 0; r < s_nr; r++)
              for (uint32_t o = 0; o < s_len[r]; o += 16) {
                  const uint8_t* p = vm_base + s_ea[r] + o;
                  if (!nz_count(p, 16)) continue;
                  fprintf(stderr, "[ahex]   %08X:", s_ea[r] + o);
                  for (int i = 0; i < 16; i += 4)
                      fprintf(stderr, " %02X%02X%02X%02X", p[i], p[i + 1], p[i + 2], p[i + 3]);
                  fprintf(stderr, "\n");
              }
      } }
}
