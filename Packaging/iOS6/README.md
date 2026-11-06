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

## Linking an app

See `test/Makefile`, which builds `vlcplay` this way:

- Compile ARM code (`-marm`), not Thumb.
- Link with `-L build/iOS6/link-stubs/usr/lib -framework MobileVLCKit -lc++
  -lc++abi -liconv -lbz2 -lz -lresolv -lsqlite3` and the system frameworks
  listed there. Not `AudioUnit.framework`, which iOS 6 doesn't have (its API
  is in AudioToolbox), and not `-fobjc-arc` on the link line (clang would add
  libarclite, which Xcode no longer ships; compiling with ARC is fine).
- Check the result with `check_imports.py ios-6.1.6-armv7-exports.txt <app>`:
  it fails if a strong import doesn't exist on iOS 6, which would keep dyld
  from launching the app.

## Testing on a device

```bash
cd Packaging/iOS6/test
make run MEDIA=movie.mp4          # VLCPLAY_VERBOSE=1 for libvlc's log
```

On an iPod touch 4 (iOS 6.1.6) MP3, H.264/AAC MP4 and VP8/Opus MKV files
play to the end, and video starts about half a second after the audio.
`VLCPLAY_VERBOSE=1` prints libvlc's log with milliseconds since launch.

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
  plain dispatch queues before iOS 8. Left out: librist (its mbedtls needs
  `clock_gettime`, iOS 10), VideoToolbox (iOS 8, libavcodec decodes in
  software) and the CoreImage filters (iOS 6's CoreImage lacks
  `kCIOutputImageKey`).
- **`@available`.** compiler-rt's support for it needs iOS 14's
  `_availability_version_check` and is Thumb code, so the framework brings
  its own `__isOSVersionAtLeast` (`availability.c`).
- **Two sets of stubs.** `build/iOS6/stubs` lists only what iOS 6 exports and
  is used to build libvlc, so configure checks are exact.
  `build/iOS6/link-stubs` adds the SDK's symbols, as `@available` fallbacks
  reference newer symbols weakly and those still need a definition at link
  time; `check_imports.py` then rejects strong references iOS 6 can't
  satisfy.
- **Linker workarounds.** ffmpeg's ARM assembly labels its GOT pointers
  `.Lpic`, a named symbol on Mach-O, which makes Xcode 27's ld assert; they
  use the Mach-O private prefix `L` instead. libvlc's Bonjour module looks up
  `NSNetService` at run time, as it moved from Foundation (iOS 6) to
  CFNetwork.
- **Video output.** The iOS video output sets up its OpenGL ES surface on
  its own thread, whose implicit Core Animation transaction iOS 6 never
  commits: the layer never showed and each frame waited 1 s to present
  (`0057`). And the subtitle renderer's CoreText family lookup matched on
  display names too, which reads every font on the system: 2.5 s before
  the first frame on an iPod (`0056`).
- **No implicit autorelease pools.** iOS 6 threads have none, so the iOS
  audio output drains its AVAudioSession objects itself, and RemoteIO there
  has no channel layout property, which mono and stereo don't need.
