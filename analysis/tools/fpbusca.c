/* Procura no ELF um trecho cujo fingerprint FNV-1a bata com o de um job.
 * uso: fpbusca <elf> <fp_hex> <tamanho> <passo> [saida.bin] */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char** argv)
{
    if (argc < 5) return 2;
    FILE* f = fopen(argv[1], "rb");
    if (!f) return 3;
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    uint8_t* b = malloc(n);
    if (fread(b, 1, n, f) != (size_t)n) return 4;
    fclose(f);
    uint64_t alvo = strtoull(argv[2], 0, 16);
    long tam = atol(argv[3]), passo = atol(argv[4]);
    int achados = 0;
    for (long o = 0; o + tam <= n; o += passo) {
        uint64_t h = 1469598103934665603ULL;
        for (long i = 0; i < tam; i++) {
            h ^= b[o + i];
            h *= 1099511628211ULL;
        }
        if (h == alvo) {
            printf("achado em offset 0x%lX\n", o);
            if (argc > 5 && !achados) {
                FILE* s = fopen(argv[5], "wb");
                if (s) { fwrite(b + o, 1, tam, s); fclose(s); }
            }
            achados++;
        }
    }
    printf("total %d em %ld bytes\n", achados, n);
    return achados ? 0 : 1;
}
