import Foundation
import Network
import SwiftUI
import UIKit
import os

private let assistLog = Logger(
    subsystem: "art.robotross.AmbientFieldLens", category: "assist"
)

/// Talks to backend POST /assist and holds the gate verdict for the HUD.
/// Decodes the Phase 3 evidence shape; missing optional fields fall back
/// to the Phase 1 stub shape. The client never manufactures green.
@MainActor
final class AssistViewModel: ObservableObject {
    struct CheckInfo {
        var name: String
        var state: String
        var correction: String
    }

    struct ReceiptInfo {
        var summary: String
        var scoreLine: String?
        /// Quoted manual excerpt, present only when the coverage gate
        /// passed. Quotation, never an endorsed instruction.
        var passage: String?
    }

    enum Verdict {
        case none
        case verified(step: String, receipt: ReceiptInfo)
        case verify(detail: String, corrections: [CheckInfo], receipt: ReceiptInfo?)
    }

    @Published var baseURLString: String = "https://miguel-40686--afl-assist-api.us-east.modal.run"
    @Published var query: String = "Can I draw this here?"
    @Published var verdict: Verdict = .none
    @Published var isAsking = false
    @Published var lastError: String?
    @Published var tcpStatus: String = "not tested"
    @Published var lastRequestLog: String = "no request yet"
    @Published var gapState: GapState = .none
    @Published var gapError: String?
    /// Quote card dismissal. One card per answer: reset on every ask.
    @Published var quoteDismissed = false

    /// One report per answer. Reset on every new ask.
    enum GapState {
        case none
        case posting
        case reported
    }

    /// The question that produced the current verdict (may differ from the
    /// live query field if the operator retyped after asking).
    private var askedQuery: String = ""

    /// Machine tail of a NOT COVERED detail (docs/live-assist-wiring.md):
    /// the measured distance and the top chunk id the report must carry
    /// verbatim. Pure, so the simulator suite pins it.
    /// Manual passages are plain text with markdown conventions AND
    /// literal backslashes (Windows paths). Display pipeline, all pure:
    /// paths condense, `##+` numbering runs drop (a lone `#` keeps its
    /// heading), inline code spans get boxed backgrounds, backslashes are
    /// doubled so none is eaten as an escape. Falls back to plain text if
    /// parsing fails. Pinned by tests.
    nonisolated static func formattedQuote(from text: String) -> AttributedString {
        var src = Self.condensedPaths(in: text)
        src = src.replacingOccurrences(
            of: "#{2,}\\s*", with: " ", options: .regularExpression
        )
        src = Self.boxCodeSpans(in: src)
        let escaped = src.replacingOccurrences(of: "\\", with: "\\\\")
        guard var rendered = try? AttributedString(markdown: escaped) else {
            return AttributedString(src)
        }
        Self.decorateCode(in: &rendered)
        return rendered
    }

    nonisolated private static let codeOpen = "\u{E000}"
    nonisolated private static let codeClose = "\u{E001}"

    /// Wrap `code` spans in private-use markers that survive markdown
    /// parsing, so the spans can be found and boxed afterwards.
    nonisolated static func boxCodeSpans(in text: String) -> String {
        guard
            let pattern = try? NSRegularExpression(pattern: "`([^`\\n]+)`")
        else { return text }
        var out = text
        let range = NSRange(text.startIndex..., in: text)
        for match in pattern.matches(in: text, range: range).reversed() {
            guard
                let full = Range(match.range, in: text),
                let inner = Range(match.range(at: 1), in: text)
            else { continue }
            out.replaceSubrange(
                full, with: codeOpen + text[inner] + codeClose
            )
        }
        return out
    }

    /// Box code spans and fenced blocks with a subtle background. Runs
    /// first for block intents, then pairs the private-use markers.
    nonisolated static func decorateCode(in rendered: inout AttributedString) {
        let box = Color.white.opacity(0.16)
        for run in rendered.runs {
            if let intent = run.attributes.presentationIntent,
                "\(intent)".contains("codeBlock")
            {
                rendered[run.range].backgroundColor = box
            }
        }
        var opens: [AttributedString.Index] = []
        var closes: [AttributedString.Index] = []
        var idx = rendered.characters.startIndex
        while idx != rendered.characters.endIndex {
            let ch = rendered.characters[idx]
            if ch == Character(codeOpen) { opens.append(idx) }
            if ch == Character(codeClose) { closes.append(idx) }
            idx = rendered.characters.index(after: idx)
        }
        for (open, close) in zip(opens, closes) {
            guard open < close else { continue }
            let innerLower = rendered.characters.index(after: open)
            rendered[innerLower..<close].backgroundColor = box
            rendered[innerLower..<close].font = .system(
                .callout, design: .monospaced
            )
        }
        for marker in (opens + closes).sorted(by: >) {
            rendered.removeSubrange(
                marker..<rendered.index(afterCharacter: marker)
            )
        }
    }

    /// Phone display only: file paths condense to basenames
    /// (`skills\hunit\hunit_write.py` -> `hunit_write.py`). The quoted
    /// passage underneath stays verbatim; provenance travels in the
    /// machine tail, never on screen. URLs, versions and bare filenames
    /// are left alone. Pure, pinned by tests.
    nonisolated static func condensedPaths(in text: String) -> String {
        // No spaces in either class: a path match must never eat the
        // prose before it. A match preceded by ":" is a URL scheme.
        guard
            let pattern = try? NSRegularExpression(
                pattern: "([\\w.~\\\\/\\-]*[\\\\/])([\\w.\\-]*[A-Za-z][\\w.\\-]*\\.\\w{1,5})\\b"
            )
        else { return text }
        let range = NSRange(text.startIndex..., in: text)
        var out = text
        for match in pattern.matches(in: text, range: range).reversed() {
            guard
                let full = Range(match.range, in: text),
                let base = Range(match.range(at: 2), in: text)
            else { continue }
            if text[..<full.lowerBound].last == ":" { continue }
            out.replaceSubrange(full, with: String(text[base]))
        }
        return out
    }

    nonisolated static func gapTail(
        from detail: String
    ) -> (chunkID: String, distance: Double)? {
        guard detail.hasPrefix("NOT COVERED") else { return nil }
        guard
            let topRange = detail.range(
                of: "top=([0-9a-f]{16,128})\\s*$",
                options: .regularExpression
            )
        else { return nil }
        let tail = String(detail[topRange]).dropFirst(4).trimmingCharacters(
            in: .whitespaces
        )
        guard
            let dRange = detail.range(
                of: "d=([0-9]*\\.?[0-9]+)>",
                options: .regularExpression
            )
        else { return nil }
        let dText =
            String(detail[dRange])
            .dropFirst(2)
            .dropLast()
        guard let distance = Double(dText) else { return nil }
        return (String(tail), distance)
    }

    private struct CheckResponse: Decodable {
        var name: String
        var state: String
        var reason: String
        var correction: String?
    }

    private struct GroundingResponse: Decodable {
        var score: Double?
        var threshold: Double?
        var method: String?
    }

    private struct ReceiptResponse: Decodable {
        var frame_sha256: String?
        var chunk_ids: [String]?
        var model: String?
    }

    private struct AssistResponse: Decodable {
        var verdict: String
        var step: String?
        var detail: String?
        var checks: [CheckResponse]?
        var grounding: GroundingResponse?
        var receipt: ReceiptResponse?
        var passage: String?
    }

    /// Downscale a camera frame to fit the server's wire contract
    /// (<= 4 MPixels, <= 2 MB JPEG). Full-res phone frames are rejected
    /// with 422, so this runs before every ask with a frame.
    static func contractFrameJPEG(_ frame: UIImage) -> Data? {
        let maxDimension: CGFloat = 1600
        let size = frame.size
        let longest = max(size.width, size.height)
        let scaled: UIImage
        if longest > maxDimension, let cg = frame.cgImage {
            let ratio = maxDimension / longest
            let target = CGSize(
                width: floor(size.width * ratio),
                height: floor(size.height * ratio)
            )
            UIGraphicsBeginImageContextWithOptions(target, true, 1.0)
            UIImage(cgImage: cg).draw(in: CGRect(origin: .zero, size: target))
            scaled = UIGraphicsGetImageFromCurrentImageContext() ?? frame
            UIGraphicsEndImageContext()
        } else {
            scaled = frame
        }
        return scaled.jpegData(compressionQuality: 0.7)
    }

    private struct AssistRequest: Encodable {
        var query: String
        var image_jpeg_base64: String
    }

    private static func receipt(
        from response: AssistResponse
    ) -> ReceiptInfo {
        var parts: [String] = []
        if let sha = response.receipt?.frame_sha256, !sha.isEmpty {
            parts.append("frame " + sha.prefix(12))
        }
        if let chunks = response.receipt?.chunk_ids, !chunks.isEmpty {
            parts.append("\(chunks.count) chunks")
        }
        if let model = response.receipt?.model, !model.isEmpty {
            parts.append(model)
        }
        var scoreLine: String?
        if let score = response.grounding?.score,
            let threshold = response.grounding?.threshold
        {
            var line =
                String(format: "score %.3f / %.2f", score, threshold)
            if let method = response.grounding?.method, !method.isEmpty
            {
                line += " · " + method
            }
            scoreLine = line
        }
        return ReceiptInfo(
            summary: parts.isEmpty ? "no receipt" : parts.joined(separator: " · "),
            scoreLine: scoreLine,
            passage: (response.passage?.isEmpty == false) ? response.passage : nil
        )
    }

    /// Raw TCP connect to the configured host:port. Bypasses HTTP and
    /// ATS verdicts: established means routing works and the fault is
    /// HTTP-layer; failed means the device cannot route there at all.
    func testTCP() {
        guard let host = URL(string: baseURLString)?.host,
            let portString = URL(string: baseURLString)?.port
        else {
            tcpStatus = "bad URL"
            return
        }
        tcpStatus = "connecting \(host):\(portString)…"
        let connection = NWConnection(
            host: NWEndpoint.Host(host),
            port: NWEndpoint.Port(rawValue: UInt16(portString))!,
            using: .tcp
        )
        connection.stateUpdateHandler = { [weak self] state in
            Task { @MainActor in
                switch state {
                case .ready:
                    self?.tcpStatus = "TCP established"
                    connection.cancel()
                case .failed(let error):
                    self?.tcpStatus = "TCP failed: \(error)"
                    connection.cancel()
                case .cancelled:
                    break
                default:
                    break
                }
            }
        }
        connection.start(queue: .global())
    }

    func ask(frame: UIImage?) async {
        guard
            let url = URL(string: baseURLString + "/assist")
        else {
            lastError = "Bad backend URL."
            return
        }
        isAsking = true
        lastError = nil
        askedQuery = query
        // New ask clears the previous answer: quote card, report button,
        // chips and detail all fall back to idle until it lands.
        verdict = .none
        gapState = .none
        gapError = nil
        quoteDismissed = false
        defer { isAsking = false }

        var imageB64 = ""
        if let frame = frame,
            let data = Self.contractFrameJPEG(frame)
        {
            imageB64 = data.base64EncodedString()
        }
        do {
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            // Live provider path (retrieval + SAM + Glimmer) can take a
            // minute warm and several minutes cold. Fail loudly, not early.
            request.timeoutInterval = 180
            request.setValue(
                "application/json", forHTTPHeaderField: "Content-Type"
            )
            let body = try JSONEncoder().encode(
                AssistRequest(query: query, image_jpeg_base64: imageB64)
            )
            request.httpBody = body
            let started = Date()
            assistLog.debug(
                "POST \(url.absoluteString, privacy: .public) body=\(body.count) bytes"
            )
            self.lastRequestLog =
                "POST \(url.host ?? "?"):\(url.port ?? 0)/assist body=\(body.count)B…"
            let configuration = URLSessionConfiguration.default
            configuration.timeoutIntervalForRequest = 180
            let session = URLSession(configuration: configuration)
            let (data, response) = try await session.data(for: request)
            let status =
                (response as? HTTPURLResponse)?.statusCode ?? -1
            let elapsed = Date().timeIntervalSince(started)
            assistLog.debug(
                "response status=\(status) bytes=\(data.count) in \(elapsed, format: .fixed(precision: 2))s"
            )
            self.lastRequestLog =
                "status=\(status) bytes=\(data.count) in \(String(format: "%.2f", elapsed))s"
            let decoded = try JSONDecoder().decode(
                AssistResponse.self, from: data
            )
            let receipt = Self.receipt(from: decoded)
            if decoded.verdict == "verified", let step = decoded.step {
                verdict = .verified(step: step, receipt: receipt)
            } else {
                let corrections = (decoded.checks ?? []).filter {
                    $0.state != "pass"
                }.map {
                    CheckInfo(
                        name: $0.name, state: $0.state,
                        correction: $0.correction ?? "")
                }
                verdict = .verify(
                    detail: decoded.detail ?? "Verify in the manual.",
                    corrections: corrections, receipt: receipt)
            }
        } catch {
            verdict = .none
            gapState = .none
            gapError = nil
            let nsError = error as NSError
            assistLog.error(
                "request failed: \(nsError.domain, privacy: .public) \(nsError.code) \(error.localizedDescription, privacy: .public)"
            )
            self.lastRequestLog =
                "failed [\(nsError.domain) \(nsError.code)]"
            lastError =
                "\(error.localizedDescription) [\(nsError.domain) \(nsError.code)]"
        }
    }

    private struct GapReportRequest: Encodable {
        var question: String
        var answer: String
        // swiftlint:disable:next identifier_name
        var retrieved_chunk_ids: [String]
        var top1_distance: Double
        var comment: String
    }

    private struct GapReportResponse: Decodable {
        var ok: Bool
        var error: String?
    }

    /// One tap files the coverage refusal showing on screen into the SM
    /// Feedback Flywheel. Only the NOT COVERED prefix arms it; anything
    /// else (or an unparseable tail) is a silent no-op. One report per
    /// answer: after success the button stays "Reported". Failures render
    /// inline and keep the button armed. Never blocks the viewfinder.
    func reportGap() async {
        guard case .verify(let detail, _, _) = verdict,
            let tail = Self.gapTail(from: detail),
            gapState != .reported
        else { return }
        guard let url = URL(string: baseURLString + "/report_gap") else {
            gapError = "Bad backend URL."
            return
        }
        gapState = .posting
        gapError = nil
        defer {
            if gapState == .posting { gapState = .none }
        }
        do {
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.timeoutInterval = 60
            request.setValue(
                "application/json", forHTTPHeaderField: "Content-Type"
            )
            request.httpBody = try JSONEncoder().encode(
                GapReportRequest(
                    question: askedQuery,
                    answer: detail,
                    retrieved_chunk_ids: [tail.chunkID],
                    top1_distance: tail.distance,
                    comment: ""
                )
            )
            let (data, _) = try await URLSession.shared.data(for: request)
            let decoded = try JSONDecoder().decode(
                GapReportResponse.self, from: data
            )
            if decoded.ok {
                gapState = .reported
            } else {
                gapError = "Not filed (\(decoded.error ?? "unknown"))."
            }
        } catch {
            gapError = "Not filed (network)."
        }
    }
}
