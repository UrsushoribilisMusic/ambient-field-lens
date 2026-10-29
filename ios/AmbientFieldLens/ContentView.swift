import SwiftUI
import UIKit

/// Demo-first screen: camera + Ask + verdict, no setup taps.
/// Glasses/session controls live in Setup for later; the robot shoot runs
/// on the phone camera with everything prefilled and auto-started.
struct ContentView: View {
    @StateObject private var wearables = WearablesViewModel()
    @StateObject private var assist = AssistViewModel()
    @StateObject private var phoneCamera = PhoneCameraViewModel()
    @StateObject private var setup = DemoSetup()
    @Environment(\.verticalSizeClass) private var verticalSizeClass

    /// Demo frame: glasses first, phone-camera still second.
    private var askFrame: UIImage? {
        wearables.currentFrame ?? phoneCamera.lastPhoto
    }

    var body: some View {
        NavigationStack {
            Group {
                if verticalSizeClass == .compact {
                    HStack(alignment: .top, spacing: 16) {
                        cameraCard
                        ScrollView {
                            VStack(alignment: .leading, spacing: 16) {
                                askCard
                                hudCard
                                setupCard
                            }
                            .padding()
                        }
                        .frame(maxWidth: 420)
                    }
                } else {
                    ScrollView {
                        VStack(alignment: .leading, spacing: 16) {
                            cameraCard
                            askCard
                            hudCard
                            setupCard
                        }
                        .padding()
                    }
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
        }
        .task {
            wearables.observe()
            phoneCamera.start()
            await setup.runOnce(wearables: wearables)
        }
    }

    private var cameraCard: some View {
        GroupBox("Camera") {
            VStack(alignment: .leading, spacing: 8) {
                if let frame = wearables.currentFrame {
                    Image(uiImage: frame)
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                } else if let photo = phoneCamera.lastPhoto {
                    Image(uiImage: photo)
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                } else {
                    PhoneCameraPreview(session: phoneCamera.previewSession)
                        .frame(minHeight: 260)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                }
                if let error = phoneCamera.lastError {
                    Text(error)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
                Button("Capture frame") {
                    phoneCamera.capture()
                }
                .buttonStyle(.borderedProminent)
                .disabled(!phoneCamera.isReady)
                .frame(maxWidth: .infinity, minHeight: 48)
                Text(
                    wearables.currentFrame != nil
                        ? "Frame source: glasses."
                        : phoneCamera.lastPhoto != nil
                            ? "Frame source: phone still."
                            : "No frame yet — capture one."
                )
                .font(.caption2)
                .foregroundStyle(.secondary)
            }
        }
    }

    private var askCard: some View {
        GroupBox("Ask") {
            VStack(alignment: .leading, spacing: 8) {
                TextField("Question", text: $assist.query)
                    .textFieldStyle(.roundedBorder)
                Button(assist.isAsking ? "Asking…" : "Ask") {
                    Task {
                        await assist.ask(frame: askFrame)
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(assist.isAsking || askFrame == nil)
                .frame(maxWidth: .infinity, minHeight: 56)
                Text(assist.lastRequestLog)
                    .font(.caption2.monospaced())
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var hudCard: some View {
        HUDCard(verdict: assist.verdict)
    }

    private var setupCard: some View {
        DisclosureGroup("Setup (automatic)") {
            VStack(alignment: .leading, spacing: 8) {
                Text(setup.status(wearables: wearables))
                    .font(.caption2.monospaced())
                    .foregroundStyle(.secondary)
                TextField("Backend base URL", text: $assist.baseURLString)
                    .textFieldStyle(.roundedBorder)
                    .textInputAutocapitalization(.never)
                HStack {
                    Button("Mock glasses") {
                        wearables.enableMock()
                    }
                    .buttonStyle(.bordered)
                    Button("Start session") {
                        Task { await wearables.startSession() }
                    }
                    .buttonStyle(.bordered)
                    Button("Start preview") {
                        wearables.startPreview()
                    }
                    .buttonStyle(.bordered)
                }
                .font(.caption)
            }
        }
        .font(.caption)
        .foregroundStyle(.secondary)
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

    func status(wearables: WearablesViewModel) -> String {
        "devices=\(wearables.deviceCount) session=\(wearables.sessionState) stream=\(wearables.streamState)"
    }
}
