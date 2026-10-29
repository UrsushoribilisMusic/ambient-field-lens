import SwiftUI
import UIKit

/// Demo viewfinder: fullscreen camera, one status line on top, one ask
/// bar at the bottom. Nothing covers the work area. Glasses/session setup
/// happens automatically at launch; Setup holds manual fallbacks.
struct ContentView: View {
    @StateObject private var wearables = WearablesViewModel()
    @StateObject private var assist = AssistViewModel()
    @StateObject private var phoneCamera = PhoneCameraViewModel()
    @StateObject private var setup = DemoSetup()
    @State private var showSetup = false
    @State private var askPulse = 0
    private let pulseTimer = Timer.publish(every: 0.25, on: .main, in: .common)
        .autoconnect()

    var body: some View {
        NavigationStack {
            ZStack {
                PhoneCameraPreview(session: phoneCamera.previewSession)
                    .ignoresSafeArea()
                VStack(spacing: 0) {
                    statusBar
                    Spacer()
                    askBar
                }
                .ignoresSafeArea(.container)
            }
            .navigationBarHidden(true)
            .alert(
                "Error",
                isPresented: Binding(
                    get: {
                        wearables.lastError != nil || assist.lastError != nil
                    },
                    set: { _ in
                        wearables.lastError = nil
                        assist.lastError = nil
                    }
                )
            ) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(wearables.lastError ?? assist.lastError ?? "")
            }
            .sheet(isPresented: $showSetup) {
                setupSheet
            }
        }
        .task {
            wearables.observe()
            phoneCamera.start()
            await setup.runOnce(wearables: wearables)
        }
    }

    // MARK: - Top status bar

    private var statusBar: some View {
        VStack(alignment: .leading, spacing: 2) {
            HStack(spacing: 4) {
                Text("Field Lens")
                    .font(.caption.bold())
                    .foregroundStyle(.white)
                statusDot(phoneCamera.isReady, label: "cam")
                statusDot(wearables.deviceCount > 0, label: "\(wearables.deviceCount)")
                statusDot(wearables.sessionStarted, label: "ses")
                semaphore
                Spacer()
                Button {
                    showSetup = true
                } label: {
                    Image(systemName: "gearshape")
                        .font(.caption)
                        .foregroundStyle(.black)
                        .padding(6)
                        .background(.white.opacity(0.85))
                        .clipShape(Circle())
                }
                .accessibilityLabel("Setup")
            }
            Text(statusText)
                .font(.caption2.monospaced())
                .foregroundStyle(.white)
                .lineLimit(2)
        }
        .padding(.horizontal, 1)
        .padding(.vertical, 6)
        .background(.black.opacity(0.55))
    }

    private func statusDot(_ ok: Bool, label: String) -> some View {
        HStack(spacing: 2) {
            Circle()
                .fill(ok ? Color.green : Color.gray)
                .frame(width: 8, height: 8)
            Text(label)
                .font(.caption2.monospaced())
                .foregroundStyle(.white)
        }
    }

    /// Semaphore: what the assistant is doing right now.
    private var semaphore: some View {
        Text(semaphoreText)
            .font(.caption2.bold())
            .foregroundStyle(.black)
            .padding(.horizontal, 8)
            .padding(.vertical, 2)
            .background(semaphoreColor)
            .clipShape(Capsule())
    }

    private var semaphoreText: String {
        if assist.isAsking { return "ASKING" }
        if assist.lastError != nil { return "ERROR" }
        switch assist.verdict {
        case .none:
            return phoneCamera.isReady ? "READY" : "STARTING"
        case .verified:
            return "DONE"
        case .verify:
            return "VERIFY"
        }
    }

    private var semaphoreColor: Color {
        if assist.isAsking { return .yellow }
        if assist.lastError != nil { return .red }
        switch assist.verdict {
        case .none:
            return phoneCamera.isReady ? .green : .gray
        case .verified:
            return .green
        case .verify:
            return .orange
        }
    }

    /// Rolling status: error, in-flight request, verdict detail, idle.
    /// While asking, the previous verdict yields to the live request log.
    private var statusText: String {
        if let error = assist.lastError ?? wearables.lastError {
            return error
        }
        if assist.isAsking {
            return assist.lastRequestLog
        }
        switch assist.verdict {
        case .none:
            break
        case .verified(let step, _):
            return step
        case .verify(let detail, _, _):
            return detail.isEmpty ? "Verify in manual." : detail
        }
        return assist.lastRequestLog
    }

    // MARK: - Bottom ask bar

    private var askBar: some View {
        HStack(spacing: 8) {
            TextField("Can I draw this here?", text: $assist.query)
                .textFieldStyle(.roundedBorder)
            if assist.isAsking {
                askingWave
                    .frame(maxWidth: .infinity, minHeight: 44)
                    .onReceive(pulseTimer) { _ in
                        askPulse += 1
                    }
            } else {
                Button("Ask") {
                    Task { await askAboutView() }
                }
                .buttonStyle(.borderedProminent)
                .disabled(!phoneCamera.isReady)
                .frame(minWidth: 72, minHeight: 44)
            }
        }
        .padding(.horizontal, 1)
        .padding(.vertical, 8)
        .background(.black.opacity(0.55))
    }

    /// Bouncing highlight while the back end works: one bright letter
    /// ping-pongs across "Asking", the rest stays dim.
    private var askingWave: some View {
        let word = Array("Asking")
        let period = word.count * 2 - 2
        let step = askPulse % period
        let hot = step < word.count ? step : period - step
        return HStack(spacing: 1) {
            ForEach(word.indices, id: \.self) { i in
                Text(String(word[i]))
                    .font(.title3.bold())
                    .foregroundStyle(
                        i == hot ? Color.white : Color.white.opacity(0.25))
            }
        }
    }

    /// One tap: capture the current view, then ask about it.
    private func askAboutView() async {
        if let glasses = wearables.currentFrame {
            await assist.ask(frame: glasses)
            return
        }
        do {
            let photo = try await phoneCamera.capturePhoto()
            await assist.ask(frame: photo)
        } catch let failure
            as PhoneCameraViewModel.CaptureFailure
        {
            assist.lastError = failure.message
        } catch {
            assist.lastError = error.localizedDescription
        }
    }

    // MARK: - Setup fallback sheet

    private var setupSheet: some View {
        NavigationStack {
            Form {
                TextField("Backend base URL", text: $assist.baseURLString)
                    .textInputAutocapitalization(.never)
                Button("Mock glasses") { wearables.enableMock() }
                Button("Start session") {
                    Task { await wearables.startSession() }
                }
                Button("Start glasses preview") {
                    wearables.startPreview()
                }
                Text(
                    "devices=\(wearables.deviceCount) session=\(wearables.sessionState) stream=\(wearables.streamState)"
                )
                .font(.caption2.monospaced())
            }
            .navigationTitle("Setup")
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}

/// One-shot automatic setup: mock glasses + session, once per launch.
/// Manual buttons in Setup remain as fallback; failures stay visible there.
@MainActor
final class DemoSetup: ObservableObject {
    private var didRun = false

    func runOnce(wearables: WearablesViewModel) async {
        guard !didRun else { return }
        didRun = true
        wearables.enableMock()
        await wearables.startSession()
    }
}
