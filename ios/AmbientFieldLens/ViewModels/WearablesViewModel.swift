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
    @Published var deviceDiagnostics: String = "no data"
    @Published var hasCompatibleDevice = false

    private var deviceCompatibility: [DeviceIdentifier: String] = [:]
    private var compatibilityTokens: [DeviceIdentifier: AnyListenerToken] =
        [:]
    @Published var sessionState: String = "Idle"
    @Published var sessionStarted = false
    @Published var streamState: String = "Stopped"
    @Published var currentFrame: UIImage?
    @Published var lastError: String?

    private let wearables = Wearables.shared
    private let deviceSelector: AutoDeviceSelector
    private var deviceSession: DeviceSession?
    private var camera: Camera?
    private var stream: MWDATCamera.Stream?
    private var mockEnabled = false
    private let sessionTokens = ListenerTokenBag()

    @Published var selectorDevice: String = "none"

    init() {
        registrationState = Wearables.shared.registrationState
        deviceSelector = AutoDeviceSelector(wearables: Wearables.shared)
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
                self.monitorCompatibility(deviceIds: deviceIds)
            }
        }
        Task {
            for await active in deviceSelector.activeDeviceStream() {
                self.selectorDevice = active ?? "none"
            }
        }
    }

    private func monitorCompatibility(deviceIds: [DeviceIdentifier]) {
        let current = Set(deviceIds)
        compatibilityTokens = compatibilityTokens.filter {
            current.contains($0.key)
        }
        deviceCompatibility = deviceCompatibility.filter {
            current.contains($0.key)
        }
        for id in deviceIds {
            guard compatibilityTokens[id] == nil else { continue }
            guard let device = wearables.deviceForIdentifier(id) else {
                continue
            }
            deviceCompatibility[id] = "\(device.compatibility())"
            self.refreshDiagnostics()
            let token = device.addCompatibilityListener {
                [weak self] compatibility in
                Task { @MainActor in
                    self?.deviceCompatibility[id] = "\(compatibility)"
                    self?.refreshDiagnostics()
                }
            }
            compatibilityTokens[id] = token
        }
        refreshDiagnostics()
    }

    private func refreshDiagnostics() {
        var lines: [String] = []
        for id in deviceCompatibility.keys.sorted() {
            if let device = wearables.deviceForIdentifier(id) {
                lines.append(
                    "\(device.nameOrId()): type=\(device.deviceType()) link=\(device.linkState) compat=\(deviceCompatibility[id] ?? "?")"
                )
            } else {
                lines.append("\(id): unresolvable")
            }
        }
        deviceDiagnostics = lines.isEmpty
            ? "registry empty" : lines.joined(separator: "\n")
        hasCompatibleDevice = deviceCompatibility.values.contains {
            $0.lowercased().contains("compatible")
                && !$0.lowercased().contains("incompatible")
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
        lastError = nil
        MockDeviceKit.shared.enable()
        do {
            let device = try MockDeviceKit.shared.pairGlasses(
                model: .metaRayBanDisplay
            )
            device.powerOn()
            device.unfold()
            device.don()
            mockEnabled = true
        } catch {
            lastError = "Mock pairing failed: \(error.localizedDescription)"
        }
    }

    func startSession() async {
        lastError = nil
        sessionState = "Starting"
        do {
            // The device registry can lag behind the glasses toggle:
            // retry creation briefly before reporting no device.
            var session: DeviceSession?
            var lastThrown: Error?
            for _ in 0..<2 {
                do {
                    session = try wearables.createSession(
                        deviceSelector: deviceSelector
                    )
                    lastThrown = nil
                    break
                } catch {
                    lastThrown = error
                    try? await Task.sleep(
                        for: .seconds(1)
                    )
                }
            }
            guard let session else { throw lastThrown! }
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
