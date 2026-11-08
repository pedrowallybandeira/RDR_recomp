"""Copia work_v3/overlay/cellGcmSys.c e acrescenta o NV0039 (copia memoria a memoria)
no subcanal 1, ligado por GCM_SUBCH1_M2MF=1. Nao altera work_v3."""
import os as _os
# Raiz da arvore de trabalho privada (layout original: build_rdr2/, referencias/).
ROOT = _os.environ.get("RDR_ROOT", _os.getcwd())
import sys
src = ROOT + r"\build_rdr2\work_v3\overlay\cellGcmSys.c"
dst = sys.argv[1]
t = open(src, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in t else "\n"
t = t.replace("\r\n", "\n")

bloco = r'''
/* NV0039 -- memory to memory format (M2MF). libgcm binds it to subchannel 1;
 * cellGcmSetTransferData emits SET_CONTEXT_DMA_BUFFER_IN/OUT (0x184/0x188),
 * then OFFSET_IN .. BUFFER_NOTIFY (0x30C..0x328): a write of BUFFER_NOTIFY
 * starts the copy of LINE_COUNT lines of LINE_LENGTH_IN bytes. Only the
 * byte-for-byte format (0x101) is handled. GCM_SUBCH1_M2MF=1 turns it on:
 * a title that binds NV4097 to subchannel 1 (Twisted Metal) must keep the
 * old routing. */
static struct {
    u32 dma_in, dma_out, off_in, off_out, pitch_in, pitch_out, len, lines, fmt;
} s_m2mf;

static int gcm_s1_m2mf(void)
{
    static int on = -1;
    if (on < 0) { const char* e = getenv("GCM_SUBCH1_M2MF"); on = e ? atoi(e) : 0; }
    return on;
}

static void nv0039_transfer(void)
{
    static int logn = -1, nlog;
    if (logn < 0) { const char* e = getenv("GCM_M2MF_LOG"); logn = e ? atoi(e) : 0; }
    const u32 lines = s_m2mf.lines ? s_m2mf.lines : 1u, len = s_m2mf.len;
    const u32 in_loc  = s_m2mf.dma_in  == 0xFEED0001u ? RSX_LOCATION_MAIN : RSX_LOCATION_LOCAL;
    const u32 out_loc = s_m2mf.dma_out == 0xFEED0001u ? RSX_LOCATION_MAIN : RSX_LOCATION_LOCAL;
    int ok = len != 0 && s_m2mf.fmt == 0x101u;
    if (ok) {
        extern u8* vm_base;
        for (u32 i = 0; i < lines; i++) {
            u8* s = gcm_tiled_ptr(NULL, in_loc,  s_m2mf.off_in  + i * s_m2mf.pitch_in,  len);
            u8* d = gcm_tiled_ptr(NULL, out_loc, s_m2mf.off_out + i * s_m2mf.pitch_out, len);
            if (!s || !d) { ok = 0; break; }
            gcm_row_copy((u32)(d - vm_base), (u32)(s - vm_base), len);
        }
    }
    if (nlog < logn || (!ok && nlog < 16)) { nlog++;
        printf("[NV0039] %s in=%c:0x%08X out=%c:0x%08X len=%u lines=%u pitch=%u/%u fmt=0x%X%c",
               ok ? "copy" : "SKIP", in_loc == RSX_LOCATION_MAIN ? 'M' : 'L', s_m2mf.off_in,
               out_loc == RSX_LOCATION_MAIN ? 'M' : 'L', s_m2mf.off_out, len, lines,
               s_m2mf.pitch_in, s_m2mf.pitch_out, s_m2mf.fmt, 10); }
}

/* 1 when the method belongs to NV0039 and was consumed. */
static int gcm_m2mf_method(u32 m, u32 v)
{
    switch (m) {
    case 0x0184: s_m2mf.dma_in    = v; return 1;
    case 0x0188: s_m2mf.dma_out   = v; return 1;
    case 0x030C: s_m2mf.off_in    = v; return 1;
    case 0x0310: s_m2mf.off_out   = v; return 1;
    case 0x0314: s_m2mf.pitch_in  = v; return 1;
    case 0x0318: s_m2mf.pitch_out = v; return 1;
    case 0x031C: s_m2mf.len       = v; return 1;
    case 0x0320: s_m2mf.lines     = v; return 1;
    case 0x0324: s_m2mf.fmt       = v; return 1;
    case 0x0328: nv0039_transfer();    return 1;
    }
    return 0;
}

'''
ancora = "static void gcm_2d_method(u32 subch, u32 method, u32 data)"
assert t.count(ancora) == 1
t = t.replace(ancora, bloco.lstrip("\n") + ancora)

rapido = "if (!wdiag && count && (subch == 0 || (subch == 1 && !s1_2d)) &&"
assert t.count(rapido) == 1
t = t.replace(rapido, "if (!wdiag && count && (subch == 0 || (subch == 1 && !s1_2d && !gcm_s1_m2mf())) &&")

desp = "} else if (subch == 0 || (subch == 1 && !s1_2d)) {"
assert t.count(desp) == 1
t = t.replace(desp, "} else if (subch == 1 && gcm_s1_m2mf() && gcm_m2mf_method(m, vm_read32(dea))) {\n"
                    "                    /* NV0039, consumed */\n                " + desp)
open(dst, "w", encoding="utf-8", newline="").write(t.replace("\n", nl))
print("ok", dst)
