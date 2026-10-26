import Foundation
import UIKit

/// Talks to backend POST /assist and holds the gate verdict for the HUD.
@MainActor
final class AssistViewModel: ObservableObject {
    enum Verdict {
        case none
        case verified(step: String)
        case verify(detail: String)
    }

    @Published var baseURLString: String = "http://localhost:8000"
    @Published var query: String = ""
    @Published var verdict: Verdict = .none
    @Published var isAsking = false
    @Published var lastError: String?

    private struct AssistResponse: Decodable {
        var verdict: String
        var step: String?
        var score: Double
        var detail: String
    }

    private struct AssistRequest: Encodable {
        var query: String
        var image_jpeg_base64: String
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
            request.setValue(
                "application/json", forHTTPHeaderField: "Content-Type"
            )
            request.httpBody = try JSONEncoder().encode(
                AssistRequest(query: query, image_jpeg_base64: imageB64)
            )
            let (data, _) = try await URLSession.shared.data(for: request)
            let response = try JSONDecoder().decode(
                AssistResponse.self, from: data
            )
            if response.verdict == "verified", let step = response.step {
                verdict = .verified(step: step)
            } else {
                verdict = .verify(detail: response.detail)
            }
        } catch {
            verdict = .none
            lastError = error.localizedDescription
        }
    }
}
