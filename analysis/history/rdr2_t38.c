/* rdr2_t38.c -- temporary, passive observation for attempt 38.
 *
 * Off unless RDR2_T38_DIR is set. Records how each job's descriptor reads under
 * the two paths its entry code can take, for the first instances of each image
 * and every 512th after that. Guest memory and the local store are only read.
 */
#include "spu_context.h"
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

extern uint8_t* vm_base;

#define N_IMG 32

static struct { int image; unsigned n, inout, zero_out, both; } s_img[N_IMG];
static SRWLOCK s_lock = SRWLOCK_INIT;
static FILE* s_f;
static int s_state;

static uint32_t be32(uint32_t ea)
{
    return _byteswap_ulong(*(const uint32_t*)(vm_base + ea));
}

static uint32_t ls32(const spu_context* c, uint32_t a)
{
    const uint8_t* p = c->ls + a;
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3];
}

static int readable(uint32_t ea)
{
    MEMORY_BASIC_INFORMATION mi;
    if (ea < 0x10000u || !VirtualQuery(vm_base + ea, &mi, sizeof mi)) return 0;
    return mi.State == MEM_COMMIT && !(mi.Protect & (PAGE_NOACCESS | PAGE_GUARD));
}

void rdr2_t38_job(int image_id, uint32_t job_ea, uint32_t ctx_ls, const spu_context* c)
{
    if (s_state == 2) return;
    AcquireSRWLockExclusive(&s_lock);
    if (!s_state) {
        char path[460];
        const char* d = getenv("RDR2_T38_DIR");
        s_state = 2;
        if (d && *d) {
            snprintf(path, sizeof path, "%s\\descritores.txt", d);
            s_f = fopen(path, "w");
            if (s_f) s_state = 1;
        }
    }
    if (s_state != 1) { ReleaseSRWLockExclusive(&s_lock); return; }
    int i = 0;
    for (; i < N_IMG; i++)
        if (s_img[i].image == image_id || !s_img[i].image) break;
    if (i == N_IMG) { ReleaseSRWLockExclusive(&s_lock); return; }
    s_img[i].image = image_id;
    const unsigned n = ++s_img[i].n;
    const uint32_t use_io = be32(job_ea + 0x10), size_in = be32(job_ea + 0x14), size_out = be32(job_ea + 0x18);
    const uint32_t size_dma = be32(job_ea + 0x08) & 0xFFFFu, size_cache = be32(job_ea + 0x24);
    s_img[i].inout += use_io != 0;
    s_img[i].zero_out += size_out == 0;
    s_img[i].both += use_io != 0 && size_out == 0;
    if (n <= 6 || (n & 511u) == 0) {
        const uint32_t nd = size_dma / 8u, nc = size_cache / 8u;
        const uint32_t base = job_ea + 0x30u + (nd + nc) * 8u;
        const uint32_t caminho_sem = be32(base), caminho_com = be32(base + 8u);
        fprintf(s_f, "img=%d n=%u job=%08X io=%u in=%X out=%X dma=%u cache=%u obuf=%05X iobuf=%05X sbuf=%05X "
                     "cont_sem_obuf=%X cont_com_obuf=%X tot[inout=%u out0=%u ambos=%u]\n",
                image_id, n, job_ea, use_io, size_in, size_out, nd, nc,
                ls32(c, ctx_ls + 0x1Cu), ls32(c, ctx_ls + 0x00u), ls32(c, ctx_ls + 0x20u),
                caminho_sem, caminho_com, s_img[i].inout, s_img[i].zero_out, s_img[i].both);
        fprintf(s_f, "  desc+30:");
        for (uint32_t o = 0x30; o < 0xA0; o += 4) fprintf(s_f, " %08X", be32(job_ea + o));
        fprintf(s_f, "\n");
        /* The list the job's GET would address if the count were read one
         * element earlier: EA and element count are the first two words. */
        if (n <= 3 && caminho_sem >= 2u && caminho_sem <= 64u) {
            const uint32_t ea = be32(base + 4u), cnt = be32(base + 8u);
            if (readable(ea) && cnt && cnt <= 64u) {
                fprintf(s_f, "  lista ea=%08X n=%u:", ea, cnt);
                for (uint32_t o = 0; o < cnt * 28u && o < 0x100u; o += 4) {
                    if ((o % 28u) == 0) fprintf(s_f, "\n    ");
                    fprintf(s_f, " %08X", be32(ea + o));
                }
                fprintf(s_f, "\n");
            }
        }
        fflush(s_f);
    }
    ReleaseSRWLockExclusive(&s_lock);
}
