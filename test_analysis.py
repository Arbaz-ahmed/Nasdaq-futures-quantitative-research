"""Explicitly synthetic test fixtures for logic checks ONLY, never used as market findings."""
import numpy as np
import pandas as pd
from analysis import Config, load_prices, signal_and_backtest, metric_row, _trades_for_interval


def prices_fixture():
    n = 150
    dates = pd.bdate_range("2022-01-03", periods=n)
    v = np.linspace(100, 250, n)
    return pd.DataFrame({"date": dates, "open": v, "high": v+2,
                         "low": v-2, "close": v+1, "volume": np.ones(n)})


def test_signal_is_lagged_and_uses_next_open():
    prices = load_prices(prices_fixture(), as_of=pd.Timestamp("2026-11-12"))
    cfg = Config(fast_window=5, slow_window=10, initial_capital=250000)
    res = signal_and_backtest(prices, cfg)
    assert res.iloc[9]["position_at_open"] == 0  # Signal first possible at close bar 9
    assert res.iloc[10]["position_at_open"] == 1  # Earliest entry following open
    assert res.iloc[10]["strategy_gross_usd"] == 20 * (prices.iloc[11]["open"] - prices.iloc[10]["open"])
    assert res.iloc[10]["strategy_cost_usd"] == 7.50
    assert res["position_at_open"].isin([-1, 0, 1]).all()


def test_reversal_costs_two_sides():
    x = prices_fixture()
    x.loc[65:, "open"] = np.linspace(200, 70, len(x)-65)
    x.loc[65:, "close"] = x.loc[65:, "open"] + 1
    x["high"] = x[["open", "close"]].max(axis=1) + 2
    x["low"] = x[["open", "close"]].min(axis=1) - 2
    d = signal_and_backtest(load_prices(x), Config(fast_window=5, slow_window=10))
    flips = d["trade_sides"] == 2
    assert flips.any()
    assert (d.loc[flips, "strategy_cost_usd"] == 15).all()


def test_duplicate_dates_rejected():
    x = prices_fixture()
    x.loc[1, "date"] = x.loc[0, "date"]
    try:
        load_prices(x)
    except ValueError as err:
        assert "Duplicate" in str(err)
    else:
        raise AssertionError("Expected duplicate validation error")


def test_last_open_requires_future_bar():
    """Record observed final open, but never invent next-open gross P&L."""
    d = signal_and_backtest(load_prices(prices_fixture()), Config(fast_window=5, slow_window=10))
    assert len(d) == len(prices_fixture())
    assert bool(d.iloc[-1]["has_next_open"]) is False
    assert d.iloc[-1]["strategy_gross_usd"] == 0
    assert d.index[-1] == prices_fixture().iloc[-1]["date"]


def test_terminal_flip_is_closed_trade_with_both_sides_costed():
    """Regression: final observed open can close a short and enter a long."""
    x = prices_fixture()
    # Make an initial bullish run, then long bearish run, then abrupt bullish close.
    x.loc[40:147,"close"] = np.linspace(140,80,108)
    x.loc[40:147,"open"] = x.loc[40:147,"close"]-1
    x.loc[148,"close"] = 1000.0
    x.loc[148,"open"] = 81.0
    x.loc[149,"open"] = 1100.0
    x.loc[149,"close"] = 1100.5
    x["high"] = x[["open","close"]].max(axis=1)+2
    x["low"] = x[["open","close"]].min(axis=1)-2
    cfg=Config(fast_window=5,slow_window=10)
    d=signal_and_backtest(load_prices(x),cfg)
    assert d.iloc[-2]["position_at_open"] == -1
    assert d.iloc[-1]["position_at_open"] == 1
    assert d.iloc[-1]["trade_sides"] == 2
    assert d.iloc[-1]["strategy_cost_usd"] == 15
    assert d.iloc[-1]["strategy_gross_usd"] == 0
    ledger=_trades_for_interval(d,cfg,cfg.cost_per_side)
    assert len(ledger)>0
    assert ledger.iloc[-1]["exit_date"]==d.index[-1]
    assert ledger.iloc[-1]["direction"]=="SHORT"
    expected=-1*(d.iloc[-1]["open"]-ledger.iloc[-1]["entry_price"])*20 - 2*7.5
    assert np.isclose(ledger.iloc[-1]["net_pnl_usd"],expected)


def test_terminal_unclosed_position_is_not_fake_trade():
    cfg=Config(fast_window=5,slow_window=10)
    d=signal_and_backtest(load_prices(prices_fixture()),cfg)
    ledger=_trades_for_interval(d,cfg,cfg.cost_per_side)
    assert len(ledger)==0
    assert d.iloc[-1].position_at_open==1


def test_trade_ledger_reconciles_when_last_event_closes_to_flat():
    # Directly exercise the ledger with a deliberate final-day closure event.
    cfg=Config(fast_window=2,slow_window=3)
    dates=pd.bdate_range('2022-01-03',periods=4)
    d=pd.DataFrame({'open':[100.,103.,97.,99.],
                    'position_at_open':[0,1,1,0]},index=dates)
    ledger=_trades_for_interval(d,cfg,cfg.cost_per_side)
    assert len(ledger)==1
    assert ledger.iloc[0]['exit_date']==dates[-1]
    assert ledger.iloc[0]['net_pnl_usd']==(99-103)*20-15



def test_cost_sensitivity_only_changes_transaction_costs():
    prices = load_prices(prices_fixture())
    cfg = Config(fast_window=5, slow_window=10)
    free = signal_and_backtest(prices, cfg, cost_per_side=0)
    costly = signal_and_backtest(prices, cfg, cost_per_side=30)
    assert np.allclose(free["strategy_gross_usd"], costly["strategy_gross_usd"])
    assert np.allclose(free["strategy_net_usd"] - costly["strategy_net_usd"],
                       costly["trade_sides"] * 30)


def test_metrics_do_not_confuse_initial_capital_with_price_returns():
    prices = load_prices(prices_fixture())
    cfg = Config(fast_window=5, slow_window=10, initial_capital=250000)
    d = signal_and_backtest(prices, cfg)
    m = metric_row(d, cfg)
    assert np.isclose(m["return_pct"], d["strategy_net_usd"].sum()/250000*100)
    assert m["max_drawdown_pct"] <= 0


def test_missing_or_inconsistent_ohlc_rejected():
    x = prices_fixture()
    x.loc[70, "high"] = x.loc[70, "low"] - 1
    try:
        load_prices(x)
    except ValueError as err:
        assert "OHLC inconsistency" in str(err)
    else:
        raise AssertionError("Expected an OHLC data integrity error")


def test_no_lookahead_on_signal_date():
    """Changing the final close cannot change positions already entered earlier."""
    cfg = Config(fast_window=5, slow_window=10)
    price = load_prices(prices_fixture())
    baseline = signal_and_backtest(price, cfg)
    changed = price.copy()
    changed.iloc[-1, changed.columns.get_loc("close")] = float(changed.iloc[-1]["close"]) * 1.05
    changed.iloc[-1, changed.columns.get_loc("high")] = max(
        changed.iloc[-1]["high"], changed.iloc[-1]["close"])
    revised = signal_and_backtest(changed, cfg)
    assert baseline["position_at_open"].equals(revised["position_at_open"])
    assert np.allclose(baseline["strategy_net_usd"], revised["strategy_net_usd"])
