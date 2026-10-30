import XCTest

@testable import AmbientFieldLens

/// Quote formatting: markdown renders, literal backslashes survive.
final class QuoteFormatTests: XCTestCase {
    func testBoldAndHeadingRenderWithoutMarkers() {
        // Mirrors the real Calibration excerpt: the leading "# " is a
        // heading marker and renders away, while the mid-line "## 1."
        // numbering is literal text and stays (faithful to the source).
        let out = AssistViewModel.formattedQuote(
            from: "# Calibration Topic ## 1. **Tool**: `run.py`"
        )
        let plain = String(out.characters)
        XCTAssertFalse(plain.hasPrefix("#"))
        XCTAssertFalse(plain.contains("**"))
        XCTAssertFalse(plain.contains("`"))
        XCTAssertTrue(plain.contains("Calibration Topic ## 1."))
        XCTAssertTrue(plain.contains("Tool"))
    }

    func testWindowsPathBackslashesSurvive() {
        let out = AssistViewModel.formattedQuote(
            from: "run skills\\hunit\\hunit_write.py \"Hello\""
        )
        XCTAssertEqual(
            String(out.characters),
            "run skills\\hunit\\hunit_write.py \"Hello\""
        )
    }

    func testPlainTextPassesThrough() {
        let text = "The lock file keeps one job at a time."
        XCTAssertEqual(
            String(
                AssistViewModel.formattedQuote(from: text).characters
            ),
            text
        )
    }
}
