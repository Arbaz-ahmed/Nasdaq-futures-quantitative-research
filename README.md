# NASDAQ-100 Futures | Quantitative Market Research & Backtesting
> **Independent research portfolio (not live trading):** Historical NQ futures data, a reproducible Python backtest, an interactive HTML dashboard and a results-led PDF. Start with [Open_Dashboard.html](Open_Dashboard.html) or [Research_Brief.pdf](Research_Brief.pdf).


**Completed independent portfolio research project | Python, pandas, SciPy, Plotly, ReportLab, pytest**

> **A negative relative finding is still a finding.** A fixed 20/100-session trend-following strategy produced positive modelled P&L but underperformed holding one NQ contract long on the *public continuous-futures series*. This work demonstrates research design, reliable execution accounting, data auditing and risk interpretation. It **does not** demonstrate audited profits or an investable execution strategy.

## Start here: finished results

- **`Open_Dashboard.html`**: finished interactive dashboard with actual simulated model results, not a blank CSV importer; works offline.
- **`Research_Brief.pdf`**: 4-page findings report (real statistics, strategy-versus-benchmark chart, year-by-year attribution, interpretation and data caveats).
- **`outputs/Research_Results.pdf`** and **`outputs/dashboard_results.html`**: automatically reproducible results copies.
- **`nq_daily.csv`**: packaged, date-stamped real OHLCV data reconstructed from the public historical archive, prices represented to two decimal places. No generated or fictitious market observations.
- **`outputs/metrics.json`**, **`outputs/daily_backtest.csv`**, **`outputs/closed_trades.csv`**, **`outputs/annual_results.csv`** and **`outputs/data_quality_flags.csv`**: underlying numerical evidence.

### Key results (2023-01-01 through 2026-11-11; last source observation 2026-11-11)

| Metric | 20/100 SMA strategy | Always-long one NQ |
|---|---:|---:|
| Net simulated P&L | **+$69,150** | **+$335,540** |
| Simple P&L / $250k initial capital | +27.66% | +134.22% |
| Daily-P&L Sharpe (0% benchmark) | 0.198 | 0.962 |
| Max model-equity drawdown | -29.52% | -21.75% |
| Annualised fixed-capital daily P&L volatility | 36.28% | 36.21% |

**Finding:** the strategy underperformed the comparable baseline by **$266,390** over this chronological evaluation. Its completed-trade win rate was **44.4% across only nine completed evaluation-period trades**; one final short remained open and is excluded from the win rate. The +27.66% and +134.22% figures are simple cumulative P&L / reference capital, **not** investment CAGR or cash-index returns.

The model showed +$49,815 in 2023, +$85,000 in 2024, +$11,720 in 2025, and -$77,385 in 2026 to date. The 2026 decline is a material driver of underperformance. Transaction-cost sensitivity at $0, $7.50, $15 and $30 per side is included.

## Re-run the entire project on the included data

From the unzipped project folder in Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe run.py --csv nq_daily.csv
```

If you prefer an existing Python environment:

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
python run.py --csv nq_daily.csv
```

The complete report, dashboard and CSV outputs are regenerated. `Open_Dashboard.html` and `Research_Brief.pdf` are also updated from the run. `START_HERE.bat` opens the finished dashboard without running the backtest.

To use the latest public remote CSV instead of the frozen 2026-11-11 data snapshot:

```powershell
python run.py --csv "https://raw.githubusercontent.com/Chief-rich/nasdaq100-data/main/data/nq_daily/history.csv"
```

**Important:** This source is a third-party Yahoo-derived dataset and may change; updated runs can produce different figures. Cite the data date and preserve the snapshot rather than pretending the data is unchanged.

## Data origin, integrity and warnings

- Original public source: <https://github.com/Chief-rich/nasdaq100-data/blob/main/data/nq_daily/history.csv>, published as Yahoo Finance-derived ticker `NQ=F` and archived by a third party. The repository documents the instrument and fields but does not establish an exchange-authenticated, historical point-in-time contract chain or a verified roll-adjustment policy.
- Included data: 1,980 observed bars from **2019-01-02 to 2026-11-11**. Date, open, close, high, low and volume values were retrieved from the archive on 2026-11-12. All OHLC prices were rounded to cents for transfer/packaging; thus this is a derived snapshot, not a byte-identical original. Volume and dates were retained. The whole derived history was checked against the source after cent rounding using a row-ordered checksum; inspection samples were also matched.
- Packaged CSV SHA-256: `c5563a6133f4d31062ebc708b4d183407cbdd4eb5b0f3e48dc79c151968ddfea`.
- Screening flagged **16 sessions with unusually large gaps** and **30 bars with off-tick OHLC values**, including high-volatility periods in March 2020 and April 2025. The flags are not proof of an erroneous contract roll. See `outputs/data_quality_flags.csv`.
- **Unverified roll mechanics make all P&L estimates illustrative.** Underlying futures may have been rolled on dates not known to this study; artificial price discontinuities could bias modelled returns. Separate contract-level history, point-in-time back-adjustment, an explicit roll schedule and fill simulation would be needed for a stronger claim.
- No audited fills, intraday stop/limit executions, collateral interest, margin liquidation, taxes, full exchange fee schedule, roll execution slippage or capacity model. The $250k is a fixed reference account, not an assumption about the exchange's initial margin requirement.
- The 2023+ period is chronological but was chosen and examined retrospectively. It is **not a prospectively sealed test**; do not claim independent forward validation. The reported p-values are exploratory and not serial-dependence or multiple-test adjusted.
- When publishing source data publicly, check the original archive's licence and the upstream data provider's redistribution terms. The included copy is for local analysis and review.

## Exact strategy and accounting

| Feature | Specification |
|---|---|
| Signal | SMA20 of completed daily closes > SMA100 of completed daily closes => long +1 NQ; otherwise short -1 |
| Warm-up | No active position until signal can be computed from 100 completed closes |
| Entry | At first available **next session's open**; no use of future closes |
| P&L | Signed open-to-next-open price movement × **$20 per point** × one contract |
| Friction | $2.50 per side commission + one 0.25-point tick ($5) slippage = $7.50 per side; reversals cost $15 |
| Baseline | Always long one NQ contract after same warm-up, using same initial capital and per-side cost assumptions |
| Capital | $250,000 reference; cash net P&L is not marked as compounded unlevered index returns |
| Research split | 2019-2022 research development; 2023 onward chronological evaluation of the fixed parameters |
| Final date | Final **observed open** is included for actual entry/exit/reversal execution and costs; no unknown later open-to-open gross return is invented |
| Win rate | Closed-trade ledger only; final still-open position is not treated as a completed winner or loser |

The closed-trade ledger sums closed-trade gains/losses minus both execution sides; any remaining open position is marked only to its last observed open with its entry cost paid. This reconciles to total model net P&L. An automated regression test verifies closure or reversal on the terminal observed open.

## Statistical interpretation

A secondary analysis found mean next-day close-to-close return after a prior up day of **+0.029%** versus **+0.165%** after a prior down day; a Welch test gave **p=0.0533** (not conventionally significant at 5%). Lag-one absolute-return correlation was **+0.243**, consistent with volatility clustering. Both tests are exploratory; naïve significance can be misleading under serial dependence, continuous-contract artifacts and retrospective selection.

## Reproducibility and unit tests

Test fixtures under `tests/` use **explicitly synthetic** prices for numerical unit tests only. The published dashboard and numerical report use the included actual sourced snapshot. Key tests cover lagged execution, reversal costs, terminal-day closure, no fake final future return, open-trade exclusion, cost sensitivity and input integrity.

```text
NASDAQ_Futures_Research_Project/
├── Open_Dashboard.html         # Finished, interactive offline results dashboard
├── Research_Brief.pdf          # Finished four-page findings-led research PDF
├── nq_daily.csv                # Real sourced daily OHLCV data, cent-quantized snapshot
├── analysis.py                 # Source validation, risk analysis, strategy, closed ledger
├── report.py                   # Reproducible PDF report and matplotlib chart
├── run.py                      # Deterministic pipeline, Plotly dashboard, results files
├── requirements.txt
├── START_HERE.bat
├── PORTFOLIO_PRESENTATION.md
├── tests/test_analysis.py
└── outputs/
    ├── annual_results.csv
    ├── closed_trades.csv
    ├── daily_backtest.csv
    ├── data_quality_flags.csv
    ├── dashboard_results.html
    ├── metrics.json
    ├── Research_Results.pdf
    └── strategy_vs_benchmark.png
```

**Next research extension:** independently audited front-month contract prices with explicit roll rules and margin-aware, point-in-time walk-forward or paper-trading evaluation. A losing relative strategy can still be useful as evidence of rigorous research if its limitations are candidly presented.
