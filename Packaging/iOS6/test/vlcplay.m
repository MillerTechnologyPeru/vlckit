/*
 * vlcplay: plays a media file with MobileVLCKit from the command line, to
 * check an iOS 6 build on a device.
 *
 *   vlcplay <file or URL> [seconds]
 *
 * VLCPLAY_VERBOSE=1 prints libvlc's debug log too, and VLCPLAY_OPTIONS adds
 * libvlc options (separated by spaces).
 *
 * Prints the libvlc version, then the player's state and time every half
 * second, and exits 0 if the player played and its time moved. Video is
 * decoded into a dummy output, as a command-line tool has no view.
 */

#import <Foundation/Foundation.h>
#import <MobileVLCKit/MobileVLCKit.h>

/* VLCConsoleLogger only logs in debug builds of VLCKit */
@interface StderrLogger : NSObject <VLCLogging>
@property (readwrite, nonatomic) VLCLogLevel level;
@end

@implementation StderrLogger
- (void)handleMessage:(NSString *)message
             logLevel:(VLCLogLevel)level
              context:(VLCLogContext *)context
{
    fprintf(stderr, "[%s] %s\n", context.module.UTF8String ?: "?", message.UTF8String);
}
@end

int main(int argc, char **argv)
{
    @autoreleasepool {
        if (argc < 2) {
            fprintf(stderr, "usage: %s <file or URL> [seconds]\n", argv[0]);
            return 2;
        }
        NSString *arg = [NSString stringWithUTF8String:argv[1]];
        double seconds = argc > 2 ? atof(argv[2]) : 5;

        /* video is decoded, but there's no view to draw into here */
        NSMutableArray *options = [NSMutableArray arrayWithObject:@"--vout=dummy"];
        const char *extra = getenv("VLCPLAY_OPTIONS");
        if (extra != NULL)
            [options addObjectsFromArray:[[NSString stringWithUTF8String:extra]
                                          componentsSeparatedByString:@" "]];
        VLCLibrary *library = [[VLCLibrary alloc] initWithOptions:options];
        printf("libvlc %s\n", library.version.UTF8String);
        if (getenv("VLCPLAY_VERBOSE")) {
            StderrLogger *logger = [[StderrLogger alloc] init];
            logger.level = kVLCLogLevelDebug;
            library.loggers = @[logger];
        }

        NSURL *url = [arg rangeOfString:@"://"].location != NSNotFound
            ? [NSURL URLWithString:arg] : [NSURL fileURLWithPath:arg];
        VLCMedia *media = [VLCMedia mediaWithURL:url];
        VLCMediaPlayer *player = [[VLCMediaPlayer alloc] initWithLibrary:library];
        player.media = media;
        [player play];

        BOOL playing = NO;
        int lastTime = -1, moved = 0;
        for (double t = 0; t < seconds; t += 0.5) {
            [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.5]];
            int time = player.time.intValue;
            printf("%4.1fs state %-10s time %6d ms / %d ms\n", t + 0.5,
                   VLCMediaPlayerStateToString(player.state).UTF8String,
                   time, media.length.intValue);
            /* VLCKit reports Buffering after Playing, as libvlc sends a
             * buffering event once playback started */
            if (player.isPlaying)
                playing = YES;
            if (lastTime >= 0 && time > lastTime)
                moved++;
            lastTime = time;
        }
        printf("tracks: %d audio, %d video, video size %dx%d\n",
               player.numberOfAudioTracks, player.numberOfVideoTracks,
               (int)player.videoSize.width, (int)player.videoSize.height);
        [player stop];
        return playing && moved > 0 ? 0 : 1;
    }
}
