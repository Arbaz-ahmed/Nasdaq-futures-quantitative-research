# How to describe this project in finance applications

**Independent NASDAQ-100 Futures Research | Python, pandas, SciPy, Plotly**

The research does **not** show a profitable advantage versus the baseline. That is an important and useful conclusion: the moving-average trend rule underperformed in both risk-adjusted terms and total simulated P&L across the 2023-2026 chronological evaluation. It is better to highlight technical discipline and risk judgement than select flattering numbers.

## CV project section (adapt in your own words)

**Quantitative Markets Research — NASDAQ-100 Futures (Independent Python Project)**

- Built a reproducible daily-bar futures research pipeline using sourced historical OHLCV, lagged moving-average signals and open-to-open P&L, with transaction-cost and terminal-day trade-accounting checks.
- Compared a 20/100-session trend strategy against an always-long one-contract NQ benchmark across a chronological 2023-2026 evaluation, computing Sharpe, drawdown, closed-trade win rate and cost sensitivity.
- Published a Python/Plotly visualisation and findings-led PDF, identifying significant model underperformance versus the baseline and screening 16 unusually large price-gap sessions while documenting continuous-futures roll limitations.

This is a **simulated backtest**. Do not call it audited profit, live performance or an institutional trading strategy. You may discuss exact net numbers during an interview if you can explain the source and assumptions without overstating credibility.

## LinkedIn summary

Conducted independent quantitative market research into E-mini Nasdaq-100 futures using Python, pandas, SciPy and Plotly. Built a reproducible historical backtest with no same-day signal look-ahead, transaction-cost accounting, a closed-trade ledger and benchmark/risk comparisons. In the 2023-2026 historical simulation, the 20/100 SMA strategy lagged an always-long NQ exposure; the project discusses why non-validated continuous-futures roll data prevents a live-profit claim. Reported findings through an interactive dashboard and research PDF.

## Interview pitch (30 seconds)

> I wanted to demonstrate research skills beyond placing futures trades. I developed a Python backtesting study using public Nasdaq-100 futures market data and compared a fixed trend rule against staying long one contract. My model accounts for when signals were actually observable, transaction costs, final-day exits and max drawdown. The strategy made positive simulated P&L but substantially underperformed the benchmark. I focused on explaining why, and flagged the dataset's unverified contract rolls, rather than exaggerating the results. It was a useful exercise in testing hypotheses and being rigorous about risk.

## Important technical questions

**Why did the strategy lose against the baseline?** The bullish benchmark benefited from persistent long exposure, whereas the strategy was exposed to timing and short-position risk. The strategy performed particularly poorly in 2026. Confirm causality with more controlled research before claiming one mechanism explains all of it.

**How do you know it does not look ahead?** The close-based SMA on bar t is executed only at open t+1; P&L begins at the entry open. This is regression-tested.

**What was fixed in the bug review?** The original code dropped the final bar before building its closed-trade ledger. The new engine retains the final observed open for executions, closing trades and associated costs, but sets its future gross return to zero because no subsequent open has been observed.

**Is the data institutional-grade?** No. It is a third-party Yahoo-derived continuous futures snapshot with unverified roll adjustments. We used data-integrity screening and a provenance snapshot, but meaningful historical fill accuracy requires contract-by-contract, point-in-time data with explicit rolling.

**Why test a losing hypothesis?** Banks value the ability to reject weak signals, compare relevant baselines, model costs, check data reliability and clearly communicate quantitative uncertainty.

**How would you improve it?** Use authenticated individual quarterly futures contracts, a deterministic roll rule, tradeable fills, margin and collateral yield, an initially untouched forward sample, and dependence-robust diagnostics.
