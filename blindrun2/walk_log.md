# Blind run 2 — the chronological walk

**175 candidates. 0 qualifiers.** Walked in strict order of `(filing date, accession number)`, the tie-break fixed cold in `screen_log.md` before the walk began. Criteria applied in **numerical order**, first failure recorded, per `criteria.md`.

Every candidate document was opened through `firewall/edgar.py`, which enforces the filing-date ceiling in code and logs each open with its date. **175 opened, 0 failures, 0 post-fire filings touched.**

## Summary — first failing criterion

| Criterion | Count | What it asks |
|---|---:|---|
| **Q1** | 99 | Citable forcing -- a specific, retrievable document removes discretion from a named actor |
| **Q2** | 34 | Price insensitivity -- does the rule specify what and when but NOT at what price? |
| **Q3** | 5 | Magnitude floor -- forced flow must exceed 0.8 days of ADV of the named set |
| **Q7** | 37 | Enumeration content -- the set must not be published in advance |
| | **175** | **and none reached Q4, Q5, Q6, Q8a or Q8b** |

No candidate survived as far as Q4. The screen never got to the criteria that blind run 1 died on.

## Class dispositions, each verified on named instances

### 3.01-B deficiency notice — 51 candidates — fails **Q1**

Item 3.01 subtype B -- DEFICIENCY NOTICE WITH A CURE PERIOD. The registrant reports receiving notice that it is out of compliance and has time to regain it. Nothing is compelled: this is the "condition" pattern named in the quarantine standard, a state of the world that may or may not obtain. Verified on candidates 3 (Gencor, late 10-Q, six-month cure period) and 11 (HCW Biologics, minimum bid price, extension to 2026-07-29).

### 3.01-C involuntary delisting — 34 candidates — fails **Q7**

Item 3.01 subtype C -- INVOLUNTARY DELISTING DETERMINATION, usually consequent on a bankruptcy filing. Here forced selling is real: index funds and mandate-constrained holders must exit a delisted security. But the rules that compel them -- index methodologies and eligibility mandates -- are PUBLISHED IN ADVANCE, so the set is handed to the operator and the event tests transmission rather than enumeration. That is precisely what Q7 excludes, and spec section 3 says so in terms: "This is why index reconstitution does not qualify." Verified on candidates 74 (Sleep Number, Nasdaq "determined to delist" under Rules 5101/5110(b)/IM-5101-1 following Chapter 11) and 160 (Actelis Networks, Form 25-NSE after a trading suspension dated 2026-04-10).

### 3.01-A merger completion — 28 candidates — fails **Q2**

Item 3.01 subtype A -- MERGER-COMPLETION DELISTING. Q1 passes: the merger agreement genuinely removes discretion, each share having "ceased to have any rights ... except the right to receive" the consideration. But Q2 asks whether the rule specifies what and when BUT NOT AT WHAT PRICE, and a merger agreement specifies the price exactly -- the Mixed, Cash or Stock Consideration is fixed in the agreement, published months in advance. The forced holder is not price-insensitive; they receive a contractually fixed amount. Verified on candidates 1 (Thermon/CECO), 4 (Enviri), 5 (Flushing Financial) and 94 (Clearwater Analytics).

### item 2.05 — 23 candidates — fails **Q1**

Item 2.05 reports COSTS associated with exit or disposal activities -- workforce reductions, facility closures, restructuring charges. It is an operational and accounting event. No document removes discretion from any named actor to transact in an instrument, so there is no forced flow of any size. Verified on candidates 2 (Manhattan Associates, 6% headcount reduction), 14 (Gitlab, 14% workforce, exit of 22 countries) and 24 (Fulcrum Therapeutics, 85% workforce reduction).

### N-8F — 9 candidates — fails **Q1**

Form N-8F is an application to DEREGISTER an investment company that has ALREADY wound up. It reports a completed state of affairs and removes discretion from nobody. Verified on candidate 22 (Weitz Funds - Nebraska Tax Free Income Fund), which answers "Has the fund distributed all of its assets to the fund's shareholders? Yes" and dates the distributions 2026-03-27 -- three months before the filing, before D, and before the operator's training cutoff -- and on candidate 51 (Value Line Core Bond Fund), same answer. The forcing, if any existed, is over before the document exists. This is the fund-world analogue of the 13F that ended blind run 1: it reports what happened, not that anything must happen.

## Full walk, all 175 in order

| # | Filed | Entity | Items | Failed | Disposition |
|---:|---|---|---|:---:|---|
| 1 | 2026-06-01 | Thermon Group Holdings, Inc.  (THR) | 1.02,2.01,3.01,3.03,5.01,5.02,7.01,9.01 | **Q2** | 3.01-A merger completion |
| 2 | 2026-06-01 | MANHATTAN ASSOCIATES INC  (MANH) | 2.05,7.01 | **Q1** | item 2.05 |
| 3 | 2026-06-01 | GENCOR INDUSTRIES INC  (GENC) | 3.01,7.01,9.01 | **Q1** | 3.01-B deficiency notice |
| 4 | 2026-06-01 | ENVIRI Corp  (NVRI) | 1.02,2.01,3.01,3.03,5.01,9.01 | **Q2** | 3.01-A merger completion |
| 5 | 2026-06-01 | FLUSHING FINANCIAL CORP  (FFIC) | 2.01,3.01,3.03,5.01,5.02,9.01 | **Q2** | 3.01-A merger completion |
| 6 | 2026-06-01 | Columbus Acquisition Corp/Cayman Islands  (C | 3.01 | **Q1** | 3.01-B deficiency notice |
| 7 | 2026-06-01 | Twenty One Capital, Inc.  (XXI) | 3.01 | **Q1** | individual |
| 8 | 2026-06-01 | iSpecimen Inc.  (ISPC) | 3.01 | **Q1** | 3.01-B deficiency notice |
| 9 | 2026-06-01 | EchoStar CORP  (SATS) | 2.04,9.01 | **Q1** | individual |
| 10 | 2026-06-01 | NUSATRIP Inc  (NUTR) | 3.01,9.01 | **Q1** | 3.01-B deficiency notice |
| 11 | 2026-06-01 | HCW Biologics Inc.  (HCWB) | 3.01 | **Q1** | 3.01-B deficiency notice |
| 12 | 2026-06-02 | Triller Group Inc.  (ILLR, ILLRW) | 3.01,9.01 | **Q1** | 3.01-B deficiency notice |
| 13 | 2026-06-02 | LendingClub Corp  (LC) | 3.01,7.01,9.01 | **Q1** | individual |
| 14 | 2026-06-02 | Gitlab Inc.  (GTLB) | 2.02,2.05,7.01,9.01 | **Q1** | item 2.05 |
| 15 | 2026-06-02 | Venture Global, Inc.  (VG) | 2.04,8.01,9.01 | **Q2** | individual |
| 16 | 2026-06-03 | ESTEE LAUDER COMPANIES INC  (EL) | 2.05,9.01 | **Q1** | item 2.05 |
| 17 | 2026-06-03 | Inotiv, Inc.  (NOTV) | 1.01,1.03,2.04,7.01,8.01,9.01 | **Q1** | individual |
| 18 | 2026-06-03 | DevvStream Corp.  (DEVS) | 1.01,2.04 | **Q3** | individual |
| 19 | 2026-06-03 | FIFTH THIRD BANCORP  (FITB, FITBI, FITBM, FI | 3.01,7.01,9.01 | **Q1** | individual |
| 20 | 2026-06-03 | FONAR CORP  (FONR) | 1.01,2.01,2.03,3.01,3.03,5.01,5.02,5.03,9.01 | **Q2** | 3.01-A merger completion |
| 21 | 2026-06-03 | REED'S, INC.  (REED) | 3.01,8.01,9.01 | **Q7** | 3.01-C involuntary delisting |
| 22 | 2026-06-03 | WEITZ FUNDS | form:N-8F | **Q1** | N-8F |
| 23 | 2026-06-03 | Cardlytics, Inc.  (CDLX) | 3.01,3.03 | **Q7** | 3.01-C involuntary delisting |
| 24 | 2026-06-04 | Fulcrum Therapeutics, Inc.  (FULC) | 2.05,8.01 | **Q1** | item 2.05 |
| 25 | 2026-06-04 | Abpro Holdings, Inc.  (ABPO, ABPWW) | 3.01 | **Q2** | 3.01-A merger completion |
| 26 | 2026-06-04 | VEEA INC.  (VEEA, VEEAW) | 3.01 | **Q1** | 3.01-B deficiency notice |
| 27 | 2026-06-04 | AMERICAN SHARED HOSPITAL SERVICES  (AMS) | 2.04 | **Q1** | individual |
| 28 | 2026-06-04 | Volato Group, Inc.  (SOAR, SOARW) | 3.01,8.01,9.01 | **Q1** | 3.01-B deficiency notice |
| 29 | 2026-06-04 | ChronoScale Corp  (CHRN) | 2.05 | **Q1** | item 2.05 |
| 30 | 2026-06-04 | SMITH MIDLAND CORP  (SMID) | 3.01,9.01 | **Q1** | 3.01-B deficiency notice |
| 31 | 2026-06-04 | Lamb Weston Holdings, Inc.  (LW) | 2.05 | **Q1** | item 2.05 |
| 32 | 2026-06-05 | Ribbon Acquisition Corp.  (RIBB, RIBBR, RIBB | 3.01 | **Q7** | 3.01-C involuntary delisting |
| 33 | 2026-06-05 | Arrive AI Inc.  (ARAI) | 3.01 | **Q1** | 3.01-B deficiency notice |
| 34 | 2026-06-05 | RESEARCH FRONTIERS INC  (REFR) | 3.01,9.01 | **Q1** | 3.01-B deficiency notice |
| 35 | 2026-06-05 | Driven Brands Holdings Inc.  (DRVN) | 3.01,7.01,9.01 | **Q1** | 3.01-B deficiency notice |
| 36 | 2026-06-08 | aTYR PHARMA INC  (ATYR) | 3.01 | **Q7** | 3.01-C involuntary delisting |
| 37 | 2026-06-08 | SILVER STAR PROPERTIES REIT, INC | 1.03,2.04,7.01,9.01 | **Q1** | individual |
| 38 | 2026-06-08 | Vivos Therapeutics, Inc.  (VVOS) | 1.01,2.03,3.01,3.02,7.01,9.01 | **Q1** | 3.01-B deficiency notice |
| 39 | 2026-06-08 | GoHealth, Inc.  (GOCO) | 1.03,2.04,5.02,7.01,9.01 | **Q1** | individual |
| 40 | 2026-06-09 | Jasper Therapeutics, Inc.  (JSPR, JSPRW) | 3.01 | **Q1** | 3.01-B deficiency notice |
| 41 | 2026-06-09 | Eureka Acquisition Corp  (EURK, EURKR, EURKU | 3.01 | **Q1** | 3.01-B deficiency notice |
| 42 | 2026-06-09 | Professional Diversity Network, Inc.  (IPDN) | 3.01 | **Q7** | 3.01-C involuntary delisting |
| 43 | 2026-06-10 | MASIMO CORP  (MASI) | 1.02,2.01,3.01,3.03,5.01,5.02,5.03,9.01 | **Q2** | 3.01-A merger completion |
| 44 | 2026-06-10 | BIO KEY INTERNATIONAL INC  (BKYI) | 3.01,7.01,9.01 | **Q1** | 3.01-B deficiency notice |
| 45 | 2026-06-10 | Veritone, Inc.  (VERI) | 2.05 | **Q1** | item 2.05 |
| 46 | 2026-06-10 | Legato Merger Corp. III  (LEGT, LEGT-UN, LEG | 1.01,1.02,2.01,3.01,3.03,5.01,5.02,5.06,7.01,9.01 | **Q2** | 3.01-A merger completion |
| 47 | 2026-06-11 | KalVista Pharmaceuticals, Inc.  (KALV) | 1.01,1.02,2.01,2.03,3.01,3.03,5.01,5.02,5.03,7.01,9.01 | **Q2** | 3.01-A merger completion |
| 48 | 2026-06-11 | GoHealth, Inc.  (GOCO) | 3.01 | **Q7** | 3.01-C involuntary delisting |
| 49 | 2026-06-11 | YHN Acquisition I Ltd  (YHNA, YHNAR, YHNAU) | 3.01 | **Q1** | 3.01-B deficiency notice |
| 50 | 2026-06-12 | Sleep Number Corp  (SNBR) | 1.01,1.03,2.04,7.01,9.01 | **Q1** | individual |
| 51 | 2026-06-12 | Value Line Core Bond Fund | form:N-8F | **Q1** | N-8F |
| 52 | 2026-06-12 | SOLIGENIX, INC.  (SNGX) | 3.01,5.02,8.01,9.01 | **Q7** | 3.01-C involuntary delisting |
| 53 | 2026-06-12 | Adagio Medical Holdings, Inc.  (ADGM) | 3.01 | **Q1** | 3.01-B deficiency notice |
| 54 | 2026-06-12 | BiomX Inc.  (PHGE) | 3.01,7.01,9.01 | **Q1** | 3.01-B deficiency notice |
| 55 | 2026-06-12 | CYABRA, INC.  (CYAB) | 3.01,9.01 | **Q7** | 3.01-C involuntary delisting |
| 56 | 2026-06-12 | La Rosa Holdings Corp.  (LRHC) | 3.01 | **Q7** | 3.01-C involuntary delisting |
| 57 | 2026-06-12 | BioCardia, Inc.  (BCDA) | 3.01 | **Q1** | 3.01-B deficiency notice |
| 58 | 2026-06-12 | Genprex, Inc.  (GNPX) | 3.01,8.01,9.01 | **Q7** | 3.01-C involuntary delisting |
| 59 | 2026-06-12 | OFA Group  (OFAL) | 3.01,8.01,9.01 | **Q7** | 3.01-C involuntary delisting |
| 60 | 2026-06-12 | Wellgistics Health, Inc.  (WGRX) | 3.01,8.01 | **Q1** | 3.01-B deficiency notice |
| 61 | 2026-06-12 | Laser Photonics Corp  (LASE) | 3.01,9.01 | **Q1** | individual |
| 62 | 2026-06-12 | MICROVISION, INC.  (MVIS) | 1.01,3.01,7.01,9.01 | **Q1** | 3.01-B deficiency notice |
| 63 | 2026-06-12 | Celularity Inc  (CELU, CELUW) | 3.01 | **Q7** | 3.01-C involuntary delisting |
| 64 | 2026-06-12 | Perfect Moment Ltd.  (PMNT) | 3.01,7.01,9.01 | **Q7** | 3.01-C involuntary delisting |
| 65 | 2026-06-12 | Corteva, Inc.  (CTVA) | 2.05,2.06 | **Q1** | item 2.05 |
| 66 | 2026-06-15 | Neumora Therapeutics, Inc.  (NMRA) | 1.01,2.03,2.05,7.01,8.01,9.01 | **Q1** | item 2.05 |
| 67 | 2026-06-15 | enGene Therapeutics Inc.  (ENGN, ENGNW) | 2.02,2.05,5.02,7.01,8.01,9.01 | **Q1** | item 2.05 |
| 68 | 2026-06-15 | Functional Brands Inc.  (MEHA) | 3.01,7.01,9.01 | **Q7** | 3.01-C involuntary delisting |
| 69 | 2026-06-15 | ESS Tech, Inc.  (GWH, GWH-WT) | 3.01,7.01,9.01 | **Q1** | 3.01-B deficiency notice |
| 70 | 2026-06-16 | MAXCYTE, INC.  (MXCT) | 3.01 | **Q1** | 3.01-B deficiency notice |
| 71 | 2026-06-16 | Assertio Holdings, Inc.  (ASRT) | 1.01,2.01,2.04,3.01,3.03,5.01,5.02,5.03,8.01,9.01 | **Q2** | individual |
| 72 | 2026-06-16 | Kennedy-Wilson Holdings, Inc.  (KW) | 1.01,1.02,2.01,3.01,3.03,5.01,5.02,5.03,7.01,9.01 | **Q2** | 3.01-A merger completion |
| 73 | 2026-06-16 | Robinhood Markets, Inc.  (HOOD) | 2.05 | **Q1** | item 2.05 |
| 74 | 2026-06-17 | Sleep Number Corp  (SNBR) | 3.01 | **Q7** | 3.01-C involuntary delisting |
| 75 | 2026-06-17 | GENCOR INDUSTRIES INC  (GENC) | 3.01 | **Q1** | 3.01-B deficiency notice |
| 76 | 2026-06-17 | Vestand Inc.  (VSTD) | 3.01,9.01 | **Q7** | 3.01-C involuntary delisting |
| 77 | 2026-06-18 | enGene Therapeutics Inc.  (ENGN, ENGNW) | 2.05,5.02 | **Q1** | item 2.05 |
| 78 | 2026-06-18 | DYADIC INTERNATIONAL INC  (DYAI) | 3.01 | **Q1** | 3.01-B deficiency notice |
| 79 | 2026-06-18 | Algorhythm Holdings, Inc.  (RIME) | 3.01 | **Q1** | 3.01-B deficiency notice |
| 80 | 2026-06-22 | SUMISHO AIR LEASE CORP | 2.05 | **Q1** | item 2.05 |
| 81 | 2026-06-22 | AAM Alternatives Trust | form:N-8F | **Q1** | N-8F |
| 82 | 2026-06-22 | Lucid Group, Inc.  (LCID) | 2.05,5.02,9.01 | **Q1** | item 2.05 |
| 83 | 2026-06-23 | OFFICE PROPERTIES INCOME TRUST  (OPIRQ, OPIT | 1.01,1.02,1.03,2.03,3.02,3.03,5.01,5.02,5.03,8.01,9.01 | **Q7** | individual |
| 84 | 2026-06-23 | DevvStream Corp.  (DEVS) | 3.01 | **Q7** | 3.01-C involuntary delisting |
| 85 | 2026-06-23 | Boundless Bio, Inc.  (BOLD) | 1.01,2.05,3.02,5.01,5.02,7.01,8.01,9.01 | **Q1** | item 2.05 |
| 86 | 2026-06-23 | SANGAMO THERAPEUTICS, INC  (SGMO) | 1.01,1.03,2.03,2.05 | **Q2** | individual |
| 87 | 2026-06-23 | TON Strategy Co  (TONX) | 3.01 | **Q1** | 3.01-B deficiency notice |
| 88 | 2026-06-24 | Centessa Pharmaceuticals plc  (CNTA) | 1.02,2.01,3.01,3.03,5.01,5.02,8.01,9.01 | **Q2** | 3.01-A merger completion |
| 89 | 2026-06-24 | Definitive Healthcare Corp.  (DH) | 3.01 | **Q1** | 3.01-B deficiency notice |
| 90 | 2026-06-24 | Aditxt, Inc.  (ADTX) | 3.01,9.01 | **Q7** | 3.01-C involuntary delisting |
| 91 | 2026-06-24 | SRX Global Inc.  (SRXH) | 3.01,5.07,9.01 | **Q1** | 3.01-B deficiency notice |
| 92 | 2026-06-24 | Elastic N.V.  (ESTC) | 2.05,5.02 | **Q1** | item 2.05 |
| 93 | 2026-06-25 | AMC ENTERTAINMENT HOLDINGS, INC.  (AMC) | 2.04,7.01,8.01,9.01 | **Q2** | individual |
| 94 | 2026-06-25 | Clearwater Analytics Holdings, Inc.  (CWAN) | 1.01,1.02,2.01,2.03,2.04,3.01,3.03,5.01,5.02,5.03,7.01,9.01 | **Q2** | individual |
| 95 | 2026-06-25 | HERON THERAPEUTICS, INC. /DE/  (HRTX) | 3.01,9.01 | **Q1** | 3.01-B deficiency notice |
| 96 | 2026-06-25 | Permex Petroleum Corp | 2.04,8.01,9.01 | **Q3** | individual |
| 97 | 2026-06-25 | Global Interactive Technologies, Inc.  (GITS | 3.01 | **Q1** | 3.01-B deficiency notice |
| 98 | 2026-06-26 | Destiny Alternative Fund LLC | form:N-8F | **Q1** | N-8F |
| 99 | 2026-06-26 | Destiny Alternative Fund (TEI) LLC | form:N-8F | **Q1** | N-8F |
| 100 | 2026-06-26 | Outlook Therapeutics, Inc.  (OTLK) | 3.01 | **Q1** | 3.01-B deficiency notice |
| 101 | 2026-06-26 | PROASSURANCE CORP  (PRA) | 1.02,2.01,3.01,3.03,5.01,5.02,5.03,9.01 | **Q2** | 3.01-A merger completion |
| 102 | 2026-06-26 | VSEE HEALTH, INC.  (VSEE, VSEEW) | 2.04 | **Q3** | individual |
| 103 | 2026-06-26 | UPEXI, INC.  (UPXI) | 3.01,8.01,9.01 | **Q1** | 3.01-B deficiency notice |
| 104 | 2026-06-26 | Matinas BioPharma Holdings, Inc.  (MTNB) | 3.01,8.01,9.01 | **Q1** | 3.01-B deficiency notice |
| 105 | 2026-06-29 | BIOCRYST PHARMACEUTICALS INC  (BCRX) | 2.05,7.01,9.01 | **Q1** | item 2.05 |
| 106 | 2026-06-30 | JANUS HENDERSON GROUP PLC  (JHG) | 1.01,1.02,2.01,2.03,3.01,3.03,5.01,5.02,5.03,8.01,9.01 | **Q2** | 3.01-A merger completion |
| 107 | 2026-06-30 | GULF RESOURCES, INC.  (GURE) | 3.01 | **Q1** | 3.01-B deficiency notice |
| 108 | 2026-06-30 | HCW Biologics Inc.  (HCWB) | 3.01,9.01 | **Q1** | 3.01-B deficiency notice |
| 109 | 2026-06-30 | SolarMax Technology, Inc.  (SMXT) | 3.01,9.01 | **Q1** | 3.01-B deficiency notice |
| 110 | 2026-07-01 | WHIRLPOOL CORP /DE/  (WHR, WHR-PA) | 2.05 | **Q1** | item 2.05 |
| 111 | 2026-07-01 | STRATUS PROPERTIES INC  (STRS) | 3.01,8.01,9.01 | **Q3** | individual |
| 112 | 2026-07-01 | SELECT MEDICAL HOLDINGS CORP  (SEM) | 1.01,2.01,2.03,3.01,3.03,5.01,5.02,5.03,7.01,9.01 | **Q2** | 3.01-A merger completion |
| 113 | 2026-07-01 | QXO Insulation, LLC  (BLD) | 1.01,1.02,2.01,2.03,3.01,3.03,5.01,5.02,5.03,8.01,9.01 | **Q2** | 3.01-A merger completion |
| 114 | 2026-07-01 | Sila Realty Trust, Inc.  (SILA) | 2.01,3.01,3.03,5.01,5.02,5.03,7.01,9.01 | **Q2** | 3.01-A merger completion |
| 115 | 2026-07-01 | Stellar Bancorp, Inc.  (STEL) | 2.01,3.01,3.03,5.01,5.02,5.03,8.01,9.01 | **Q2** | 3.01-A merger completion |
| 116 | 2026-07-01 | EXXON MOBIL CORP  (XOM) | 1.01,2.01,3.01,3.03,5.02,5.03,9.01 | **Q2** | 3.01-A merger completion |
| 117 | 2026-07-01 | INNSUITES HOSPITALITY TRUST  (IHT) | 3.01,9.01 | **Q1** | 3.01-B deficiency notice |
| 118 | 2026-07-01 | ESS Tech, Inc.  (GWH, GWH-WT) | 3.01 | **Q7** | individual |
| 119 | 2026-07-02 | MV Oil Trust  (MVO) | 2.02,3.01,9.01 | **Q3** | individual |
| 120 | 2026-07-02 | HeartBeam, Inc.  (BEAT, BEATW) | 3.01 | **Q1** | 3.01-B deficiency notice |
| 121 | 2026-07-02 | Linkhome Holdings Inc.  (LHAI) | 2.01,3.01,7.01,9.01 | **Q7** | 3.01-C involuntary delisting |
| 122 | 2026-07-02 | RenovoRx, Inc.  (RNXT) | 3.01 | **Q1** | 3.01-B deficiency notice |
| 123 | 2026-07-02 | Snail, Inc.  (SNAL) | 3.01,3.03,5.03,8.01,9.01 | **Q7** | 3.01-C involuntary delisting |
| 124 | 2026-07-02 | AI Financial Corp  (AIFC) | 3.01 | **Q7** | 3.01-C involuntary delisting |
| 125 | 2026-07-02 | CALLAN JMB INC.  (CJMB) | 3.01 | **Q1** | 3.01-B deficiency notice |
| 126 | 2026-07-02 | FingerMotion, Inc.  (FNGR) | 3.01,9.01 | **Q7** | 3.01-C involuntary delisting |
| 127 | 2026-07-02 | Boxlight Corp  (BOXL) | 3.01,9.01 | **Q1** | 3.01-B deficiency notice |
| 128 | 2026-07-06 | Cytosorbents Corp  (CTSO) | 3.01 | **Q7** | 3.01-C involuntary delisting |
| 129 | 2026-07-06 | Fortress Net Lease REIT | 1.01,2.04,9.01 | **Q1** | individual |
| 130 | 2026-07-06 | CISO Global, Inc.  (CISO) | 3.01 | **Q1** | 3.01-B deficiency notice |
| 131 | 2026-07-06 | Polar Power, Inc.  (POLA) | 3.01 | **Q1** | 3.01-B deficiency notice |
| 132 | 2026-07-06 | Coursera, Inc.  (COUR) | 2.05 | **Q1** | item 2.05 |
| 133 | 2026-07-07 | ESTEE LAUDER COMPANIES INC  (EL) | 2.05,9.01 | **Q1** | item 2.05 |
| 134 | 2026-07-07 | DevvStream Corp.  (DEVSF) | 3.01,9.01 | **Q2** | 3.01-A merger completion |
| 135 | 2026-07-07 | OLAPLEX HOLDINGS, INC.  (OLPX) | 1.02,2.01,3.01,3.03,5.01,5.02,5.03,8.01,9.01 | **Q2** | 3.01-A merger completion |
| 136 | 2026-07-08 | TRIDAN CORP | form:N-8F | **Q1** | N-8F |
| 137 | 2026-07-08 | Borealis Foods Inc.  (BRLS, BRLSW) | 3.01,9.01 | **Q7** | 3.01-C involuntary delisting |
| 138 | 2026-07-08 | Cantor Equity Partners II, Inc.  (CEPT) | 2.01,3.01,3.02,3.03,5.01,5.02,7.01,8.01 | **Q2** | 3.01-A merger completion |
| 139 | 2026-07-08 | Securitize Corp.  (SECZ) | 1.01,2.01,3.01,3.02,3.03,4.01,5.01,5.02,5.03,5.05,9.01 | **Q2** | 3.01-A merger completion |
| 140 | 2026-07-08 | Real Asset Acquisition Corp.  (RAAQ, RAAQU,  | 1.01,2.01,3.01,3.03,5.01,5.02,9.01 | **Q2** | 3.01-A merger completion |
| 141 | 2026-07-08 | AXT INC  (AXTI) | 2.04 | **Q1** | individual |
| 142 | 2026-07-09 | Prairie Operating Co.  (PROP) | 3.01 | **Q7** | 3.01-C involuntary delisting |
| 143 | 2026-07-09 | TruBridge, Inc.  (TBRG) | 1.02,2.01,3.01,3.03,5.01,5.02,5.03,7.01,9.01 | **Q2** | 3.01-A merger completion |
| 144 | 2026-07-09 | Popular Income Plus Fund, Inc. | form:N-8F | **Q1** | N-8F |
| 145 | 2026-07-09 | HYDROFARM HOLDINGS GROUP, INC.  (HYFM) | 3.01 | **Q1** | 3.01-B deficiency notice |
| 146 | 2026-07-09 | Bayview Acquisition Corp  (BAYA, BAYAR, BAYA | 3.01 | **Q7** | 3.01-C involuntary delisting |
| 147 | 2026-07-09 | Onfolio Holdings, Inc  (ONFO, ONFOP, ONFOW) | 3.01 | **Q1** | 3.01-B deficiency notice |
| 148 | 2026-07-09 | SPLASH BEVERAGE GROUP, INC.  (SBEV) | 3.01,7.01,9.01 | **Q1** | 3.01-B deficiency notice |
| 149 | 2026-07-10 | LM FUNDING AMERICA, INC.  (LMFA) | 3.01,3.03,5.03,7.01,8.01,9.01 | **Q7** | 3.01-C involuntary delisting |
| 150 | 2026-07-10 | MERCER INTERNATIONAL INC.  (MERC) | 3.01,9.01 | **Q1** | 3.01-B deficiency notice |
| 151 | 2026-07-10 | Lakeside Holding Ltd  (LSH) | 3.01 | **Q7** | 3.01-C involuntary delisting |
| 152 | 2026-07-10 | GeoVax Labs, Inc.  (GOVX) | 3.01 | **Q7** | 3.01-C involuntary delisting |
| 153 | 2026-07-10 | SOBR Safe, Inc.  (SOBR) | 2.05,9.01 | **Q1** | item 2.05 |
| 154 | 2026-07-10 | ENvue Medical, Inc.  (FEED) | 3.01,9.01 | **Q7** | 3.01-C involuntary delisting |
| 155 | 2026-07-10 | TCG Strategic Income Fund | form:N-8F | **Q1** | N-8F |
| 156 | 2026-07-13 | MFS SPECIAL VALUE TRUST | form:N-8F | **Q1** | N-8F |
| 157 | 2026-07-13 | BNB PLUS CORP.  (BNBX) | 3.01,7.01,9.01 | **Q7** | 3.01-C involuntary delisting |
| 158 | 2026-07-13 | Esperion Therapeutics, Inc.  (ESPR) | 1.01,1.02,2.01,2.03,3.01,3.03,5.01,5.02,5.03,9.01 | **Q2** | 3.01-A merger completion |
| 159 | 2026-07-13 | Pluri Inc.  (PLUR) | 3.01 | **Q7** | 3.01-C involuntary delisting |
| 160 | 2026-07-13 | ACTELIS NETWORKS INC  (ASNS) | 3.01 | **Q7** | 3.01-C involuntary delisting |
| 161 | 2026-07-13 | DATA I/O CORP  (DAIO) | 1.02,2.04,3.02,5.02,5.07,9.01 | **Q7** | individual |
| 162 | 2026-07-14 | NextCure, Inc.  (NXTC) | 1.01,2.05,5.01,5.02,7.01,8.01,9.01 | **Q1** | item 2.05 |
| 163 | 2026-07-14 | XOMA Royalty Corp  (XOMA, XOMAO, XOMAP) | 1.02,2.01,3.01,3.03,5.01,5.02,5.07,8.01,9.01 | **Q2** | 3.01-A merger completion |
| 164 | 2026-07-14 | Trinity Capital Inc.  (TRIN, TRINI, TRINZ) | 3.01,7.01,9.01 | **Q1** | individual |
| 165 | 2026-07-14 | Emerald Holding, Inc.  (EEX) | 1.02,2.01,3.01,3.03,5.01,5.02,5.03,8.01,9.01 | **Q2** | 3.01-A merger completion |
| 166 | 2026-07-14 | Whitestone REIT  (WSR) | 1.02,2.01,3.01,3.03,5.01,5.02,5.03,8.01,9.01 | **Q2** | 3.01-A merger completion |
| 167 | 2026-07-14 | SBC Medical Group Holdings Inc  (SBC, SBCWW) | 3.01,3.03,5.03,5.07,9.01 | **Q1** | 3.01-B deficiency notice |
| 168 | 2026-07-14 | D-Wave Quantum Inc.  (QBTS) | 3.01,7.01,9.01 | **Q1** | individual |
| 169 | 2026-07-15 | Creative Media & Community Trust Corp  (CMCT | 2.04 | **Q1** | individual |
| 170 | 2026-07-15 | SemiLEDs Corp  (LEDS) | 3.01 | **Q1** | individual |
| 171 | 2026-07-15 | Nuvalent, Inc.  (NUVL) | 2.01,3.01,3.03,5.01,5.02,5.03,9.01 | **Q2** | 3.01-A merger completion |
| 172 | 2026-07-15 | Triller Group Inc.  (ILLR, ILLRW) | 3.01 | **Q1** | 3.01-B deficiency notice |
| 173 | 2026-07-15 | SPAR Group, Inc.  (SGRP) | 3.01,5.07 | **Q7** | 3.01-C involuntary delisting |
| 174 | 2026-07-15 | Sprout Social, Inc.  (SPT) | 2.02,2.05,7.01,9.01 | **Q1** | item 2.05 |
| 175 | 2026-07-15 | LIPELLA PHARMACEUTICALS INC.  (LIPO) | 1.03,9.01 | **Q2** | individual |

## The 30 assessed individually

Every Item 2.04 and Item 1.03 candidate, plus the nine the classifier refused to place and referred for individual reading. Quotations are verbatim from the fetched filing.

**7. 2026-06-01 — Twenty One Capital, Inc.  (XXI)** — fails **Q1**

Governance deficiency: the audit committee lacked two independent members under NYSE Listed Company Manual section 303A.07(a), with a cure date of 2026-06-05 and a "below compliance" tape indicator as the consequence. A cure period and a flag, not a compelled transaction. Subtype B in substance.

**9. 2026-06-01 — EchoStar CORP  (SATS)** — fails **Q1**

EchoStar "has ELECTED not to make approximately $183 million in cash interest payments". A voluntary election, and the 8-K adds that "we have a 30-day grace period to make the Interest Payments before such non-payment constitutes an Event of Default". Nothing is compelled and nothing has yet occurred -- both the "condition" pattern and outright discretion.

**13. 2026-06-02 — LendingClub Corp  (LC)** — fails **Q1**

VOLUNTARY listing transfer: LendingClub "acting pursuant to authorization from its Board of Directors, notified the NYSE of its intention to VOLUNTARILY withdraw the listing ... and transfer the listing to Nasdaq". The security remains listed throughout and no rule removes discretion from anyone. To the extent an exchange-specific index forces a residue of flow, those rules are published in advance and Q7 would dispose of it.

**15. 2026-06-02 — Venture Global, Inc.  (VG)** — fails **Q2**

Conditional notice of redemption of the 8.125% senior secured notes due 2028. The rule names the price: "The redemption price ... shall be equal to 102.031% of the principal amount of redeemed Existing Notes plus accrued and unpaid interest." Price specified, so the forced holder is not price-insensitive.

**17. 2026-06-03 — Inotiv, Inc.  (NOTV)** — fails **Q1**

Chapter 11. The acceleration is asserted -- "principal and interest ... shall be immediately due and payable" -- but the same paragraph neutralises it: "Any efforts to enforce such payment obligations under the Debt Instruments are AUTOMATICALLY STAYED as a result of the Chapter 11 Cases." No named actor is required to transact.

**18. 2026-06-03 — DevvStream Corp.  (DEVS)** — fails **Q3**

The strongest candidate in the pool and the only one to reach Q3. Q1 passes: a Notice of Exclusive Control was delivered to the custodian under section 3 of the Account Control Agreement, which was "previously filed as exhibits to the Company's Current Report on Form 8-K filed on July 22, 2025" and is therefore retrievable. Q2 passes: no price is named. Q3 fails, and by about five orders of magnitude. The forced supply set IS identified -- "approximately 22.23 Bitcoin, approximately 12,610 Solana ... approximately $2.8 million" -- but 22.23 BTC and 12,610 SOL against the daily volume of Bitcoin and Solana is on the order of 1e-5 days of ADV, against a floor of 0.8 days. Q4 would fail too: BTC and SOL are the opposite of thinly covered.

**19. 2026-06-03 — FIFTH THIRD BANCORP  (FITB, FITBI, FITBM, FITBO, FITBP)** — fails **Q1**

VOLUNTARY listing transfer, NYSE to Nasdaq, common stock plus four series of depositary shares. Same disposition as 13.

**27. 2026-06-04 — AMERICAN SHARED HOSPITAL SERVICES  (AMS)** — fails **Q1**

The lender asserted Events of Default and raised the rate to the Default Rate, but the filing states plainly: "As of the date of this Form 8-K, the Lender HAS NOT ACCELERATED the obligations of the Loan Parties." Rights were reserved, not exercised.

**37. 2026-06-08 — SILVER STAR PROPERTIES REIT, INC** — fails **Q1**

Chapter 11 filing "made in an abundance of caution" by the guarantor of four defaulted mortgage loans. The automatic stay applies, so no actor is required to transact. The underlying collateral is real property in any event, which has no ADV against which Q3 could be measured.

**39. 2026-06-08 — GoHealth, Inc.  (GOCO)** — fails **Q1**

Chapter 11. Indebtedness "has become immediately due and payable", but enforcement is stayed by the filing. Same disposition as 17.

**50. 2026-06-12 — Sleep Number Corp  (SNBR)** — fails **Q1**

Chapter 11 plus debtor-in-possession financing of up to ~$260m from the prepetition lenders. Obligations accelerated, enforcement stayed, and the DIP amendment refinances rather than forces a sale.

**61. 2026-06-12 — Laser Photonics Corp  (LASE)** — fails **Q1**

The opposite of a forcing event: Laser Photonics received a LETTER OF COMPLIANCE confirming the earlier deficiency "was now closed". Nothing is compelled because nothing is wrong.

**71. 2026-06-16 — Assertio Holdings, Inc.  (ASRT)** — fails **Q2**

Merger closing. Consideration fixed by the merger agreement, same disposition as 3.01 subtype A.

**83. 2026-06-23 — OFFICE PROPERTIES INCOME TRUST  (OPIRQ, OPITQ)** — fails **Q7**

Plan of reorganization confirmed. The allocation of reorganized common equity and the 2029 Secured Exit Notes / New 2027 Senior Secured Notes is set out in the plan itself, published in advance of the effective date. The destination set is handed to the operator.

**86. 2026-06-23 — SANGAMO THERAPEUTICS, INC  (SGMO)** — fails **Q2**

Chapter 11 with stalking-horse asset purchase agreements. A stalking horse names both the purchaser and the price, so the rule specifies what, when AND at what price.

**93. 2026-06-25 — AMC ENTERTAINMENT HOLDINGS, INC.  (AMC)** — fails **Q2**

Redemption of senior subordinated notes funded by a completed registered direct offering. A redemption is executed at the contractual redemption price. Same disposition as 15.

**94. 2026-06-25 — Clearwater Analytics Holdings, Inc.  (CWAN)** — fails **Q2**

Merger consummated; consideration fixed by the merger agreement.

**96. 2026-06-25 — Permex Petroleum Corp** — fails **Q3**

Genuine forcing -- a notice of acceleration and demand followed by a "notice of foreclosure sale ... pertaining to the Company's rights, title and interest in certain oil and gas leases". Q1 and Q2 pass. Q3 fails: the forced supply set is oil and gas leases, which are not traded instruments and have no ADV, so the 0.8-day floor cannot be met or even evaluated.

**102. 2026-06-26 — VSEE HEALTH, INC.  (VSEE, VSEEW)** — fails **Q3**

The holder asserted an Event of Default on an "8% original issue discount secured promissory note in the aggregate principal amount of $271,739.13". Even taken at face value the sum is de minimis, and no securities supply set is identified.

**111. 2026-07-01 — STRATUS PROPERTIES INC  (STRS)** — fails **Q3**

Plan of complete liquidation and dissolution, with voluntary delisting. The forced supply set is real property held by a real estate company; no ADV exists against which the floor can be measured. The delisting is also explicitly voluntary and pre-announced.

**118. 2026-07-01 — ESS Tech, Inc.  (GWH, GWH-WT)** — fails **Q7**

NYSE "determined to (a) commence proceedings to delist the Company's Public Warrants ... and (b) immediately suspend trading ... due to abnormally low trading price levels pursuant to Section 802.01D". A genuine involuntary delisting determination, so subtype C: any holder actually compelled to exit is compelled by mandate or index-eligibility rules published in advance. Common stock is explicitly unaffected.

**119. 2026-07-02 — MV Oil Trust  (MVO)** — fails **Q3**

The most structurally interesting candidate in the pool and the only automatic, contractual dissolution. Q1 passes cleanly: the net profits interest "terminated on June 30, 2026 ... in accordance with the terms of the Conveyance of Net Profits Interest ... because the minimum amount of production (14.4 million barrels of oil equivalent) ... has been produced and sold", and "the Trust dissolved as of the Termination Date". Discretion is removed by a public trust instrument, automatically, on a quantitative trigger. Q2 passes: no price is named anywhere. Q3 fails, and it fails at zero. The wind-up is a CASH DISTRIBUTION followed by cancellation -- "the final quarterly cash distribution on July 24, 2026 to the Trust unitholders of record on July 15, 2026", then "the cancellation of the Trust Units". No instrument is sold into any market by anyone, so forced flow is 0.0 days of ADV against a floor of 0.8. A forced sale with no sale.

**129. 2026-07-06 — Fortress Net Lease REIT** — fails **Q1**

A New Lender Joinder Agreement adding Regions Bank to the credit facility. Item 2.04 covers events that accelerate OR INCREASE an obligation; this is an increase in borrowing capacity. Nothing is compelled to be sold.

**141. 2026-07-08 — AXT INC  (AXTI)** — fails **Q1**

Withdrawal of a STAR Market IPO application gives rise to a redemption right for eleven private equity funds -- and the filing states twice that it is optional: "each fund has THE RIGHT, BUT NOT THE OBLIGATION, to require the Company or Tongmei to redeem its investment, and the Company or Tongmei has THE RIGHT, BUT NOT THE OBLIGATION, to redeem". Discretion is retained on both sides. Q2 would fail too: the price is "equal to the original amount invested".

**161. 2026-07-13 — DATA I/O CORP  (DAIO)** — fails **Q7**

Conversion of the Note into the issuer's own equity. The destination instrument is named in the converting instrument itself, so the event tests transmission rather than enumeration -- the same disposition the previous session reached for mandatory conversion and mandatory exchange.

**164. 2026-07-14 — Trinity Capital Inc.  (TRIN, TRINI, TRINZ)** — fails **Q1**

VOLUNTARY listing transfer, Nasdaq to NYSE and NYSE Texas, common stock and two note series. Same disposition as 13.

**168. 2026-07-14 — D-Wave Quantum Inc.  (QBTS)** — fails **Q1**

VOLUNTARY listing transfer, NYSE to Nasdaq; the stock "has been approved for listing on Nasdaq, where it will continue to trade under its current ticker symbol". Same disposition as 13.

**169. 2026-07-15 — Creative Media & Community Trust Corp  (CMCT)** — fails **Q1**

Maturity default on a non-recourse mortgage on a single property. The company "remains current on the monthly interest payments" and "ELECTED NOT TO INVEST additional capital in the asset that would have been required to refinance the mortgage". A choice, not a compulsion, and non-recourse means the lender's remedy is the building.

**170. 2026-07-15 — SemiLEDs Corp  (LEDS)** — fails **Q1**

SemiLEDs "believes that it has REGAINED COMPLIANCE with the stockholders' equity requirement" after reporting $3.1m against a $2.5m minimum. Same disposition as 61.

**175. 2026-07-15 — LIPELLA PHARMACEUTICALS INC.  (LIPO)** — fails **Q2**

Chapter 11 asset sale under an Asset Purchase Agreement with a named purchaser, approved by the Bankruptcy Court. Purchaser and price are both specified.

