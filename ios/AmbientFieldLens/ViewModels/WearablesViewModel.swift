import Foundation
import MWDATCamera
import MWDATCore
import MWDATDisplay
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
    @Published var previewActive = false
    @Published var currentFrame: UIImage?
    @Published var lastError: String?

    /// Set once by the App entry point after `Wearables.configure()`.
    /// On the iOS Simulator the SDK has no transport and configure throws,
    /// so nothing here may touch `Wearables.shared` unless this is true.
    static var sdkAvailable = false

    private var wearables: (any WearablesInterface)?
    private var deviceSelector: AutoDeviceSelector?
    private var deviceSession: DeviceSession?
    private var camera: Camera?
    private var stream: MWDATCamera.Stream?
    private var mockEnabled = false
    private var mockDevice: MockGlasses?
    private var display: Display?
    private var displayToken: AnyListenerToken?
    private var pendingDisplay: (detail: String, query: String)?
    private let sessionTokens = ListenerTokenBag()

    @Published var selectorDevice: String = "none"
    @Published var displayState: String = "Idle"
    @Published var displayConnected = false

    init() {
        registrationState = .unavailable
        guard Self.sdkAvailable else { return }
        let shared = Wearables.shared
        wearables = shared
        registrationState = shared.registrationState
        deviceSelector = AutoDeviceSelector(wearables: shared)
    }

    func observe() {
        guard let wearables, let deviceSelector else { return }
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
            guard let device = wearables?.deviceForIdentifier(id) else {
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
            if let device = wearables?.deviceForIdentifier(id) {
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
        guard let wearables else {
            lastError = "Glasses unavailable on this device."
            return
        }
        do {
            try await wearables.startRegistration()
        } catch {
            lastError = error.localizedDescription
        }
    }

    func enableMock() {
        guard Self.sdkAvailable else {
            lastError = "Glasses unavailable on this device."
            return
        }
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
            device.services.camera.setCameraFeed(cameraFacing: .back)
            mockDevice = device
            mockEnabled = true
        } catch {
            lastError = "Mock pairing failed: \(error.localizedDescription)"
        }
    }

    /// Phone-side render of what the glasses would show. Mock only.
    func mockPreviewView() -> UIView? {
        mockDevice?.services.display.createPreviewView()
    }

    /// Attach the Display capability on the already-started session.
    /// Must run after sessionState == .started; keeps the state token
    /// alive while the display is in use.
    func attachDisplay() {
        guard let session = deviceSession else {
            lastError = "Start the session first."
            return
        }
        guard sessionStarted else {
            lastError = "Display needs a started session."
            return
        }
        guard display == nil else { return }
        lastError = nil
        displayState = "Starting"
        do {
            let capability = try session.addDisplay()
            display = capability
            displayToken = capability.statePublisher.listen { [weak self] state in
                Task { @MainActor in
                    self?.displayState = "\(state)"
                    if state == .started {
                        self?.displayConnected = true
                        if let pending = self?.pendingDisplay {
                            self?.pendingDisplay = nil
                            self?.sendCard(
                                detail: pending.detail, query: pending.query
                            )
                        }
                    } else if state == .stopped {
                        self?.displayConnected = false
                    } else {
                        self?.displayConnected = false
                    }
                }
            }
            capability.start()
        } catch {
            displayState = "Idle"
            displayConnected = false
            display = nil
            displayToken = nil
            lastError = error.localizedDescription
        }
    }

    /// Manual validation path: mirror the current amber refusal onto the
    /// glasses (mock preview or real Display). Quotation only, no step.
    func sendVerdictToGlasses(detail: String, query: String) {
        guard !detail.isEmpty else { return }
        guard display != nil, displayConnected else {
            pendingDisplay = (detail, query)
            attachDisplay()
            if display == nil {
                pendingDisplay = nil
            }
            return
        }
        sendCard(detail: detail, query: query)
    }

    private func sendCard(detail: String, query: String) {
        guard let capability = display else { return }
        Task {
            do {
                try await capability.send(
                    AmberDisplayCard.make(detail: detail, query: query)
                )
            } catch {
                await MainActor.run {
                    self.lastError = error.localizedDescription
                }
            }
        }
    }

    func detachDisplay() {
        pendingDisplay = nil
        displayToken = nil
        if let capability = display {
            capability.stop()
        }
        display = nil
        displayState = "Idle"
        displayConnected = false
    }

    func startSession() async {
        guard let wearables, let deviceSelector else {
            sessionState = "Idle"
            lastError = "Glasses unavailable on this device."
            return
        }
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
        guard !previewActive else { return }
        previewActive = true
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
            previewActive = false
            return
        }
        guard let stream else {
            previewActive = false
            return
        }
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
        previewActive = false
    }

    func endSession() {
        stopPreview()
        detachDisplay()
        deviceSession?.stop()
        deviceSession = nil
        sessionState = "Idle"
        sessionStarted = false
    }
}
