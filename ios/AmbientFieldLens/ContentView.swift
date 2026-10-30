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
    @State private var source: FrameSource = .phone
    private let pulseTimer = Timer.publish(every: 0.25, on: .main, in: .common)
        .autoconnect()

    var body: some View {
        NavigationStack {
            ZStack {
                viewfinder
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
                Text(
                    Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion")
                        as? String ?? "?"
                )
                .font(.caption2.monospaced())
                .foregroundStyle(.white.opacity(0.6))
                statusDot(phoneCamera.isReady, label: "cam")
                statusDot(wearables.deviceCount > 0, label: "\(wearables.deviceCount)")
                statusDot(wearables.sessionStarted, label: "ses")
                semaphore
                gateChip("WORLD", mark: worldMark)
                gateChip("COVERAGE", mark: coverageMark)
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
            if isGapReportable {
                gapReportRow
            }
            if isQuoteVisible {
                quoteCard
            }
        }
        .padding(.horizontal, 1)
        .padding(.vertical, 6)
        .background(.black.opacity(0.55))
    }

    /// The manual answering: quoted excerpt when the coverage gate passed,
    /// on every path including WORLD CHECK FAILED. Dismissed with OK, back
    /// on the next answer. Never an instruction, never a pass.
    private var quotePassage: String? {
        switch assist.verdict {
        case .verify(_, _, let receipt):
            return receipt?.passage
        case .verified(_, let receipt):
            return receipt.passage
        case .none:
            return nil
        }
    }

    private var isQuoteVisible: Bool {
        guard let passage = quotePassage, !passage.isEmpty else {
            return false
        }
        return !assist.quoteDismissed
    }

    private var quoteCard: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("FROM YOUR MANUALS")
                .font(.caption2.bold())
                .foregroundStyle(.white.opacity(0.7))
            ScrollView {
                Text(AssistViewModel.formattedQuote(from: quotePassage ?? ""))
                    .font(.callout)
                    .foregroundStyle(.white)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .frame(maxHeight: 220)
            HStack {
                Spacer()
                Button {
                    assist.quoteDismissed = true
                } label: {
                    Text("OK")
                        .font(.caption.bold())
                        .foregroundStyle(.black)
                        .padding(.horizontal, 16)
                        .padding(.vertical, 4)
                        .background(Color.white.opacity(0.92))
                        .clipShape(Capsule())
                }
                .accessibilityLabel("Dismiss manual quote")
            }
        }
        .padding(8)
        .background(.black.opacity(0.45))
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }

    /// The repair loop made visible: only a NOT COVERED refusal arms it.
    /// WORLD CHECK FAILED and every other deny never show this button.
    private var isGapReportable: Bool {
        guard let d = gateDetail else { return false }
        return d.hasPrefix("NOT COVERED")
    }

    private var gapReportRow: some View {
        HStack(spacing: 6) {
            switch assist.gapState {
            case .reported:
                Text("Reported")
                    .font(.caption2.bold())
                    .foregroundStyle(.black)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 4)
                    .background(Color.gray.opacity(0.9))
                    .clipShape(Capsule())
            case .posting:
                Text("Reporting…")
                    .font(.caption2.bold())
                    .foregroundStyle(.black)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 4)
                    .background(Color.yellow.opacity(0.9))
                    .clipShape(Capsule())
            case .none:
                Button {
                    Task { await assist.reportGap() }
                } label: {
                    Text("Report missing instruction")
                        .font(.caption2.bold())
                        .foregroundStyle(.black)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 4)
                        .background(Color.white.opacity(0.92))
                        .clipShape(Capsule())
                }
                .accessibilityLabel("Report missing instruction")
            }
            if let error = assist.gapError {
                Text(error)
                    .font(.caption2.monospaced())
                    .foregroundStyle(.white)
            }
        }
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

    /// Gate chips derived from the server prefix contract
    /// (docs/live-assist-wiring.md). Display only: no chip can pass anything.
    private var gateDetail: String? {
        if case .verify(let detail, _, _) = assist.verdict, !detail.isEmpty {
            return detail
        }
        return nil
    }

    /// Gate chips: only the two real failures earn color. Everything the
    /// system has not established renders gray "…" — a green ✓ beside an
    /// amber verdict would claim what the backend documents it cannot.
    private var worldMark: (String, Color) {
        guard let d = gateDetail else { return ("–", .gray) }
        if d.hasPrefix("WORLD CHECK FAILED") { return ("✗", .orange) }
        return ("…", .gray)
    }

    private var coverageMark: (String, Color) {
        guard let d = gateDetail else { return ("–", .gray) }
        if d.hasPrefix("NOT COVERED") { return ("✗", .orange) }
        return ("…", .gray)
    }

    private func gateChip(_ name: String, mark: (String, Color)) -> some View {
        HStack(spacing: 2) {
            Text(name)
            Text(mark.0).bold()
        }
        .font(.caption2.monospaced())
        .foregroundStyle(.black)
        .padding(.horizontal, 6)
        .padding(.vertical, 2)
        .background(mark.1.opacity(0.9))
        .clipShape(Capsule())
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

    /// The rendered source IS the submitted source. Switching clears the
    /// retained phone still so a stale phone frame can never ride along
    /// with a glasses ask (and vice versa: the binding ignores it).
    private var viewfinder: some View {
        Group {
            switch source {
            case .phone:
                PhoneCameraPreview(session: phoneCamera.previewSession)
            case .glasses:
                if let frame = wearables.currentFrame {
                    Image(uiImage: frame)
                        .resizable()
                        .aspectRatio(contentMode: .fill)
                } else {
                    Text("No glasses frame — start a session, or use Phone.")
                        .foregroundStyle(.white)
                        .padding()
                }
            }
        }
    }

    private var askFrame: UIImage? {
        resolveFrame(
            source: source,
            glasses: wearables.currentFrame,
            phone: phoneCamera.lastPhoto)
    }

    /// Ask is armed only when the SELECTED source holds a frame.
    private var canAsk: Bool {
        switch source {
        case .phone:
            return phoneCamera.isReady
        case .glasses:
            return askFrame != nil
        }
    }

    private func switchSource() {
        source.toggle()
        if source == .glasses {
            phoneCamera.lastPhoto = nil
        }
    }

    // MARK: - Bottom ask bar

    private var askBar: some View {
        HStack(spacing: 8) {
            Button(source.label) { switchSource() }
                .font(.caption2.bold())
                .foregroundStyle(.black)
                .padding(.horizontal, 8)
                .padding(.vertical, 6)
                .background(.white.opacity(0.85))
                .clipShape(Capsule())
                .accessibilityLabel("Frame source, currently \(source.label)")
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
                .disabled(!canAsk)
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

    /// One tap: capture the selected source, then ask about exactly that.
    private func askAboutView() async {
        switch source {
        case .glasses:
            await assist.ask(frame: askFrame)
        case .phone:
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
