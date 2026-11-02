import SwiftUI
import UIKit

/// Phone-side render of the glasses Display. Mock only: shows what the
/// last sent amber card looks like without wearing hardware.
struct MockDisplayPreview: UIViewRepresentable {
    let makeView: () -> UIView?

    func makeUIView(context: Context) -> UIView {
        makeView() ?? UIView()
    }

    func updateUIView(_ uiView: UIView, context: Context) {}
}
