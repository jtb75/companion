import AVFoundation
import React

@objc(AudioPlayerModule)
class AudioPlayerModule: NSObject {
  private var audioPlayer: AVAudioPlayer?

  @objc
  static func requiresMainQueueSetup() -> Bool {
    return false
  }

  @objc
  func playBase64Audio(
    _ base64String: String,
    resolve: @escaping RCTPromiseResolveBlock,
    rejecter reject: @escaping RCTPromiseRejectBlock
  ) {
    guard let audioData = Data(base64Encoded: base64String) else {
      reject("INVALID_DATA", "Could not decode base64 audio", nil)
      return
    }

    DispatchQueue.main.async {
      do {
        try AVAudioSession.sharedInstance().setCategory(
          .playback,
          mode: .spokenAudio,
          options: [.duckOthers]
        )
        try AVAudioSession.sharedInstance().setActive(true)

        self.audioPlayer = try AVAudioPlayer(data: audioData)
        self.audioPlayer?.prepareToPlay()
        self.audioPlayer?.play()
        resolve(true)
      } catch {
        reject("PLAY_ERROR", error.localizedDescription, error)
      }
    }
  }

  @objc
  func stopAudio(
    _ resolve: @escaping RCTPromiseResolveBlock,
    rejecter reject: @escaping RCTPromiseRejectBlock
  ) {
    DispatchQueue.main.async {
      self.audioPlayer?.stop()
      self.audioPlayer = nil
      resolve(true)
    }
  }
}
