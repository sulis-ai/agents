#!/usr/bin/env python3
"""Build FINANCIALS.html — the investor-facing financial summary page.

Usage:
    python3 build_investor_financials.py <MODEL.yaml> <tokens.css> <PITCH.yaml> <output.html>

This is distinct from `build_finance_html.py`:
    - `build_finance_html.py`        → Internal `03-financials/DASHBOARD.html`,
                                       full detail, every metric and chart.
    - `build_investor_financials.py` → Root `FINANCIALS.html`, investor-facing,
                                       focused on the seven or eight figures a
                                       partner actually looks at: ask, runway,
                                       gross margin, NRR, payback, top-line
                                       projection, use of funds, key risks.

The shape mirrors a long-form web page (matching PITCH.html's voice) rather
than a dashboard. Chart.js is loaded from CDN for the single projection chart.
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


def fmt_money(v, currency: str = "USD") -> str:
    if v is None:
        return "—"
    try:
        n = float(v)
    except (TypeError, ValueError):
        return str(v)
    symbol = {"USD": "$", "GBP": "£", "EUR": "€"}.get(currency.upper(), "$")
    if abs(n) >= 1_000_000_000:
        return f"{symbol}{n / 1e9:.1f}B"
    if abs(n) >= 1_000_000:
        return f"{symbol}{n / 1e6:.1f}M"
    if abs(n) >= 1_000:
        return f"{symbol}{n / 1e3:.0f}k"
    return f"{symbol}{n:,.0f}"


def fmt_pct(v) -> str:
    if v is None:
        return "—"
    try:
        n = float(v)
    except (TypeError, ValueError):
        return str(v)
    return f"{n * 100:.0f}%" if abs(n) < 1.5 else f"{n:.0f}%"


def render_kpi(label: str, value: str, note: str = "") -> str:
    note_html = f'<div class="kpi-note">{html.escape(note)}</div>' if note else ""
    return f"""<div class="kpi">
  <div class="kpi-label">{html.escape(label)}</div>
  <div class="kpi-value">{html.escape(value)}</div>
  {note_html}
</div>"""


def build_html(model: dict, tokens_css: str, pitch_meta: dict) -> str:
    company = pitch_meta.get("name") or model.get("company") or "Company"
    stage = pitch_meta.get("stage", "").replace("-", " ").title()
    currency = (model.get("currency") or "USD").upper()

    round_data = model.get("round") or {}
    burn = model.get("burn") or {}
    ue = model.get("unit_economics") or {}
    use_of_funds = model.get("use_of_funds") or []
    risks = model.get("risks") or []
    projections = model.get("projections") or []
    market = model.get("market_sizing") or {}

    # Headline KPIs — the figures a partner asks first.
    kpis = []
    if round_data.get("ask_usd") or round_data.get("ask_gbp") or round_data.get("target_size_usd"):
        ask_val = round_data.get("ask_usd") or round_data.get("ask_gbp") or round_data.get("target_size_usd")
        kpis.append(render_kpi("The ask", fmt_money(ask_val, currency)))
    if burn.get("runway_months") or round_data.get("expected_runway_months"):
        runway = burn.get("runway_months") or round_data.get("expected_runway_months")
        kpis.append(render_kpi("Runway", f"{runway} months", "Cash ÷ trailing-3mo net burn"))
    if ue.get("gross_margin_pct") is not None:
        kpis.append(render_kpi("Gross margin", fmt_pct(ue.get("gross_margin_pct"))))
    if ue.get("nrr_pct") is not None:
        kpis.append(render_kpi("NRR", fmt_pct(ue.get("nrr_pct"))))
    if ue.get("payback_months") is not None:
        kpis.append(render_kpi("CAC payback", f"{ue.get('payback_months')} months"))
    if ue.get("ltv_cac_ratio") is not None:
        kpis.append(render_kpi("LTV : CAC", f"{ue.get('ltv_cac_ratio')}×"))

    kpis_html = "\n".join(kpis)

    # Projection chart data
    proj_labels = [p.get("period", "") for p in projections]
    proj_base = [p.get("revenue_base") for p in projections]
    proj_low = [p.get("revenue_low") for p in projections]
    proj_high = [p.get("revenue_high") for p in projections]

    chart_data = {"labels": proj_labels, "base": proj_base, "low": proj_low, "high": proj_high}
    chart_section = ""
    if proj_labels and any(v is not None for v in proj_base):
        chart_section = f"""<section class="s" id="projection">
  <div class="wrap">
    <div class="eyebrow">02 — Top-line projection</div>
    <h2>Revenue, {len(projections)} periods</h2>
    <p class="lede">Base case, with low/high bands where confidence permits ranges. Underlying inputs traceable to the proof-points dossier.</p>
    <div class="chart-wrap">
      <canvas id="revenueChart" height="120"></canvas>
    </div>
  </div>
</section>"""

    # Use of funds
    uof_rows = ""
    for u in use_of_funds:
        uof_rows += f"""<tr>
  <td>{html.escape(str(u.get('category', '')))}</td>
  <td class="num">{html.escape(fmt_money(u.get('amount_usd') or u.get('amount'), currency))}</td>
  <td>{html.escape(str(u.get('milestone', '')))}</td>
  <td>{html.escape(str(u.get('expected_outcome', '')))}</td>
</tr>"""
    uof_section = ""
    if uof_rows:
        uof_section = f"""<section class="s" id="use-of-funds">
  <div class="wrap">
    <div class="eyebrow">03 — Use of funds</div>
    <h2>Every pound tied to a milestone</h2>
    <table class="data">
      <thead><tr><th>Category</th><th class="num">Amount</th><th>Milestone</th><th>Expected outcome</th></tr></thead>
      <tbody>{uof_rows}</tbody>
    </table>
  </div>
</section>"""

    # Market sizing (compact, just headline figures with attribution)
    market_rows = ""
    for scope_key in ("tam", "sam", "som"):
        scope = market.get(scope_key) or {}
        if not scope:
            continue
        top = scope.get("top_down_usd")
        bottom = scope.get("bottom_up_usd")
        conf = scope.get("confidence", "—")
        market_rows += f"""<tr>
  <td><strong>{scope_key.upper()}</strong></td>
  <td class="num">{html.escape(fmt_money(top, currency))}</td>
  <td class="num">{html.escape(fmt_money(bottom, currency))}</td>
  <td>{html.escape(str(conf))}</td>
</tr>"""
    market_section = ""
    if market_rows:
        market_section = f"""<section class="s" id="market">
  <div class="wrap">
    <div class="eyebrow">04 — Market sizing</div>
    <h2>Top-down and bottom-up, triangulated</h2>
    <table class="data">
      <thead><tr><th>Scope</th><th class="num">Top-down</th><th class="num">Bottom-up</th><th>Confidence</th></tr></thead>
      <tbody>{market_rows}</tbody>
    </table>
  </div>
</section>"""

    # Pre-mortem risks
    risk_rows = ""
    for r in risks:
        risk_rows += f"""<tr>
  <td>{html.escape(str(r.get('reason', '')))}</td>
  <td>{html.escape(str(r.get('likelihood', '')))}</td>
  <td>{html.escape(str(r.get('impact', '')))}</td>
  <td>{html.escape(str(r.get('mitigation', '')))}</td>
</tr>"""
    risk_section = ""
    if risk_rows:
        risk_section = f"""<section class="s" id="risks">
  <div class="wrap">
    <div class="eyebrow">05 — The honest risks</div>
    <h2>If we miss by 50%, here is why</h2>
    <p class="lede">A pre-mortem, conducted before the partner runs one in the meeting.</p>
    <table class="data">
      <thead><tr><th>Risk</th><th>Likelihood</th><th>Impact</th><th>Mitigation</th></tr></thead>
      <tbody>{risk_rows}</tbody>
    </table>
  </div>
</section>"""

    base_css = """
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: var(--font-sans, system-ui, sans-serif);
  color: var(--colour-ink, #1a1a1a);
  background: var(--colour-surface, #ffffff);
  line-height: 1.55;
  font-variant-numeric: tabular-nums;
}
.wrap { max-width: 980px; margin: 0 auto; padding: 0 2rem; }

section.hero {
  padding: 5rem 0 3rem;
  border-bottom: 1px solid var(--colour-surface-alt, #eee);
}
section.hero .wordmark {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--colour-primary, #0066cc);
  margin-bottom: 2rem;
}
section.hero h1 {
  font-size: clamp(1.8rem, 3.6vw, 2.6rem);
  font-weight: 700;
  line-height: 1.15;
  margin: 0 0 0.8rem;
  max-width: 24ch;
}
section.hero .sub {
  font-size: 1.05rem;
  color: var(--colour-ink-muted, #666);
  margin: 0;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1.5rem;
  margin: 3rem 0 0;
  padding: 2rem 0;
  border-top: 1px solid var(--colour-surface-alt, #eee);
  border-bottom: 1px solid var(--colour-surface-alt, #eee);
}
.kpi-label {
  font-size: 0.75rem;
  color: var(--colour-ink-muted, #666);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 0.4rem;
}
.kpi-value { font-size: 1.5rem; font-weight: 700; }
.kpi-note { font-size: 0.75rem; color: var(--colour-ink-muted, #666); margin-top: 0.3rem; }

section.s {
  padding: 4rem 0;
  border-bottom: 1px solid var(--colour-surface-alt, #eee);
  scroll-margin-top: 60px;
}
section.s:last-of-type { border-bottom: 0; }
section.s .eyebrow {
  font-size: 0.75rem;
  color: var(--colour-primary, #0066cc);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 600;
  margin-bottom: 1rem;
}
section.s h2 {
  font-size: clamp(1.5rem, 2.8vw, 2.1rem);
  font-weight: 700;
  margin: 0 0 1.2rem;
  max-width: 28ch;
}
section.s .lede {
  font-size: 1.05rem;
  color: var(--colour-ink-muted, #666);
  max-width: 64ch;
  margin: 0 0 2rem;
}

.chart-wrap {
  padding: 1.5rem;
  border: 1px solid var(--colour-surface-alt, #eee);
  border-radius: 8px;
  background: var(--colour-surface, #fff);
}

table.data {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1rem;
}
table.data th,
table.data td {
  padding: 0.7rem 0.9rem;
  text-align: left;
  border-bottom: 1px solid var(--colour-surface-alt, #eee);
  vertical-align: top;
}
table.data th {
  font-weight: 600;
  color: var(--colour-ink-muted, #666);
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
table.data td.num,
table.data th.num { text-align: right; font-variant-numeric: tabular-nums; }

footer.colophon {
  padding: 3rem 0;
  text-align: center;
  font-size: 0.8rem;
  color: var(--colour-ink-muted, #666);
}
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(str(company))} — Financials</title>
<style>
/* --- Brand tokens (inlined from brand-assets/tokens.css) --- */
{tokens_css}

/* --- Investor-facing financial summary base styles --- */
{base_css}
</style>
</head>
<body>
<section class="hero" id="top">
  <div class="wrap">
    <div class="wordmark">{html.escape(str(company))}</div>
    <h1>The financial case, in plain figures.</h1>
    <p class="sub">{html.escape(stage)} round · {len(projections) or '—'}-period model · every input traceable to a proof-point.</p>
    <div class="kpi-grid">
      {kpis_html}
    </div>
  </div>
</section>

{chart_section}
{uof_section}
{market_section}
{risk_section}

<footer class="colophon">
  <div class="wrap">{html.escape(str(company))} · {html.escape(stage)} · {html.escape(str(pitch_meta.get('date_compiled', pitch_meta.get('updated', ''))))}</div>
</footer>

<script src="{CHARTJS_CDN}"></script>
<script>
const chartData = {json.dumps(chart_data)};
const tokens = {{
  primary: getComputedStyle(document.documentElement).getPropertyValue('--colour-primary').trim() || '#0066cc',
  neutral: getComputedStyle(document.documentElement).getPropertyValue('--colour-neutral').trim() || '#90a4ae',
  inkMuted: getComputedStyle(document.documentElement).getPropertyValue('--colour-ink-muted').trim() || '#666666',
}};
const canvas = document.getElementById('revenueChart');
if (canvas && chartData.labels.length) {{
  Chart.defaults.font.family = getComputedStyle(document.documentElement).getPropertyValue('--font-sans').trim() || 'system-ui';
  Chart.defaults.color = tokens.inkMuted;
  new Chart(canvas, {{
    type: 'line',
    data: {{
      labels: chartData.labels,
      datasets: [
        {{ label: 'Base', data: chartData.base, borderColor: tokens.primary, backgroundColor: tokens.primary, tension: 0.2, borderWidth: 3 }},
        {{ label: 'Low', data: chartData.low, borderColor: tokens.neutral, borderDash: [4, 4], tension: 0.2 }},
        {{ label: 'High', data: chartData.high, borderColor: tokens.neutral, borderDash: [4, 4], tension: 0.2 }}
      ]
    }},
    options: {{
      responsive: true,
      plugins: {{ legend: {{ position: 'bottom' }} }},
      scales: {{
        y: {{
          beginAtZero: true,
          ticks: {{ callback: (v) => '$' + (v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v) }}
        }}
      }}
    }}
  }});
}}
</script>
</body>
</html>
"""


def build(model_path: Path, tokens_css_path: Path, pitch_path: Path, output_path: Path) -> int:
    if not model_path.is_file():
        print(f"ERROR: financial model not found: {model_path}", file=sys.stderr)
        return 1
    if not pitch_path.is_file():
        print(f"ERROR: PITCH.yaml not found: {pitch_path}", file=sys.stderr)
        return 1

    model = yaml.safe_load(model_path.read_text()) or {}
    tokens_css = tokens_css_path.read_text() if tokens_css_path.is_file() else ""
    pitch_meta = yaml.safe_load(pitch_path.read_text()) or {}

    output = build_html(model, tokens_css, pitch_meta)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output)
    print(f"Wrote {output_path} (investor-facing financial summary)")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        print(__doc__, file=sys.stderr)
        return 1
    return build(Path(argv[1]), Path(argv[2]), Path(argv[3]), Path(argv[4]))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
