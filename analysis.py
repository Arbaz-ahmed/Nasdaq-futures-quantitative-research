"""NQ daily continuous-futures market research and open-to-open backtest.

P&L is illustrative: public Yahoo-derived continuous prices are not a verified
point-in-time contract chain, and this is not an investable track record.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Union
import hashlib

import numpy as np
import pandas as pd
from scipy import stats

DATA_SOURCE = (
    "https://raw.githubusercontent.com/Chief-rich/nasdaq100-data/"
    "main/data/nq_daily/history.csv"
)
TEST_START = pd.Timestamp("2023-01-01")
AS_OF = pd.Timestamp("2026-11-12")
POINT_MULTIPLIER = 20.0
TICK_SIZE = 0.25
TRADING_DAYS = 252


@dataclass(frozen=True)
class Config:
    fast_window: int = 20
    slow_window: int = 100
    initial_capital: float = 250_000.0
    point_multiplier: float = POINT_MULTIPLIER
    commission_per_side: float = 2.50
    slippage_ticks_per_side: float = 1.0
    test_start: pd.Timestamp = TEST_START
    as_of: pd.Timestamp = AS_OF

    @property
    def cost_per_side(self) -> float:
        return self.commission_per_side + self.slippage_ticks_per_side*TICK_SIZE*self.point_multiplier


def load_prices(source: Union[str, Path, pd.DataFrame] = DATA_SOURCE,
                *, as_of: pd.Timestamp = AS_OF) -> pd.DataFrame:
    """Read actual OHLCV; validate chronology, values and gross OHLC consistency."""
    raw = source.copy() if isinstance(source, pd.DataFrame) else pd.read_csv(source)
    raw.columns = [str(x).strip().lower().replace(' ', '_') for x in raw.columns]
    if 'date' not in raw and 'datetime' in raw:
        raw = raw.rename(columns={'datetime':'date'})
    required={'date','open','high','low','close'}
    if not required.issubset(raw.columns):
        raise ValueError('Missing OHLC columns: '+str(sorted(required-set(raw.columns))))
    raw['date'] = pd.to_datetime(raw['date'], utc=True, errors='coerce').dt.tz_localize(None).dt.normalize()
    if raw['date'].isna().any():
        raise ValueError('Unparseable dates in input')
    if raw['date'].duplicated().any():
        raise ValueError('Duplicate daily dates in input')
    for col in ('open','high','low','close'):
        raw[col]=pd.to_numeric(raw[col], errors='coerce')
    raw=raw.loc[raw.date <= pd.Timestamp(as_of)].sort_values('date').reset_index(drop=True)
    if len(raw)<120:
        raise ValueError('Need at least 120 daily bars')
    if raw[['open','high','low','close']].isna().any().any():
        raise ValueError('Missing/non-numeric OHLC records')
    if (raw[['open','high','low','close']]<=0).any().any():
        raise ValueError('Nonpositive OHLC price')
    if ((raw.high < raw[['open','close','low']].max(axis=1)-1e-6) |
        (raw.low > raw[['open','close','high']].min(axis=1)+1e-6)).any():
        raise ValueError('OHLC inconsistency')
    if 'volume' in raw:
        raw['volume']=pd.to_numeric(raw['volume'],errors='coerce')
    return raw.set_index('date')


def signal_and_backtest(prices: pd.DataFrame, cfg: Config = Config(), *,
                        cost_per_side: float|None=None) -> pd.DataFrame:
    """Close(t-1) signal executes at open(t); mark from open(t) to open(t+1).

    The terminal observed open is an EXECUTION-ONLY row. The next open is unknown,
    so final gross P&L = 0, but any entry/exit/reversal at that observed open is
    charged. Including it also enables a genuine closing trade on the final date.
    Terminal equity contains no hypothetical return after the latest price.
    """
    c=cfg.cost_per_side if cost_per_side is None else float(cost_per_side)
    if not np.isfinite(c) or c<0:
        raise ValueError('Transaction cost must be finite and nonnegative')
    if cfg.fast_window<=0 or cfg.slow_window <= cfg.fast_window:
        raise ValueError('slow_window must be greater than fast_window')
    d=prices.copy()
    d['fast_sma']=d.close.rolling(cfg.fast_window,min_periods=cfg.fast_window).mean()
    d['slow_sma']=d.close.rolling(cfg.slow_window,min_periods=cfg.slow_window).mean()
    d['close_to_close_return']=d.close.pct_change()
    d['ann_vol_20d']=d['close_to_close_return'].rolling(20).std()*np.sqrt(TRADING_DAYS)
    signal=np.where(d.slow_sma.isna(),0,np.where(d.fast_sma>d.slow_sma,1,-1))
    d['signal_at_close']=signal
    d['position_at_open']=pd.Series(signal,index=d.index).shift(1).fillna(0).astype(int)
    d['has_next_open']=pd.Series(np.arange(len(d))<len(d)-1,index=d.index)
    # There is no next open following the terminal record; zero GROSS P&L only,
    # not a fake future price or a fictitious closing trade.
    d['next_open_change']=(d.open.shift(-1)-d.open).fillna(0.0)
    d['trade_sides']=d.position_at_open.diff().fillna(d.position_at_open).abs().astype(int)
    d['strategy_gross_usd']=d.position_at_open*d.next_open_change*cfg.point_multiplier
    d['strategy_cost_usd']=d.trade_sides*c
    d['strategy_net_usd']=d.strategy_gross_usd-d.strategy_cost_usd
    benchmark=np.zeros(len(d),dtype=int)
    benchmark[cfg.slow_window:]=1
    d['benchmark_position']=benchmark
    d['benchmark_sides']=pd.Series(benchmark,index=d.index).diff().fillna(0).abs().astype(int)
    d['benchmark_net_usd']=d.benchmark_position*d.next_open_change*cfg.point_multiplier-d.benchmark_sides*c
    d['strategy_equity_usd']=cfg.initial_capital+d.strategy_net_usd.cumsum()
    d['benchmark_equity_usd']=cfg.initial_capital+d.benchmark_net_usd.cumsum()
    return d


def _dd(equity: pd.Series,capital:float)->float:
    v=pd.concat([pd.Series([capital]),equity.reset_index(drop=True)],ignore_index=True)
    return float((v/v.cummax()-1).min())


def _trades_for_interval(d:pd.DataFrame,cfg:Config,cost_per_side:float)->pd.DataFrame:
    """Realised closed trades only; terminal execution is included if observable."""
    events=[]
    current_pos,entry_date,entry_price=0,None,None
    for date,row in d.iterrows():
        pos=int(row.position_at_open)
        if pos==current_pos:
            continue
        price=float(row.open)
        if current_pos:
            pnl=current_pos*(price-entry_price)*cfg.point_multiplier-2*cost_per_side
            events.append({'entry_date':entry_date,'exit_date':date,
                           'direction':'LONG' if current_pos>0 else 'SHORT',
                           'entry_price':entry_price,'exit_price':price,'net_pnl_usd':pnl})
        entry_date,entry_price=(date,price) if pos else (None,None)
        current_pos=pos
    return pd.DataFrame(events,columns=['entry_date','exit_date','direction','entry_price','exit_price','net_pnl_usd'])


def metric_row(d:pd.DataFrame,cfg:Config,pnl_col:str='strategy_net_usd')->dict:
    if d.empty:
        return {'total_pnl_usd':None,'return_pct':None,'sharpe':None,
                'annual_vol_pct':None,'max_drawdown_pct':None,'positive_days_pct':None,
                'active_days':0,'observations':0}
    # A terminal execution-only row has no measured return interval.
    # Count its execution cost in total P&L, but not as a full daily observation
    # in the annualised Sharpe/volatility estimators.
    pnl=d[pnl_col].astype(float)
    completed=d.loc[d.has_next_open]
    pnl_for_r=completed[pnl_col].astype(float)
    daily_r=pnl_for_r/cfg.initial_capital
    std=float(daily_r.std(ddof=1))
    eq=cfg.initial_capital+pnl.cumsum()
    active=d.loc[d.position_at_open!=0] if pnl_col=='strategy_net_usd' else d.loc[d.benchmark_position!=0]
    return {
        'total_pnl_usd':float(pnl.sum()),
        'return_pct':float(100*pnl.sum()/cfg.initial_capital),
        'sharpe':float(np.sqrt(TRADING_DAYS)*daily_r.mean()/std) if std>0 else None,
        'annual_vol_pct':float(100*std*np.sqrt(TRADING_DAYS)) if std==std else None,
        'max_drawdown_pct':float(100*_dd(eq,cfg.initial_capital)),
        'positive_days_pct':float(100*(active[pnl_col]>0).mean()) if len(active) else None,
        'active_days':int(len(active)),
        'observations':int(len(completed))
    }


def explore_statistics(prices:pd.DataFrame)->dict:
    """Exploratory descriptive diagnostics, not evidence of a trading edge."""
    r=prices.close.pct_change().dropna()
    lagged=r.shift(1)
    up=r[lagged>0].dropna()
    down=r[lagged<0].dropna()
    if len(up)>10 and len(down)>10:
        welch=stats.ttest_ind(up,down,equal_var=False)
        diff=float(up.mean()-down.mean());p=float(welch.pvalue)
    else:diff,p=None,None
    q=pd.DataFrame({'today':r.abs(),'prior':r.abs().shift(1)}).dropna()
    if len(q)>20:
        vcor,vp=stats.pearsonr(q.today,q.prior)
        vcor,vp=float(vcor),float(vp)
    else:vcor,vp=None,None
    return {'next_return_after_up_mean_pct':float(up.mean()*100) if len(up) else None,
            'next_return_after_down_mean_pct':float(down.mean()*100) if len(down) else None,
            'direction_return_difference_pct_points':diff*100 if diff is not None else None,
            'welch_p_value_exploratory':p,
            'absolute_return_lag1_correlation':vcor,
            'volatility_clustering_p_value_exploratory':vp,
            'sample_days':int(len(r)),
            'note':'Exploratory only; serial dependence, rolls, data quality and multiple testing can invalidate p-values.'}


def data_quality(prices:pd.DataFrame)->tuple[pd.DataFrame,dict]:
    """Flag potential price discontinuities; DOES NOT authenticate roll methodology."""
    g=pd.DataFrame(index=prices.index)
    g['open']=prices.open
    g['prev_close']=prices.close.shift(1)
    g['open_to_open_pct']=100*prices.open.pct_change()
    g['close_to_open_gap_pct']=100*(prices.open/prices.close.shift(1)-1)
    g['close_to_close_pct']=100*prices.close.pct_change()
    g['abs_open_to_open_pct']=g.open_to_open_pct.abs()
    g['abs_close_to_open_gap_pct']=g.close_to_open_gap_pct.abs()
    flagged=(g.abs_open_to_open_pct>8)|(g.abs_close_to_open_gap_pct>2)
    bad=g.loc[flagged].copy()
    bad['reason']=np.where(bad.abs_open_to_open_pct>8,'ABS_OPEN_TO_OPEN_GT_8_PCT','CLOSE_TO_OPEN_GAP_GT_2_PCT')
    off_tick=pd.Series(False,index=prices.index)
    for col in ('open','high','low','close'):
        off_tick |= ~np.isclose(prices[col]/TICK_SIZE,np.round(prices[col]/TICK_SIZE),atol=0.005,rtol=0)
    info={'flagged_price_discontinuity_days':int(flagged.sum()),
          'open_to_open_over_8pct_days':int((g.abs_open_to_open_pct>8).sum()),
          'close_to_open_gap_over_2pct_days':int((g.abs_close_to_open_gap_pct>2).sum()),
          'off_tick_ohlc_bars':int(off_tick.sum()),
          'max_open_to_open_abs_pct':float(g.abs_open_to_open_pct.max()),
          'max_close_to_open_abs_gap_pct':float(g.abs_close_to_open_gap_pct.max()),
          'audit_method':'Threshold screening only. Cannot determine whether an event is a genuine market gap or futures roll.'}
    return bad,info


def summarize(prices:pd.DataFrame,cfg:Config=Config(),*,source:str=DATA_SOURCE)->tuple[pd.DataFrame,dict,pd.DataFrame]:
    d=signal_and_backtest(prices,cfg)
    insample=d.loc[d.index<cfg.test_start];oos=d.loc[d.index>=cfg.test_start]
    if len(insample)<120 or len(oos)<60:
        raise ValueError('Insufficient data for pre-2023 / 2023+ study split')
    trades=_trades_for_interval(d,cfg,cfg.cost_per_side)
    trades['in_oos']=pd.to_datetime(trades.entry_date)>=cfg.test_start
    oos_closed=trades.loc[trades.in_oos]
    flag,quality=data_quality(prices)
    metrics={
        'data':{'source':source,'start':str(prices.index.min().date()),
                'end':str(prices.index.max().date()),'bars':int(len(prices)),
                'split':str(cfg.test_start.date()),'currency':'USD',
                'contract':'NQ E-mini (continuous series)','bar_frequency':'daily',
                'data_quality':quality},
        'assumptions':{'fast':cfg.fast_window,'slow':cfg.slow_window,
                       'capital_usd':cfg.initial_capital,
                       'multiplier_usd_per_point':cfg.point_multiplier,
                       'cost_usd_per_side':cfg.cost_per_side,
                       'execution':'Previous close signal; next open execution; open-to-next-open P&L; final open execution costs charged without future gross P&L',
                       'futures_roll_warning':'Yahoo-derived NQ=F contract transitions and historic point-in-time accuracy not independently authenticated.'},
        'in_sample_strategy':metric_row(insample,cfg),
        'out_of_sample_strategy':metric_row(oos,cfg),
        'in_sample_benchmark':metric_row(insample,cfg,'benchmark_net_usd'),
        'out_of_sample_benchmark':metric_row(oos,cfg,'benchmark_net_usd'),
        'out_of_sample_closed_trade_count':int(len(oos_closed)),
        'out_of_sample_closed_trade_win_rate_pct':float(100*(oos_closed.net_pnl_usd>0).mean()) if len(oos_closed) else None,
        'open_trade_at_last_observation':bool(d.position_at_open.iloc[-1]!=0),
        'all_period_closed_trade_count':int(len(trades)),
        'statistics':explore_statistics(prices),
        'transaction_cost_sensitivity':{},
    }
    for side_cost in (0,cfg.cost_per_side,15,30):
        alt=signal_and_backtest(prices,cfg,cost_per_side=side_cost)
        metrics['transaction_cost_sensitivity'][f'{side_cost:g}']=metric_row(alt.loc[alt.index>=cfg.test_start],cfg)
    return d,metrics,trades
