from services.report_cache import split_report_sections


SAMPLE = """# Apple Inc. (AAPL)
### What you're actually looking at near $300

*Research note — 2026-09-15. Educational analysis, not financial advice.*

---

## The one-line version

Apple trades at a premium multiple against a contested earnings stream.

That's the tension. Everything below is the detail.

---

## 1. What you're paying

| | Now | Median | Gap |
|---|---|---|---|
| P/E | 36 | 27 | +33% |

Premium means growth is already priced in.

---

## 2. What the bulls are counting on

**Services.** High-margin compounding.

---

## 3. What the bears see

**Concentration risk.** One contract matters a lot.

---

## 4. What would have to be true

1. Growth holds.
2. Margins hold.

---

## 5. What to watch next

- Next earnings
- Segment growth

---

## 6. What this note does not do

It doesn't tell you to buy or sell. It won't, ever.

---

*Educational and informational purposes only. Not investment advice.*
"""


def test_split_report_sections() -> None:
    sections = split_report_sections(SAMPLE)
    assert "premium multiple" in sections["one_line"]
    assert "P/E" in sections["paying"]
    assert "Services" in sections["bulls"]
    assert "Concentration" in sections["bears"]
    assert "Growth holds" in sections["assumptions"]
    assert "Next earnings" in sections["watch"]
    assert "doesn't tell you to buy or sell" in sections["non_verdict"]
    assert "Educational and informational" in sections["disclaimer"]
