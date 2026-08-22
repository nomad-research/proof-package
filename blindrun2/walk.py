"""The chronological walk. Every candidate, the criterion it failed, and why.

Order is strict: (filing date, accession number), the tie-break fixed cold in
screen_log.md before the walk began. Criteria are applied in NUMERICAL order and
the FIRST failure is recorded, per criteria.md, so every rejection has one
unambiguous cause and the log is reproducible by anyone re-walking the pool.

Class dispositions are permitted only where verified on actual filings. Every
class rule below names the candidates on which it was verified, and each of
those was opened through firewall/edgar.py and read. A class rejection that has
not been instance-verified is not permitted, and the classifier may only route a
candidate to a disposition already verified -- never create one.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from openitem import POOL, text_of  # noqa: E402
from classify_301 import FETCHED  # noqa: E402

HERE = Path(__file__).resolve().parent

# ---------------------------------------------------------------- class rules

CLASS_2_05 = ("Q1", """Item 2.05 reports COSTS associated with exit or disposal
activities -- workforce reductions, facility closures, restructuring charges. It
is an operational and accounting event. No document removes discretion from any
named actor to transact in an instrument, so there is no forced flow of any
size. Verified on candidates 2 (Manhattan Associates, 6% headcount reduction),
14 (Gitlab, 14% workforce, exit of 22 countries) and 24 (Fulcrum Therapeutics,
85% workforce reduction).""")

CLASS_N8F = ("Q1", """Form N-8F is an application to DEREGISTER an investment
company that has ALREADY wound up. It reports a completed state of affairs and
removes discretion from nobody. Verified on candidate 22 (Weitz Funds - Nebraska
Tax Free Income Fund), which answers "Has the fund distributed all of its assets
to the fund's shareholders? Yes" and dates the distributions 2026-03-27 -- three
months before the filing, before D, and before the operator's training cutoff --
and on candidate 51 (Value Line Core Bond Fund), same answer. The forcing, if
any existed, is over before the document exists. This is the fund-world analogue
of the 13F that ended blind run 1: it reports what happened, not that anything
must happen.""")

C301_A = ("Q2", """Item 3.01 subtype A -- MERGER-COMPLETION DELISTING. Q1 passes:
the merger agreement genuinely removes discretion, each share having "ceased to
have any rights ... except the right to receive" the consideration. But Q2 asks
whether the rule specifies what and when BUT NOT AT WHAT PRICE, and a merger
agreement specifies the price exactly -- the Mixed, Cash or Stock Consideration
is fixed in the agreement, published months in advance. The forced holder is not
price-insensitive; they receive a contractually fixed amount. Verified on
candidates 1 (Thermon/CECO), 4 (Enviri), 5 (Flushing Financial) and 94
(Clearwater Analytics).""")

C301_B = ("Q1", """Item 3.01 subtype B -- DEFICIENCY NOTICE WITH A CURE PERIOD.
The registrant reports receiving notice that it is out of compliance and has
time to regain it. Nothing is compelled: this is the "condition" pattern named
in the quarantine standard, a state of the world that may or may not obtain.
Verified on candidates 3 (Gencor, late 10-Q, six-month cure period) and 11 (HCW
Biologics, minimum bid price, extension to 2026-07-29).""")

C301_C = ("Q7", """Item 3.01 subtype C -- INVOLUNTARY DELISTING DETERMINATION,
usually consequent on a bankruptcy filing. Here forced selling is real: index
funds and mandate-constrained holders must exit a delisted security. But the
rules that compel them -- index methodologies and eligibility mandates -- are
PUBLISHED IN ADVANCE, so the set is handed to the operator and the event tests
transmission rather than enumeration. That is precisely what Q7 excludes, and
spec section 3 says so in terms: "This is why index reconstitution does not
qualify." Verified on candidates 74 (Sleep Number, Nasdaq "determined to delist"
under Rules 5101/5110(b)/IM-5101-1 following Chapter 11) and 160 (Actelis
Networks, Form 25-NSE after a trading suspension dated 2026-04-10).""")

# ------------------------------------------------- individual dispositions

INDIVIDUAL: dict[int, tuple[str, str]] = {
    9: ("Q1", 'EchoStar "has ELECTED not to make approximately $183 million in '
               'cash interest payments". A voluntary election, and the 8-K adds '
               'that "we have a 30-day grace period to make the Interest Payments '
               'before such non-payment constitutes an Event of Default". Nothing '
               'is compelled and nothing has yet occurred -- both the "condition" '
               'pattern and outright discretion.'),
    15: ("Q2", 'Conditional notice of redemption of the 8.125% senior secured notes '
               'due 2028. The rule names the price: "The redemption price ... shall '
               'be equal to 102.031% of the principal amount of redeemed Existing '
               'Notes plus accrued and unpaid interest." Price specified, so the '
               'forced holder is not price-insensitive.'),
    17: ("Q1", 'Chapter 11. The acceleration is asserted -- "principal and interest '
               '... shall be immediately due and payable" -- but the same paragraph '
               'neutralises it: "Any efforts to enforce such payment obligations '
               'under the Debt Instruments are AUTOMATICALLY STAYED as a result of '
               'the Chapter 11 Cases." No named actor is required to transact.'),
    18: ("Q3", 'The strongest candidate in the pool and the only one to reach Q3. '
               'Q1 passes: a Notice of Exclusive Control was delivered to the '
               'custodian under section 3 of the Account Control Agreement, which '
               'was "previously filed as exhibits to the Company\'s Current Report '
               'on Form 8-K filed on July 22, 2025" and is therefore retrievable. '
               'Q2 passes: no price is named. Q3 fails, and by about five orders of '
               'magnitude. The forced supply set IS identified -- "approximately '
               '22.23 Bitcoin, approximately 12,610 Solana ... approximately $2.8 '
               'million" -- but 22.23 BTC and 12,610 SOL against the daily volume '
               'of Bitcoin and Solana is on the order of 1e-5 days of ADV, against '
               'a floor of 0.8 days. Q4 would fail too: BTC and SOL are the '
               'opposite of thinly covered.'),
    27: ("Q1", 'The lender asserted Events of Default and raised the rate to the '
               'Default Rate, but the filing states plainly: "As of the date of '
               'this Form 8-K, the Lender HAS NOT ACCELERATED the obligations of '
               'the Loan Parties." Rights were reserved, not exercised.'),
    37: ("Q1", 'Chapter 11 filing "made in an abundance of caution" by the guarantor '
               'of four defaulted mortgage loans. The automatic stay applies, so no '
               'actor is required to transact. The underlying collateral is real '
               'property in any event, which has no ADV against which Q3 could be '
               'measured.'),
    39: ("Q1", 'Chapter 11. Indebtedness "has become immediately due and payable", '
               'but enforcement is stayed by the filing. Same disposition as 17.'),
    50: ("Q1", 'Chapter 11 plus debtor-in-possession financing of up to ~$260m from '
               'the prepetition lenders. Obligations accelerated, enforcement '
               'stayed, and the DIP amendment refinances rather than forces a sale.'),
    71: ("Q2", 'Merger closing. Consideration fixed by the merger agreement, same '
               'disposition as 3.01 subtype A.'),
    83: ("Q7", 'Plan of reorganization confirmed. The allocation of reorganized '
               'common equity and the 2029 Secured Exit Notes / New 2027 Senior '
               'Secured Notes is set out in the plan itself, published in advance '
               'of the effective date. The destination set is handed to the '
               'operator.'),
    86: ("Q2", 'Chapter 11 with stalking-horse asset purchase agreements. A stalking '
               'horse names both the purchaser and the price, so the rule specifies '
               'what, when AND at what price.'),
    93: ("Q2", 'Redemption of senior subordinated notes funded by a completed '
               'registered direct offering. A redemption is executed at the '
               'contractual redemption price. Same disposition as 15.'),
    94: ("Q2", 'Merger consummated; consideration fixed by the merger agreement.'),
    96: ("Q3", 'Genuine forcing -- a notice of acceleration and demand followed by a '
               '"notice of foreclosure sale ... pertaining to the Company\'s rights, '
               'title and interest in certain oil and gas leases". Q1 and Q2 pass. '
               'Q3 fails: the forced supply set is oil and gas leases, which are not '
               'traded instruments and have no ADV, so the 0.8-day floor cannot be '
               'met or even evaluated.'),
    102: ("Q3", 'The holder asserted an Event of Default on an "8% original issue '
                'discount secured promissory note in the aggregate principal amount '
                'of $271,739.13". Even taken at face value the sum is de minimis, '
                'and no securities supply set is identified.'),
    111: ("Q3", 'Plan of complete liquidation and dissolution, with voluntary '
                'delisting. The forced supply set is real property held by a real '
                'estate company; no ADV exists against which the floor can be '
                'measured. The delisting is also explicitly voluntary and '
                'pre-announced.'),
    129: ("Q1", 'A New Lender Joinder Agreement adding Regions Bank to the credit '
                'facility. Item 2.04 covers events that accelerate OR INCREASE an '
                'obligation; this is an increase in borrowing capacity. Nothing is '
                'compelled to be sold.'),
    141: ("Q1", 'Withdrawal of a STAR Market IPO application gives rise to a '
                'redemption right for eleven private equity funds -- and the filing '
                'states twice that it is optional: "each fund has THE RIGHT, BUT NOT '
                'THE OBLIGATION, to require the Company or Tongmei to redeem its '
                'investment, and the Company or Tongmei has THE RIGHT, BUT NOT THE '
                'OBLIGATION, to redeem". Discretion is retained on both sides. Q2 '
                'would fail too: the price is "equal to the original amount '
                'invested".'),
    161: ("Q7", 'Conversion of the Note into the issuer\'s own equity. The '
                'destination instrument is named in the converting instrument '
                'itself, so the event tests transmission rather than enumeration -- '
                'the same disposition the previous session reached for mandatory '
                'conversion and mandatory exchange.'),
    169: ("Q1", 'Maturity default on a non-recourse mortgage on a single property. '
                'The company "remains current on the monthly interest payments" and '
                '"ELECTED NOT TO INVEST additional capital in the asset that would '
                'have been required to refinance the mortgage". A choice, not a '
                'compulsion, and non-recourse means the lender\'s remedy is the '
                'building.'),
    175: ("Q2", 'Chapter 11 asset sale under an Asset Purchase Agreement with a '
                'named purchaser, approved by the Bankruptcy Court. Purchaser and '
                'price are both specified.'),

    # --- the nine the classifier refused to place, read individually ---
    7: ("Q1", 'Governance deficiency: the audit committee lacked two independent '
              'members under NYSE Listed Company Manual section 303A.07(a), with a '
              'cure date of 2026-06-05 and a "below compliance" tape indicator as '
              'the consequence. A cure period and a flag, not a compelled '
              'transaction. Subtype B in substance.'),
    13: ("Q1", 'VOLUNTARY listing transfer: LendingClub "acting pursuant to '
               'authorization from its Board of Directors, notified the NYSE of its '
               'intention to VOLUNTARILY withdraw the listing ... and transfer the '
               'listing to Nasdaq". The security remains listed throughout and no '
               'rule removes discretion from anyone. To the extent an '
               'exchange-specific index forces a residue of flow, those rules are '
               'published in advance and Q7 would dispose of it.'),
    19: ("Q1", 'VOLUNTARY listing transfer, NYSE to Nasdaq, common stock plus four '
               'series of depositary shares. Same disposition as 13.'),
    61: ("Q1", 'The opposite of a forcing event: Laser Photonics received a LETTER '
               'OF COMPLIANCE confirming the earlier deficiency "was now closed". '
               'Nothing is compelled because nothing is wrong.'),
    118: ("Q7", 'NYSE "determined to (a) commence proceedings to delist the '
                'Company\'s Public Warrants ... and (b) immediately suspend trading '
                '... due to abnormally low trading price levels pursuant to Section '
                '802.01D". A genuine involuntary delisting determination, so subtype '
                'C: any holder actually compelled to exit is compelled by mandate or '
                'index-eligibility rules published in advance. Common stock is '
                'explicitly unaffected.'),
    119: ("Q3", 'The most structurally interesting candidate in the pool and the '
                'only automatic, contractual dissolution. Q1 passes cleanly: the '
                'net profits interest "terminated on June 30, 2026 ... in accordance '
                'with the terms of the Conveyance of Net Profits Interest ... because '
                'the minimum amount of production (14.4 million barrels of oil '
                'equivalent) ... has been produced and sold", and "the Trust '
                'dissolved as of the Termination Date". Discretion is removed by a '
                'public trust instrument, automatically, on a quantitative trigger. '
                'Q2 passes: no price is named anywhere. Q3 fails, and it fails at '
                'zero. The wind-up is a CASH DISTRIBUTION followed by cancellation '
                '-- "the final quarterly cash distribution on July 24, 2026 to the '
                'Trust unitholders of record on July 15, 2026", then "the '
                'cancellation of the Trust Units". No instrument is sold into any '
                'market by anyone, so forced flow is 0.0 days of ADV against a floor '
                'of 0.8. A forced sale with no sale.'),
    164: ("Q1", 'VOLUNTARY listing transfer, Nasdaq to NYSE and NYSE Texas, common '
                'stock and two note series. Same disposition as 13.'),
    168: ("Q1", 'VOLUNTARY listing transfer, NYSE to Nasdaq; the stock "has been '
                'approved for listing on Nasdaq, where it will continue to trade '
                'under its current ticker symbol". Same disposition as 13.'),
    170: ("Q1", 'SemiLEDs "believes that it has REGAINED COMPLIANCE with the '
                'stockholders\' equity requirement" after reporting $3.1m against a '
                '$2.5m minimum. Same disposition as 61.'),
}

# ------------------------------------------------------------- 3.01 subtypes

C_MARK = [r"determined to delist", r"form\s*25-nse", r"staff determination",
          r"suspended from trading", r"delisting determination"]
A_MARK = [r"consummation of the (?:merger|business combination)",
          r"completion of the (?:merger|acquisition)", r"closing of the mergers?",
          r"certificates? of merger", r"in connection with the (?:merger|acquisition|closing)",
          r"notification of removal from listing", r"redomiciliation merger",
          r"business combination", r"form\s*25\b"]
B_MARK = [r"regain compliance", r"compliance period", r"not in compliance",
          r"minimum bid price", r"cure period", r"listing qualifications",
          r"hearings panel", r"continued listing standard"]


def item_seg(r: dict, item: str) -> str:
    doc = r["doc_id"].split(":", 1)[1] if ":" in r["doc_id"] else ""
    p = FETCHED / f"{r['accession']}_{doc.replace('/', '_')}"
    if not p.exists():
        return ""
    t = text_of(p)
    m = re.search(item, t, re.I)
    return (t[m.start(): m.start() + 4000] if m else t[:4000]).lower()


def disposition(i: int, r: dict) -> tuple[str, str, str]:
    """Return (criterion_failed, class_label, reason)."""
    if i in INDIVIDUAL:
        c, why = INDIVIDUAL[i]
        return c, "individual", why
    if r["matched"] == "form:N-8F":
        return CLASS_N8F[0], "N-8F", CLASS_N8F[1]
    if r["matched"] == "2.05":
        return CLASS_2_05[0], "item 2.05", CLASS_2_05[1]
    seg = item_seg(r, r"item\s*3\.01")
    if any(re.search(p, seg) for p in C_MARK):
        return C301_C[0], "3.01-C involuntary delisting", C301_C[1]
    if any(re.search(p, seg) for p in A_MARK):
        return C301_A[0], "3.01-A merger completion", C301_A[1]
    if any(re.search(p, seg) for p in B_MARK):
        return C301_B[0], "3.01-B deficiency notice", C301_B[1]
    return "UNRESOLVED", "3.01-? needs reading", "no verified subtype matched"


def main() -> None:
    rows, counts, classes = [], {}, {}
    for i, r in enumerate(POOL, 1):
        c, cls, why = disposition(i, r)
        counts[c] = counts.get(c, 0) + 1
        classes[cls] = classes.get(cls, 0) + 1
        rows.append({"idx": i, "filed": r["filed"], "entity": r["entity"],
                     "accession": r["accession"], "items": r["items"],
                     "matched": r["matched"], "failed": c, "class": cls,
                     "reason": " ".join(why.split())})
    (HERE / "walk_result.json").write_text(json.dumps(rows, indent=1))
    print(f"candidates walked: {len(rows)}\n")
    print("first failing criterion:")
    for c in sorted(counts, key=lambda k: -counts[k]):
        print(f"  {c:<12} {counts[c]:>4}")
    print("\nby disposition class:")
    for c in sorted(classes, key=lambda k: -classes[k]):
        print(f"  {c:<32} {classes[c]:>4}")
    qual = [r for r in rows if r["failed"] in ("PASS", "UNRESOLVED")]
    print(f"\nqualifiers: {len([r for r in rows if r['failed'] == 'PASS'])}")
    print(f"unresolved: {len([r for r in rows if r['failed'] == 'UNRESOLVED'])}")
    for r in qual:
        print(f"  {r['idx']:>4}. {r['filed']} {r['entity'][:46]} [{r['failed']}]")


if __name__ == "__main__":
    main()
