"""Reproducible, findings-led PDF for the NQ historical research project."""
from __future__ import annotations
from pathlib import Path
from xml.sax.saxutils import escape
import pandas as pd
import numpy as np
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                PageBreak, KeepTogether, Image, HRFlowable)
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.units import mm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

DARK=colors.HexColor('#12233c')
TEAL=colors.HexColor('#008c86')
GOLD=colors.HexColor('#ad6e14')
GREY=colors.HexColor('#4f6177')
PALE=colors.HexColor('#ecf4f6')
RULE=colors.HexColor('#d5dee8')
RED=colors.HexColor('#a13d47')

FONT_FILE='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD_FILE='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
if Path(FONT_FILE).exists():
    pdfmetrics.registerFont(TTFont('DejaVu', FONT_FILE))
    pdfmetrics.registerFont(TTFont('DejaVu-Bold', BOLD_FILE))
    FONT='DejaVu';FONT_BOLD='DejaVu-Bold'
else:
    FONT='Helvetica';FONT_BOLD='Helvetica-Bold'

styles={
 'eyebrow':ParagraphStyle('eyebrow',fontName=FONT_BOLD,fontSize=8,leading=11,textColor=TEAL,spaceAfter=5),
 'title':ParagraphStyle('title',fontName=FONT_BOLD,fontSize=20,leading=27,textColor=DARK,spaceAfter=11),
 'subtitle':ParagraphStyle('subtitle',fontName=FONT,fontSize=10.3,leading=15,textColor=GREY,spaceAfter=10),
 'h':ParagraphStyle('h',fontName=FONT_BOLD,fontSize=11.1,leading=15,textColor=DARK,spaceBefore=10,spaceAfter=5),
 'p':ParagraphStyle('p',fontName=FONT,fontSize=8.7,leading=13.7,textColor=DARK,spaceAfter=6),
 'small':ParagraphStyle('small',fontName=FONT,fontSize=7.5,leading=11,textColor=GREY,spaceAfter=6),
 'cell':ParagraphStyle('cell',fontName=FONT,fontSize=7.8,leading=11,textColor=DARK),
 'cellb':ParagraphStyle('cellb',fontName=FONT_BOLD,fontSize=7.8,leading=11,textColor=DARK),
}
P=lambda s,key='p':Paragraph(str(s),styles[key])

def table(rows,widths,header=True):
    data=[]
    for i,row in enumerate(rows):data.append([P(x,'cellb' if header and i==0 else 'cell') for x in row])
    x=Table(data,colWidths=widths,hAlign='LEFT',repeatRows=1 if header else 0)
    cmds=[('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),
          ('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),5),
          ('BOTTOMPADDING',(0,0),(-1,-1),5),('LINEBELOW',(0,0),(-1,-1),.4,RULE)]
    if header:cmds += [('BACKGROUND',(0,0),(-1,0),PALE),('LINEBELOW',(0,0),(-1,0),1,TEAL)]
    x.setStyle(TableStyle(cmds));return x

def draw_header(canvas,doc):
    width,height=A4
    canvas.saveState()
    canvas.setFillColor(DARK);canvas.rect(0,height-9*mm,width,9*mm,stroke=0,fill=1)
    canvas.setStrokeColor(RULE);canvas.line(18*mm,19*mm,width-18*mm,19*mm)
    canvas.setFont(FONT,7);canvas.setFillColor(GREY)
    canvas.drawString(18*mm,13.5*mm,'NQ / QUANTITATIVE MARKET RESEARCH / 12 NOV 2026')
    canvas.drawRightString(width-18*mm,13.5*mm,'PAGE %s'%doc.page)
    canvas.restoreState()

def money(x):
    return ('-' if x<0 else '')+'$'+format(abs(x),',.0f')

def pct(x):return f'{x:+.2f}%'

def create_chart(daily:pd.DataFrame,out:Path,test_start:pd.Timestamp):
    o=daily.loc[daily.index>=test_start]
    capital=250000.0
    a=capital+o.strategy_net_usd.cumsum()
    b=capital+o.benchmark_net_usd.cumsum()
    fig,ax=plt.subplots(figsize=(9.1,3.6),dpi=180)
    ax.plot(a.index,a.values,label='20/100 SMA strategy',linewidth=2,color='#008c86')
    ax.plot(b.index,b.values,label='Always-long 1 NQ benchmark',linewidth=2,color='#bd8a35')
    ax.axhline(capital,ls='--',color='#8794a6',lw=.9)
    ax.set_ylabel('Model account equity (USD)')
    ax.grid(alpha=.18)
    ax.legend(loc='upper left',frameon=False,fontsize=8)
    ax.spines[['top','right']].set_visible(False)
    ax.tick_params(labelsize=8)
    fig.autofmt_xdate()
    fig.tight_layout(pad=1.0)
    fig.savefig(out,dpi=180,bbox_inches='tight',facecolor='white')
    plt.close(fig)

def create_report(out_file:str|Path,metrics:dict|None=None,daily:pd.DataFrame|None=None,
                  trades:pd.DataFrame|None=None):
    """Create a findings report when real outputs exist, or an honest preregistration brief."""
    from analysis import Config
    p=Path(out_file);p.parent.mkdir(parents=True,exist_ok=True)
    doc=SimpleDocTemplate(str(p),pagesize=A4,leftMargin=18*mm,rightMargin=18*mm,
                          topMargin=17*mm,bottomMargin=23*mm)
    usable=A4[0]-36*mm
    s=[Spacer(1,2*mm),P('INDEPENDENT RESEARCH  /  NASDAQ-100 E-MINI FUTURES','eyebrow'),
       P('NASDAQ Futures<br/>Quantitative Research Report','title'),
       P('Daily trend-following strategy, transaction-cost model, chronological evaluation and data-quality audit.','subtitle'),
       HRFlowable(width='100%',thickness=1,color=TEAL,spaceAfter=12)]
    if metrics is None or daily is None:
        s += [P('Status: methodology only','h'),P('Real historical results have not been supplied. Run python run.py --csv nq_daily.csv to generate a completed findings report. No returns are invented.'),
              P('The data model has documented roll and point-in-time limitations.','p')]
        doc.build(s,onFirstPage=draw_header,onLaterPages=draw_header);return p
    m=metrics; data=m['data'];st=m['out_of_sample_strategy'];bm=m['out_of_sample_benchmark']
    delta=st['total_pnl_usd']-bm['total_pnl_usd']
    flag=data['data_quality']
    s += [P('EXECUTIVE FINDING','eyebrow'),
          P('<b>Positive simulated strategy P&amp;L, but significant underperformance versus the always-long benchmark.</b> The fixed 20/100-session moving-average rule produced '+money(st['total_pnl_usd'])+' over the chronological 2023-2026 evaluation period. Holding one NQ contract long produced '+money(bm['total_pnl_usd'])+' on the same $250,000 reference capital and contract-multiplier basis. The strategy therefore lagged by '+money(abs(delta))+'.'),
          table([['Held-out metric (2023 - Nov 2026)','20/100 SMA','Always-long NQ'],
                ['Net simulated P&amp;L',money(st['total_pnl_usd']),money(bm['total_pnl_usd'])],
                ['Simple P&amp;L / start capital',pct(st['return_pct']),pct(bm['return_pct'])],
                ['Daily-P&amp;L Sharpe (0% benchmark)',f"{st['sharpe']:.2f}",f"{bm['sharpe']:.2f}"],
                ['Max model-equity drawdown',f"{st['max_drawdown_pct']:.2f}%",f"{bm['max_drawdown_pct']:.2f}%"],
                ['Annualised P&amp;L volatility',f"{st['annual_vol_pct']:.2f}%",f"{bm['annual_vol_pct']:.2f}%"]],
                [usable*.5,usable*.25,usable*.25]),
          Spacer(1,5*mm),
          P('Interpretation','h'),
          P('The strategy did <b>not</b> meet the research hypothesis of improving risk-adjusted performance. It produced a much lower Sharpe ratio, a deeper drawdown, and substantially less net P&amp;L than the comparison. These simulated dollar amounts are not live profits and are not a compounded investment return.'),
          P('Study window and trading assumptions','h'),
          P('The source spans <b>'+data['start']+' to '+data['end']+'</b> ('+format(data['bars'],',')+' daily bars). 2019-2022 is the research development window; 2023 onward is a chronological evaluation of fixed rules. Positions use the previous close signal, enter at the next recorded open, and accrue modelled open-to-next-open futures P&amp;L. The model holds one $20-per-index-point NQ contract and charges $7.50 per execution side.'),
          P('Evidence level: <b>illustrative</b>. The Yahoo-derived continuous NQ=F series has unverified roll adjustments, a source snapshot without a historical point-in-time audit, and no authenticated contract-chain execution path. Do not treat the figures as a genuinely tradable track record.','small')]

    s += [PageBreak(),P('PERFORMANCE  /  CHRONOLOGICAL EVALUATION','eyebrow'),
          P('Strategy versus benchmark','title')]
    chart=p.parent/'strategy_vs_benchmark.png'
    create_chart(daily,chart,pd.Timestamp(data['split']))
    s.append(Image(str(chart),width=usable,height=usable*0.40))
    s.append(P('Figure 1. Both curves start at $250,000 on the evaluation window; net simulated P&amp;L includes assumed entry/reversal costs. The always-long futures baseline is leveraged exposure, not the cash Nasdaq-100 index.','small'))
    oos=daily.loc[daily.index>=pd.Timestamp(data['split'])]
    rows=[['Calendar year','Trend strategy','Always-long NQ','Difference']]
    for yr,part in oos.groupby(oos.index.year):
        a=float(part.strategy_net_usd.sum());b=float(part.benchmark_net_usd.sum())
        rows.append([str(yr),money(a),money(b),money(a-b)])
    s += [P('Year-by-year comparison','h'),table(rows,[usable*.22,usable*.25,usable*.27,usable*.26]),
          P('The trend rule matched the long benchmark in 2024 because its exposure remained long throughout that year. Most of the evaluation-period gap developed during periods when the trend rule was short or changed direction while the baseline stayed long. In 2026 through 11 November, the modelled strategy lost '+money(abs(float(oos.loc[oos.index.year==2026].strategy_net_usd.sum())))+' while the long baseline gained '+money(float(oos.loc[oos.index.year==2026].benchmark_net_usd.sum()))+'. This is an attribution observation rather than proof of a causal mechanism.'),
          P('Trade-level diagnostics','h'),
          P('Completed evaluation-period trades: <b>'+str(m['out_of_sample_closed_trade_count'])+'</b>; completed-trade win rate: <b>'+f"{m['out_of_sample_closed_trade_win_rate_pct']:.1f}%"+'</b>. One position remains open at the final recorded open and is excluded from the completed-trade win rate. A nine-trade sample is too small to establish a reliable win probability. The initial training-period trade ledger is kept separately in the CSV output.')]
    s += [PageBreak(),P('VALIDATION  /  MARKET BEHAVIOUR','eyebrow'),
          P('Statistical evidence and<br/>data-quality audit','title'),
          P('Exploratory daily-return diagnostics','h')]
    stat=m['statistics']
    s += [table([['Indicator','Result','What this suggests'],
                ['Mean return after prior up day',f"{stat['next_return_after_up_mean_pct']:.3f}%",'Descriptive, not a trading signal'],
                ['Mean return after prior down day',f"{stat['next_return_after_down_mean_pct']:.3f}%",'Difference can be sample-driven'],
                ['Welch two-sample p-value',f"{stat['welch_p_value_exploratory']:.4f}",'Not below the usual 0.05 threshold'],
                ['Lag-one absolute-return correlation',f"{stat['absolute_return_lag1_correlation']:.3f}",'Some volatility clustering in sample'],
                ['Pearson exploratory p-value',f"{stat['volatility_clustering_p_value_exploratory']:.2e}",'Naive inference; serial dependence matters']],
                [usable*.38,usable*.18,usable*.44]),
          Spacer(1,2*mm),
          P('The Welch test provides no conventional 5% significance for a return-direction difference. The positive lag-one absolute-return correlation is consistent with volatility clustering; the reported p-value assumes a textbook sampling model and does not establish predictive tradeability. The study includes no multiple-testing or dependence-robust correction.'),
          P('Historical data screening','h'),
          table([['Validation measure','Result'],
                ['Daily records and range',f"{data['bars']} rows; {data['start']} - {data['end']}"],
                ['Flagged unusually large daily gaps',str(flag['flagged_price_discontinuity_days'])],
                ['Absolute open-to-open moves above 8%',str(flag['open_to_open_over_8pct_days'])],
                ['Absolute previous-close-to-open gaps above 2%',str(flag['close_to_open_gap_over_2pct_days'])],
                ['Bars with at least one off-grid price',str(flag['off_tick_ohlc_bars'])]],
                [usable*.7,usable*.3]),
          Spacer(1,2*mm),
          P('Flags are screening alerts, not confirmed bad prices. Several of the largest daily movements occur during March 2020 and April 2025; these could reflect volatile markets, contract transitions, data construction or combinations of them. This project does <b>not</b> independently verify which. The numerical results therefore remain indicative and cannot be claimed to be fully roll-safe.'),
          P('Data representation','h'),
          P('The packaged CSV reproduces the public archive\'s daily Date/Open/High/Low/Close/Volume records, rounding OHLC prices to two decimals. This cent rounding makes it a <b>derived snapshot</b>, not byte-identical source data. The original is available at github.com/Chief-rich/nasdaq100-data/blob/main/data/nq_daily/history.csv. The packaged derived series was cross-checked against the archive to cent precision using a whole-series rolling checksum.'),]
    s += [PageBreak(),P('REPRODUCIBILITY  /  MODEL GOVERNANCE','eyebrow'),
          P('Execution design, sensitivity<br/>and limitations','title'),
          P('01 - Return construction and terminal treatment','h'),
          P('Each completed date t produces a 20/100 close-based signal. The position is taken no earlier than open(t+1) and earns open-to-open price movement only while that position is held. Changes at an observed open incur one execution side for a flat-to-position change and two sides for a reversal. The final observed open is retained for the closed-trade ledger and execution costs; no unobserved next-open return is fabricated. Any still-open trade is excluded from closed-trade statistics.'),
          P('02 - Transaction-cost stress test','h')]
    cost_rows=[['Cost per side','OOS net P&amp;L','OOS Sharpe']]
    for side,x in m['transaction_cost_sensitivity'].items():
        cost_rows.append([f'${float(side):.2f}',money(x['total_pnl_usd']),f"{x['sharpe']:.3f}"])
    s += [table(cost_rows,[usable*.25,usable*.38,usable*.37]),
          P('Transaction costs modestly affect this low-turnover model, but real market impact, variable slippage, contract-roll trades, margin policy and potential liquidation are not modelled. Cost stress alone does not certify implementability.'),
          P('03 - What is deliberately not claimed','h'),
          P('No exchange-authenticated contract-by-contract prices or verified back-adjustment schedule; no audited execution fills; no interest on collateral, financing, margin calls, taxes or detailed exchange fees; no trade capacity analysis. The 2023+ evaluation is chronological but <b>not</b> a prospectively sealed, out-of-time experiment. Statistical significance can be distorted by serial dependence and model selection.'),
          P('04 - How to reproduce and independently inspect','h'),
          table([['Action','Location / command'],
                ['Install','python -m pip install -r requirements.txt'],
                ['Test terminal trade accounting','python -m pytest -q'],
                ['Run archived snapshot','python run.py --csv nq_daily.csv'],
                ['Review underlying observations','outputs/daily_backtest.csv; outputs/closed_trades.csv'],
                ['See visual research dashboard','Open_Dashboard.html or outputs/dashboard_results.html'],
                ['Review flagged dates','outputs/data_quality_flags.csv']],
                [usable*.35,usable*.65]),
          P('05 - Conclusion and next research step','h'),
          P('On this specific continuous-futures source, a basic daily 20/100 SMA signal does not outperform simply holding one NQ futures contract long across the 2023-2026 evaluation. A more credible institutional research extension would reconstruct a point-in-time contract chain with an explicit roll policy, margin and collateral rules, then retest on a newly reserved forward period.'),
          ]
    doc.build(s,onFirstPage=draw_header,onLaterPages=draw_header)
    return p
