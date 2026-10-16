"""Persistence: hidden keyword information and category use from August 2025 to September 2026.

For one Sunday per month after the migration (and the validation day), the share of statements with a keyword other than
KEYWORD_OTHER in the record level archive is compared with the share visible in the published aggregate of the same day,
and the use of new keywords is tracked. The complete aggregates give the daily series of the visible keyword share and of
the residual category share for the whole period from January 2025 to September 2026.
Run from the package root after code/03:  python3 code/06_longrun.py
Outputs: results/longrun_days.csv, results/longrun_agg_daily.csv, results/longrun.json
"""
import json
import numpy as np
import pandas as pd
from common import load_dumps, load_agg, CUT, RESIDUAL

d = load_dumps()
agg_cols = set(pd.read_csv("data/derived/complete_columns.csv", header=None).iloc[0, 3].split("|"))
idx = pd.read_csv("data/derived/dump_index.csv")
later = pd.to_datetime(idx.date)
later = later[later >= CUT + pd.Timedelta(days=28)]
rows = []
for day in later:
    g = d[d.d == day]
    if g.empty:
        continue
    n = g.n.sum()
    vis = g.kws.map(lambda t: any(k in agg_cols and k != "KEYWORD_OTHER" for k in t))
    new = g.kws.map(lambda t: any(k not in agg_cols for k in t))
    rows.append(dict(d=day.date(), n=float(n), spec_share=float(g[g.spec_any].n.sum() / n), spec_visible_share=float(g[vis].n.sum() / n),
                     new_kw_share=float(g[new].n.sum() / n), resid_share=float(g[g.resid].n.sum() / n),
                     hidden_of_spec=float(1 - g[vis].n.sum() / g[g.spec_any].n.sum()) if g[g.spec_any].n.sum() else np.nan,
                     platforms_new_kw=int(g[new].p.nunique()), platforms=int(g.p.nunique()), x_n=float(g[g.p == "X"].n.sum())))
lr = pd.DataFrame(rows)
lr.to_csv("results/longrun_days.csv", index=False)
k = load_agg()
k["resid"] = k.c.isin(RESIDUAL)
daily = k.groupby("d").apply(lambda g: pd.Series({"n": g.n.sum(), "spec_visible_share": g.any_kw.fillna(0).sum() / g.n.sum(),
                                                  "resid_share": g[g.resid].n.sum() / g.n.sum()}), include_groups=False).reset_index()
daily = daily[daily.d <= pd.Timestamp("2026-09-30")]
daily.to_csv("results/longrun_agg_daily.csv", index=False)
out = {"days": int(len(lr)), "hidden_of_spec_min": float(lr.hidden_of_spec.min()), "hidden_of_spec_max": float(lr.hidden_of_spec.max()),
       "hidden_of_spec_median": float(lr.hidden_of_spec.median()), "new_kw_share_max": float(lr.new_kw_share.max()),
       "platforms_new_kw_max": int(lr.platforms_new_kw.max()),
       "platforms_new_kw_min": int(lr.platforms_new_kw.min()), "platforms_min": int(lr.platforms.min()), "platforms_max": int(lr.platforms.max()),
       "x_n_min": float(lr.x_n.min()), "x_n_max": float(lr.x_n.max()), "x_n_first": float(lr.x_n.iloc[0]),
       "spec_share_median": float(lr.spec_share.median()), "spec_visible_share_median": float(lr.spec_visible_share.median()), "first_day": str(lr.d.min()), "last_day": str(lr.d.max())}
json.dump(out, open("results/longrun.json", "w"), indent=1)
print(json.dumps(out, indent=1))
print(lr.round(4).to_string())
