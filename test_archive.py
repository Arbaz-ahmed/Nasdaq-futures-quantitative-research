"""Regression checks on frozen real-price research snapshot (not fixtures)."""
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from analysis import Config, load_prices, signal_and_backtest, _trades_for_interval

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_SHA256 = "c5563a6133f4d31062ebc708b4d183407cbdd4eb5b0f3e48dc79c151968ddfea"


def test_packaged_archived_series_is_unchanged_and_monotone():
    path = ROOT / "nq_daily.csv"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == SNAPSHOT_SHA256
    prices = load_prices(pd.read_csv(path))
    assert len(prices) == 1980
    assert str(prices.index[0].date()) == "2019-01-02"
    assert str(prices.index[-1].date()) == "2026-11-11"
    assert prices.index.is_monotonic_increasing


def test_real_full_run_ledger_reconciles_to_model_cash_pnl():
    prices = load_prices(pd.read_csv(ROOT / "nq_daily.csv"))
    cfg = Config()
    model = signal_and_backtest(prices, cfg)
    ledger = _trades_for_interval(model, cfg, cfg.cost_per_side)
    all_pnl = float(model["strategy_net_usd"].sum())
    closed_pnl = float(ledger["net_pnl_usd"].sum())
    assert int(model.iloc[-1]["position_at_open"]) == -1
    assert bool(model.iloc[-1]["has_next_open"]) is False
    last_position = int(model.iloc[-1]["position_at_open"])
    changed = model["position_at_open"].ne(model["position_at_open"].shift(1).fillna(0))
    last_entry = model.loc[changed].iloc[-1]
    open_pnl = (last_position * (float(model.iloc[-1]["open"]) - float(last_entry["open"]))
                * cfg.point_multiplier - cfg.cost_per_side)
    assert np.isclose(all_pnl, closed_pnl + open_pnl)
    assert np.isclose(all_pnl, 108217.50)
    assert np.isclose(closed_pnl, 92955.0)
