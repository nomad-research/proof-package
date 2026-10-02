# Price-free effect space: coverage scan (2026-09-30)

Rob: don't use price at all. The evidence must come from documents: exposures (what a filing states), outcomes (a documented decision or event) and effects (what later filings report). Prices measure how the market priced an effect, not whether it occurs.
First step: can the rate-side names' FY2024 10-Ks supply documented rate sensitivities? Stored in `filings/` (JPM, BAC, WFC, C, DHI, O, AMT, NEE).

Quick scan with a narrow pattern (a 100 bp or 1% move stated against net interest income, interest expense or earnings):
- **C (Citi):** discloses it in the main text ("100 basis point (bps) shocks ... net interest income sensitivity", line 2956).
- **JPM, BAC, WFC:** no hit in the main document. WFC's main 10-K is short (its annual report is an incorporated exhibit); JPM and BAC place earnings-at-risk tables in sections this pattern did not match. To be read properly by an extraction pass, not concluded from this scan.
- **DHI, O, AMT:** no hit. **NEE:** one unrelated hit. Their rate sensitivity, if stated, is worded differently or in other sections.
This scan says only that the hedge side (homebuilder, REITs, utility) does not state a per-100 bp sensitivity in an easy-to-find place; it does not say they don't disclose one. An extraction pass with verified quotes, as done for the oil filings, is the next step.
