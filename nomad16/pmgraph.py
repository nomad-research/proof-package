"""The open-set graph (Polymarket frame; V1 pre-registration §11, A3 superseded: Rob, 2026-09-30, "the graph can be bounded by the event set open on Polymarket").

The events open at a moment are a finite, enumerable set. This module turns one universe file (the recorder's daily sweep) into that graph and reads
neighbourhoods out of it. **No price, volume or order book is used to build an edge or a neighbourhood**: edges come from structure (partition, ladder), tags and
named entities in titles, all documents. Entity and tag overlap is a heuristic stand-in (like the trigram stand-in in dilution.py): it proposes candidates for a
session to read and never supports a claim. Anything outside the set is a typed gap ("no instrument").

Event classes use the definitions of ``lookbacks/polymarket/CENSUS_SPEC.md`` (copied, not imported, because the census is frozen).
"""
from __future__ import annotations

import collections
import gzip
import json
import math
import re

GENERIC_TAGS = {"hide-from-new", "recurring", "weekly", "monthly", "daily", "yearly", "multi-strikes", "neg-risk", "parent-for-derivative", "hit-price", "today",
                "up-or-down", "daily-close", "pre-market", "close", "hits", "props", "derivatives", "main-election", "international-election-props", "world", "rewards"}
_STOP = set("""will the be a an of in on at by to for and or is are who what which when how this that with from than more less before after above below over under between
  win wins won next first last any other not no yes least most price hit reach dip market cap close closing above january february march april may june july august
  september october november december monday tuesday wednesday thursday friday saturday sunday election""".split())
MON = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"
DATE_TOK = re.compile(rf"\b{MON}\s+\d{{1,2}}(,?\s*20\d\d)?\b|\b{MON}\s+20\d\d\b|\bq[1-4]\b|\b20\d\d\b|\b{MON}\b", re.I)
NUM_TOK = re.compile(r"\$\s?[\d,\.]+\s?(k|m|b|million|billion)?|\b\d[\d,\.]*\s?(%|k|m|b)\b|\b\d[\d,\.]*\b", re.I)
TIME_TOK = re.compile(r"\b\d{1,2}(:\d{2})?\s?(am|pm)\b(\s?-\s?\d{1,2}(:\d{2})?\s?(am|pm)\b)?", re.I)
TOUCH = re.compile(r"\b(reach|reaches|hit|hits|dip|dips|touch|touches)\b", re.I)


def load_universe(path: str) -> list[dict]:
    with gzip.open(path, "rt") as f:
        return [json.loads(x) for x in f if x.strip()]


def _toks(q: str):
    d = tuple(m.group(0).lower() for m in DATE_TOK.finditer(q))
    rest = DATE_TOK.sub("@", q)
    n = tuple(m.group(0).lower() for m in NUM_TOK.finditer(rest))
    return d, n, re.sub(r"\s+", " ", NUM_TOK.sub("#", rest)).strip().lower()


def structure(e: dict) -> dict:
    """Class of one event: partition_exact | partition_open | ladder (with kind terminal | touch) | date_ladder | other | single. Header-only events: 'out_of_scope'."""
    if e.get("header_only"):
        return {"class": "out_of_scope"}
    ms = e.get("markets") or []
    if len(ms) <= 2:
        return {"class": "single"}
    open_slot = any(m.get("nro") or (m.get("git") or "").strip().lower() in ("other", "someone else") or re.match(r"person [a-z]$", (m.get("git") or "").strip().lower()) for m in ms)
    if e.get("negRisk"):
        return {"class": "partition_open" if open_slot else "partition_exact"}
    T = [_toks(m.get("q") or "") for m in ms]
    common = collections.Counter(t[2] for t in T).most_common(1)
    same = [t for t in T if common and t[2] == common[0][0]]
    thr = len({m.get("gthr") for m in ms if m.get("gthr") not in (None, "")}) >= 3
    if thr or (len(same) >= 3 and len({t[1] for t in same}) >= 3):
        touch = sum(bool(TOUCH.search(m.get("q") or "")) for m in ms) > len(ms) / 2
        return {"class": "ladder", "kind": "touch" if touch else "terminal"}
    if len(same) >= 3 and len({t[0] for t in same}) >= 3:
        return {"class": "date_ladder"}
    return {"class": "other"}


def template(title: str) -> str:
    """A title with its dates, times and numbers removed: recurring events ('Bitcoin Up or Down - September 30, 8:30AM-8:45AM ET') share one template."""
    return _toks(TIME_TOK.sub("@", title or ""))[2]


def entities(title: str) -> set[str]:
    """Capitalised words of a title that are not stop words: a crude named-entity stand-in."""
    out = set()
    for w in re.findall(r"\b[A-Z][A-Za-z\.\-']{2,}\b", title or ""):
        lw = w.lower().strip(".'-")
        if lw not in _STOP and not DATE_TOK.fullmatch(w):
            out.add(lw)
    return out


class Graph:
    def __init__(self, events: list[dict], generic_share: float = 0.05, min_idf_events: int = 2):
        self.events = {str(e["id"]): e for e in events if not e.get("header_only")}
        self.headers = sum(1 for e in events if e.get("header_only"))
        self.n = max(1, len(self.events))
        self.struct = {i: structure(e) for i, e in self.events.items()}
        tag_df, ent_df = collections.Counter(), collections.Counter()
        self.tags, self.ents = {}, {}
        self.template = {i: template(e.get("title")) for i, e in self.events.items()}
        for i, e in self.events.items():
            t = {x for x in (e.get("tags") or []) if x and x not in GENERIC_TAGS and not x.startswith("rewards")}
            en = entities(e.get("title") or "")
            self.tags[i], self.ents[i] = t, en
            tag_df.update(t); ent_df.update(en)
        cut = max(min_idf_events, int(generic_share * self.n))
        self.generic = {t for t, c in tag_df.items() if c > cut}        # a tag on more than generic_share of events links everything and so says nothing
        self.tag_idf = {t: math.log(self.n / c) for t, c in tag_df.items() if t not in self.generic}
        self.ent_idf = {t: math.log(self.n / c) for t, c in ent_df.items() if c <= cut}
        self.tag_index, self.ent_index = collections.defaultdict(set), collections.defaultdict(set)
        for i in self.events:
            for t in self.tags[i]:
                if t in self.tag_idf: self.tag_index[t].add(i)
            for t in self.ents[i]:
                if t in self.ent_idf: self.ent_index[t].add(i)

    def edges_from(self, i: str) -> dict[str, dict]:
        """Score and evidence of every event that shares a rare tag or entity with ``i``."""
        out: dict[str, dict] = {}
        for t in self.tags[i]:
            for j in self.tag_index.get(t, ()):
                if j != i:
                    d = out.setdefault(j, {"score": 0.0, "tags": [], "entities": []})
                    d["score"] += self.tag_idf[t]; d["tags"].append(t)
        for t in self.ents[i]:
            for j in self.ent_index.get(t, ()):
                if j != i:
                    d = out.setdefault(j, {"score": 0.0, "tags": [], "entities": []})
                    d["score"] += 0.5 * self.ent_idf[t]; d["entities"].append(t)
        return out

    def live(self, e: dict, at: str | None) -> bool:
        """Open at ``at`` (ISO time), by the event's own start and end; with no ``at``, every event in the universe file is open."""
        if at is None:
            return True
        return (not e.get("start") or e["start"] <= at) and (not e.get("end") or e["end"] >= at)

    def neighbourhood(self, event_id: str, depth: int = 2, cap: int = 60, at: str | None = None, decay: float = 0.5, classes: set | None = None) -> list[dict]:
        """Events reachable from ``event_id`` within ``depth`` hops, scored by summed rare-tag and entity evidence (2-hop paths decay), cut at ``cap`` by score then id.
        Deterministic and price-free."""
        event_id = str(event_id)
        if event_id not in self.events:
            raise KeyError(f"event {event_id} is not in the graph")
        best: dict[str, dict] = {}
        frontier = {event_id: 1.0}
        seen = {event_id}
        for hop in range(1, depth + 1):
            nxt: dict[str, float] = {}
            for i, w in frontier.items():
                for j, d in self.edges_from(i).items():
                    if j == event_id or not self.live(self.events[j], at):
                        continue
                    s = w * d["score"] * (decay ** (hop - 1))
                    b = best.setdefault(j, {"event_id": j, "score": 0.0, "hops": hop, "via": i if hop > 1 else None, "tags": [], "entities": []})
                    b["score"] += s
                    b["hops"] = min(b["hops"], hop)
                    b["tags"] = sorted(set(b["tags"]) | set(d["tags"])); b["entities"] = sorted(set(b["entities"]) | set(d["entities"]))
                    nxt[j] = max(nxt.get(j, 0.0), w * decay)
            seen |= set(nxt); frontier = nxt
        return self._collapse(sorted(best.values(), key=lambda b: (-b["score"], b["event_id"])), cap, classes)

    def _collapse(self, ranked: list[dict], cap: int, classes: set | None = None) -> list[dict]:
        """One entry per template (the best-scoring member; ties go to the earliest end, then id) with the size of its template group, then cut at ``cap``."""
        groups: dict[str, list[dict]] = collections.defaultdict(list)
        for b in ranked:
            if classes is not None and self.struct[b["event_id"]]["class"] not in classes:
                continue
            groups[self.template[b["event_id"]]].append(b)
        out = []
        for members in groups.values():
            top = sorted(members, key=lambda b: (-b["score"], self.events[b["event_id"]].get("end") or "", b["event_id"]))[0]
            top = dict(top, n_in_template=len(members), class_=None)
            top["class"] = self.struct[top["event_id"]]["class"]; top["title"] = self.events[top["event_id"]].get("title"); top.pop("class_")
            out.append(top)
        out.sort(key=lambda b: (-b["score"], b["event_id"]))
        return out[:cap]

    def search(self, terms: list[str], cap: int = 60, at: str | None = None, classes: set | None = None) -> list[dict]:
        """Events matching the words of a thesis, read from the open set: exact tag or entity matches weighted by rarity, title substrings at weight 1. Deterministic,
        price-free, collapsed by template. The session states its hedge thesis in words first; this returns the instruments that could express it (V1 §11 A8)."""
        terms = [t.lower().strip() for t in terms if t and t.strip()]
        best: dict[str, dict] = {}
        for i, e in self.events.items():
            if not self.live(e, at):
                continue
            title = (e.get("title") or "").lower()
            sc, hit = 0.0, []
            for t in terms:
                if t in self.tags[i] or t in self.ents[i]:
                    sc += self.tag_idf.get(t, self.ent_idf.get(t, 1.0)) + 1.0; hit.append(t)
                elif t in title:
                    sc += 1.0; hit.append(t)
            if sc > 0:
                best[i] = {"event_id": i, "score": sc, "hops": 0, "via": None, "tags": [], "entities": hit}
        return self._collapse(sorted(best.values(), key=lambda b: (-b["score"], b["event_id"])), cap, classes)

    def stats(self, sample: int = 400) -> dict:
        """Coverage of the graph: classes, how many events have any rare-tag or entity neighbour, and the neighbourhood size distribution on a deterministic sample."""
        cls = collections.Counter(s["class"] for s in self.struct.values())
        ids = sorted(self.events)
        step = max(1, len(ids) // sample)
        sizes = [len(self.edges_from(i)) for i in ids[::step]]
        sizes_sorted = sorted(sizes)
        q = lambda p: sizes_sorted[min(len(sizes_sorted) - 1, int(p * len(sizes_sorted)))] if sizes_sorted else 0
        return {"events": len(self.events), "templates": len(set(self.template.values())), "header_only_out_of_scope": self.headers, "classes": dict(cls), "generic_tags": len(self.generic),
                "sampled": len(sizes), "share_with_a_neighbour": sum(s > 0 for s in sizes) / max(1, len(sizes)), "neighbours_q10_q50_q90": [q(.1), q(.5), q(.9)]}
