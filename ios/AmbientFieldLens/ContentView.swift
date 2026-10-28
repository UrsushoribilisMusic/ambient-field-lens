import SwiftUI

/// Guided demo flow: each step unlocks the next.
/// 1 Glasses → 2 Session → 3 Preview → 4 Ask → HUD card.
struct ContentView: View {
    @StateObject private var wearables = WearablesViewModel()
    @StateObject private var assist = AssistViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    glassesSection
                    sessionSection
                    previewSection
                    assistSection
                    GeometryReader { proxy in
                        HUDCard(verdict: assist.verdict)
                            .scaleEffect(
                                min(1, proxy.size.width / 600),
                                anchor: .topLeading
                            )
                            .frame(
                                width: 600,
                                height: 600,
                                alignment: .topLeading
                            )
                    }
                    .frame(
                        height: min(600, UIScreen.main.bounds.width)
                    )
                }
                .padding()
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
        }
    }

    private var glassesSection: some View {
        GroupBox("1 · Glasses") {
            VStack(alignment: .leading, spacing: 8) {
                Text(
                    wearables.deviceCount > 0
                        ? "\(wearables.deviceCount) connected"
                        : "No glasses yet"
                )
                .font(.caption)
                .foregroundStyle(.secondary)
                HStack {
                    Button("Mock glasses") {
                        wearables.enableMock()
                    }
                    .buttonStyle(.borderedProminent)
                    Button("Register") {
                        Task { await wearables.register() }
                    }
                    .buttonStyle(.bordered)
                }
                Text("Demo path: Mock glasses. Register needs the Meta AI app.")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var sessionSection: some View {
        GroupBox("2 · Session") {
            VStack(alignment: .leading, spacing: 8) {
                Text(
                    wearables.sessionStarted
                        ? "Connected" : "Session: \(wearables.sessionState)"
                )
                .font(.caption)
                .foregroundStyle(.secondary)
                HStack {
                    Button("Start session") {
                        Task { await wearables.startSession() }
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(wearables.deviceCount == 0)
                    Button("End session", role: .destructive) {
                        wearables.endSession()
                    }
                    .buttonStyle(.bordered)
                    .disabled(!wearables.sessionStarted)
                }
                if wearables.deviceCount == 0 {
                    Text("Connect glasses first (step 1).")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }
        }
    }

    private var previewSection: some View {
        GroupBox("3 · Preview") {
            VStack(alignment: .leading, spacing: 8) {
                if let frame = wearables.currentFrame {
                    Image(uiImage: frame)
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                } else {
                    Text(
                        wearables.streamState == "Stopped"
                            ? "Preview stopped." : "Waiting for frames…"
                    )
                    .font(.caption)
                    .foregroundStyle(.secondary)
                }
                HStack {
                    Button("Start preview") {
                        wearables.startPreview()
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(!wearables.sessionStarted)
                    Button("Stop preview") {
                        wearables.stopPreview()
                    }
                    .buttonStyle(.bordered)
                }
            }
        }
    }

    private var assistSection: some View {
        GroupBox("4 · Ask") {
            VStack(alignment: .leading, spacing: 8) {
                TextField("Backend base URL", text: $assist.baseURLString)
                    .textFieldStyle(.roundedBorder)
                    .textInputAutocapitalization(.never)
                TextField("What part is this?", text: $assist.query)
                    .textFieldStyle(.roundedBorder)
                Button(assist.isAsking ? "Asking…" : "Ask") {
                    Task {
                        await assist.ask(frame: wearables.currentFrame)
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(assist.isAsking)
            }
        }
    }
}
