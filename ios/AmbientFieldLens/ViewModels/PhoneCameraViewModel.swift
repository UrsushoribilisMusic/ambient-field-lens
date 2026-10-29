import AVFoundation
import UIKit

/// Phone-camera frame source for the robot demo: no glasses needed.
/// A still photo is captured on demand and handed to Ask. The most recent
/// photo is kept so the operator can retap Ask without recapturing.
@MainActor
final class PhoneCameraViewModel: NSObject, ObservableObject {
    @Published var lastPhoto: UIImage?
    @Published var lastError: String?
    @Published var isReady = false

    // Capture objects live off the main actor (session.startRunning blocks);
    // all UI state stays @Published on MainActor.
    private nonisolated(unsafe) let session = AVCaptureSession()
    private nonisolated(unsafe) var output = AVCapturePhotoOutput()
    private var configured = false

    nonisolated var previewSession: AVCaptureSession { session }

    override init() {
        super.init()
        // No maxPhotoDimensions: arbitrary sizes the active format does not
        // support raise an ObjC exception at capture time. Full-res frames
        // are downscaled to the wire contract later by contractFrameJPEG.
    }

    func start() {
        guard !configured else {
            session.startRunning()
            return
        }
        configured = true
        Task.detached(priority: .userInitiated) { [weak self] in
            guard let self else { return }
            switch AVCaptureDevice.authorizationStatus(for: .video) {
            case .notDetermined:
                _ = await AVCaptureDevice.requestAccess(for: .video)
            default:
                break
            }
            guard AVCaptureDevice.authorizationStatus(for: .video) == .authorized
            else {
                await MainActor.run {
                    self.lastError = "Phone camera access denied."
                }
                return
            }
            do {
                self.session.beginConfiguration()
                self.session.sessionPreset = .photo
                guard
                    let device = AVCaptureDevice.default(
                        .builtInWideAngleCamera,
                        for: .video,
                        position: .back
                    ),
                    let input = try? AVCaptureDeviceInput(device: device),
                    self.session.canAddInput(input),
                    self.session.canAddOutput(self.output)
                else {
                    self.session.commitConfiguration()
                    await MainActor.run {
                        self.lastError = "Back camera unavailable."
                    }
                    return
                }
                self.session.addInput(input)
                self.session.addOutput(self.output)
                self.session.commitConfiguration()
                self.session.startRunning()
                await MainActor.run { self.isReady = true }
            }
        }
    }

    /// Capture a still, keep it as the current frame, and return it.
    /// Throws a human-readable message on failure.
    nonisolated func capturePhoto() async throws -> UIImage {
        try await withCheckedThrowingContinuation { continuation in
            self.pending.append(continuation)
            self.output.capturePhoto(
                with: AVCapturePhotoSettings(), delegate: self)
        }
    }

    private nonisolated(unsafe) var pending:
        [CheckedContinuation<UIImage, Error>] = []

    struct CaptureFailure: Error {
        let message: String
    }
}

extension PhoneCameraViewModel: AVCapturePhotoCaptureDelegate {
    nonisolated func photoOutput(
        _ output: AVCapturePhotoOutput,
        didFinishProcessingPhoto photo: AVCapturePhoto,
        error: (any Error)?
    ) {
        // Cross the actor boundary with Sendable values only.
        let data = photo.fileDataRepresentation()
        let message = error?.localizedDescription
        let continuation = self.pending.first
        if !self.pending.isEmpty { self.pending.removeFirst() }
        guard let continuation else { return }
        if let message {
            continuation.resume(throwing: CaptureFailure(message: message))
            return
        }
        guard let data, let image = UIImage(data: data) else {
            continuation.resume(
                throwing: CaptureFailure(message: "Photo decode failed."))
            return
        }
        Task { @MainActor [weak self, image] in
            self?.lastPhoto = image
        }
        continuation.resume(returning: image)
    }
}
