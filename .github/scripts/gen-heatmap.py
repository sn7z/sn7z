#!/usr/bin/env python3
"""Generate contribution heatmap SVGs (dark + light) from real GitHub data.

Data source: https://github-contributions-api.jogruber.de/v4/<user>
Writes assets/heatmap-dark.svg and assets/heatmap-light.svg relative to repo root.
Run locally with: python .github/scripts/gen-heatmap.py
"""
import json
import time
import urllib.request
from datetime import date, timedelta
from pathlib import Path

USER = "sn7z"
API = "https://github-contributions-api.jogruber.de/v4/" + USER
WEEKS = 53                                     # last ~1 year
CELL = 13; GAP = 4; PAD = 24; LABEL_H = 26      # geometry

DARK = {
    "bg": "#0d1210", "stroke": "rgba(255,255,255,0.13)",
    "levels": ["#141d18", "#0a4636", "#059669", "#10b981", "#34d399"],
    "cell_line": "rgba(255,255,255,0.05)",
    "ink": "#ffffff", "accent": "#34d399", "muted": "#9ca3af",
    "grad0": "#34d399", "grad1": "#fbbf24",
}
LIGHT = {
    "bg": "#fcfcf9", "stroke": "rgba(16,72,58,0.2)",
    "levels": ["#e8e6da", "#a7f3d0", "#34d399", "#059669", "#046c50"],
    "cell_line": "rgba(16,72,58,0.08)",
    "ink": "#12302a", "accent": "#0a7f5e", "muted": "#476559",
    "grad0": "#0a7f5e", "grad1": "#d97706",
}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "readme-heatmap/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def build_grid(data):
    days = sorted(data["contributions"], key=lambda d: d["date"])
    end = min(date.fromisoformat(days[-1]["date"]), date.today())
    start = end - timedelta(days=WEEKS * 7 - 1)
    keep = [d for d in days if d["date"] >= start.isoformat()]
    by_date = {d["date"]: d for d in keep}
    first = date.fromisoformat(keep[0]["date"])
    lead = (first.weekday() + 1) % 7              # Sunday=0 column offset
    cur = first - timedelta(days=lead)
    weeks = []
    while cur <= end:
        col = []
        for _ in range(7):
            iso = cur.isoformat()
            col.append(by_date.get(iso))
            cur += timedelta(days=1)
        weeks.append(col)
    return weeks


def render(p, weeks, meta):
    nweek = len(weeks)
    w = PAD * 2 + nweek * (CELL + GAP) - GAP
    h = PAD + LABEL_H + 7 * (CELL + GAP) - GAP + 34
    out = []
    uid = "hm" + p["accent"].lstrip("#")
    out.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="GitHub contribution heatmap for %s">' % (w, h, w, h, USER))
    out.append("  <title>Syed Numaan — GitHub Contribution Heatmap</title>")
    out.append("  <defs>")
    out.append('    <linearGradient id="%s" x1="0" y1="0" x2="1" y2="0">' % uid)
    out.append('      <stop offset="0" stop-color="%s"/>' % p["grad0"])
    out.append('      <stop offset="1" stop-color="%s"/>' % p["grad1"])
    out.append("    </linearGradient>")
    out.append("  </defs>")
    out.append('  <rect width="%d" height="%d" rx="14" fill="%s"/>' % (w, h, p["bg"]))
    out.append('  <rect x="0.5" y="0.5" width="%d" height="%d" rx="13.5" fill="none" stroke="%s" stroke-width="1"/>' % (w - 1, h - 1, p["stroke"]))
    out.append('  <text x="%d" y="%d" font-family="Segoe UI, Inter, Arial, sans-serif" font-size="15" font-weight="700" letter-spacing="2" fill="%s">CONTRIBUTION HEATMAP <tspan fill="%s">— LAST 12 MONTHS</tspan></text>' % (PAD, PAD + 12, p["ink"], p["accent"]))
    out.append('  <text x="%d" y="%d" text-anchor="end" font-family="Segoe UI, Inter, Arial, sans-serif" font-size="12" font-weight="600" fill="%s">%s</text>' % (w - PAD, PAD + 12, p["muted"], meta["totals"]))

    x0, y0 = PAD, PAD + LABEL_H
    prev_month = None
    last_label_x = -100
    for i, week in enumerate(weeks):
        first_day = next((d for d in week if d is not None), None)
        if first_day is None:
            continue
        d = date.fromisoformat(first_day["date"])
        if d.month != prev_month and (i == 0 or i - last_label_x >= 3):
            out.append('  <text x="%d" y="%d" font-family="Segoe UI, Inter, Arial, sans-serif" font-size="10" fill="%s">%s</text>' % (x0 + i * (CELL + GAP), y0 - 8, p["muted"], MONTHS[d.month - 1]))
            prev_month = d.month
            last_label_x = i

    out.append('  <g shape-rendering="crispEdges">')
    for i, week in enumerate(weeks):
        for j, day in enumerate(week):
            x = x0 + i * (CELL + GAP)
            y = y0 + j * (CELL + GAP)
            if day is None:
                out.append('    <rect x="%d" y="%d" width="%d" height="%d" rx="3" fill="none"/>' % (x, y, CELL, CELL))
                continue
            lvl = max(0, min(4, int(day.get("level", 0))))
            tip = "%s — %d contribution%s" % (day["date"], day["count"], "" if day["count"] == 1 else "s")
            out.append('    <rect x="%d" y="%d" width="%d" height="%d" rx="3" fill="%s"><title>%s</title></rect>' % (x, y, CELL, CELL, p["levels"][lvl], tip))
    out.append("  </g>")

    ly = y0 + 7 * (CELL + GAP) + 14
    out.append('  <text x="%d" y="%d" font-family="Segoe UI, Inter, Arial, sans-serif" font-size="10" fill="%s">less</text>' % (x0, ly, p["muted"]))
    for li in range(5):
        out.append('  <rect x="%d" y="%d" width="%d" height="%d" rx="3" fill="%s" stroke="%s"/>' % (x0 + 34 + li * (CELL + 4), ly - 9, CELL, CELL, p["levels"][li], p["cell_line"]))
    out.append('  <text x="%d" y="%d" font-family="Segoe UI, Inter, Arial, sans-serif" font-size="10" fill="%s">more</text>' % (x0 + 34 + 5 * (CELL + 4) + 6, ly, p["muted"]))
    out.append('  <text x="%d" y="%d" text-anchor="end" font-family="Segoe UI, Inter, Arial, sans-serif" font-size="10" font-style="italic" fill="%s">real GitHub data · generated %s</text>' % (w - PAD, ly, p["muted"], meta["stamp"]))
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    data = fetch(API)
    weeks = build_grid(data)
    totals = data.get("total", {})
    years = sorted(int(y) for y in totals)
    parts = ["%s: %s" % (y, totals[str(y)]) for y in years[-2:]]
    meta = {"totals": " · ".join(parts), "stamp": time.strftime("%d %b %Y")}
    root = Path(__file__).resolve().parents[2] / "assets"
    (root / "heatmap-dark.svg").write_text(render(DARK, weeks, meta), encoding="utf-8")
    (root / "heatmap-light.svg").write_text(render(LIGHT, weeks, meta), encoding="utf-8")
    print("weeks=%d %s" % (len(weeks), meta["totals"]))


if __name__ == "__main__":
    main()
