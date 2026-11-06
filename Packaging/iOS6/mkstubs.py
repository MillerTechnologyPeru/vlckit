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

With --sdk, the stubs also list the SDK's symbols. That's for linking apps:
@available fallbacks reference newer symbols weakly, and a weak reference
still needs a definition at link time. check_imports.py then makes sure
that every strong import exists on iOS 6.

usage: mkstubs.py [--sdk <sdk>] <exports.txt> <out dir>
"""

import collections
import glob
import os
import re
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


def sdk_symbols(sdk, install_name):
    """Symbols the SDK's .tbd stubs export for an install name (armv7)."""
    lib = os.path.join(sdk, "usr", "lib")
    if install_name == LIBSYSTEM:
        # not libcompiler_rt: compiler builtins iOS 6 lacks (__extendhfsf2...)
        # must come from the static compiler-rt instead
        files = [os.path.join(lib, "libSystem.B.tbd")] + \
            [f for f in glob.glob(os.path.join(lib, "system", "*.tbd"))
             if os.path.basename(f) != "libcompiler_rt.tbd"]
    else:
        files = [os.path.join(lib, os.path.basename(install_name).rsplit(".dylib", 1)[0] + ".tbd")]
    symbols = set()
    for path in files:
        if not os.path.exists(path):
            continue
        text = open(path).read()
        for block in re.split(r"\n  - archs:", text)[1:]:
            archs, _, body = block.partition("\n")
            if "armv7" not in archs:
                continue
            for key in ("symbols", "objc-classes", "objc-ivars", "weak-def-symbols"):
                for m in re.finditer(r"\b%s:\s*\[(.*?)\]" % key, body, re.S):
                    for name in m.group(1).replace("\n", " ").split(","):
                        name = name.strip().strip("'\"")
                        if not name:
                            continue
                        if key == "objc-classes":
                            for prefix in ("_OBJC_CLASS_$", "_OBJC_METACLASS_$"):
                                symbols.add(prefix + name)
                        elif key == "objc-ivars":
                            symbols.add("_OBJC_IVAR_$" + name)
                        else:
                            symbols.add(name)
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
    args = sys.argv[1:]
    sdk = None
    if args[:1] == ["--sdk"]:
        sdk = args[1]
        args = args[2:]
    if len(args) != 2:
        sys.exit(__doc__.strip().splitlines()[-1])
    symbols = read(args[0])
    libdir = os.path.join(args[1], "usr", "lib")
    os.makedirs(libdir, exist_ok=True)
    for install_name, files in NAMES.items():
        if not symbols.get(install_name):
            sys.exit("no symbols for %s in %s" % (install_name, sys.argv[1]))
        names = symbols[install_name]
        if sdk:
            names = names | sdk_symbols(sdk, install_name)
        text = tbd(install_name, names)
        for name in files:
            with open(os.path.join(libdir, name), "w") as f:
                f.write(text)


if __name__ == "__main__":
    main()
