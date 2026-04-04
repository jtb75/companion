import UIKit
import VisionKit
import React

@objc(DocumentScannerModule)
class DocumentScannerModule: NSObject {

  private var resolve: RCTPromiseResolveBlock?
  private var reject: RCTPromiseRejectBlock?

  @objc
  static func requiresMainQueueSetup() -> Bool {
    return false
  }

  @objc
  func scanDocument(
    _ resolve: @escaping RCTPromiseResolveBlock,
    rejecter reject: @escaping RCTPromiseRejectBlock
  ) {
    self.resolve = resolve
    self.reject = reject

    DispatchQueue.main.async {
      guard VNDocumentCameraViewController.isSupported else {
        reject("UNSUPPORTED", "Document scanning is not supported on this device", nil)
        return
      }

      let scanner = VNDocumentCameraViewController()
      scanner.delegate = self

      guard let rootVC = UIApplication.shared.connectedScenes
        .compactMap({ $0 as? UIWindowScene })
        .flatMap({ $0.windows })
        .first(where: { $0.isKeyWindow })?
        .rootViewController else {
        reject("NO_ROOT_VC", "Unable to find root view controller", nil)
        return
      }

      var presenter = rootVC
      while let presented = presenter.presentedViewController {
        presenter = presented
      }

      presenter.present(scanner, animated: true)
    }
  }

  private func resizeImage(_ image: UIImage, maxDimension: CGFloat) -> UIImage {
    let size = image.size
    guard size.width > maxDimension || size.height > maxDimension else {
      return image
    }

    let ratio = min(maxDimension / size.width, maxDimension / size.height)
    let newSize = CGSize(width: size.width * ratio, height: size.height * ratio)

    let renderer = UIGraphicsImageRenderer(size: newSize)
    return renderer.image { _ in
      image.draw(in: CGRect(origin: .zero, size: newSize))
    }
  }
}

extension DocumentScannerModule: VNDocumentCameraViewControllerDelegate {

  func documentCameraViewController(
    _ controller: VNDocumentCameraViewController,
    didFinishWith scan: VNDocumentCameraScan
  ) {
    controller.dismiss(animated: true)

    DispatchQueue.global(qos: .userInitiated).async { [weak self] in
      guard let self = self else { return }

      var uris: [String] = []
      let tempDir = NSTemporaryDirectory()

      for index in 0..<scan.pageCount {
        let pageImage = scan.imageOfPage(at: index)
        let resized = self.resizeImage(pageImage, maxDimension: 2048)

        guard let data = resized.jpegData(compressionQuality: 0.8) else { continue }

        let fileName = "scan_\(UUID().uuidString).jpg"
        let filePath = (tempDir as NSString).appendingPathComponent(fileName)
        let fileURL = URL(fileURLWithPath: filePath)

        do {
          try data.write(to: fileURL)
          uris.append(fileURL.absoluteString)
        } catch {
          // Skip pages that fail to write
        }
      }

      self.resolve?(uris)
      self.resolve = nil
      self.reject = nil
    }
  }

  func documentCameraViewControllerDidCancel(
    _ controller: VNDocumentCameraViewController
  ) {
    controller.dismiss(animated: true)
    resolve?([String]())
    resolve = nil
    reject = nil
  }

  func documentCameraViewController(
    _ controller: VNDocumentCameraViewController,
    didFailWithError error: Error
  ) {
    controller.dismiss(animated: true)
    reject?("SCAN_FAILED", error.localizedDescription, error)
    resolve = nil
    reject = nil
  }
}
