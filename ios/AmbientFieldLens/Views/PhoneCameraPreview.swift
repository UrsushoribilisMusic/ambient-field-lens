import AVFoundation
import SwiftUI
import UIKit

/// Live back-camera preview. Stills go through PhoneCameraViewModel.capture().
/// Keeps the preview and capture orientations glued to the device so a
/// landscape phone shows a landscape view.
struct PhoneCameraPreview: UIViewRepresentable {
    let session: AVCaptureSession

    nonisolated static func landscapeOrientation() -> AVCaptureVideoOrientation {
        switch UIDevice.current.orientation {
        case .landscapeLeft:
            // Home button on the right: sensor needs the opposite.
            return .landscapeRight
        case .landscapeRight:
            return .landscapeLeft
        default:
            return .landscapeRight
        }
    }

    func makeUIView(context: Context) -> PreviewHolder {
        let holder = PreviewHolder()
        holder.videoLayer.videoGravity = .resizeAspectFill
        holder.videoLayer.session = session
        holder.videoLayer.connection?.videoOrientation =
            Self.landscapeOrientation()
        NotificationCenter.default.addObserver(
            holder,
            selector: #selector(PreviewHolder.reorient),
            name: UIDevice.orientationDidChangeNotification,
            object: nil
        )
        return holder
    }

    func updateUIView(_ view: PreviewHolder, context: Context) {}

    static func dismantleUIView(
        _ view: PreviewHolder, coordinator: Void
    ) {
        NotificationCenter.default.removeObserver(view)
    }

    final class PreviewHolder: UIView {
        override class var layerClass: AnyClass {
            AVCaptureVideoPreviewLayer.self
        }
        var videoLayer: AVCaptureVideoPreviewLayer {
            super.layer as! AVCaptureVideoPreviewLayer
        }
        @objc func reorient() {
            videoLayer.connection?.videoOrientation =
                PhoneCameraPreview.landscapeOrientation()
        }
        override func layoutSubviews() {
            super.layoutSubviews()
            reorient()
        }
    }
}
