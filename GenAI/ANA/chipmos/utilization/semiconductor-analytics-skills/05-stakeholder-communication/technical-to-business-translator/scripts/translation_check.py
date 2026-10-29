"""
Checks that a plain-language translation keeps the meaning of the technical statement.

Per technical -> plain pair
  * numbers: every number in the plain version comes from the technical one (rounded, or a percentage
    restated as "N of every 100"); none is invented; at least one is kept; the technical numbers trace to the
    analysis document (a declared `derived-numbers` comment covers sums)
  * caveats: lower bound, range, hypothesis, OEE not available, excluded readings and "noise" in the technical
    statement must reappear in plain words
  * positions: a direction word (top / bottom / left / right) or "rows a to b" next to position numbers must
    match the handler grid (highest row on top, column 1 on the left)
  * language: no jargon beyond the persona's allowance (engineer / manager / customer)
  * readability: sentence length and jargon density (`readability_scorer.py`)

Usage:
    python translation_check.py             # the filled translations and the pattern library
"""

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "04-data-storytelling-visualization/executive-summary-generator/scripts"))
import contactor_io as cio  # noqa: E402
import deferral  # noqa: E402
import exec_summary_check as esc  # noqa: E402
import jargon_detector  # noqa: E402
import readability_scorer  # noqa: E402

BASE = HERE.parents[1]
TRANSLATIONS = BASE / "assets" / "translations_sep_oct_2026.md"
LIBRARY = BASE / "references" / "translation_pattern_library.md"
PERSONA_ALLOW = {
    "engineer": {"oee", "site", "cluster", "closed site", "2x2", "block alignment", "availability", "lower bound", "chronic", "near-full", "read failure", "assumption id"},
    "manager": {"oee"},
    "customer": set(),
}
CAVEATS = [
    ("lower bound", r"lower bound|at least|never below|under-?report", r"at least|minimum|could be higher|may be higher|slightly higher|as low as|might be higher"),
    ("uncertainty range", r"plausible range|\brange\b|interval", r"between|range|plausibly|as low as|roughly"),
    ("hypothesis", r"hypothes|not confirmed|unconfirmed", r"not confirmed|hypothesis|suggests|may be|might|could be|not proven|not established|unknown"),
    ("OEE not available", r"oee[^.]{0,60}(blocked|cannot|not yet|until)|blocked[^.]{0,40}oee", r"not yet|cannot|can't|do not have|don't have|no data"),
    ("excluded readings", r"excluded|dropped|left out|unreadable|failed read", r"left out|not counted|excluded|unreadable|failed|set aside"),
    ("noise or chance", r"noise|by chance|cannot be told apart", r"noise|chance|normal swing|should not be read as real|not read as real|normal"),
]


# ---------- grid geometry ----------
def site_groups(technical: str) -> list[set[int]]:
    return [{int(x) for x in m.group(0).split("/")} for m in re.finditer(r"\b\d{1,3}(?:/\d{1,3})+\b", technical)]


def region(sites: set[int]) -> dict:
    """Where on the handler grid a set of sites is (highest row on top, column 1 on the left)."""
    rc = [cio.site_row_col(s) for s in sites]
    rows, cols = [r for r, _ in rc], [c for _, c in rc]
    rear = max(sites) > cio.SITES_PER_SIDE
    local = [r - 16 if rear else r for r in rows]
    mean_row, mean_col = sum(local) / len(local), sum(cols) / len(cols)
    return {"rows": (min(rows), max(rows)), "vertical": "top" if mean_row >= 11 else "bottom" if mean_row <= 6 else "middle",
            "horizontal": "right" if mean_col >= 11 else "left" if mean_col <= 6 else "middle"}


def check_positions(technical: str, plain: str) -> str | None:
    known = set().union(*site_groups(technical)) if site_groups(technical) else set()
    if not known:
        return None
    problems = []
    for clause in re.split(r"[;]|(?<!\d)\.(?!\d)", plain):
        sites = {int(x) for x in re.findall(r"(?<![\d.])\d{1,3}(?![\d%]|\.\d)", clause) if int(x) in known}
        if len(sites) < 2:
            continue
        reg = region(sites)
        low = clause.lower()
        for word, want in (("top", "top"), ("upper", "top"), ("bottom", "bottom"), ("lower", "bottom")):
            if re.search(rf"\b{word}\b", low) and reg["vertical"] != want:
                problems.append(f"'{word}' for positions {sorted(sites)[:3]}... which are {reg['vertical']} (rows {reg['rows'][0]}-{reg['rows'][1]})")
        for word in ("left", "right"):
            if re.search(rf"\b{word}\b", low) and reg["horizontal"] != word:
                problems.append(f"'{word}' for positions {sorted(sites)[:3]}... which are {reg['horizontal']}")
        m = re.search(r"rows?\s+(\d+)\s*(?:to|and|-)\s*(\d+)", low)
        if m and (int(m.group(1)), int(m.group(2))) != reg["rows"]:
            problems.append(f"rows {m.group(1)}-{m.group(2)} but the positions are in rows {reg['rows'][0]}-{reg['rows'][1]}")
    return "; ".join(problems) or None


# ---------- numbers, caveats, language ----------
def check_numbers(technical: str, plain: str) -> str | None:
    t = [(v, d) for _, v, d in esc.numbers(technical)]
    kept, invented = 0, []
    for tok, val, dec in esc.numbers(plain):
        ok = any(esc._round(v, dec) == esc._round(val, dec) for v, _ in t)
        if not ok and tok.endswith("%"):
            ok = any(esc._round(100 - v, dec) == esc._round(val, dec) for v, _ in t)
        kept += ok
        if not ok:
            invented.append(tok)
    for m in re.finditer(r"(\d+)\s+(?:of every|in every|out of every)\s+100", plain.lower()):
        k = int(m.group(1))
        if any(esc._round(100 - v, 0) == k or esc._round(v, 0) == k for v, _ in t):
            kept += 1
        else:
            invented.append(f"{k} of every 100")
    t_ints = {int(x) for x in re.findall(r"(?<![\d.])\d+(?![\d%]|\.\d)", technical)}
    kept += sum(1 for x in re.findall(r"(?<![\d.])\d+(?![\d%]|\.\d)", plain) if int(x) in t_ints)  # whole numbers carried over
    if invented:
        return f"not in the technical statement: {', '.join(invented)}"
    if t and kept == 0:
        return "keeps none of the technical numbers"
    return None


def check_caveats(technical: str, plain: str) -> str | None:
    lost = [name for name, trig, ok in CAVEATS if re.search(trig, technical.lower()) and not re.search(ok, plain.lower())]
    return f"caveat lost: {', '.join(lost)}" if lost else None


def check_pair(technical: str, plain: str, persona: str, analysis: str | None = None, derived: dict | None = None) -> list[tuple[str, str, str]]:
    res = []
    add = lambda name, err: res.append((name, "FAIL" if err else "PASS", err or ""))
    if analysis is not None:
        bad = esc.untraceable(technical, analysis, derived or {})
        add("technical numbers trace to the analysis document", f"not found: {', '.join(bad)}" if bad else None)
    add("numbers kept, none invented", check_numbers(technical, plain))
    add("caveats kept", check_caveats(technical, plain))
    add("positions described correctly", check_positions(technical, plain))
    allow = PERSONA_ALLOW.get(persona, set())
    hits = [f"{t} x{n}" for t, n, _ in jargon_detector.detect(plain) if t not in allow]
    add(f"plain language for the {persona} persona", f"jargon: {', '.join(hits)}" if hits else None)
    r = readability_scorer.score(plain, allow)
    add("readable", f"{r['verdict']} (avg {r['avg_words_per_sentence']}, jargon {r['jargon_per_100_words']}/100 words)" if r["verdict"] != "OK" else None)
    money = deferral.check(plain)
    add("no money or throughput figures while impact is deferred", ", ".join(money[:2]) if money else None)
    return res


# ---------- files ----------
def rows_of(section_text: str) -> list[tuple[str, str]]:
    rows = [l.strip() for l in section_text.splitlines() if l.strip().startswith("|")]
    rows = [r for r in rows if not re.match(r"^\|[\s:|-]+\|$", r)][1:]
    out = []
    for r in rows:
        cells = [c.strip() for c in r.strip("|").split("|")]
        if len(cells) >= 2 and "[REQUIRED" not in cells[0]:
            out.append((cells[0].strip('"'), cells[1].strip('"')))
    return out


def parse_translations(text: str) -> list[tuple[str, str, str]]:
    out = []
    for m in re.finditer(r"^## Persona:\s*(\w+)[^\n]*\n(.*?)(?=^## |\Z)", text, re.DOTALL | re.MULTILINE):
        out += [(m.group(1).lower(), t, p) for t, p in rows_of(m.group(2))]
    return out


def check_text(text: str, analysis: str, default_persona: str | None = None) -> list[tuple[str, str, str]]:
    """All pairs in a translations file (persona sections) or a library table (default persona)."""
    body = esc.strip_comments(text)
    der = esc.derived(text)
    pairs = parse_translations(body) if default_persona is None else [(default_persona, t, p) for t, p in rows_of(body)]
    res = []
    if not pairs:
        return [("translations found", "FAIL", "no technical -> plain table rows")]
    for i, (persona, tech, plain) in enumerate(pairs, 1):
        for name, status, detail in check_pair(tech, plain, persona, analysis, der):
            res.append((f"[{persona} #{i}] {name}", status, detail))
    return res


def main():
    argparse.ArgumentParser(description="Translation checker").parse_args()
    analysis = esc.DEFAULT_ANALYSIS.read_text(encoding="utf-8")
    res = check_text(TRANSLATIONS.read_text(encoding="utf-8"), analysis) + \
        [(f"[library] {n}", s, d) for n, s, d in check_text(LIBRARY.read_text(encoding="utf-8"), analysis, default_persona="manager")]
    for name, status, detail in res:
        if status != "PASS":
            print(f"[{status:4s}] {name:70s} {detail}")
    fails = sum(1 for _, s, _ in res if s == "FAIL")
    print(f"{len(res)} checks over the translations and the library: {fails} FAIL")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
