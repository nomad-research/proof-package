#!/usr/bin/env python3
"""EDGAR access with a hard filing-date ceiling.

The analyst's carve-out permits EDGAR because filing metadata and filing text
carry no outcome narrative. But EDGAR *does* carry post-fire-date filings -- a
Q2 2026 13F filed in August would show exactly what changed. So the ceiling is
enforced here in code rather than kept by hand:

  - `filings` lists filings and marks anything filed on/after the fire date
    BLOCKED. It prints dates only; it never fetches a blocked document.
  - `open` refuses outright if the filing date is on/after the fire date.
  - `fts` filters full-text-search hits to pre-fire filings BEFORE they are
    printed, so a post-dated snippet is never surfaced.

Every filing opened is appended to firewall/fetch_log.jsonl with its date,
per operating procedure section 6.
"""
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CFG = json.loads((HERE / "config.json").read_text())
FIRE = CFG["fire_date"]
LOG = HERE / "fetch_log.jsonl"
SAVE = HERE / "fetched"
UA = "nomad-research bato2912@gmail.com"


def _curl(url, raw=False):
    p = subprocess.run(["curl", "-sS", "--max-time", "90", "-H", f"User-Agent: {UA}", url],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"curl failed rc={p.returncode}: {p.stderr[:200]}")
    return p.stdout


def _log(**kw):
    kw["ts_utc"] = datetime.now(timezone.utc).isoformat()
    with open(LOG, "a") as fh:
        fh.write(json.dumps(kw) + "\n")


def _blocked(d: str) -> bool:
    return bool(d) and d >= FIRE


def find(name):
    """Company search -- returns CIK + name only. No filing documents."""
    url = ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
           f"&company={name.replace(' ', '+')}&type=13F&dateb=&owner=include"
           "&count=100&output=atom")
    t = _curl(url)
    ciks = re.findall(r"<CIK>(\d+)</CIK>", t)
    names = re.findall(r"<conformed-name>([^<]*)</conformed-name>", t)
    _log(kind="edgar_find", query=name, hits=len(ciks))
    if not ciks:
        # single-company match redirects to the company page
        c = re.findall(r"CIK=(\d{10})", t)
        n = re.findall(r"<title>([^<]*)</title>", t)
        for a, b in zip(c, n):
            print(f"  {a}  {b}")
        if not c:
            print("  no matches")
        return
    for a, b in zip(ciks, names or ciks):
        print(f"  {a}  {b}")


def filings(cik, form=None):
    """List filings with dates. Marks post-fire filings BLOCKED. Fetches nothing."""
    cik10 = str(cik).zfill(10)
    d = json.loads(_curl(f"https://data.sec.gov/submissions/CIK{cik10}.json"))
    r = d["filings"]["recent"]
    rows = list(zip(r["form"], r["filingDate"], r["reportDate"],
                    r["accessionNumber"], r["primaryDocument"]))
    if form:
        rows = [x for x in rows if form.upper() in x[0].upper()]
    print(f"  entity: {d.get('name')}   CIK {cik10}   fire_date {FIRE}")
    print(f"  {'FORM':<12} {'FILED':<12} {'PERIOD':<12} {'ACCESSION':<22} STATUS")
    n_ok = n_blocked = 0
    for form_t, filed, period, acc, doc in rows:
        if _blocked(filed):
            status = "*** BLOCKED (post-fire) ***"
            n_blocked += 1
        else:
            status = "openable"
            n_ok += 1
        print(f"  {form_t:<12} {filed:<12} {period or '':<12} {acc:<22} {status}")
    older = d["filings"].get("files", [])
    _log(kind="edgar_filings", cik=cik10, form=form, openable=n_ok, blocked=n_blocked)
    print(f"  -- {n_ok} openable, {n_blocked} blocked as post-fire; "
          f"{len(older)} older-submission page(s) not loaded")


def open_filing(cik, accession, doc=None):
    """Fetch a filing document, refusing anything filed on/after the fire date."""
    cik10 = str(cik).zfill(10)
    d = json.loads(_curl(f"https://data.sec.gov/submissions/CIK{cik10}.json"))
    r = d["filings"]["recent"]
    idx = None
    for i, a in enumerate(r["accessionNumber"]):
        if a == accession:
            idx = i
            break
    if idx is None:
        sys.exit(f"REFUSED: accession {accession} not in recent filings for CIK {cik10}")
    filed = r["filingDate"][idx]
    if _blocked(filed):
        _log(kind="edgar_open_REFUSED", cik=cik10, accession=accession, filing_date=filed)
        sys.exit(f"REFUSED: {accession} was filed {filed}, on/after the fire date {FIRE}. "
                 "Opening it would contaminate the run.")
    doc = doc or r["primaryDocument"][idx]
    acc_nodash = accession.replace("-", "")
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik10)}/{acc_nodash}/{doc}"
    body = _curl(url)
    SAVE.mkdir(parents=True, exist_ok=True)
    out = SAVE / f"{accession}_{doc.replace('/', '_')}"
    out.write_text(body)
    _log(kind="edgar_open", cik=cik10, accession=accession, filing_date=filed,
         form=r["form"][idx], period=r["reportDate"][idx], url=url,
         bytes=len(body), saved_to=str(out), clause_located=None)
    print(f"OPENED {r['form'][idx]} filed {filed} (period {r['reportDate'][idx]}) "
          f"-> {out}  [{len(body)} bytes]")
    return out


def fts(query, forms=None):
    """Full-text search, with post-fire hits filtered out before printing."""
    url = ("https://efts.sec.gov/LATEST/search-index?q=" + query.replace(" ", "+")
           + (f"&forms={forms}" if forms else "") + "&dateRange=custom"
           f"&startdt=2024-01-01&enddt={FIRE}")
    try:
        d = json.loads(_curl(url))
    except Exception as e:
        print(f"  FTS unavailable ({e})")
        return
    hits = d.get("hits", {}).get("hits", [])
    shown = dropped = 0
    for h in hits:
        s = h.get("_source", {})
        filed = s.get("file_date", "")
        if _blocked(filed):
            dropped += 1
            continue
        shown += 1
        print(f"  {s.get('form','?'):<10} {filed:<12} {s.get('display_names',[''])[0][:60]}"
              f"  {h.get('_id','')}")
    _log(kind="edgar_fts", query=query, shown=shown, dropped_post_fire=dropped)
    print(f"  -- {shown} pre-fire hits shown, {dropped} post-fire hits withheld")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: edgar.py find|filings|open|fts ...")
    cmd = sys.argv[1]
    if cmd == "find":
        find(" ".join(sys.argv[2:]))
    elif cmd == "filings":
        filings(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif cmd == "open":
        open_filing(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    elif cmd == "fts":
        fts(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    else:
        sys.exit(f"unknown command {cmd}")
