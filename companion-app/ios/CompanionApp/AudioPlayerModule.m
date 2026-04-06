#import <React/RCTBridgeModule.h>

@interface RCT_EXTERN_MODULE(AudioPlayerModule, NSObject)

RCT_EXTERN_METHOD(playBase64Audio:(NSString *)base64String
                  resolve:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject)

RCT_EXTERN_METHOD(stopAudio:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject)

@end
