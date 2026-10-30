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

    func testWindowsPathCondensesWithoutMerging() {
        // Display condenses to the basename; the key check is that no
        // backslash is eaten as a markdown escape (which would merge
        // "skills\hunit" into "skillshunit").
        let out = AssistViewModel.formattedQuote(
            from: "run skills\\hunit\\hunit_write.py \"Hello\""
        )
        let plain = String(out.characters)
        XCTAssertTrue(plain.contains("hunit_write.py"))
        XCTAssertFalse(plain.contains("skillshunit"))
        XCTAssertFalse(plain.contains("\\"))
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

    func testPathsCondenseToBasenames() {
        XCTAssertEqual(
            AssistViewModel.condensedPaths(
                in: "run skills\\hunit\\hunit_write.py \"Hello\""
            ),
            "run hunit_write.py \"Hello\""
        )
        XCTAssertEqual(
            AssistViewModel.condensedPaths(
                in: "see atf-wiki/Topics/Calibration.md for details"
            ),
            "see Calibration.md for details"
        )
    }

    func testUrlsVersionsAndBareNamesUntouched() {
        let text =
            "see https://x.test/a/b.md, ratio 1.0/2.0, run hunit_write.py"
        XCTAssertEqual(AssistViewModel.condensedPaths(in: text), text)
    }

    func testCondensedQuoteStillRenders() {
        let out = AssistViewModel.formattedQuote(
            from: "Run `skills\\hunit\\hunit_write.py` **now**"
        )
        let plain = String(out.characters)
        XCTAssertTrue(plain.contains("hunit_write.py"))
        XCTAssertFalse(plain.contains("skills"))
        XCTAssertFalse(plain.contains("**"))
    }
}
