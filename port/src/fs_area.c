/* fs_area.c -- grow a host file to a given size without writing it.
 *
 * cellFsAllocateFileAreaWithoutZeroFill(path, size) is how RDR2 sizes its disk
 * cache (/dev_hdd1/cache.dat, 0x6FE02000 bytes). The game reads the size back on
 * the next boot and rebuilds the cache from scratch when it is wrong. SetEndOfFile
 * moves the end of file without zeroing the new space (NTFS reads it back as
 * zeroes), so 1.75 GB costs no writes. Returns 0, or -1 when the file cannot be
 * opened or extended. A file already that large is left as it is. */
#include <stdint.h>
#ifdef _WIN32
#include <windows.h>

int host_extend_file(const char* path, uint64_t size)
{
    HANDLE h = CreateFileA(path, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE,
                           NULL, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) return -1;
    LARGE_INTEGER cur, want;
    int rc = 0;
    want.QuadPart = (LONGLONG)size;
    if (!GetFileSizeEx(h, &cur)) rc = -1;
    else if (cur.QuadPart < want.QuadPart &&
             (!SetFilePointerEx(h, want, NULL, FILE_BEGIN) || !SetEndOfFile(h)))
        rc = -1;
    CloseHandle(h);
    return rc;
}
#else
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>

int host_extend_file(const char* path, uint64_t size)
{
    int fd = open(path, O_RDWR | O_CREAT, 0644);
    if (fd < 0) return -1;
    struct stat st;
    int rc = fstat(fd, &st);
    if (rc == 0 && (uint64_t)st.st_size < size) rc = ftruncate(fd, (off_t)size);
    close(fd);
    return rc == 0 ? 0 : -1;
}
#endif
