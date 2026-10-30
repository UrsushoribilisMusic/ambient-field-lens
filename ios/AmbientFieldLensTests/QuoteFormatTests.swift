import SwiftUI
import XCTest

@testable import AmbientFieldLens

/// Quote formatting: markdown renders, literal backslashes survive.
final class QuoteFormatTests: XCTestCase {
    func testBoldAndHeadingRenderWithoutMarkers() {
        // Numbering runs (##+) drop everywhere; a lone "#" keeps its
        // heading. Code ticks are consumed by the box pass.
        let out = AssistViewModel.formattedQuote(
            from: "# Calibration Topic ## 1. **Tool**: `run.py`"
        )
        let plain = String(out.characters)
        XCTAssertFalse(plain.hasPrefix("#"))
        XCTAssertFalse(plain.contains("##"))
        XCTAssertFalse(plain.contains("**"))
        XCTAssertFalse(plain.contains("`"))
        XCTAssertTrue(plain.contains("Calibration Topic"))
        XCTAssertTrue(plain.contains("Tool"))
    }

    func testInlineCodeSpanIsBoxed() {
        var out = AssistViewModel.formattedQuote(
            from: "Run `hunit_write.py` now"
        )
        XCTAssertFalse(String(out.characters).contains("`"))
        var boxed = false
        for run in out.runs {
            let text = String(out.characters[run.range])
            if text.contains("hunit_write.py") {
                boxed = run.attributes.backgroundColor != nil
            }
        }
        XCTAssertTrue(boxed)
    }

    func testFencedBlockIsBoxed() {
        var out = AssistViewModel.formattedQuote(
            from: "Try:\n```\nrun x.py\n```\n"
        )
        var boxed = false
        for run in out.runs {
            if String(out.characters[run.range]).contains("run x.py") {
                boxed = run.attributes.backgroundColor != nil
            }
        }
        XCTAssertTrue(boxed)
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
