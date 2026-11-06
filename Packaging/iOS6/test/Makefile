# Builds vlcplay against build/iOS6/MobileVLCKit.framework and runs it on an
# iOS 6 device over SSH (as Swift-iOS6 does, see its README for iproxy).
#
#   make                         build and check build/iOS6/vlcplay
#   make run MEDIA=/path/on/mac  copy vlcplay and a media file over and play it

ROOT     := $(abspath ../../..)
SDK      ?= $(ROOT)/../Swift-iOS6/sdk/iPhoneOS9.3.sdk
SSH_CONF ?= $(ROOT)/../Swift-iOS6/ipod-ssh.conf
SSH_HOST ?= ipod
BUILD    := $(ROOT)/build/iOS6
MEDIA    ?=
SECONDS  ?= 12

CC       := xcrun clang
# ARM code: Xcode's linker drops the Thumb bit from LC_MAIN and from
# pointers to local Thumb functions
CFLAGS   := -arch armv7 -marm -isysroot $(SDK) -miphoneos-version-min=6.0 \
            -fobjc-arc -Os -Wall -Werror=unguarded-availability -F$(BUILD)
# iOS 6's own libSystem and libc++ stubs first (plus the SDK's symbols, for
# weak references; check_imports.py rejects strong ones iOS 6 lacks). No -fobjc-arc when linking
# (clang would add libarclite) and no AudioUnit.framework (iOS 6 has none,
# its API is in AudioToolbox).
FRAMEWORKS := Foundation CoreFoundation UIKit AVFoundation AudioToolbox \
              CoreAudio CoreGraphics CoreText CoreVideo CoreMedia OpenGLES \
              QuartzCore Security SystemConfiguration CFNetwork MediaPlayer \
              ImageIO MobileCoreServices
LDFLAGS  := -arch armv7 -isysroot $(SDK) -miphoneos-version-min=6.0 \
            -L$(BUILD)/link-stubs/usr/lib -F$(BUILD) -framework MobileVLCKit \
            $(addprefix -framework ,$(FRAMEWORKS)) \
            -lc++ -lc++abi -liconv -lbz2 -lz -lresolv -lsqlite3

.PHONY: all run clean

all: $(BUILD)/vlcplay

$(BUILD)/vlcplay.o: vlcplay.m
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD)/vlcplay: $(BUILD)/vlcplay.o
	$(CC) $(LDFLAGS) $< -o $@.tmp
	python3 -I ../check_imports.py ../ios-6.1.6-armv7-exports.txt $@.tmp
	ldid -S $@.tmp
	mv $@.tmp $@

run: $(BUILD)/vlcplay
	@test -n "$(MEDIA)" || { echo "usage: make run MEDIA=<file>"; exit 2; }
	ssh -F $(SSH_CONF) $(SSH_HOST) 'cat > /var/tmp/vlcplay && chmod 755 /var/tmp/vlcplay' < $(BUILD)/vlcplay
	ssh -F $(SSH_CONF) $(SSH_HOST) 'cat > "/var/tmp/$(notdir $(MEDIA))"' < "$(MEDIA)"
	ssh -F $(SSH_CONF) $(SSH_HOST) '/var/tmp/vlcplay "/var/tmp/$(notdir $(MEDIA))" $(SECONDS)'

clean:
	rm -f $(BUILD)/vlcplay $(BUILD)/vlcplay.o
