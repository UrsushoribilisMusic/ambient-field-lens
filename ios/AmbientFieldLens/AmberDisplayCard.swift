import MWDATDisplay

/// Amber-only glasses card. Quotation of the refusal detail, never an
/// instruction and never a pass. One root FlexBox per send; each send
/// replaces the previous content on the glasses.
enum AmberDisplayCard {
    static func make(detail: String, query: String) -> FlexBox {
        let short = String(detail.prefix(140))
        return FlexBox(direction: .column, spacing: 10) {
            MWDATDisplay.Text("Field Lens — verify", style: .heading)
            MWDATDisplay.Text(query, style: .meta, color: .secondary)
            MWDATDisplay.Text(short, style: .body)
            MWDATDisplay.Text(
                "Amber only — evidence on phone.",
                style: .meta,
                color: .secondary
            )
        }
        .padding(24)
        .background(.card)
    }
}
