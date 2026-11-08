"""Liga ou desliga a sonda passiva da tentativa 37 sobre a copia de trabalho.

uso: t37_liga.py <work_v3> liga|desliga
Desligar devolve os arquivos ao texto anterior; os spu_recomp.c voltam com copia da v9.
"""
import os
import shutil
import sys


def le(p):
    b = open(p, "rb").read()
    return b.decode("utf-8").replace("\r\n", "\n"), b"\r\n" in b


def grava(p, t, crlf):
    if crlf:
        t = t.replace("\n", "\r\n")
    open(p, "wb").write(t.encode("utf-8"))


def troca(t, velho, novo, nome):
    if t.count(velho) != 1:
        sys.exit(f"{nome}: {t.count(velho)} ocorrencias")
    return t.replace(velho, novo)


GCM = [
    ("static u32 s_fifo_getoff  = 0;\n/* Backward JUMPs",
     "static u32 s_fifo_getoff  = 0;\n"
     "/* TEMP attempt 37 */\n"
     "extern void rdr2_t37_rsx(u32 m, u32 v, u32 getoff, int path);\n"
     "extern void rdr2_t37_nv406e(u32 m, u32 v, u32 sema_off, u32 getoff, int path);\n"
     "void rdr2_t37_gcm_state(u32* put, u32* get, u32* getoff)\n"
     "{\n"
     "    *put = vm_read32(GCM_CONTROL_GUEST_ADDR + 0);\n"
     "    *get = vm_read32(GCM_CONTROL_GUEST_ADDR + 4);\n"
     "    *getoff = s_fifo_getoff;\n"
     "}\n"
     "extern void rdr2_t40_resync(const char* why, u32 from, u32 put, u32 land);\n"
     "extern void rdr2_t40_resync_end(u32 from, u32 land, u32 stop, unsigned fences, unsigned labels);\n"
     "extern void rdr2_t40_recycle(u32 ctx, u32 begin, u32 current);\n"
     "extern void rdr2_t42_put(u32 ea, u32 size);\n"
     "extern void rdr2_t42_read(u32 io, u32 w);\n"
     "void rdr2_t40_gcm_ctx(u32* out_ea, u32* ours)\n"
     "{\n"
     "    *out_ea = s_gcm_ctx_out_ea;\n"
     "    *ours = s_gcm_context_ea;\n"
     "}\n"
     "/* Backward JUMPs"),
    ("    extern u32 g_rsx_last_reference;\n    /* #466:",
     "    extern u32 g_rsx_last_reference;\n"
     "    if (m == 0x01A4u || m == 0x1D6Cu || m == 0x1D70u || m == 0x1D74u || m == 0x1800u ||\n"
     "        m == 0x01A8u || m == 0x0050u)\n"
     "        rdr2_t37_rsx(m, v, s_fifo_getoff, 0);\n"
     "    /* #466:"),
    ("                    if (m == 0x64u)      s_sema_offset = v;\n",
     "                    if (m == 0x64u || m == 0x6Cu) rdr2_t37_nv406e(m, v, s_sema_offset, s_fifo_getoff, 0);\n"
     "                    if (m == 0x64u)      s_sema_offset = v;\n"),
    ("    /* Sweep only the range still being skipped; the walker will consume the\n",
     "    rdr2_t40_resync(why, *getoff, put, land);\n"
     "    /* Sweep only the range still being skipped; the walker will consume the\n"),
    ("        unsigned labels = 0;\n"
     "        for (u32 io = from; io + 4 <= land; ) {\n"
     "            const u32 ea = gcm_io2ea(io); if (!ea) break;\n",
     "        unsigned labels = 0;\n"
     "        u32 t40_stop = from;\n"
     "        for (u32 io = from; io + 4 <= land; ) {\n"
     "            t40_stop = io;\n"
     "            const u32 ea = gcm_io2ea(io); if (!ea) break;\n"),
    ("                    atomic_thread_fence(memory_order_release);\n"
     "                    vm_write32(GCM_LABEL_GUEST_BASE + (s_sema_offset & 0xFFFFu), v);\n"
     "                    labels++;\n",
     "                    atomic_thread_fence(memory_order_release);\n"
     "                    vm_write32(GCM_LABEL_GUEST_BASE + (s_sema_offset & 0xFFFFu), v);\n"
     "                    rdr2_t37_nv406e(m, v, s_sema_offset, io, 1);\n"
     "                    labels++;\n"),
    ("                    rsx_process_method(&s_resync_state, m, v);\n",
     "                    rdr2_t37_rsx(m, v, io, 1);\n"
     "                    rsx_process_method(&s_resync_state, m, v);\n"),
    ("        if (rescued || labels) { static int m = 0; if (PS3_LOG_FIRST(m, 8))\n",
     "        rdr2_t40_resync_end(from, land, t40_stop, rescued, labels);\n"
     "        if (rescued || labels) { static int m = 0; if (PS3_LOG_FIRST(m, 8))\n"),
    ("    u32 current = vm_read32(ctx_ea + 0x8);\n"
     "    if (current <= begin) return;                       /* nothing to recycle */\n",
     "    u32 current = vm_read32(ctx_ea + 0x8);\n"
     "    rdr2_t40_recycle(ctx_ea, begin, current);\n"
     "    if (current <= begin) return;                       /* nothing to recycle */\n"),
    ("void gcm_note_spu_put(u32 ea, u32 size)\n{\n    if (!size || size > 0x40000u) return;\n",
     "void gcm_note_spu_put(u32 ea, u32 size)\n{\n    rdr2_t42_put(ea, size);\n"
     "    if (!size || size > 0x40000u) return;\n"),
    ("        if (w && ((w & 0xE0000003u) == 0x20000000u || (w & 3u) == 1u || (w & 3u) == 2u)) {\n"
     "            s_cf_off[s_cf_i % 8] = s_fifo_getoff;",
     "        if (s_fifo_getoff - 0x5000u < 0xD000u) rdr2_t42_read(s_fifo_getoff, w);\n"
     "        if (w && ((w & 0xE0000003u) == 0x20000000u || (w & 3u) == 1u || (w & 3u) == 2u)) {\n"
     "            s_cf_off[s_cf_i % 8] = s_fifo_getoff;"),
]
SEM = [("    ppu_thread_note_block(ctx->thread_id);   /* PS3_PRIO_START */\n"
        "    int64_t r = sys_semaphore_wait_impl(ctx);\n",
        "    ppu_thread_note_block(ctx->thread_id);   /* PS3_PRIO_START */\n"
        "    extern void rdr2_t42_sema(uint32_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t);\n"
        "    const uint32_t t42_id = (uint32_t)ctx->gpr[3], t42_lr = (uint32_t)ctx->lr, t42_sp = (uint32_t)ctx->gpr[1];\n"
        "    rdr2_t42_sema(1, t42_id, (uint32_t)ctx->thread_id, t42_lr, t42_sp, 0);\n"
        "    int64_t r = sys_semaphore_wait_impl(ctx);\n"
        "    rdr2_t42_sema(2, t42_id, (uint32_t)ctx->thread_id, t42_lr, t42_sp, (uint32_t)r);\n"),
       ("    uint32_t sem_id = LV2_ARG_U32(ctx, 0);\n"
        "    int32_t  count  = LV2_ARG_S32(ctx, 1);\n\n"
        "    { static int _n=0, st = -1; if (st < 0) st = getenv(\"SEMTID\") ? 1 : 0;\n",
        "    uint32_t sem_id = LV2_ARG_U32(ctx, 0);\n"
        "    int32_t  count  = LV2_ARG_S32(ctx, 1);\n"
        "    { extern void rdr2_t42_sema(uint32_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t);\n"
        "      rdr2_t42_sema(3, sem_id, (uint32_t)ctx->thread_id, (uint32_t)ctx->lr, (uint32_t)ctx->gpr[1], (uint32_t)count); }\n\n"
        "    { static int _n=0, st = -1; if (st < 0) st = getenv(\"SEMTID\") ? 1 : 0;\n")]
JOB = [("    spu_run_with_halt(entry, &ctx);\n",
        "    { extern void rdr2_t37_job_begin(int, uint32_t);\n"
        "      extern void rdr2_t37_job_end(int, uint32_t, int, const spu_context*);\n"
        "      rdr2_t37_job_begin(image_id, job_ea);\n"
        "      const int t37_halted = spu_run_with_halt(entry, &ctx);\n"
        "      rdr2_t37_job_end(image_id, job_ea, t37_halted, &ctx); }\n")]
CMAKE = [('"${CMAKE_CURRENT_SOURCE_DIR}/../spu_jobs/jobs_register.c")',
          '"${CMAKE_CURRENT_SOURCE_DIR}/../spu_jobs/jobs_register.c"\n'
          '         "${CMAKE_CURRENT_SOURCE_DIR}/../overlay/rdr2_t37.c")')]
# cellGcmGetLabelAddress com contexto: mesmo retorno, mais r13 e lr de quem chamou.
MAIN = [("/* ---------------------------------------------------------------------------\n"
         " * What the scaffold gives this file\n",
         "/* TEMP attempt 40 */\n"
         "extern \"C\" void* cellGcmGetLabelAddress(uint8_t index);\n"
         "extern \"C\" void rdr2_t40_poll(uint32_t r13, uint32_t lr);\n"
         "extern \"C\" void ps3_hle_register_ctx(uint32_t nid, const char* name, void (*fn)(ppu_context*));\n"
         "static void t40_label_address(ppu_context* c)\n"
         "{\n"
         "    rdr2_t40_poll((uint32_t)c->gpr[13], (uint32_t)c->lr);\n"
         "    c->gpr[3] = (uint64_t)(uintptr_t)cellGcmGetLabelAddress((uint8_t)c->gpr[3]);\n"
         "}\n\n"
         "/* ---------------------------------------------------------------------------\n"
         " * What the scaffold gives this file\n"),
        ("    lv2_init_syscalls();     /* the lv2 syscall table */\n",
         "    ps3_hle_register_ctx(0xF80196C1u, \"cellGcmGetLabelAddress\", t40_label_address);\n"
         "    lv2_init_syscalls();     /* the lv2 syscall table */\n")]


def main():
    w, modo = sys.argv[1:3]
    for rel, pares in (("overlay/cellGcmSys.c", GCM), ("overlay/spurs_job.c", JOB), ("project/CMakeLists.txt", CMAKE),
                       ("project/main.cpp", MAIN), ("overlay/sys_semaphore.c", SEM)):
        p = os.path.join(w, rel)
        t, crlf = le(p)
        for velho, novo in pares:
            t = troca(t, velho, novo, rel) if modo == "liga" else troca(t, novo, velho, rel)
        grava(p, t, crlf)
    a = os.path.join(w, "tools", "rdr2_t37.c")
    b = os.path.join(w, "overlay", "rdr2_t37.c")
    if modo == "liga":
        shutil.copy(a, b)
    else:
        os.remove(b)
    print(modo, "ok")


if __name__ == "__main__":
    main()
