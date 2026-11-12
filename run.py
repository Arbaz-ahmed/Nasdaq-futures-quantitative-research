"""Run the complete NQ research project on validated historical CSV input."""
import argparse
import html
import json
import shutil
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.offline import plot

from analysis import DATA_SOURCE, Config, load_prices, summarize, data_quality
from report import create_report

NAVY = '#101a2e'
TEAL = '#22b8a9'
GOLD = '#f2bd68'
WHITE = '#f0f4fa'


def _fmt(value, fmt='.2f', suffix=''):
    return 'N/A' if value is None or not np.isfinite(value) else f'{value:{fmt}}{suffix}'


def save_dashboard(d: pd.DataFrame, m: dict, output_path: Path, cfg: Config) -> None:
    oos = d.loc[d.index >= cfg.test_start].copy()
    oos['strategy_rebased'] = cfg.initial_capital + oos['strategy_net_usd'].cumsum()
    oos['benchmark_rebased'] = cfg.initial_capital + oos['benchmark_net_usd'].cumsum()
    peak = np.maximum.accumulate(np.r_[cfg.initial_capital, oos['strategy_rebased'].values])[1:]
    oos['drawdown'] = 100*(oos['strategy_rebased']/peak-1)
    month = oos['strategy_net_usd'].resample('MS').sum()
    fig = make_subplots(rows=2, cols=2, subplot_titles=(
        'Out-of-sample account equity (USD)', 'Strategy drawdown (%)',
        'Rolling 20-session close-to-close volatility', 'Monthly strategy net P&L (USD)'),
        vertical_spacing=.15, horizontal_spacing=.1)
    fig.add_trace(go.Scatter(x=oos.index, y=oos['strategy_rebased'], name='20/100 trend strategy',
                             line=dict(color=TEAL, width=2.6)), row=1, col=1)
    fig.add_trace(go.Scatter(x=oos.index, y=oos['benchmark_rebased'], name='Long one NQ',
                             line=dict(color=GOLD, width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=oos.index, y=oos['drawdown'], name='Drawdown',
                             fill='tozeroy', line=dict(color='#ec8391')), row=1, col=2)
    fig.add_trace(go.Scatter(x=oos.index, y=oos['ann_vol_20d']*100, name='Annualised realised vol',
                             line=dict(color='#83a8f4')), row=2, col=1)
    fig.add_trace(go.Bar(x=month.index, y=month, name='Monthly P&L',
                         marker_color=[TEAL if z >= 0 else '#ec8391' for z in month]), row=2, col=2)
    fig.update_layout(template='plotly_dark', paper_bgcolor=NAVY, plot_bgcolor=NAVY,
                      font=dict(family='Arial, sans-serif', color=WHITE, size=12),
                      height=850, legend=dict(orientation='h', y=-.1), margin=dict(t=75,b=65,l=45,r=35),
                      hovermode='x unified', showlegend=True)
    fig.update_xaxes(showgrid=True, gridcolor='#233149')
    fig.update_yaxes(showgrid=True, gridcolor='#233149', zerolinecolor='#38455d')
    o = m['out_of_sample_strategy']; b = m['out_of_sample_benchmark']; stats = m['statistics']
    cards = [
        ('OOS NET P&L', f"${_fmt(o['total_pnl_usd'], ',.0f')}", f"Long-NQ benchmark: ${_fmt(b['total_pnl_usd'], ',.0f')}"),
        ('OOS RETURN ON START CAPITAL', _fmt(o['return_pct'], '.1f', '%'), 'Fixed one-contract exposure'),
        ('OOS SHARPE', _fmt(o['sharpe']), '0% risk-free rate; fixed-capital daily returns'),
        ('OOS MAX DRAWDOWN', _fmt(o['max_drawdown_pct'], '.1f', '%'), 'Based on simulated cash equity'),
        ('CLOSED-TRADE WIN RATE', _fmt(m['out_of_sample_closed_trade_win_rate_pct'], '.1f', '%'), f"{m['out_of_sample_closed_trade_count']} complete OOS trades"),
    ]
    card_html = ''.join('<div class="metric"><div class="label">%s</div><div class="value">%s</div><div class="hint">%s</div></div>' % tuple(map(html.escape, x)) for x in cards)
    costrows = ''.join('<tr><td>$%s</td><td>%s</td><td>%s</td></tr>' % (html.escape(k),
        _fmt(v['total_pnl_usd'], ',.0f'), _fmt(v['sharpe'])) for k,v in m['transaction_cost_sensitivity'].items())
    plt = plot(fig, output_type='div', include_plotlyjs=True, config={'responsive':True,'displaylogo':False})
    source = html.escape(m['data']['source_url'], quote=True)
    doc = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>NQ Futures | Market Research & Strategy Backtest</title><style>
    body{{margin:0;background:#0b1220;color:#edf3fc;font-family:Inter,Segoe UI,Arial,sans-serif}}
    header,main{{max-width:1400px;margin:auto;padding:26px 32px}}header{{padding-top:48px}}.kicker{{font-size:11px;color:#65ddc9;letter-spacing:.18em;font-weight:800}}
    h1{{font-size:35px;letter-spacing:-.04em;margin:12px 0 8px}}p{{color:#abb8c9;line-height:1.7}}.metrics{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:24px 0}}
    .metric,.panel{{border:1px solid #2a374c;border-radius:15px;background:#111b2e;padding:19px}}
    .label{{color:#8b9ab0;font-size:10px;letter-spacing:.12em;font-weight:700}}.value{{font-size:24px;font-weight:800;letter-spacing:-.04em;margin:12px 0 5px}}.hint{{color:#8799ae;font-size:11px;line-height:1.45}}
    h2{{font-size:19px;margin:10px 0 16px}}.cols{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{padding:12px;border-bottom:1px solid #263249;text-align:left}}th{{color:#9eacc0}}strong{{color:#e5ecf7}}.foot{{font-size:12px}}
    @media(max-width:850px){{.metrics{{grid-template-columns:repeat(2,1fr)}}.cols{{grid-template-columns:1fr}}header,main{{padding-left:17px;padding-right:17px}}}}
    </style></head><body><header><div class="kicker">QUANTITATIVE RESEARCH / EDUCATIONAL BACKTEST</div>
    <h1>NASDAQ-100 futures <span style="color:#65ddc9">/</span> market strategy lab</h1>
    <p>E-mini NQ &nbsp;|&nbsp; 20 / 100 SMA trend following &nbsp;|&nbsp; historical data: {m['data']['start']} – {m['data']['end']} &nbsp;|&nbsp; out-of-sample: 2023 onward</p>
    <div class="metrics">{card_html}</div></header><main>
    <section class="panel" style="margin-bottom:20px"><h2>Research conclusion: benchmark outperformed</h2>
    <p>The strategy generated a positive modelled out-of-sample net P&amp;L of <strong>${o['total_pnl_usd']:,.0f}</strong>, but the always-long one-contract baseline earned <strong>${b['total_pnl_usd']:,.0f}</strong>. The strategy lagged by <strong>${b['total_pnl_usd']-o['total_pnl_usd']:,.0f}</strong>. Its Sharpe ({_fmt(o['sharpe'])}) was below the benchmark ({_fmt(b['sharpe'])}), and its max drawdown ({_fmt(o['max_drawdown_pct'],'.1f','%')}) was deeper. These are simulated cash P&amp;L figures, not realised returns or a validated investable edge.</p></section>
    <section class="panel">{plt}</section>
    <div class="cols" style="margin-top:20px"><section class="panel"><h2>Cost sensitivity</h2><p>Out-of-sample results, one NQ contract. Commission + slippage per execution side.</p>
    <table><thead><tr><th>USD / SIDE</th><th>NET P&L (USD)</th><th>SHARPE</th></tr></thead><tbody>{costrows}</tbody></table></section>
    <section class="panel"><h2>Statistical diagnostics</h2><table>
    <tr><td>Next-day close return after up day</td><td>{_fmt(stats['next_return_after_up_mean_pct'],'.3f','%')}</td></tr>
    <tr><td>Next-day close return after down day</td><td>{_fmt(stats['next_return_after_down_mean_pct'],'.3f','%')}</td></tr>
    <tr><td>Welch p-value (exploratory)</td><td>{_fmt(stats['welch_p_value_exploratory'],'.4f')}</td></tr>
    <tr><td>Lag-1 absolute-return correlation</td><td>{_fmt(stats['absolute_return_lag1_correlation'],'.3f')}</td></tr>
    <tr><td>Clustering p-value (exploratory)</td><td>{_fmt(stats['volatility_clustering_p_value_exploratory'],'.4f')}</td></tr></table></section></div>
    <section class="panel" style="margin-top:20px"><h2>Research design & limitations</h2>
    <p><strong>Timing:</strong> SMAs use the completed close on date t; position changes occur at the next available open, and P&L is earned from that open to the following open. No look-ahead. Strategy is specified once without historical optimisation; 2019–2022 is development and 2023 onward is held-out evaluation.</p>
    <p><strong>Economics:</strong> One whole E-mini NQ contract, ${cfg.point_multiplier:.0f}/index point, $250,000 reference capital, ${cfg.cost_per_side:.2f}/side execution costs (commission + one tick). Baseline holds one NQ contract. Sharpe uses daily P&L divided by fixed starting capital, not an unleveraged index return. No margin, interest, taxes, futures-roll execution or liquidation modeled.</p>
    <p><strong>Data-quality audit:</strong> {m['data']['data_quality']['flagged_price_discontinuity_days']} days triggered large-price-gap screening and {m['data']['data_quality']['off_tick_ohlc_bars']} contained at least one off-tick recorded OHLC value. These alerts are not proof of roll errors. Packaged source prices were rounded to cents after independent archive retrieval. The adjustment and point-in-time policies of this Yahoo-derived continuous <code>NQ=F</code> ticker are not verified; the simulation is not a tradable track record.</p>
    <p><strong>Terminal-day accounting:</strong> the final observed open is used for any real opening/closing event and associated transaction cost, but no future price movement is invented. The terminal open trade is excluded from the 9 complete-trade win-rate denominator. Statistical tests are exploratory and not dependence- or multiple-test-adjusted.</p>
    <p class="foot">Data: <a style="color:#65ddc9" href="{source}">public source CSV</a>. Generated from the Python project's <code>analysis.py</code> and <code>run.py</code>.</p></section></main></body></html>'''
    output_path.write_text(doc, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='Reproducible NQ futures backtest (no demo/fake market data).')
    parser.add_argument('--csv', default='nq_daily.csv' if Path('nq_daily.csv').exists() else DATA_SOURCE, help='Path to NQ daily OHLC CSV, or an HTTPS data URL')
    parser.add_argument('--out', default='outputs', help='Output directory')
    args = parser.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    cfg = Config()
    print('Reading original market data from:', args.csv)
    try:
        prices = load_prices(args.csv, as_of=cfg.as_of)
    except Exception as exc:
        print('\nDATA DOWNLOAD / VALIDATION FAILED:', exc)
        print('Download source CSV in your browser, save as nq_daily.csv, then run:')
        print('  python run.py --csv nq_daily.csv')
        raise SystemExit(2) from exc
    daily, metrics, trades = summarize(prices, cfg, source=str(args.csv))
    flagged, quality = data_quality(prices)
    flagged.to_csv(out/'data_quality_flags.csv', float_format='%.6f')
    year = daily.loc[daily.index >= cfg.test_start].copy()
    annual = year.groupby(year.index.year).agg(strategy_net_usd=('strategy_net_usd', 'sum'), benchmark_net_usd=('benchmark_net_usd', 'sum'), trade_sides=('trade_sides','sum'))
    annual.index.name='year'
    annual.to_csv(out/'annual_results.csv')
    if Path(args.csv).is_file():
        metrics['data']['snapshot_sha256'] = hashlib.sha256(Path(args.csv).read_bytes()).hexdigest()
        metrics['data']['snapshot_ohlc_precision']='rounded to $0.01 from original public source (derived, not byte-identical)'
    metrics['data']['source_url']=DATA_SOURCE
    daily.to_csv(out/'daily_backtest.csv', float_format='%.8f')
    trades.to_csv(out/'closed_trades.csv', index=False)
    (out/'metrics.json').write_text(json.dumps(metrics, indent=2, allow_nan=False), encoding='utf-8')
    save_dashboard(daily, metrics, out/'dashboard_results.html', cfg)
    create_report(out/'Research_Results.pdf', metrics, daily, trades)
    shutil.copyfile(out/'dashboard_results.html', Path(__file__).with_name('Open_Dashboard.html'))
    shutil.copyfile(out/'Research_Results.pdf', Path(__file__).with_name('Research_Brief.pdf'))
    print('\nBacktest completed on', len(prices), 'validated input daily bars, through', prices.index.max().date())
    print('Out-of-sample:', metrics['out_of_sample_strategy'])
    print('Files written:', out.resolve())


if __name__ == '__main__':
    main()
