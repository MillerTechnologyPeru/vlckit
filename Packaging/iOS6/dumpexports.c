/*
 * dumpexports: print the external symbols a loaded dylib defines, on device.
 *
 * iOS 6 keeps its system libraries in the dyld shared cache, so they can't be
 * read off the file system. This loads each library given on the command line
 * and walks its symbol table in memory. The output ("<install name> <symbol>"
 * per line) feeds mkstubs.py, which writes .tbd stubs that match iOS 6.
 *
 * Build: clang -arch armv7 -marm -miphoneos-version-min=6.0 -isysroot <sdk> dumpexports.c -o dumpexports
 */

#include <dlfcn.h>
#include <mach-o/dyld.h>
#include <mach-o/loader.h>
#include <mach-o/nlist.h>
#include <stdint.h>
#include <stdio.h>

/* the iOS 9.3 SDK's stubs don't list strcmp for armv7 */
static int streq(const char *a, const char *b)
{
    while (*a && *a == *b)
        a++, b++;
    return *a == *b;
}

static void dump(const char *path, const struct mach_header *mh, intptr_t slide)
{
    const struct load_command *lc = (const void *)(mh + 1);
    const struct symtab_command *symtab = NULL;
    const struct segment_command *linkedit = NULL, *text = NULL;

    for (uint32_t i = 0; i < mh->ncmds; i++) {
        if (lc->cmd == LC_SYMTAB)
            symtab = (const void *)lc;
        else if (lc->cmd == LC_SEGMENT) {
            const struct segment_command *seg = (const void *)lc;
            if (streq(seg->segname, SEG_LINKEDIT))
                linkedit = seg;
            else if (streq(seg->segname, SEG_TEXT))
                text = seg;
        } else if (lc->cmd == LC_REEXPORT_DYLIB) {
            const struct dylib_command *d = (const void *)lc;
            printf("%s !reexport %s\n", path, (const char *)d + d->dylib.name.offset);
        }
        lc = (const void *)((const char *)lc + lc->cmdsize);
    }
    if (!symtab || !linkedit || !text)
        return;

    /* file offsets in LC_SYMTAB are relative to __LINKEDIT's file offset */
    uintptr_t base = linkedit->vmaddr + slide - linkedit->fileoff;
    const struct nlist *syms = (const void *)(base + symtab->symoff);
    const char *strs = (const char *)(base + symtab->stroff);

    for (uint32_t i = 0; i < symtab->nsyms; i++) {
        const struct nlist *n = &syms[i];
        if ((n->n_type & N_STAB) || !(n->n_type & N_EXT))
            continue;
        if ((n->n_type & N_TYPE) != N_SECT && (n->n_type & N_TYPE) != N_INDR)
            continue;
        printf("%s %s\n", path, strs + n->n_un.n_strx);
    }
}

int main(int argc, char **argv)
{
    setvbuf(stdout, NULL, _IOLBF, 0);
    for (int a = 1; a < argc; a++) {
        if (!dlopen(argv[a], RTLD_LAZY | RTLD_GLOBAL)) {
            fprintf(stderr, "%s: %s\n", argv[a], dlerror());
            continue;
        }
        for (uint32_t i = 0; i < _dyld_image_count(); i++) {
            if (streq(_dyld_get_image_name(i), argv[a]))
                dump(argv[a], _dyld_get_image_header(i), _dyld_get_image_vmaddr_slide(i));
        }
    }
    return 0;
}
