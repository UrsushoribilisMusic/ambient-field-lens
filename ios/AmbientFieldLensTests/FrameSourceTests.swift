import UIKit
import XCTest

@testable import AmbientFieldLens

/// The submitted frame must always come from the rendered source.
/// Regression for the viewfinder showing the phone preview while Ask
/// silently preferred a retained glasses frame.
final class FrameSourceTests: XCTestCase {
    private func image() -> UIImage {
        UIGraphicsBeginImageContextWithOptions(CGSize(width: 8, height: 8), true, 1.0)
        defer { UIGraphicsEndImageContext() }
        return UIGraphicsGetImageFromCurrentImageContext() ?? UIImage()
    }

    func testPhoneSourceUsesPhoneFrameOnly() {
        let phone = image()
        let glasses = image()
        XCTAssertTrue(
            resolveFrame(source: .phone, glasses: glasses, phone: phone) === phone)
        XCTAssertNil(resolveFrame(source: .phone, glasses: glasses, phone: nil))
    }

    func testGlassesSourceUsesGlassesFrameOnly() {
        let phone = image()
        let glasses = image()
        XCTAssertTrue(
            resolveFrame(source: .glasses, glasses: glasses, phone: phone) === glasses)
        XCTAssertNil(resolveFrame(source: .glasses, glasses: nil, phone: phone))
    }

    func testNoFrameFromEitherSourceIsNil() {
        XCTAssertNil(resolveFrame(source: .phone, glasses: nil, phone: nil))
        XCTAssertNil(resolveFrame(source: .glasses, glasses: nil, phone: nil))
    }
}
