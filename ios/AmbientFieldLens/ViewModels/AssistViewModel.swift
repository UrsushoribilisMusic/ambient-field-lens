import Foundation
import UIKit

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

    @Published var baseURLString: String = "http://localhost:8000"
    @Published var query: String = ""
    @Published var verdict: Verdict = .none
    @Published var isAsking = false
    @Published var lastError: String?

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
            request.httpBody = try JSONEncoder().encode(
                AssistRequest(query: query, image_jpeg_base64: imageB64)
            )
            let configuration = URLSessionConfiguration.default
            configuration.timeoutIntervalForRequest = 10
            let session = URLSession(configuration: configuration)
            let (data, _) = try await session.data(for: request)
            let response = try JSONDecoder().decode(
                AssistResponse.self, from: data
            )
            let receipt = Self.receipt(from: response)
            if response.verdict == "verified", let step = response.step {
                verdict = .verified(step: step, receipt: receipt)
            } else {
                let corrections = (response.checks ?? []).filter {
                    $0.state != "pass"
                }.map {
                    CheckInfo(
                        name: $0.name, state: $0.state,
                        correction: $0.correction ?? "")
                }
                verdict = .verify(
                    detail: response.detail ?? "Verify in the manual.",
                    corrections: corrections, receipt: receipt)
            }
        } catch {
            verdict = .none
            lastError = error.localizedDescription
        }
    }
}
