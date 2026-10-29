import SwiftUI
import UIKit

/// Demo viewfinder: fullscreen camera, one Ask button, verdict overlay.
/// No columns, no scrolling, nothing to squeeze. Glasses/session setup
/// happens automatically at launch; manual controls hide in Setup.
struct ContentView: View {
    @StateObject private var wearables = WearablesViewModel()
    @StateObject private var assist = AssistViewModel()
    @StateObject private var phoneCamera = PhoneCameraViewModel()
    @StateObject private var setup = DemoSetup()
    @State private var showSetup = false

    /// Demo frame: glasses first, phone-camera still second.
    private var askFrame: UIImage? {
        wearables.currentFrame ?? phoneCamera.lastPhoto
    }

    var body: some View {
        NavigationStack {
            ZStack {
                PhoneCameraPreview(session: phoneCamera.previewSession)
                    .ignoresSafeArea()
                VStack(spacing: 0) {
                    topBar
                    Spacer()
                    bottomPanel
                }
            }
            .navigationTitle("Field Lens")
            .navigationBarTitleDisplayMode(.inline)
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

    private var topBar: some View {
        HStack {
            Text(setup.status(wearables: wearables, cameraReady: phoneCamera.isReady))
                .font(.caption2.monospaced())
                .foregroundStyle(.white)
                .padding(.horizontal, 10)
                .padding(.vertical, 4)
                .background(.black.opacity(0.55))
                .clipShape(Capsule())
            Spacer()
            Button("Setup") { showSetup = true }
                .font(.caption)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(.white.opacity(0.85))
                .clipShape(Capsule())
        }
        .padding(.horizontal, 12)
        .padding(.top, 8)
    }

    private var bottomPanel: some View {
        VStack(alignment: .leading, spacing: 10) {
            TextField("Question", text: $assist.query)
                .textFieldStyle(.roundedBorder)
            Button(assist.isAsking ? "Asking…" : "Ask") {
                Task { await askAboutView() }
            }
            .buttonStyle(.borderedProminent)
            .disabled(assist.isAsking || !phoneCamera.isReady)
            .frame(maxWidth: .infinity, minHeight: 56)
            verdictLine
            Text(assist.lastRequestLog)
                .font(.caption2.monospaced())
                .foregroundStyle(.white)
        }
        .padding(12)
        .background(.black.opacity(0.55))
        .clipShape(
            RoundedRectangle(cornerRadius: 16, style: .continuous))
        .padding(12)
    }

    /// One status line, not a dialog: dot + short text.
    private var verdictLine: some View {
        HStack(spacing: 8) {
            Circle()
                .fill(verdictColor)
                .frame(width: 10, height: 10)
            Text(verdictText)
                .font(.callout)
                .foregroundStyle(.white)
                .lineLimit(2)
        }
    }

    private var verdictColor: Color {
        switch assist.verdict {
        case .none:
            .gray
        case .verified:
            .green
        case .verify:
            .orange
        }
    }

    private var verdictText: String {
        switch assist.verdict {
        case .none:
            phoneCamera.isReady
                ? "Ready — frame the rig and Ask."
                : "Starting camera…"
        case .verified(let step, _):
            step
        case .verify(let detail, _, _):
            detail.isEmpty ? "Verify in manual." : detail
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
                Text(setup.status(wearables: wearables, cameraReady: phoneCamera.isReady))
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

    func status(wearables: WearablesViewModel, cameraReady: Bool) -> String {
        "camera=\(cameraReady ? "ready" : "starting") glasses=\(wearables.deviceCount) session=\(wearables.sessionState)"
    }
}
