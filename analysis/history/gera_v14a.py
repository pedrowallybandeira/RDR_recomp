"""Experimento sobre a v14: cache.dat com o tamanho pedido e saida de audio estereo.

1. overlay/ppu_fs.cpp: cellFsAllocateFileAreaWithoutZeroFill(path, size) passa a
   aumentar o arquivo (fs_area.c). Antes devolvia CELL_OK sem fazer nada, e o RDR
   reconstruia o cache.dat a cada boot.
2. libs/misc/cellAvconfExt.c: PS3_AUDIO_OUT_CH=<2|6|8> limita o maximo de canais
   LPCM de cellAudioOutGetSoundAvailability. O RPCS3 anuncia 2, e o RDR escolhe
   "8->2 channel downmix"; aqui escolhia 6. Sem a variavel, o valor de antes (6).
"""
import os as _os
# Raiz da arvore de trabalho privada (layout original: build_rdr2/, referencias/).
ROOT = _os.environ.get("RDR_ROOT", _os.getcwd())
W = ROOT + "/build_rdr2/work_v3"
T = ROOT + "/referencias/ps3recomp-v0.18.0"
S = ROOT + "/build_rdr2/exp_t49/v14"


def troca(txt, velho, novo):
    if "\r\n" in txt:
        velho = velho.replace("\n", "\r\n")
        novo = novo.replace("\n", "\r\n")
    assert txt.count(velho) == 1, velho[:60]
    return txt.replace(velho, novo)


s = open(W + "/overlay/ppu_fs.cpp", encoding="utf-8", newline="").read()
s = troca(s, """/* File-area preallocation (LBP cache warm-up spams this): host filesystems
 * grow files on write, so accepting is correct -- no preallocation needed. */
static void cellFsAllocateFileAreaWithoutZeroFill(ppu_context* ctx) { ctx->gpr[3] = CELL_OK; }
""", """/* cellFsAllocateFileAreaWithoutZeroFill(path, u64 size): give the file that size.
 * Accepting it without doing anything left RDR2's cache.dat at whatever size its
 * writes had reached, and the game, which checks the size on the next boot,
 * rebuilt the cache from scratch every time. The new space is not written
 * (fs_area.c). */
extern "C" int host_extend_file(const char* path, uint64_t size);
static void cellFsAllocateFileAreaWithoutZeroFill(ppu_context* ctx)
{
    char gpath[1024], hpath[1100];
    guest_strcpy(gpath, (uint32_t)ctx->gpr[3], sizeof gpath);
    host_path(hpath, sizeof hpath, gpath);
    const int rc = host_extend_file(hpath, (uint64_t)ctx->gpr[4]);
    { static int _n = 0;
      if (PS3_LOG_FIRST(_n, 8))
          fprintf(stderr, "[fs] AllocateFileArea '%s' -> '%s' size=0x%llX rc=%d\\n", gpath, hpath,
                  (unsigned long long)ctx->gpr[4], rc); }
    ctx->gpr[3] = rc == 0 ? CELL_OK : (uint64_t)(int64_t)CELL_FS_EIO;
}
""")
open(S + "/ppu_fs.cpp", "w", encoding="utf-8", newline="").write(s)

a = open(T + "/libs/misc/cellAvconfExt.c", encoding="utf-8", newline="").read()
a = troca(a, '#include "cellAvconfExt.h"', '#include "' + T + '/libs/misc/cellAvconfExt.h"')
a = troca(a, """    if (type == CELL_AUDIO_OUT_CODING_TYPE_LPCM) {
        if (fs & CELL_AUDIO_OUT_FS_48KHZ) return CELL_AUDIO_OUT_CHNUM_6;  /* 5.1 (A/B: was 8) */
""", """    if (type == CELL_AUDIO_OUT_CODING_TYPE_LPCM) {
        /* PS3_AUDIO_OUT_CH=<n>: the LPCM maximum to report (RPCS3 with a stereo
         * device reports 2, and RDR2 then mixes down to 2 channels). */
        static int s_ch = -1;
        if (s_ch < 0) { const char* e = getenv("PS3_AUDIO_OUT_CH"); s_ch = e ? atoi(e) : 0; }
        if (s_ch == 2 || s_ch == 6 || s_ch == 8) return s_ch;
        if (fs & CELL_AUDIO_OUT_FS_48KHZ) return CELL_AUDIO_OUT_CHNUM_6;  /* 5.1 (A/B: was 8) */
""")
open(S + "/cellAvconfExt.c", "w", encoding="utf-8", newline="").write(a)
print("gerado")
