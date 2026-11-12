/* spu_helpers.h -- native float for the audio SPU code (Red Dead Redemption port).
 *
 * Sits in an include directory that only the audio units get, ahead of the
 * toolkit's: it includes the original (#include_next) and, only in a unit built
 * with -DSPU_FAST_FLOAT, replaces spu_fa/fs/fm/fma/fms/fnms with native float:
 *   - inputs and result with a denormal (exponent 0) become zero, as on the SPU;
 *   - a result with exponent 255 (Inf/NaN on the host) saturates to the largest
 *     float with its sign;
 *   - fma/fms/fnms use a real FMA (one rounding).
 * Difference from the SPU: rounding is to nearest, not toward zero (at most 1 ulp),
 * and inputs with exponent 255 (numbers to the SPU) saturate. Without
 * -DSPU_FAST_FLOAT nothing changes. Upstream sp00nznet/ps3recomp#632
 * (SPU_FLOAT_RZ) solves the same cost exactly and for all SPU code. */
#include_next "spu_helpers.h"

#if defined(SPU_FAST_FLOAT) && !defined(SPU_FAST_FLOAT_APLICADO)
#define SPU_FAST_FLOAT_APLICADO 1
#include <immintrin.h>

static inline __attribute__((always_inline)) __m128 spuff_flush(__m128 v)
{
    const __m128i u = _mm_castps_si128(v);
    const __m128i e = _mm_and_si128(u, _mm_set1_epi32(0x7F800000));
    const __m128i den = _mm_cmpeq_epi32(e, _mm_setzero_si128());
    const __m128i inf = _mm_cmpeq_epi32(e, _mm_set1_epi32(0x7F800000));
    __m128i r = _mm_andnot_si128(den, u);
    const __m128i sat = _mm_or_si128(_mm_and_si128(u, _mm_set1_epi32((int)0x80000000u)), _mm_set1_epi32(0x7F7FFFFF));
    r = _mm_blendv_epi8(r, sat, inf);
    return _mm_castsi128_ps(r);
}
static inline __attribute__((always_inline)) __m128 spuff_ld(u128 a) { return spuff_flush(_mm_loadu_ps(a._f32)); }
static inline __attribute__((always_inline)) u128 spuff_st(__m128 v) { u128 r; _mm_storeu_ps(r._f32, spuff_flush(v)); return r; }

static inline __attribute__((always_inline)) u128 spuff_fa(u128 a, u128 b)   { return spuff_st(_mm_add_ps(spuff_ld(a), spuff_ld(b))); }
static inline __attribute__((always_inline)) u128 spuff_fs(u128 a, u128 b)   { return spuff_st(_mm_sub_ps(spuff_ld(a), spuff_ld(b))); }
static inline __attribute__((always_inline)) u128 spuff_fm(u128 a, u128 b)   { return spuff_st(_mm_mul_ps(spuff_ld(a), spuff_ld(b))); }
static inline __attribute__((always_inline)) u128 spuff_fma(u128 a, u128 b, u128 c)  { return spuff_st(_mm_fmadd_ps(spuff_ld(a), spuff_ld(b), spuff_ld(c))); }
static inline __attribute__((always_inline)) u128 spuff_fms(u128 a, u128 b, u128 c)  { return spuff_st(_mm_fmsub_ps(spuff_ld(a), spuff_ld(b), spuff_ld(c))); }
static inline __attribute__((always_inline)) u128 spuff_fnms(u128 a, u128 b, u128 c) { return spuff_st(_mm_fnmadd_ps(spuff_ld(a), spuff_ld(b), spuff_ld(c))); }

#define spu_fa(a, b)      spuff_fa((a), (b))
#define spu_fs(a, b)      spuff_fs((a), (b))
#define spu_fm(a, b)      spuff_fm((a), (b))
#define spu_fma(a, b, c)  spuff_fma((a), (b), (c))
#define spu_fms(a, b, c)  spuff_fms((a), (b), (c))
#define spu_fnms(a, b, c) spuff_fnms((a), (b), (c))
#endif
