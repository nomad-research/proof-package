"""Alternative data for geopolitical and physical-world rounds: satellites, AIS, event
feeds, outages (added 2026-09-29 at the user's request).

These are in-harness adapters standing in for the data product (T1, §26), which is not
built here. Each one obeys the same three rules as every other input:

1. **Point in time.** Every record carries a ``knowable_from`` computed by a stated rule
   (below; lags are appetite ``ALT_LATENCY``), and nothing knowable after the round's
   bound (pre-lock clock, or the walk frontier) is saved or printed. The server-side
   date filter is never trusted: every record is re-checked in memory (§12: "never
   trust a filter's promise, verify the payload against its own metadata").
2. **Probed before trusted.** ``alt_probe`` runs a discriminating probe on a fixed past
   window and checks the payload against its own metadata; ``alt_fetch`` refuses a
   source without a passing probe.
3. **Typed gaps.** A source that needs a credential nobody has set is ``not_covered``,
   with what would fix it; it is never silently skipped.

| source | what | knowable_from rule |
|---|---|---|
| ``s2_scenes`` | Sentinel-2 L2A scenes over a bbox (Planetary Computer STAC) | the product's processing timestamp (in its id) + ALT_LATENCY.s2 hours |
| ``s2_image`` | a true-colour crop of one scene, saved as PNG (read it with the Read tool), plus a crude bright-object count | as its scene |
| ``portwatch_chokepoint`` / ``portwatch_port`` | IMF PortWatch daily AIS transit / port-call counts by vessel type | record date + ALT_LATENCY.portwatch days (weekly publication) |
| ``gdelt_events`` | GDELT 2.0 15-minute event exports, filtered by country or bbox; counts by CAMEO root and mean Goldstein | the export file's timestamp |
| ``ioda`` | IODA internet-outage signals for a country | sample time + ALT_LATENCY.ioda hours |
| ``usgs_quakes`` | USGS earthquake catalogue in a bbox | origin time + ALT_LATENCY.usgs hours; magnitudes are revisable (flagged) |
| ``firms`` | NASA FIRMS VIIRS active-fire detections in a bbox | acquisition time + ALT_LATENCY.firms hours; needs FIRMS_MAP_KEY |
| ``gfw`` / ``acled`` / ``black_marble`` | vessel presence / conflict events / night lights | ``not_covered`` until GFW_TOKEN / ACLED_KEY+ACLED_EMAIL / EARTHDATA_TOKEN are set |
"""
from __future__ import annotations

import csv
import datetime as _dt
import io
import json
import os
import re
import urllib.parse
import zipfile

import numpy as np

from . import config
from .db import DB, ROOT, Refused, sha
from .pit import _advance, _log, _save, bound
from .util import curl, day, ts

PC_STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
PC_RENDER = ("https://planetarycomputer.microsoft.com/api/data/v1/item/bbox/{bbox}.png?collection={col}"
             "&item={item}&assets=visual&asset_bidx=visual%7C1%2C2%2C3&max_size={size}")
PW = "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/{layer}/FeatureServer/0/query"
GDELT = "http://data.gdeltproject.org/gdeltv2/{stamp}.export.CSV.zip"
IODA = "https://api.ioda.inetintel.cc.gatech.edu/v2/signals/raw/country/{cc}?from={f}&until={u}"
USGS = "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime={s}&endtime={e}&minlatitude={a}&maxlatitude={b}&minlongitude={c}&maxlongitude={d}"
FIRMS = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_SNPP_NRT/{bbox}/{days}/{date}"

SOURCES = {"s2_scenes", "s2_image", "portwatch_chokepoint", "portwatch_port", "gdelt_events", "ioda",
           "usgs_quakes", "firms", "gfw", "acled", "black_marble"}
NEEDS_KEY = {"firms": ["FIRMS_MAP_KEY"], "gfw": ["GFW_TOKEN"], "acled": ["ACLED_KEY", "ACLED_EMAIL"],
             "black_marble": ["EARTHDATA_TOKEN"]}
NOT_BUILT = {"gfw", "acled", "black_marble"}


def lat(name: str) -> float:
    return float(config.get("ALT_LATENCY")[name])


def _bbox(b) -> list[float]:
    if isinstance(b, str):
        b = [float(x) for x in b.split(",")]
    if len(b) != 4:
        raise Refused("bbox is [min_lon, min_lat, max_lon, max_lat]")
    return [float(x) for x in b]


def _iso(t) -> str:
    return ts(t).strftime("%Y-%m-%dT%H:%M:%SZ")


# ------------------------------------------------------------------ record fetchers (no bound here)
def _s2_scenes(bbox, start, end, max_cloud=60):
    body = json.dumps({"collections": ["sentinel-2-l2a"], "bbox": bbox, "limit": 200,
                       "datetime": f"{_iso(start)}/{_iso(end)}",
                       "query": {"eo:cloud_cover": {"lt": max_cloud}}})
    import subprocess
    from .util import BROWSER_UA
    p = subprocess.run(["curl", "-sS", "-L", "--max-time", "90", "-A", BROWSER_UA, "-X", "POST",
                        "-H", "Content-Type: application/json", "-d", body, PC_STAC],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise Refused(f"STAC search failed: {p.stderr[:200]}")
    d = json.loads(p.stdout)
    out = []
    for f in d.get("features", []):
        m = re.search(r"_(\d{8}T\d{6})$", f["id"])
        proc = _dt.datetime.strptime(m.group(1), "%Y%m%dT%H%M%S").replace(tzinfo=_dt.timezone.utc) if m else None
        acq = f["properties"]["datetime"]
        kf = (proc if proc else ts(acq).to_pydatetime()) + _dt.timedelta(hours=lat("s2"))
        out.append({"scene_id": f["id"], "acquired": acq, "cloud": f["properties"].get("eo:cloud_cover"),
                    "processed": proc.isoformat() if proc else None, "knowable_from": kf.isoformat(),
                    "tile": f["properties"].get("s2:mgrs_tile"), "bbox": f.get("bbox")})
    return sorted(out, key=lambda r: r["acquired"])


def _count_bright(png_bytes: bytes, thresh: int = 170, min_px: int = 3, max_px: int = 4000) -> dict:
    """Crude bright-object count (ships on dark water, flares, fires). A proposer, never support."""
    from PIL import Image
    from scipy import ndimage
    im = np.asarray(Image.open(io.BytesIO(png_bytes)).convert("L"), dtype=np.uint8)
    valid = im > 0
    mask = (im >= thresh) & valid
    lab, n = ndimage.label(mask)
    sizes = ndimage.sum(mask, lab, range(1, n + 1)) if n else []
    objs = int(sum(1 for s in sizes if min_px <= s <= max_px))
    return {"bright_objects": objs, "valid_fraction": float(valid.mean()), "threshold": thresh,
            "note": "crude connected-component count of pixels above a brightness threshold; clouds and "
                    "surf also count. Use to propose, never to support (§6: analogical modes don't support)"}


def _portwatch(layer, name, start, end):
    where = f"portname='{name}' AND date >= DATE '{day(start)}' AND date <= DATE '{day(end)}'"
    q = urllib.parse.urlencode({"where": where, "outFields": "*", "orderByFields": "date ASC",
                                "resultRecordCount": 2000, "f": "json"})
    d = json.loads(curl(f"{PW.format(layer=layer)}?{q}"))
    if "error" in d:
        raise Refused(f"PortWatch error: {d['error']}")
    out = []
    for f in d.get("features", []):
        a = f["attributes"]
        dt = a.get("date")
        dd = (_dt.datetime(1970, 1, 1) + _dt.timedelta(milliseconds=dt)).strftime("%Y-%m-%d") if isinstance(dt, (int, float)) else str(dt)[:10]
        rec = {k: v for k, v in a.items() if k.startswith("n_") or k.startswith("capacity") or k in ("portid", "portname")}
        rec["date"] = dd
        rec["knowable_from"] = (ts(dd) + _dt.timedelta(days=lat("portwatch"))).strftime("%Y-%m-%d")
        out.append(rec)
    return out


def _gdelt(start, end, country=None, bbox=None, max_files=96):
    t = ts(start).floor("15min")
    e = ts(end)
    files, rows = 0, []
    agg: dict = {}
    while t <= e and files < max_files:
        stamp = t.strftime("%Y%m%d%H%M%S")
        try:
            raw = curl(GDELT.format(stamp=stamp), binary=True, timeout=60)
            files += 1
            z = zipfile.ZipFile(io.BytesIO(raw))
            txt = z.read(z.namelist()[0]).decode("utf-8", errors="replace")
            for r in csv.reader(io.StringIO(txt), delimiter="\t"):
                if len(r) < 61:
                    continue
                cc, la, lo = r[53], r[56], r[57]
                if country and cc != country:
                    continue
                if bbox:
                    try:
                        la, lo = float(la), float(lo)
                    except ValueError:
                        continue
                    if not (bbox[1] <= la <= bbox[3] and bbox[0] <= lo <= bbox[2]):
                        continue
                root = r[28]
                a = agg.setdefault(root, {"n": 0, "goldstein": 0.0, "mentions": 0})
                a["n"] += 1
                a["goldstein"] += float(r[30] or 0)
                a["mentions"] += int(r[31] or 0)
                if len(rows) < 50:
                    rows.append({"file": stamp, "root": root, "code": r[26], "actor1": r[6], "actor2": r[16],
                                 "geo": r[52], "domain": urllib.parse.urlparse(r[60]).netloc})
        except Refused:
            pass
        t += _dt.timedelta(minutes=15)
    for a in agg.values():
        a["goldstein_mean"] = a["goldstein"] / a["n"] if a["n"] else None
    return {"files_read": files, "by_cameo_root": dict(sorted(agg.items())), "sample": rows,
            "knowable_from": _iso(min(t, e))}


def _ioda(cc, start, end):
    f, u = int(ts(start).timestamp()), int(ts(end).timestamp())
    d = json.loads(curl(IODA.format(cc=cc, f=f, u=u)))
    out = []
    for series in (d.get("data") or [[]])[0]:
        vals = series.get("values") or []
        step, t0 = series.get("step"), series.get("from")
        pts = [(t0 + i * step, v) for i, v in enumerate(vals)]
        out.append({"datasource": series.get("datasource"), "step": step, "from": t0, "until": series.get("until"),
                    "points": pts})
    return out


def _usgs(bbox, start, end):
    d = json.loads(curl(USGS.format(s=_iso(start), e=_iso(end), a=bbox[1], b=bbox[3], c=bbox[0], d=bbox[2])))
    out = []
    for f in d.get("features", []):
        p = f["properties"]
        t = _dt.datetime.fromtimestamp(p["time"] / 1000, _dt.timezone.utc)
        out.append({"id": f["id"], "time": t.isoformat(), "mag": p.get("mag"), "place": p.get("place"),
                    "knowable_from": (t + _dt.timedelta(hours=lat("usgs"))).isoformat(),
                    "revisable": True})
    return out


def _firms(bbox, end, days):
    key = os.environ.get("FIRMS_MAP_KEY")
    txt = curl(FIRMS.format(key=key, bbox=",".join(str(x) for x in bbox), days=int(days), date=day(end)))
    rows = list(csv.DictReader(io.StringIO(txt)))
    for r in rows:
        hhmm = str(r.get("acq_time", "0")).zfill(4)
        t = ts(f"{r['acq_date']}T{hhmm[:2]}:{hhmm[2:]}:00Z")
        r["knowable_from"] = (t + _dt.timedelta(hours=lat("firms"))).isoformat()
    return rows


# ------------------------------------------------------------------ tools
def _probe_ok(db, source):
    rows = db.rows("notes", "subject=?", (f"probe:{source}",))
    return rows and rows[-1]["text"].startswith("PASS")


def alt_probe(db: DB, source: str) -> dict:
    """A discriminating probe on a fixed past window; checks the payload against its own metadata."""
    if source not in SOURCES:
        raise Refused(f"unknown source; one of {sorted(SOURCES)}")
    miss = [k for k in NEEDS_KEY.get(source, []) if not os.environ.get(k)]
    if source in NOT_BUILT or miss:
        verdict = f"NOT_COVERED: needs {NEEDS_KEY.get(source)}" + (" and an adapter" if source in NOT_BUILT else "")
        db.append("notes", round_id=None, segment_idx=None, subject=f"probe:{source}", text=verdict)
        return {"source": source, "verdict": verdict}
    start, end = "2025-01-01T00:00:00Z", "2025-01-15T00:00:00Z"
    problems, n = [], 0
    try:
        if source in {"s2_scenes", "s2_image"}:
            r = _s2_scenes([56.0, 26.3, 56.6, 26.8], start, end)
            n = len(r)
            problems += [x["scene_id"] for x in r if not (start[:10] <= x["acquired"][:10] <= end[:10])]
            if source == "s2_image" and r:
                png = curl(PC_RENDER.format(bbox="56.2,26.5,56.4,26.65", col="sentinel-2-l2a",
                                            item=r[0]["scene_id"], size=512), binary=True)
                if not png.startswith(b"\x89PNG"):
                    problems.append("render did not return a PNG")
        elif source.startswith("portwatch"):
            layer, name = (("Daily_Chokepoints_Data", "Strait of Hormuz") if source == "portwatch_chokepoint"
                           else ("Daily_Ports_Data", "Rotterdam"))
            r = _portwatch(layer, name, start, end)
            n = len(r)
            problems += [x["date"] for x in r if not (start[:10] <= x["date"] <= end[:10])]
            if n == 0:
                problems.append("no records in a window that must have them")
        elif source == "gdelt_events":
            r = _gdelt("2025-01-02T00:00:00Z", "2025-01-02T01:00:00Z", country="IR", max_files=4)
            n = sum(v["n"] for v in r["by_cameo_root"].values())
            if r["files_read"] == 0:
                problems.append("no export files read")
            if n == 0:
                problems.append("files read but no events matched a country that has events every hour: "
                                "the parser or the column mapping is broken")
        elif source == "ioda":
            r = _ioda("IR", start, end)
            n = sum(len(s["points"]) for s in r)
            for s in r:
                if s["until"] and s["until"] > int(ts(end).timestamp()) + 86400:
                    problems.append(f"{s['datasource']} runs past the window")
        elif source == "usgs_quakes":
            r = _usgs([44.0, 25.0, 64.0, 40.0], start, end)
            n = len(r)
            problems += [x["id"] for x in r if not (start[:10] <= x["time"][:10] <= end[:10])]
        elif source == "firms":
            r = _firms([56.0, 26.0, 57.0, 27.0], "2025-01-10", 5)
            n = len(r)
            problems += [x.get("acq_date") for x in r if not ("2025-01-05" <= x.get("acq_date", "") <= "2025-01-10")]
    except Refused as e:
        problems.append(str(e))
    verdict = ("PASS" if not problems else "FAIL") + f": n={n} problems={problems[:5]}"
    db.append("notes", round_id=None, segment_idx=None, subject=f"probe:{source}", text=verdict)
    return {"source": source, "verdict": verdict}


def alt_fetch(db: DB, round_id: str, source: str, as_of: str, reason: str, bbox=None, start: str | None = None,
              name: str | None = None, country: str | None = None, scene_id: str | None = None,
              max_cloud: float = 60, days: int = 5, max_files: int = 96) -> dict:
    if source not in SOURCES:
        raise Refused(f"unknown source; one of {sorted(SOURCES)}")
    if not reason:
        raise Refused("every fetch states its reason")
    miss = [k for k in NEEDS_KEY.get(source, []) if not os.environ.get(k)]
    if source in NOT_BUILT or miss:
        _log(db, round_id, source, name or country or str(bbox), as_of, reason, "not_covered")
        return {"source": source, "status": "not_covered",
                "fix": f"set {NEEDS_KEY.get(source)} in the environment's secrets"
                       + (" and build the adapter" if source in NOT_BUILT else "")}
    if not _probe_ok(db, source):
        raise Refused(f"source {source} has no passing probe; run alt_probe first (§12)")
    as_of = bound(db, round_id, as_of)
    cap = ts(as_of)
    start = start or (cap - _dt.timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    dropped = 0
    if source == "s2_scenes":
        b = _bbox(bbox)
        recs = _s2_scenes(b, start, as_of, max_cloud)
        keep = [r for r in recs if ts(r["knowable_from"]) <= cap]
        dropped = len(recs) - len(keep)
        content = json.dumps({"bbox": b, "scenes": keep}, indent=1)
        eid = _save(db, round_id, source, f"s2_{sha(str(b))[:8]}_{day(as_of)}.json", content, PC_STAC,
                    day(as_of), "sentinel2", f"{len(keep)} scenes knowable by {day(as_of)}")
        out = {"scenes": keep}
    elif source == "s2_image":
        if not scene_id:
            raise Refused("s2_image needs scene_id (from s2_scenes)")
        b = _bbox(bbox)
        m = re.search(r"_(\d{8}T\d{6})$", scene_id)
        if not m:
            raise Refused("scene id carries no processing timestamp; its knowable_from can't be established")
        kf = _dt.datetime.strptime(m.group(1), "%Y%m%dT%H%M%S").replace(tzinfo=_dt.timezone.utc) + _dt.timedelta(hours=lat("s2"))
        if kf > cap.to_pydatetime():
            raise Refused(f"scene knowable from {kf.isoformat()}, after the bound {as_of}")
        png = curl(PC_RENDER.format(bbox=",".join(str(x) for x in b), col="sentinel-2-l2a", item=scene_id, size=1024),
                   binary=True)
        if not png.startswith(b"\x89PNG"):
            raise Refused("render did not return a PNG")
        d = ROOT / "rounds" / round_id / "fetched"
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"s2_{scene_id}_{sha(str(b))[:6]}.png"
        p.write_bytes(png)
        cnt = _count_bright(png)
        eid = _save(db, round_id, source, p.name + ".json", json.dumps({"scene": scene_id, "bbox": b, "png": str(p.relative_to(ROOT)), **cnt}),
                    f"planetarycomputer:{scene_id}", kf.isoformat(), "sentinel2", f"crop of {scene_id}; {cnt['bright_objects']} bright objects")
        out = {"png": str(p.relative_to(ROOT)), "knowable_from": kf.isoformat(), **cnt,
               "view": "open the png with the Read tool to look at it"}
    elif source in {"portwatch_chokepoint", "portwatch_port"}:
        if not name:
            raise Refused("name the chokepoint or port exactly as PortWatch names it")
        layer = "Daily_Chokepoints_Data" if source == "portwatch_chokepoint" else "Daily_Ports_Data"
        recs = _portwatch(layer, name, start, as_of)
        keep = [r for r in recs if ts(r["knowable_from"]) <= cap]
        dropped = len(recs) - len(keep)
        eid = _save(db, round_id, source, f"pw_{sha(name)[:8]}_{day(as_of)}.json", json.dumps(keep, indent=1),
                    PW.format(layer=layer), day(as_of), "portwatch", f"{name}: {len(keep)} daily records")
        out = {"records": keep, "revisions": "PortWatch restates recent days; REVISION_CHAINS missing: terms "
                                             "reading these values are flagged contaminated"}
    elif source == "gdelt_events":
        b = _bbox(bbox) if bbox else None
        if not (country or b):
            raise Refused("filter by country (FIPS code) or bbox")
        g = _gdelt(start, as_of, country=country, bbox=b, max_files=max_files)
        eid = _save(db, round_id, source, f"gdelt_{country or sha(str(b))[:8]}_{day(as_of)}.json", json.dumps(g, indent=1),
                    "data.gdeltproject.org/gdeltv2", g["knowable_from"], "gdelt",
                    f"{g['files_read']} files; roots {list(g['by_cameo_root'])[:8]}")
        out = g
    elif source == "ioda":
        if not country:
            raise Refused("ioda needs a country code (ISO2)")
        until = cap - _dt.timedelta(hours=lat("ioda"))
        r = _ioda(country, start, until)
        for s in r:
            s["points"] = [p for p in s["points"] if p[0] <= until.timestamp()]
        eid = _save(db, round_id, source, f"ioda_{country}_{day(as_of)}.json", json.dumps(r), IODA, _iso(until),
                    "ioda", f"{country}: {len(r)} signals")
        out = {"signals": [{k: s[k] for k in ("datasource", "step")} | {"n": len(s["points"]),
                            "last": s["points"][-5:]} for s in r]}
    elif source == "usgs_quakes":
        recs = _usgs(_bbox(bbox), start, as_of)
        keep = [r for r in recs if ts(r["knowable_from"]) <= cap]
        dropped = len(recs) - len(keep)
        eid = _save(db, round_id, source, f"usgs_{day(as_of)}.json", json.dumps(keep, indent=1), USGS, day(as_of),
                    "usgs", f"{len(keep)} events (magnitudes revisable)")
        out = {"events": keep}
    elif source == "firms":
        recs = _firms(_bbox(bbox), as_of, days)
        keep = [r for r in recs if ts(r["knowable_from"]) <= cap]
        dropped = len(recs) - len(keep)
        eid = _save(db, round_id, source, f"firms_{day(as_of)}.json", json.dumps(keep, indent=1), "firms", day(as_of),
                    "firms", f"{len(keep)} fire detections")
        out = {"detections": keep[:500], "n": len(keep)}
    _log(db, round_id, source, name or country or scene_id or str(bbox), as_of, reason, "ok", eid,
         detail=f"dropped {dropped} records knowable after the bound")
    _advance(db, round_id, as_of, source)
    return {"source": source, "evidence_id": eid, "dropped_after_bound": dropped, **out}
