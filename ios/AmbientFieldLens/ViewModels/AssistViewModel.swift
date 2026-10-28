import Foundation
import Network
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
    }

    enum Verdict {
        case none
        case verified(step: String, receipt: ReceiptInfo)
        case verify(detail: String, corrections: [CheckInfo], receipt: ReceiptInfo?)
    }

    @Published var baseURLString: String = "http://192.168.0.56:8000"
    @Published var query: String = ""
    @Published var verdict: Verdict = .none
    @Published var isAsking = false
    @Published var lastError: String?
    @Published var tcpStatus: String = "not tested"
    @Published var lastRequestLog: String = "no request yet"

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
            scoreLine: scoreLine
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
        defer { isAsking = false }

        var imageB64 = ""
        if let data = frame?.jpegData(compressionQuality: 0.7) {
            imageB64 = data.base64EncodedString()
        }
        do {
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.timeoutInterval = 10
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
            configuration.timeoutIntervalForRequest = 10
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
}
