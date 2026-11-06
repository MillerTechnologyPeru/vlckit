#!/usr/bin/env python3
"""
Writes .tbd link stubs for iOS 6's system libraries from a symbol dump.

The iOS 9.3 SDK's stubs describe iOS 9: they list functions iOS 6 lacks,
leave out ones it has (strcmp, strlen, ...), and expect libc++ to re-export
libc++abi, which it doesn't on iOS 6. Linking with these stubs ahead of the
SDK's (-L <out>/usr/lib) makes both configure checks and the final link see
exactly what iOS 6 exports.

libSystem's sub-libraries are flattened into one libSystem stub: binaries
bind to libSystem.B.dylib anyway, and dyld finds each symbol through its
re-exports at run time.

usage: mkstubs.py <exports.txt> <out dir>
"""

import collections
import os
import sys

LIBSYSTEM = "/usr/lib/libSystem.B.dylib"

# install name -> stub file names (the first is the real one)
NAMES = {
    LIBSYSTEM: ["libSystem.B.tbd", "libSystem.tbd"],
    "/usr/lib/libc++.1.dylib": ["libc++.1.tbd", "libc++.tbd"],
    "/usr/lib/libc++abi.dylib": ["libc++abi.tbd"],
    "/usr/lib/libobjc.A.dylib": ["libobjc.A.tbd", "libobjc.tbd"],
    "/usr/lib/libz.1.dylib": ["libz.1.tbd", "libz.tbd"],
    "/usr/lib/libbz2.1.0.dylib": ["libbz2.1.0.tbd", "libbz2.tbd"],
    "/usr/lib/libiconv.2.dylib": ["libiconv.2.tbd", "libiconv.tbd"],
    "/usr/lib/libsqlite3.dylib": ["libsqlite3.tbd"],
    "/usr/lib/libresolv.9.dylib": ["libresolv.9.tbd", "libresolv.tbd"],
    "/usr/lib/libxml2.2.dylib": ["libxml2.2.tbd", "libxml2.tbd"],
}


def read(path):
    symbols = collections.defaultdict(set)
    reexports = collections.defaultdict(list)
    with open(path) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            lib, rest = line.split(None, 1)
            rest = rest.strip()
            if rest.startswith("!reexport "):
                reexports[lib].append(rest.split(None, 1)[1])
            else:
                symbols[lib].add(rest)
    # flatten libSystem
    for child in reexports[LIBSYSTEM]:
        symbols[LIBSYSTEM] |= symbols.pop(child, set())
    return symbols


def tbd(install_name, symbols):
    lines = [
        "---",
        "archs:                 [ armv7 ]",
        "platform:              ios",
        "install-name:          %s" % install_name,
        "current-version:       1",
        "compatibility-version: 1",
        "exports:",
        "  - archs:              [ armv7 ]",
        "    symbols:            [ %s ]" % ",\n                          ".join(sorted(symbols)),
        "...",
        "",
    ]
    return "\n".join(lines)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__.strip().splitlines()[-1])
    symbols = read(sys.argv[1])
    libdir = os.path.join(sys.argv[2], "usr", "lib")
    os.makedirs(libdir, exist_ok=True)
    for install_name, files in NAMES.items():
        if not symbols.get(install_name):
            sys.exit("no symbols for %s in %s" % (install_name, sys.argv[1]))
        text = tbd(install_name, symbols[install_name])
        for name in files:
            with open(os.path.join(libdir, name), "w") as f:
                f.write(text)


if __name__ == "__main__":
    main()
