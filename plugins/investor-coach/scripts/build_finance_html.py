#!/usr/bin/env python3
"""Build financial-summary.html (Chart.js dashboard) from financial-model.yaml.

Usage:
    python3 build_finance_html.py <financial-model.yaml> <tokens.css> <output.html>

Renders a single self-contained HTML file with:
    - Header (company, stage, ask, runway)
    - Revenue projection chart (low/base/high band where present)
    - Unit economics summary cards
    - Use of funds table (milestone-tied)
    - Cohort retention chart (if data present)
    - Sensitivity grid (if enabled)
    - Risks (pre-mortem)
    - Source footer

Chart.js is loaded from CDN at view time. Brand tokens are inlined.
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


CHARTJS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"


def fmt_money(v) -> str:
    if v is None:
        return "—"
    try:
        n = float(v)
    except (TypeError, ValueError):
        return str(v)
    if abs(n) >= 1_000_000_000:
        return f"${n / 1e9:.1f}B"
    if abs(n) >= 1_000_000:
        return f"${n / 1e6:.1f}M"
    if abs(n) >= 1_000:
        return f"${n / 1e3:.0f}k"
    return f"${n:,.0f}"


def fmt_pct(v) -> str:
    if v is None:
        return "—"
    try:
        n = float(v)
    except (TypeError, ValueError):
        return str(v)
    return f"{n * 100:.1f}%" if abs(n) < 1.5 else f"{n:.1f}%"


def build_html(model: dict, tokens_css: str) -> str:
    company = model.get("company", "Company")
    stage = model.get("stage", "")
    round_data = model.get("round", {}) or {}
    burn = model.get("burn", {}) or {}
    ue = model.get("unit_economics", {}) or {}
    market = model.get("market_sizing", {}) or {}
    projections = model.get("projections", []) or []
    use_of_funds = model.get("use_of_funds", []) or []
    cohorts = model.get("cohorts", {}) or {}
    sensitivity = model.get("sensitivity", {}) or {}
    risks = model.get("risks", []) or []

    # Projection data for Chart.js
    proj_labels = [p.get("period", "") for p in projections]
    proj_base = [p.get("revenue_base") for p in projections]
    proj_low = [p.get("revenue_low") for p in projections]
    proj_high = [p.get("revenue_high") for p in projections]

    chart_data = {
        "labels": proj_labels,
        "base": proj_base,
        "low": proj_low,
        "high": proj_high,
    }

    # Cohort data
    cohort_rows = cohorts.get("cohort_data", []) or []
    cohort_data = {
        "labels": [c.get("cohort", "") for c in cohort_rows],
        "m6": [c.get("retained_m6") for c in cohort_rows],
        "m12": [c.get("retained_m12") for c in cohort_rows],
        "acquired": [c.get("acquired") for c in cohort_rows],
    }

    # KPI cards
    cards = [
        ("Stage", html.escape(stage.upper())),
        ("Ask", fmt_money(round_data.get("ask_usd"))),
        ("Runway", f"{burn.get('runway_months', '—')} mo"),
        ("Net burn / mo", fmt_money(burn.get("current_net_burn_usd_monthly"))),
        ("Gross margin", fmt_pct(ue.get("gross_margin_pct"))),
        ("LTV : CAC", str(ue.get("ltv_cac_ratio") or "—")),
        ("Payback", f"{ue.get('payback_months', '—')} mo"),
        ("NRR", fmt_pct(ue.get("nrr_pct"))),
    ]
    cards_html = "\n".join(
        f"<div class='card'><div class='card-label'>{html.escape(label)}</div><div class='card-value'>{html.escape(str(value))}</div></div>"
        for label, value in cards
    )

    # Market sizing
    market_html = "<table><thead><tr><th>Scope</th><th>Top-down</th><th>Bottom-up</th><th>Confidence</th></tr></thead><tbody>"
    for scope_key in ("tam", "sam", "som"):
        scope = market.get(scope_key, {}) or {}
        market_html += (
            f"<tr><td>{scope_key.upper()}</td>"
            f"<td>{fmt_money(scope.get('top_down_usd'))}</td>"
            f"<td>{fmt_money(scope.get('bottom_up_usd'))}</td>"
            f"<td>{html.escape(str(scope.get('confidence') or '—'))}</td></tr>"
        )
    market_html += "</tbody></table>"

    # Use of funds
    uof_html = (
        "<table><thead><tr><th>Category</th><th>Amount</th><th>Milestone</th><th>Outcome</th></tr></thead><tbody>"
    )
    for u in use_of_funds:
        uof_html += (
            f"<tr><td>{html.escape(str(u.get('category', '')))}</td>"
            f"<td>{fmt_money(u.get('amount_usd'))}</td>"
            f"<td>{html.escape(str(u.get('milestone', '')))}</td>"
            f"<td>{html.escape(str(u.get('expected_outcome', '')))}</td></tr>"
        )
    uof_html += "</tbody></table>"

    # Risks
    risks_html = (
        "<table><thead><tr><th>Risk</th><th>Likelihood</th><th>Impact</th><th>Mitigation</th></tr></thead><tbody>"
    )
    for r in risks:
        risks_html += (
            f"<tr><td>{html.escape(str(r.get('reason', '')))}</td>"
            f"<td>{html.escape(str(r.get('likelihood', '')))}</td>"
            f"<td>{html.escape(str(r.get('impact', '')))}</td>"
            f"<td>{html.escape(str(r.get('mitigation', '')))}</td></tr>"
        )
    risks_html += "</tbody></table>"

    # Sensitivity
    sensitivity_html = ""
    if sensitivity.get("enabled"):
        sensitivity_html = "<h3>Sensitivity outcomes</h3><table><thead><tr><th>Scenario</th><th>Runway</th><th>ARR @ 12mo</th></tr></thead><tbody>"
        for o in sensitivity.get("outcomes", []) or []:
            sensitivity_html += (
                f"<tr><td>{html.escape(str(o.get('scenario', '')))}</td>"
                f"<td>{o.get('runway_months', '—')} mo</td>"
                f"<td>{fmt_money(o.get('arr_12mo_usd'))}</td></tr>"
            )
        sensitivity_html += "</tbody></table>"

    cohort_section = ""
    if cohort_rows:
        cohort_section = """
<section>
  <h2>Cohort retention</h2>
  <canvas id="cohortChart" height="120"></canvas>
</section>
"""

    base_css = """
:root {
  --colour-ink: #1a1a1a;
  --colour-ink-muted: #666;
  --colour-surface: #ffffff;
  --colour-surface-alt: #f5f5f5;
  --colour-primary: #0066cc;
  --colour-positive: #2e7d32;
  --colour-negative: #c62828;
  --colour-neutral: #90a4ae;
  --font-sans: system-ui, -apple-system, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  --font-serif: Georgia, serif;
}
* { box-sizing: border-box; }
body { font-family: var(--font-sans); color: var(--colour-ink); background: var(--colour-surface); margin: 0; line-height: 1.5; }
.container { max-width: 1200px; margin: 0 auto; padding: 3rem 2rem; }
h1 { font-size: 2.4rem; margin: 0 0 0.4rem; }
h2 { font-size: 1.4rem; margin: 3rem 0 1rem; color: var(--colour-ink); }
h3 { font-size: 1.1rem; margin: 1.5rem 0 0.8rem; }
.stage-line { color: var(--colour-ink-muted); margin-bottom: 2rem; }
.cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem; }
.card { padding: 1rem; border: 1px solid var(--colour-surface-alt); border-radius: 8px; background: var(--colour-surface); }
.card-label { font-size: 0.8rem; color: var(--colour-ink-muted); text-transform: uppercase; letter-spacing: 0.05em; }
.card-value { font-size: 1.4rem; font-weight: 700; margin-top: 0.3rem; font-variant-numeric: tabular-nums; }
section { margin-bottom: 2.5rem; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 0.6rem 0.8rem; text-align: left; border-bottom: 1px solid var(--colour-surface-alt); vertical-align: top; }
th { font-weight: 600; color: var(--colour-ink-muted); font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.04em; }
td { font-variant-numeric: tabular-nums; }
footer { margin-top: 4rem; padding-top: 2rem; border-top: 1px solid var(--colour-surface-alt); color: var(--colour-ink-muted); font-size: 0.85rem; }
@media (max-width: 800px) { .cards { grid-template-columns: repeat(2, 1fr); } }
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(company)} — Financial Summary</title>
<style>
/* --- Brand tokens (from brand-assets/tokens.css) --- */
{tokens_css}
/* --- Dashboard base styles --- */
{base_css}
</style>
</head>
<body>
<div class="container">
  <h1>{html.escape(company)}</h1>
  <div class="stage-line">Stage: <strong>{html.escape(stage)}</strong> · Horizon: {model.get("horizon_months", "—")} months</div>

  <section>
    <h2>Headline</h2>
    <div class="cards">
{cards_html}
    </div>
  </section>

  <section>
    <h2>Revenue projection</h2>
    <canvas id="revenueChart" height="120"></canvas>
  </section>

  <section>
    <h2>Market sizing</h2>
    {market_html}
  </section>

  <section>
    <h2>Use of funds</h2>
    {uof_html}
  </section>

  {cohort_section}

  <section>
    <h2>Pre-mortem</h2>
    {risks_html}
  </section>

  {('<section>' + sensitivity_html + '</section>') if sensitivity_html else ''}

  <footer>
    Generated by <code>investor-coach</code> — Investor Deck Coach. Every input in this dashboard
    is sourced from <code>financial-model.yaml</code> and grounded in proof-points in
    <code>proof-points/</code>.
  </footer>
</div>

<script src="{CHARTJS_CDN}"></script>
<script>
const chartData = {json.dumps(chart_data)};
const cohortData = {json.dumps(cohort_data)};
const tokens = {{
  primary: getComputedStyle(document.documentElement).getPropertyValue('--colour-primary').trim() || '#0066cc',
  neutral: getComputedStyle(document.documentElement).getPropertyValue('--colour-neutral').trim() || '#90a4ae',
  positive: getComputedStyle(document.documentElement).getPropertyValue('--colour-positive').trim() || '#2e7d32',
  ink: getComputedStyle(document.documentElement).getPropertyValue('--colour-ink').trim() || '#1a1a1a',
  inkMuted: getComputedStyle(document.documentElement).getPropertyValue('--colour-ink-muted').trim() || '#666666',
}};

Chart.defaults.font.family = getComputedStyle(document.documentElement).getPropertyValue('--font-sans').trim() || 'system-ui';
Chart.defaults.color = tokens.inkMuted;

new Chart(document.getElementById('revenueChart'), {{
  type: 'line',
  data: {{
    labels: chartData.labels,
    datasets: [
      {{ label: 'Revenue (base)', data: chartData.base, borderColor: tokens.primary, backgroundColor: tokens.primary, tension: 0.2 }},
      {{ label: 'Revenue (low)', data: chartData.low, borderColor: tokens.neutral, borderDash: [4,4], tension: 0.2 }},
      {{ label: 'Revenue (high)', data: chartData.high, borderColor: tokens.neutral, borderDash: [4,4], tension: 0.2 }}
    ]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ position: 'bottom' }} }},
    scales: {{
      y: {{ beginAtZero: true, ticks: {{ callback: v => '$' + (v >= 1000 ? (v/1000).toFixed(0) + 'k' : v) }} }}
    }}
  }}
}});

if (document.getElementById('cohortChart') && cohortData.labels.length) {{
  new Chart(document.getElementById('cohortChart'), {{
    type: 'bar',
    data: {{
      labels: cohortData.labels,
      datasets: [
        {{ label: 'Retained at M+6', data: cohortData.m6, backgroundColor: tokens.primary }},
        {{ label: 'Retained at M+12', data: cohortData.m12, backgroundColor: tokens.neutral }}
      ]
    }},
    options: {{
      responsive: true,
      plugins: {{ legend: {{ position: 'bottom' }} }},
      scales: {{ y: {{ beginAtZero: true }} }}
    }}
  }});
}}
</script>
</body>
</html>
"""


def build(model_path: Path, tokens_css_path: Path, output_path: Path) -> int:
    if not model_path.is_file():
        print(f"ERROR: model not found: {model_path}", file=sys.stderr)
        return 1
    model = yaml.safe_load(model_path.read_text()) or {}
    tokens_css = tokens_css_path.read_text() if tokens_css_path.is_file() else ""
    output = build_html(model, tokens_css)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output)
    print(f"Wrote {output_path}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__, file=sys.stderr)
        return 1
    return build(Path(argv[1]), Path(argv[2]), Path(argv[3]))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
