import SwiftUI

struct ContentView: View {
    @StateObject private var wearables = WearablesViewModel()
    @StateObject private var assist = AssistViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    registrationSection
                    sessionSection
                    previewSection
                    assistSection
                    HUDCard(verdict: assist.verdict)
                        .frame(maxWidth: .infinity)
                }
                .padding()
            }
            .navigationTitle("Ambient Field Lens")
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

    private var registrationSection: some View {
        GroupBox("1 · Registration") {
            VStack(alignment: .leading, spacing: 8) {
                Text("State: \(wearables.registrationState)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                HStack {
                    Button("Register") {
                        Task { await wearables.register() }
                    }
                    .buttonStyle(.borderedProminent)
                    Button("Mock glasses") {
                        wearables.enableMock()
                    }
                    .buttonStyle(.bordered)
                }
            }
        }
    }

    private var sessionSection: some View {
        GroupBox("2 · Session (devices: \(wearables.deviceCount))") {
            VStack(alignment: .leading, spacing: 8) {
                Text("Session: \(wearables.sessionState)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                HStack {
                    Button("Start session") {
                        Task { await wearables.startSession() }
                    }
                    .buttonStyle(.borderedProminent)
                    Button("End session", role: .destructive) {
                        wearables.endSession()
                    }
                    .buttonStyle(.bordered)
                }
            }
        }
    }

    private var previewSection: some View {
        GroupBox("3 · Preview (\(wearables.streamState))") {
            VStack(alignment: .leading, spacing: 8) {
                if let frame = wearables.currentFrame {
                    Image(uiImage: frame)
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                } else {
                    Text("No frames yet.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                HStack {
                    Button("Start preview") {
                        wearables.startPreview()
                    }
                    .buttonStyle(.borderedProminent)
                    Button("Stop preview") {
                        wearables.stopPreview()
                    }
                    .buttonStyle(.bordered)
                }
            }
        }
    }

    private var assistSection: some View {
        GroupBox("4 · Ask (frame → /assist → HUD)") {
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
