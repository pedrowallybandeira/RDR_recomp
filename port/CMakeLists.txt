# Red Dead Redemption (BLUS30418) port of ps3recomp.
# Derived from templates/project/CMakeLists.txt of ps3recomp (MIT,
# Copyright (c) 2026 Ned Heller / sp00nznet). Changes for this port:
# toolkit sources replaced by the patched copies in PORT_OVERLAY_DIR,
# lifted SPU jobs and DSP plugins read from PORT_LOCAL_DIR.
cmake_minimum_required(VERSION 3.20)
project(MyGameRecomp
    VERSION 0.1.0
    LANGUAGES C CXX
    DESCRIPTION "Recompiled PS3 game project (ps3recomp)"
)

# ---------------------------------------------------------------------------
# Standards
# ---------------------------------------------------------------------------
set(CMAKE_C_STANDARD 17)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Prefer Ninja if available
if(NOT CMAKE_GENERATOR MATCHES "Ninja" AND NOT DEFINED ENV{CMAKE_GENERATOR})
    message(STATUS "Tip: use -G Ninja for faster builds")
endif()

# ---------------------------------------------------------------------------
# The two directories this project is built from
# ---------------------------------------------------------------------------
# PS3RECOMP_DIR is the toolkit checkout: include/, runtime/, libs/, tools/.
# RECOMP_DIR is where the lifter's output for THIS game lives. They are
# separate on purpose -- a port keeps its generated code in its own tree and
# points at whatever toolkit checkout it is building against:
#
#   cmake -B build -G Ninja \
#         -DPS3RECOMP_DIR=/path/to/ps3recomp \
#         -DRECOMP_DIR=/path/to/my_game/recompiled
#
if(NOT DEFINED PS3RECOMP_DIR)
    # Default: this project is still sitting inside ps3recomp/templates/project/
    get_filename_component(PS3RECOMP_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../" ABSOLUTE)
endif()
get_filename_component(PS3RECOMP_DIR "${PS3RECOMP_DIR}" ABSOLUTE)

set(RECOMP_DIR "${CMAKE_CURRENT_SOURCE_DIR}/recompiled" CACHE PATH
    "Directory holding the lifter's output: ppu_recomp.h and the lifted sources")
get_filename_component(RECOMP_DIR "${RECOMP_DIR}" ABSOLUTE)

# Everything derived from the game stays out of the repository, under
# PORT_LOCAL_DIR (default: <repo>/local, git-ignored). PORT_OVERLAY_DIR holds
# the toolkit files patched by patches/ps3recomp-v0.19.0-rdr.patch, written by
# scripts/prepare_overlay.ps1.
set(PORT_LOCAL_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../local" CACHE PATH
    "Local, git-ignored tree: lifted SPU jobs/DSP plugins, optional lifted-file overrides")
set(PORT_OVERLAY_DIR "${PORT_LOCAL_DIR}/overlay" CACHE PATH
    "Patched toolkit files (scripts/prepare_overlay.ps1)")
get_filename_component(PORT_LOCAL_DIR "${PORT_LOCAL_DIR}" ABSOLUTE)
get_filename_component(PORT_OVERLAY_DIR "${PORT_OVERLAY_DIR}" ABSOLUTE)
if(NOT EXISTS "${PORT_OVERLAY_DIR}/cellSpurs.c")
    message(FATAL_ERROR
        "No patched toolkit files in ${PORT_OVERLAY_DIR}. Run "
        "scripts/prepare_overlay.ps1 first (it applies patches/ to a clean "
        "ps3recomp v0.19.0), or point -DPORT_OVERLAY_DIR= at them.")
endif()

message(STATUS "ps3recomp SDK:   ${PS3RECOMP_DIR}")
message(STATUS "Port overlay:    ${PORT_OVERLAY_DIR}")
message(STATUS "Lifted output:   ${RECOMP_DIR}")

if(NOT EXISTS "${RECOMP_DIR}/ppu_recomp.h")
    message(FATAL_ERROR
        "No ppu_recomp.h in ${RECOMP_DIR}.\n"
        "That header and the lifted sources beside it are what "
        "tools/ppu_lifter.py writes. Run the lifter, drop its output there, "
        "or point -DRECOMP_DIR= at wherever it already is.")
endif()

# The lifted translation units. A game's lift is hundreds of generated files,
# so they are globbed rather than listed; re-run CMake after a fresh lift.
file(GLOB RECOMP_SOURCES CONFIGURE_DEPENDS
    "${RECOMP_DIR}/*.c"
    "${RECOMP_DIR}/*.cpp"
)
if(NOT RECOMP_SOURCES)
    message(FATAL_ERROR
        "${RECOMP_DIR} has a ppu_recomp.h but no .c or .cpp beside it. The "
        "lifted functions and the function table live in those; without them "
        "there is nothing to run.")
endif()
# Optional: ppu_recomp_023.cpp with a probe in the voice-list walk of
# func_0066BEA8, which leaves a loop that runs 100,000 laps (a list head
# reading 0xCDCD) and logs it as [t54]. It is lifted game code, so it is never
# in the repository: scripts/gera_voz.py writes it into PORT_OVERLAY_DIR from
# your own lift. Without it the unmodified lifted file is used, and the boot
# can hang in that loop.
if(EXISTS "${PORT_OVERLAY_DIR}/ppu_recomp_023.cpp")
    list(FILTER RECOMP_SOURCES EXCLUDE REGEX "/ppu_recomp_023\\.cpp$")
    list(APPEND RECOMP_SOURCES "${PORT_OVERLAY_DIR}/ppu_recomp_023.cpp")
    message(STATUS "Lifted override: ppu_recomp_023.cpp ([t54] probe)")
endif()
list(LENGTH RECOMP_SOURCES RECOMP_SOURCE_COUNT)
message(STATUS "Lifted sources:  ${RECOMP_SOURCE_COUNT} file(s)")

# ---------------------------------------------------------------------------
# ps3recomp runtime library
# ---------------------------------------------------------------------------
# Built from source as a subdirectory rather than imported as a prebuilt
# archive. A static library carries none of its own link requirements, so an
# imported one arrives without SDL2, pthreads, the Metal frameworks or the
# Winsock/XInput imports -- the link then fails on every platform for a
# different reason. add_subdirectory hands all of that over with the target.
add_subdirectory("${PS3RECOMP_DIR}" "${CMAKE_BINARY_DIR}/ps3recomp_sdk"
                 EXCLUDE_FROM_ALL)

# The semaphore overlay raises SYS_SEMAPHORE_MAX. Its #includes stay relative to
# runtime/syscalls, as upstream, and only it uses the constant.
get_target_property(PORT_RUNTIME_SOURCES ps3recomp_runtime SOURCES)
# spu_channels/spu_drain: runtime-loaded SPU code runs as a call (analysis/history/gera.py).
# rsx_live_draw: MAX_SURFACES 512. sys_timer: PS3_USLEEP_WAIT_US (upstream #628).
# cellAvconfExt: PS3_AUDIO_OUT_CH=<2|6|8> (analysis/history/gera_v14a.py).
# sys_ppu_thread: PPU_PRIO_ABOVE=<n>, guest priority < n -> THREAD_PRIORITY_ABOVE_NORMAL.
# cellSysutil: BGM playback status in the PS3's values (PLAY = 0, STOP = 1).
list(FILTER PORT_RUNTIME_SOURCES EXCLUDE REGEX
     "(sys_semaphore|cellGcmSys|spurs_job|spu_channels|spu_drain|rsx_live_draw|rsx_fp_decompiler|sys_timer|cellAvconfExt|sys_ppu_thread|cellSysutil)\\.c$")
list(APPEND PORT_RUNTIME_SOURCES "${PORT_OVERLAY_DIR}/sys_semaphore.c"
                                 "${PORT_OVERLAY_DIR}/cellGcmSys.c"
                                 "${PORT_OVERLAY_DIR}/spurs_job.c"
                                 "${PORT_OVERLAY_DIR}/spu_channels.c"
                                 "${PORT_OVERLAY_DIR}/spu_drain.c"
                                 "${PORT_OVERLAY_DIR}/rsx_live_draw.c"
                                 "${PORT_OVERLAY_DIR}/sys_timer.c"
                                 "${PORT_OVERLAY_DIR}/cellAvconfExt.c"
                                 "${PORT_OVERLAY_DIR}/rsx_fp_decompiler.c"
                                 "${PORT_OVERLAY_DIR}/sys_ppu_thread.c"
                                 "${PORT_OVERLAY_DIR}/cellSysutil.c")
set_target_properties(ps3recomp_runtime PROPERTIES SOURCES "${PORT_RUNTIME_SOURCES}")
target_include_directories(ps3recomp_runtime PRIVATE "${PS3RECOMP_DIR}/runtime/syscalls"
                                                     "${PS3RECOMP_DIR}/runtime/spu"
                                                     "${PS3RECOMP_DIR}/libs/video"
                                                     "${PS3RECOMP_DIR}/libs/system")

# ---------------------------------------------------------------------------
# The HLE NID table
# ---------------------------------------------------------------------------
# Maps each firmware import NID onto the handler in the runtime that answers
# it. A port may keep a hand-curated one beside its lift; otherwise generate
# the canonical every-module table, which is what the toolkit's own boot
# harness uses.
if(EXISTS "${RECOMP_DIR}/ppu_hle_nids.cpp")
    set(HLE_NID_TABLE "${RECOMP_DIR}/ppu_hle_nids.cpp")
    message(STATUS "HLE NID table:   ${HLE_NID_TABLE}")
else()
    find_package(Python3 COMPONENTS Interpreter REQUIRED)
    set(HLE_NID_TABLE "${CMAKE_CURRENT_BINARY_DIR}/ppu_hle_nids.cpp")
    # The generator discovers handlers from library definitions. Rebuild when
    # an existing module changes, and reconfigure when a new module is added.
    file(GLOB_RECURSE HLE_NID_SOURCES CONFIGURE_DEPENDS
        "${PS3RECOMP_DIR}/libs/*.c")
    # A removed input cannot make the output older than a remaining dependency.
    # Track the list itself so deletions also remove stale handler references.
    set(HLE_NID_SOURCE_LIST "${CMAKE_CURRENT_BINARY_DIR}/hle_nid_sources.txt")
    file(GENERATE OUTPUT "${HLE_NID_SOURCE_LIST}" CONTENT "${HLE_NID_SOURCES}\n")
    add_custom_command(
        OUTPUT "${HLE_NID_TABLE}"
        COMMAND "${Python3_EXECUTABLE}"
                "${PS3RECOMP_DIR}/tools/gen_hle_nids.py"
                --out "${HLE_NID_TABLE}" --all
        DEPENDS "${PS3RECOMP_DIR}/tools/gen_hle_nids.py"
                "${PS3RECOMP_DIR}/tools/nid_database.py"
                ${HLE_NID_SOURCES} "${HLE_NID_SOURCE_LIST}"
        COMMENT "Generating the HLE NID -> handler table")
    message(STATUS "HLE NID table:   generated (every module)")
endif()

# ---------------------------------------------------------------------------
# The game executable
# ---------------------------------------------------------------------------
# The PPU boot scaffold is compiled here rather than taken from the runtime
# library: every one of these files #includes the lifter's per-game
# ppu_recomp.h, so they can only be built against a particular lift.
set(PS3RECOMP_SCAFFOLD
    "${PS3RECOMP_DIR}/runtime/ppu/ppu_loader.cpp"
    "${PS3RECOMP_DIR}/runtime/ppu/ppu_hle.cpp"
    "${PORT_OVERLAY_DIR}/ppu_fs.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/fs_area.c"
    "${PORT_OVERLAY_DIR}/ppu_sysprx.cpp"
)

# The overlay keeps the upstream #includes, which are relative to runtime/ppu.
set_source_files_properties("${PORT_OVERLAY_DIR}/ppu_fs.cpp"
    PROPERTIES COMPILE_OPTIONS "-I${PS3RECOMP_DIR}/runtime/ppu")

# MinGW has no clang-cl defaults: ppu_loader.cpp needs __try/__except and the
# Microsoft rule that lets ppu_resv_break go from extern to static.
if(MINGW)
    set_source_files_properties("${PS3RECOMP_DIR}/runtime/ppu/ppu_loader.cpp"
        PROPERTIES COMPILE_OPTIONS "-fms-extensions")
endif()

# ---------------------------------------------------------------------------
# Lifted SPU images (optional)
# ---------------------------------------------------------------------------
# A title that runs SPU work gets its images lifted into <SPU_DIR>/<image>/ by
# tools/spu_lifter.py, with a registration TU generated by
# tools/build_spu_workloads.py. cellSpurs dispatches them by content
# fingerprint, so the generated table is keyed to the images THIS build ships:
# a table generated from another release registers signatures that can never
# match, which is worse than shipping none. Both the table and the job-module
# registry self-register from constructors and are therefore optional -- a tree
# that has not lifted its SPU images yet configures and links without them.
set(SPU_DIR "${CMAKE_CURRENT_SOURCE_DIR}/spu" CACHE PATH
    "Directory holding the lifted SPU images (<SPU_DIR>/<image>/spu_recomp.c)")
option(PORT_ENABLE_SPU "Compile and register the title's lifted SPU images" ON)

set(PORT_SPU_INPUTS "" CACHE STRING
    "Input files to scan for all embedded SPU ELF programs (semicolon-separated decrypted ELF/PRX/data paths)")
set(SPU_SOURCES "")
if(PORT_ENABLE_SPU AND PORT_SPU_INPUTS)
    include("${PS3RECOMP_DIR}/cmake/PS3RecompSPU.cmake")
    ps3recomp_generate_spu("${CMAKE_CURRENT_BINARY_DIR}/generated_spu" ${PORT_SPU_INPUTS})
    list(APPEND SPU_SOURCES ${SPU_GENERATED_SOURCES}
         "${PS3RECOMP_DIR}/runtime/spu/spu_dispatch_mt.c")
    # Job binaries the title loads from its data files, so they are in no ELF:
    # captured with SPU_DUMP_MISS and lifted by analysis/tools/lift_jobs.py
    # into PORT_LOCAL_DIR/spu_jobs (lifted game code: local only).
    if(EXISTS "${PORT_LOCAL_DIR}/spu_jobs/jobs_register.c")
        file(GLOB PORT_SPU_JOBS CONFIGURE_DEPENDS "${PORT_LOCAL_DIR}/spu_jobs/*/spu_recomp.c")
        list(APPEND SPU_SOURCES ${PORT_SPU_JOBS} "${PORT_LOCAL_DIR}/spu_jobs/jobs_register.c")
    else()
        message(STATUS "  (no ${PORT_LOCAL_DIR}/spu_jobs -- those jobs fall back to the interpreter or MISS)")
    endif()
    # Multistream's DSP plugins, loaded at LS 0x36800 and lifted by
    # analysis/tools/lift_dsp.py into PORT_LOCAL_DIR/spu_dsp (local only).
    if(EXISTS "${PORT_LOCAL_DIR}/spu_dsp/dsp_register.c")
        file(GLOB PORT_SPU_DSP CONFIGURE_DEPENDS "${PORT_LOCAL_DIR}/spu_dsp/*/spu_recomp.c")
        list(APPEND SPU_SOURCES ${PORT_SPU_DSP} "${PORT_LOCAL_DIR}/spu_dsp/dsp_register.c")
    else()
        message(STATUS "  (no ${PORT_LOCAL_DIR}/spu_dsp -- DSP plugins run interpreted)")
    endif()
    # Multistream's MP3 decoder (flashMP3.pic from your firmware), loaded at LS 0x1A100
    # and lifted by analysis/tools/lift_mp3.py into PORT_LOCAL_DIR/spu_mp3 (local only:
    # it is translated firmware code). Interpreted, a mixer pass took ~170 ms.
    if(EXISTS "${PORT_LOCAL_DIR}/spu_mp3/mp3_register.c")
        file(GLOB PORT_SPU_MP3 CONFIGURE_DEPENDS "${PORT_LOCAL_DIR}/spu_mp3/*/spu_recomp.c")
        list(APPEND SPU_SOURCES ${PORT_SPU_MP3} "${PORT_LOCAL_DIR}/spu_mp3/mp3_register.c")
    else()
        message(STATUS "  (no ${PORT_LOCAL_DIR}/spu_mp3 -- the MP3 decoder runs interpreted)")
    endif()
elseif(PORT_ENABLE_SPU)
    file(GLOB SPU_LIFTED CONFIGURE_DEPENDS "${SPU_DIR}/*/spu_recomp.c")
    if(SPU_LIFTED)
        list(LENGTH SPU_LIFTED SPU_IMAGE_COUNT)
        message(STATUS "Lifted SPU:      ${SPU_IMAGE_COUNT} image(s)")
        # The musttail indirect-branch fast path. Excluded from the runtime
        # library on purpose (see the SDK root CMakeLists): it must be built
        # here, by clang, or the tail call degrades to a plain call and a guest
        # loop that branches indirectly walks the thread stack off its guard
        # page a few thousand iterations in.
        list(APPEND SPU_SOURCES ${SPU_LIFTED}
             "${PS3RECOMP_DIR}/runtime/spu/spu_dispatch_mt.c")
        # Generated beside the lift; each is present only once its generator
        # has been run, so each is included only if it is actually here.
        foreach(gen IN ITEMS spu_workloads.c jobmods_register.c taskset_policy_bytes.c)
            if(EXISTS "${SPU_DIR}/${gen}")
                list(APPEND SPU_SOURCES "${SPU_DIR}/${gen}")
            else()
                message(STATUS "  (no ${gen} -- not registered)")
            endif()
        endforeach()
    else()
        message(STATUS "Lifted SPU:      none found in ${SPU_DIR}")
    endif()
endif()

# Corrected copies of libs/spurs/cellSpurs.c and cellFiber.c. Each defines every
# symbol of its library member, so the linker never pulls the original. Their
# relative includes resolve through libs/spurs.
set(PORT_OVERLAY_SOURCES "${PORT_OVERLAY_DIR}/cellSpurs.c"
                         "${PORT_OVERLAY_DIR}/cellFiber.c")
set_source_files_properties(${PORT_OVERLAY_SOURCES} PROPERTIES
    COMPILE_OPTIONS "-I${PS3RECOMP_DIR}/libs/spurs;-w")
add_executable(${PROJECT_NAME}
    ${PORT_OVERLAY_SOURCES}
    main.cpp
    stubs.cpp
    ${PS3RECOMP_SCAFFOLD}
    ${HLE_NID_TABLE}
    ${RECOMP_SOURCES}
    ${SPU_SOURCES}
)

# The lifted SPU sources use bare #include "spu_context.h". Scope that include
# directory (and their flags) to those TUs alone: adding it to the whole target
# changes the compile command of every lifted PPU TU, and those are large enough
# that the needless rebuild is measured in tens of minutes.
#   SPU_USE_DISPATCH_MT -- route SPU_IB_DISPATCH through the musttail path.
#   -O2                 -- the target-wide -O1 exists for the huge PPU TUs; the
#                          SPU sources are small and decode-hot, so they get
#                          full optimization. The last -O on the line wins.
#   -mavx2 -mfma        -- spu_helpers.h gates its vector forms on these: without
#                          them each shufb and quadword rotate is a 16-byte loop
#                          and the EDGE jobs run about five times slower.
#   -ffp-contract=off   -- as the PPU sources and the runtime: -mfma must not let
#                          the compiler fuse a multiply and an add on its own.
if(SPU_SOURCES)
    # overlay/spu_inc: the runtime/spu headers with upstream #637 (SPU_LS_VEC) and
    # the LS probes behind SPU_LS_PROBES, which is 0 here.
    set_source_files_properties(${SPU_SOURCES} PROPERTIES
        INCLUDE_DIRECTORIES "${PORT_OVERLAY_DIR}/spu_inc;${PS3RECOMP_DIR}/runtime/spu"
        COMPILE_DEFINITIONS "SPU_USE_DISPATCH_MT;SPU_LS_PROBES=0")
    if(NOT MSVC OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
        set_source_files_properties(${SPU_SOURCES} PROPERTIES COMPILE_OPTIONS "-O2;-mavx2;-mfma;-ffp-contract=off")
    endif()
    # Audio code (the Multistream image, its MP3 decoder and DSP plugins) with native
    # float for spu_fa/fs/fm/fma/fms/fnms (src/audio_float): denormals flushed,
    # overflow saturated, at most 1 ulp from the exact SPU rounding. The exact
    # emulation made a mixer pass take ~14 ms for 10.7 ms of sound while the
    # title's MP3 stream played. The long name is the Multistream image's hash.
    set(PORT_SPU_FASTFLOAT
        "${CMAKE_CURRENT_BINARY_DIR}/generated_spu/spu_ed8663640d0259176e31478684089aed6bb7c46b6b56e871063e60153072e31b/spu_recomp.c"
        ${PORT_SPU_MP3} ${PORT_SPU_DSP})
    set_source_files_properties(${PORT_SPU_FASTFLOAT} PROPERTIES
        INCLUDE_DIRECTORIES "${CMAKE_CURRENT_SOURCE_DIR}/src/audio_float;${PORT_OVERLAY_DIR}/spu_inc;${PS3RECOMP_DIR}/runtime/spu"
        COMPILE_DEFINITIONS "SPU_USE_DISPATCH_MT;SPU_LS_PROBES=0;SPU_FAST_FLOAT")
endif()

# app.rc carries the icon, the version block and the manifest, and needs a
# resource compiler. Listing it as a source on a host that has none is not a
# link error, it is a "no rule to make" for a file nothing can consume.
if(WIN32 AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/app.rc")
    target_sources(${PROJECT_NAME} PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/app.rc")
endif()

target_include_directories(${PROJECT_NAME} PRIVATE
    "${RECOMP_DIR}"                            # the generated ppu_recomp.h
    "${PS3RECOMP_DIR}/include"
    "${PS3RECOMP_DIR}/runtime/ppu"
    "${PS3RECOMP_DIR}/runtime/spu"
    "${PS3RECOMP_DIR}/runtime/memory"
    "${PS3RECOMP_DIR}/runtime/syscalls"
    "${PS3RECOMP_DIR}/runtime/platform"        # win32_compat.h and friends
    "${PS3RECOMP_DIR}/libs/video"
    "${CMAKE_CURRENT_SOURCE_DIR}"
)

target_link_libraries(${PROJECT_NAME} PRIVATE
    ps3recomp_runtime
)

# The runtime is C++, and on Apple also Objective-C. Letting CMake infer the
# link language from the generated C would leave the C++ standard library out.
set_target_properties(${PROJECT_NAME} PROPERTIES LINKER_LANGUAGE CXX)

# Windows system import libraries. dbghelp symbolizes crash-handler addresses
# against the PDB, user32 and gdi32 are what the backend's window and its GDI
# present are made of, and winmm is timeBeginPeriod. None of the four names
# anything a POSIX linker can find; the D3D12 backend's own imports come in
# through the #pragma comment(lib) in libs/video/rsx_d3d12_backend.c.
if(WIN32)
    target_link_libraries(${PROJECT_NAME} PRIVATE
        dbghelp
        user32
        gdi32
        winmm
    )
endif()

# lld ignores the backend's #pragma comment(lib) under MinGW.
if(MINGW)
    target_link_libraries(${PROJECT_NAME} PRIVATE d3d12 dxgi d3dcompiler dxguid)
endif()

# ---------------------------------------------------------------------------
# Compiler-specific flags
# ---------------------------------------------------------------------------
if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    target_compile_options(${PROJECT_NAME} PRIVATE
        -Wall -Wextra -Wno-unused-parameter
        -fno-strict-aliasing
        # The lift spells PPC arithmetic as signed C arithmetic, which must wrap;
        # without this, clang exploits overflow UB (e.g. folds "x*x < 0" to false).
        -fwrapv
        # The target-wide -O1 the SPU note above relies on, for a build whose
        # configuration sets no optimisation level (no CMAKE_BUILD_TYPE, or one
        # CMake has no defaults for). Without it every lifted PPU TU compiled at
        # -O0: each static inline helper (ppc_rlw64, vmx_w, vm_read32_inl) is a
        # real call that spills to the stack, and those calls were most of the
        # PPU thread's profile. -O1 keeps the huge TUs' build time sane. Debug
        # and the optimised configurations keep their own levels.
        $<$<NOT:$<CONFIG:Debug,Release,RelWithDebInfo,MinSizeRel>>:-O1>
    )
elseif(MSVC)
    target_compile_options(${PROJECT_NAME} PRIVATE
        /W3 /wd4100 /wd4244 /wd4267
        /Zc:__cplusplus         # report correct __cplusplus value
        # ppu_recomp.h defines PPU_FENCE, the lowering of the guest's
        # sync/lwsync/eieio/isync, and in C that is <stdatomic.h>. The lifter
        # writes C++ by default, but --single-file writes ppu_recomp.c, and a
        # port that took it would not compile without this. The runtime's own
        # build already carries the same flag for the same reason.
        /experimental:c11atomics
    )
    target_compile_definitions(${PROJECT_NAME} PRIVATE
        _CRT_SECURE_NO_WARNINGS
    )
endif()

# The lifted translation units are machine-generated and can run to hundreds of
# thousands of lines each, so they get their own flags:
#
#   - warnings off. They are about generated code and nobody will act on them,
#     and at this volume they bury the diagnostics that matter.
#   - no floating-point contraction. arm64 fuses a multiply and an add by
#     default; a PPC fmadd is spelt as one where the lifter means one.
#   - /bigobj on MSVC. A single lifted file routinely passes the 65,536-section
#     limit of the default object format.
if(MSVC)
    set_source_files_properties(${RECOMP_SOURCES} PROPERTIES
        COMPILE_OPTIONS "/w;/bigobj")
else()
    set_source_files_properties(${RECOMP_SOURCES} PROPERTIES
        COMPILE_OPTIONS "-w;-ffp-contract=off")
endif()

# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------
install(TARGETS ${PROJECT_NAME} RUNTIME DESTINATION bin)

# ---------------------------------------------------------------------------
# The window launcher (macOS)
# ---------------------------------------------------------------------------
# A title that replaces its executable (sys_game_process_exitspawn, done by a
# port as an exec) loses its window with the old process image. The launcher
# holds the window for the whole session instead: it runs the port with
# PS3RECOMP_HOST_SURFACES set, the Metal backend renders into IOSurfaces it
# shares (libs/video/rsx_host_surface.h), and the image an exec brings up
# attaches to the same window again. One Objective-C file and no runtime
# library, so it builds in seconds:
#
#   ./MyGameRecomp_window [--title T] [--size WxH] -- ./MyGameRecomp <args>
if(APPLE)
    enable_language(OBJC)
    add_executable(${PROJECT_NAME}_window "${PS3RECOMP_DIR}/tools/host_window/host_window.m")
    target_include_directories(${PROJECT_NAME}_window PRIVATE "${PS3RECOMP_DIR}/libs/video")
    target_compile_definitions(${PROJECT_NAME}_window PRIVATE HOST_WINDOW_TITLE="${PROJECT_NAME}")
    target_compile_options(${PROJECT_NAME}_window PRIVATE -fobjc-arc -Wall -Wextra -Wno-unused-parameter)
    target_link_libraries(${PROJECT_NAME}_window PRIVATE
        "-framework AppKit" "-framework Metal" "-framework QuartzCore" "-framework IOSurface")
    install(TARGETS ${PROJECT_NAME}_window RUNTIME DESTINATION bin)
endif()
