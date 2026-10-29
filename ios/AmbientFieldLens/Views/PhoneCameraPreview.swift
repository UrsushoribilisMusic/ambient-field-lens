import AVFoundation
import SwiftUI

/// Live back-camera preview. Stills go through PhoneCameraViewModel.capture().
struct PhoneCameraPreview: UIViewRepresentable {
    let session: AVCaptureSession

    func makeUIView(context: Context) -> PreviewHolder {
        let holder = PreviewHolder()
        holder.videoLayer.videoGravity = .resizeAspectFill
        holder.videoLayer.session = session
        return holder
    }

    func updateUIView(_ view: PreviewHolder, context: Context) {}

    final class PreviewHolder: UIView {
        override class var layerClass: AnyClass {
            AVCaptureVideoPreviewLayer.self
        }
        var videoLayer: AVCaptureVideoPreviewLayer {
            super.layer as! AVCaptureVideoPreviewLayer
        }
    }
}
