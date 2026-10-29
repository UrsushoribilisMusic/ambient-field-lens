import UIKit

/// Frame-source selection for Ask. The request always carries the frame
/// from the source rendered in the viewfinder — never a retained frame
/// from the other source.
enum FrameSource: String, CaseIterable {
    case phone
    case glasses

    var label: String {
        switch self {
        case .phone: return "Phone"
        case .glasses: return "Glass"
        }
    }

    mutating func toggle() {
        self = self == .phone ? .glasses : .phone
    }
}

/// Pure binding: the submitted frame for a source selection.
/// Kept free of UI so a unit test can pin it.
func resolveFrame(
    source: FrameSource, glasses: UIImage?, phone: UIImage?
) -> UIImage? {
    switch source {
    case .phone:
        return phone
    case .glasses:
        return glasses
    }
}
