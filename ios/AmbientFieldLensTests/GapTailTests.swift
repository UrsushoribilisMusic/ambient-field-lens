import XCTest

@testable import AmbientFieldLens

/// The gap-report button arms only on the NOT COVERED prefix and posts
/// the machine tail verbatim. These pin the tail contract shared with
/// the backend (docs/live-assist-wiring.md).
final class GapTailTests: XCTestCase {
    private let chunk =
        "8135308218c2c50dfd8b0aec8c0a48b25782d42098b2af9d4aa03fb2d71ccbb6"
    private var detail: String {
        "NOT COVERED: No manual passage within the coverage threshold "
            + "(d=0.820>0.760; 8 covered max 0.741). Verify in the manual. "
            + "top=" + chunk
    }

    func testParsesChunkAndDistance() {
        let tail = AssistViewModel.gapTail(from: detail)
        XCTAssertNotNil(tail)
        XCTAssertEqual(tail?.chunkID, chunk)
        XCTAssertEqual(tail?.distance ?? -1, 0.820, accuracy: 0.0005)
    }

    func testRejectsOtherPrefixes() {
        XCTAssertNil(
            AssistViewModel.gapTail(
                from: "WORLD CHECK FAILED: No paper candidate. top=" + chunk
            )
        )
        XCTAssertNil(
            AssistViewModel.gapTail(
                from: "Live check (amber): paper candidates 1. top=" + chunk
            )
        )
    }

    func testRejectsMissingTail() {
        XCTAssertNil(
            AssistViewModel.gapTail(
                from: "NOT COVERED: No manual passage within the coverage threshold."
            )
        )
    }
}
