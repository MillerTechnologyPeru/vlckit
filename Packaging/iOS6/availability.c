/*
 * @available / __builtin_available support for iOS 6.
 *
 * Clang implements these with __isOSVersionAtLeast() and
 * __isPlatformVersionAtLeast() from compiler-rt. Xcode's copy needs
 * _availability_version_check() (iOS 14) and is Thumb code that hands a
 * local function to dispatch_once, which Xcode's linker can't point to
 * correctly. MobileVLCKit's iOS 6 build defines both here instead, in ARM
 * code, reading the version from SystemVersion.plist as compiler-rt does on
 * older systems. Being in MobileVLCKit, they come before compiler-rt on the
 * link line, so its versions aren't linked.
 */

#include <CoreFoundation/CoreFoundation.h>
#include <dispatch/dispatch.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

static int32_t os_major, os_minor, os_subminor;
static dispatch_once_t os_version_once;

static void read_os_version(void *ctx)
{
    (void)ctx;
    FILE *f = fopen("/System/Library/CoreServices/SystemVersion.plist", "rb");
    if (f == NULL)
        return;

    char buf[4096];
    size_t len = fread(buf, 1, sizeof buf, f);
    fclose(f);

    CFDataRef data = CFDataCreateWithBytesNoCopy(NULL, (const UInt8 *)buf, len,
                                                 kCFAllocatorNull);
    if (data == NULL)
        return;
    CFPropertyListRef plist = CFPropertyListCreateWithData(NULL, data,
                                                           kCFPropertyListImmutable,
                                                           NULL, NULL);
    CFRelease(data);
    if (plist == NULL)
        return;

    if (CFGetTypeID(plist) == CFDictionaryGetTypeID()) {
        CFTypeRef version = CFDictionaryGetValue(plist, CFSTR("ProductVersion"));
        char str[32];
        if (version != NULL && CFGetTypeID(version) == CFStringGetTypeID()
         && CFStringGetCString(version, str, sizeof str, kCFStringEncodingUTF8))
            sscanf(str, "%d.%d.%d", &os_major, &os_minor, &os_subminor);
    }
    CFRelease(plist);
}

int32_t __isOSVersionAtLeast(int32_t major, int32_t minor, int32_t subminor)
{
    dispatch_once_f(&os_version_once, NULL, read_os_version);
    if (os_major != major)
        return os_major > major;
    if (os_minor != minor)
        return os_minor > minor;
    return os_subminor >= subminor;
}

int32_t __isPlatformVersionAtLeast(uint32_t platform, uint32_t major,
                                   uint32_t minor, uint32_t subminor)
{
    (void)platform; /* this build only runs on iOS */
    return __isOSVersionAtLeast((int32_t)major, (int32_t)minor, (int32_t)subminor);
}
