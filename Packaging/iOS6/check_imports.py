#!/usr/bin/env python3
"""
Checks that a linked armv7 binary only imports what iOS 6 exports.

Every strong (non-weak) import must be exported by the iOS 6.1.6 library it
binds to, or dyld refuses to launch the binary. Weak imports are what
@available fallbacks reference and may be missing. Libraries iOS 6 doesn't
have at all (AudioUnit.framework, for one) are errors too, unless weakly
linked.

usage: check_imports.py <exports.txt> <binary>
"""

import collections
import re
import subprocess
import sys

LIBSYSTEM = "/usr/lib/libSystem.B.dylib"


def exports(path):
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
    for child in reexports[LIBSYSTEM]:
        symbols[LIBSYSTEM] |= symbols.get(child, set())
    return symbols


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__.strip().splitlines()[-1])
    available = exports(sys.argv[1])
    binary = sys.argv[2]

    # install names, in load command order (two-level namespace ordinals)
    otool = subprocess.run(["xcrun", "otool", "-l", binary], check=True,
                           capture_output=True, text=True).stdout
    dylibs = []
    weak_dylibs = set()
    for cmd, name in re.findall(r"cmd (LC_LOAD_DYLIB|LC_LOAD_WEAK_DYLIB|LC_REEXPORT_DYLIB|LC_LOAD_UPWARD_DYLIB)\n"
                                r"\s+cmdsize \d+\n\s+name (\S+)", otool):
        dylibs.append(name)
        if cmd == "LC_LOAD_WEAK_DYLIB":
            weak_dylibs.add(name)

    def short(name):
        return name.rsplit("/", 1)[-1].split(".")[0]

    by_short = {short(d): d for d in dylibs}

    nm = subprocess.run(["xcrun", "nm", "-m", "-arch", "armv7", binary], check=True,
                        capture_output=True, text=True).stdout
    missing = collections.defaultdict(list)
    count = 0
    for line in nm.splitlines():
        m = re.match(r"\s*\(undefined\) (weak )?external (\S+) \(from (\S+)\)", line)
        if not m:
            continue
        weak, symbol, lib = m.groups()
        count += 1
        if weak:
            continue
        install_name = by_short.get(lib, lib)
        if install_name in weak_dylibs:
            continue
        if symbol not in available.get(install_name, ()):
            missing[install_name].append(symbol)

    for name in dylibs:
        if name not in available and name not in weak_dylibs:
            print("missing on iOS 6: library %s" % name)
    for lib, symbols in sorted(missing.items()):
        for s in sorted(symbols):
            print("missing on iOS 6: %s (%s)" % (s, lib))
    bad = sum(len(v) for v in missing.values()) + \
        sum(1 for d in dylibs if d not in available and d not in weak_dylibs)
    print("%d imports from %d libraries checked, %d problems" % (count, len(dylibs), bad))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
