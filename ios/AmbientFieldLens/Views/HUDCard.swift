import SwiftUI

/// 600x600 HUD card: green verified step, or amber verify-in-manual
/// with failing checks, grounding score and receipt identifiers.
struct HUDCard: View {
    var verdict: AssistViewModel.Verdict

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            switch verdict {
            case .none:
                Text("Ambient Field Lens")
                    .font(.title2.bold())
                Text("Ask about the part in view.")
                    .foregroundStyle(.secondary)
            case .verified(let step, let receipt):
                Label("Verified", systemImage: "checkmark.seal.fill")
                    .font(.title2.bold())
                    .foregroundStyle(.green)
                Text(step)
                    .font(.body)
                receiptView(receipt)
            case .verify(let detail, let corrections, let receipt):
                Label(
                    "Verify in manual",
                    systemImage: "exclamationmark.triangle.fill"
                )
                .font(.title2.bold())
                .foregroundStyle(.orange)
                Text(
                    detail.isEmpty
                        ? "Do not proceed from this card." : detail
                )
                .font(.body)
                .foregroundStyle(.secondary)
                ForEach(corrections, id: \.name) { check in
                    Text("\(check.name): \(check.correction)")
                        .font(.callout)
                }
                if let receipt {
                    receiptView(receipt)
                }
            }
            Spacer()
        }
        .padding(24)
        .frame(width: 600, height: 600)
        .background(.thinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 28))
    }

    private func receiptView(
        _ receipt: AssistViewModel.ReceiptInfo
    ) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            if let scoreLine = receipt.scoreLine {
                Text(scoreLine)
                    .font(.caption.monospaced())
            }
            Text(receipt.summary)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }
}
