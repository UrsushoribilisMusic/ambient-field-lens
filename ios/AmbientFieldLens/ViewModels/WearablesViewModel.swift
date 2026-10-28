import Foundation
import MWDATCamera
import MWDATCore
import MWDATMockDevice
import UIKit

/// Owns registration, the device session, and the camera stream.
/// Two explicit steps: start session, then start preview.
@MainActor
final class WearablesViewModel: ObservableObject {
    @Published var registrationState: RegistrationState
    @Published var deviceCount: Int = 0
    @Published var sessionState: String = "Idle"
    @Published var sessionStarted = false
    @Published var streamState: String = "Stopped"
    @Published var currentFrame: UIImage?
    @Published var lastError: String?

    private let wearables = Wearables.shared
    private var deviceSession: DeviceSession?
    private var camera: Camera?
    private var stream: MWDATCamera.Stream?
    private var mockEnabled = false
    private let sessionTokens = ListenerTokenBag()

    init() {
        registrationState = Wearables.shared.registrationState
    }

    func observe() {
        Task {
            for await state in wearables.registrationStateStream() {
                self.registrationState = state
            }
        }
        Task {
            for await deviceIds in wearables.devicesStream() {
                self.deviceCount = deviceIds.count
            }
        }
    }

    func register() async {
        do {
            try await wearables.startRegistration()
        } catch {
            lastError = error.localizedDescription
        }
    }

    func enableMock() {
        guard !mockEnabled else { return }
        MockDeviceKit.shared.enable()
        if let device = try? MockDeviceKit.shared.pairGlasses(
            model: .metaRayBanDisplay
        ) {
            device.powerOn()
            device.unfold()
            device.don()
        }
        mockEnabled = true
    }

    func startSession() async {
        lastError = nil
        sessionState = "Starting"
        do {
            let selector = AutoDeviceSelector(wearables: wearables)
            let session = try wearables.createSession(deviceSelector: selector)
            deviceSession = session
            try session.start()
            for await state in session.stateStream() {
                sessionState = "\(state)"
                if state == .started {
                    sessionStarted = true
                    break
                }
            }
            // Keep watching after started: a stopped session must
            // unlock the guided flow again. Never restart from here.
            session.statePublisher.listen { [weak self] state in
                Task { @MainActor in
                    self?.sessionState = "\(state)"
                    if state == .stopped {
                        self?.sessionStarted = false
                    }
                }
            }.store(in: sessionTokens)
        } catch {
            sessionState = "Idle"
            sessionStarted = false
            lastError = error.localizedDescription
        }
    }

    func startPreview() {
        guard let session = deviceSession else {
            lastError = "Start the session first."
            return
        }
        lastError = nil
        do {
            let config = StreamConfiguration(
                videoCodec: .raw, resolution: .low, frameRate: 24
            )
            guard let added = try session.addCamera(config: config) else {
                lastError = "Glasses camera unavailable."
                return
            }
            camera = added
            stream = added.stream
        } catch {
            lastError = error.localizedDescription
            return
        }
        guard let stream else { return }
        _ = stream.statePublisher.listen { [weak self] state in
            Task { @MainActor in
                self?.streamState = "\(state)"
            }
        }
        _ = stream.errorPublisher.listen { [weak self] error in
            Task { @MainActor in
                self?.lastError = error.localizedDescription
            }
        }
        _ = stream.videoFramePublisher.listen { [weak self] frame in
            guard let image = frame.makeUIImage() else { return }
            Task { @MainActor in
                self?.currentFrame = image
            }
        }
        stream.start()
    }

    func stopPreview() {
        camera?.stop()
        stream = nil
        camera = nil
        streamState = "Stopped"
    }

    func endSession() {
        stopPreview()
        deviceSession?.stop()
        deviceSession = nil
        sessionState = "Idle"
        sessionStarted = false
    }
}
