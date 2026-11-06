# MobileVLCKit for iOS 6

`./buildMobileVLCKit.sh -6` builds libvlc 3 and MobileVLCKit for armv7 with
iOS 6.0 as the deployment target, using Xcode 27's clang and the iOS 9.3 SDK
from [Swift-iOS6](https://github.com/colemancda/Swift-iOS6). The result is a
static `build/iOS6/MobileVLCKit.framework` for the Swift-iOS6 Makefiles.

```bash
# needs ../Swift-iOS6/sdk/iPhoneOS9.3.sdk (or IOS6_SDKROOT), Homebrew's
# autotools, and GNU make 4 (macOS's make 3.81 breaks meson/ninja jobservers)
brew install autoconf automake libtool pkg-config yasm nasm ragel make
VLC_PATH=/opt/homebrew/opt/make/libexec/gnubin ./buildMobileVLCKit.sh -6
```

Apps link it with `-framework MobileVLCKit -lc++ -lc++abi -liconv -lbz2 -lz`
plus the system frameworks it uses, and must be ARM code (`-marm`), not Thumb.

## Why each step is there

- **ARM, not Thumb.** Xcode 27's linker drops the Thumb bit from pointers to
  local Thumb functions stored in data (and from `LC_MAIN`), so calling
  through one runs Thumb code as ARM and crashes. Everything is built with
  `-marm`.
- **iOS 6's own link stubs.** The 9.3 SDK's `.tbd` files describe iOS 9: they
  list functions iOS 6 lacks, leave out ones it has (`strcmp`, `strlen`), and
  expect libc++ to re-export libc++abi, which it doesn't on iOS 6.
  `ios-6.1.6-armv7-exports.txt` is what iOS 6.1.6 really exports, dumped on an
  iPod touch (iPod4,1) with `dumpexports.c`. `mkstubs.py` turns it into stubs
  that come before the SDK's (`-L build/iOS6/stubs/usr/lib`), so configure
  checks and links see exactly iOS 6.
- **libc++ 3.8 headers.** The SDK only has GCC 4.2's libstdc++ headers, and
  Xcode 27's libc++ headers no longer support iOS 6. The script fetches
  libc++ 3.8.0's headers (those of Xcode 7, the 9.3 SDK's Xcode, checked by
  SHA-256) and builds C++ with them against iOS 6's `libc++.1.dylib`.
- **No thread-local storage.** Clang only allows TLS on armv7 iOS from 9.0.
  `libvlc/patches/0048-*` moves libvlc's few `thread_local`s to pthread keys,
  `0049-*` does the same for libgcrypt and fixes two contribs' OS checks.
- **Availability.** `-Werror=unguarded-availability` turns any API newer than
  iOS 6 into a compile error. VLCKit falls back to `UIAlertView` dialogs and
  plain dispatch queues before iOS 8, and librist (whose mbedtls needs
  `clock_gettime`, iOS 10) is left out.
