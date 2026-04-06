import AVFoundation
import React

@objc(AudioRecorderModule)
class AudioRecorderModule: NSObject, AVAudioRecorderDelegate {
  private var audioRecorder: AVAudioRecorder?
  private var recordingURL: URL?
  private var resolveBlock: RCTPromiseResolveBlock?

  @objc
  static func requiresMainQueueSetup() -> Bool {
    return false
  }

  @objc
  func startRecording(
    _ resolve: @escaping RCTPromiseResolveBlock,
    rejecter reject: @escaping RCTPromiseRejectBlock
  ) {
    DispatchQueue.main.async {
      do {
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(
          .playAndRecord,
          mode: .spokenAudio,
          options: [.defaultToSpeaker, .allowBluetooth]
        )
        try session.setActive(true)

        let tempDir = FileManager.default.temporaryDirectory
        let url = tempDir.appendingPathComponent("dd_recording.wav")
        self.recordingURL = url

        let settings: [String: Any] = [
          AVFormatIDKey: Int(kAudioFormatLinearPCM),
          AVSampleRateKey: 16000,
          AVNumberOfChannelsKey: 1,
          AVLinearPCMBitDepthKey: 16,
          AVLinearPCMIsBigEndianKey: false,
          AVLinearPCMIsFloatKey: false,
        ]

        self.audioRecorder = try AVAudioRecorder(url: url, settings: settings)
        self.audioRecorder?.delegate = self
        self.audioRecorder?.record()
        resolve(true)
      } catch {
        reject("RECORD_ERROR", error.localizedDescription, error)
      }
    }
  }

  @objc
  func stopRecording(
    _ resolve: @escaping RCTPromiseResolveBlock,
    rejecter reject: @escaping RCTPromiseRejectBlock
  ) {
    DispatchQueue.main.async {
      guard let recorder = self.audioRecorder, recorder.isRecording else {
        reject("NOT_RECORDING", "No active recording", nil)
        return
      }

      recorder.stop()

      guard let url = self.recordingURL else {
        reject("NO_FILE", "Recording file not found", nil)
        return
      }

      do {
        let data = try Data(contentsOf: url)
        let base64 = data.base64EncodedString()

        // Reset audio session for playback
        try AVAudioSession.sharedInstance().setCategory(
          .playback,
          mode: .spokenAudio,
          options: [.duckOthers]
        )

        // Clean up
        try? FileManager.default.removeItem(at: url)
        self.audioRecorder = nil
        self.recordingURL = nil

        resolve(base64)
      } catch {
        reject("READ_ERROR", error.localizedDescription, error)
      }
    }
  }
}
