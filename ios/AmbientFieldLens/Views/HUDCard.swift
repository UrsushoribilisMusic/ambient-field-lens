import SwiftUI

/// 600x600 HUD card: green verified step, or amber verify-in-manual.
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
            case .verified(let step):
                Label("Verified", systemImage: "checkmark.seal.fill")
                    .font(.title2.bold())
                    .foregroundStyle(.green)
                Text(step)
                    .font(.body)
            case .verify(let detail):
                Label("Verify in manual", systemImage: "exclamationmark.triangle.fill")
                    .font(.title2.bold())
                    .foregroundStyle(.orange)
                Text(detail.isEmpty ? "Do not proceed from this card." : detail)
                    .font(.body)
                    .foregroundStyle(.secondary)
            }
            Spacer()
        }
        .padding(24)
        .frame(width: 600, height: 600)
        .background(.thinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 28))
    }
}
