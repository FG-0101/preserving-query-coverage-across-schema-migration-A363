"""What the published aggregates show and hide: record level archives against the aggregates of the same day.

For every archive day, totals and keyword counts of the record level data are compared with the official complete
aggregate of the same day. Keywords that exist as columns in the aggregates must match exactly; keywords without a
column are invisible in the aggregates. Platform names are matched by exact daily totals where they differ.
Run from the package root after code/01 and code/02:  python3 code/03_validate.py
Outputs: results/validation_days.csv, results/validation_keywords.csv, results/hidden_by_category.csv,
results/keyword_platform_window.csv,
results/platform_names.csv, results/validation.json
"""
import glob
import json
import re
from collections import Counter
import numpy as np
import pandas as pd
from common import load_dumps, load_agg, CUT

d = load_dumps()
idx = pd.read_csv("data/derived/dump_index.csv")
expected_days=set(idx.date)
available_days=set(d.d.dt.strftime("%Y-%m-%d"))
from pathlib import Path
file_days={f.stem.removeprefix('dump_') for f in Path('data/derived').glob('dump_20*.parquet')}
assert expected_days == file_days, (expected_days-file_days,file_days-expected_days)
assert expected_days.issubset(available_days), expected_days-available_days
days = sorted(pd.to_datetime(idx.date[idx.date.isin(d.d.dt.strftime("%Y-%m-%d").unique())]))
months = sorted(set(pd.Timestamp(x).strftime("%Y-%m") for x in days))
k = load_agg(months)
k = k[k.d.isin(days)]
agg_cols = [c for c in k.columns if c.startswith("KEYWORD_")]
cols_log = pd.read_csv("data/derived/complete_columns.csv", header=None, names=["month", "n_kw", "n_add", "kw"])
out = {"days": len(days), "months_columns_identical": int(cols_log.kw.nunique() == 1), "agg_keyword_columns": len(agg_cols)}

# platform name matching by exact daily totals
pd_d = d.groupby(["p", "d"]).n.sum().reset_index()
pd_k = k.groupby(["p", "d"]).n.sum().reset_index()
names = []
for p in sorted(set(pd_d.p) - set(pd_k.p)):
    a = pd_d[pd_d.p == p].set_index("d").n
    candidates = []
    for q in sorted(set(pd_k.p) - set(pd_d.p)):
        b = pd_k[pd_k.p == q].set_index("d").n
        both = a.index.intersection(b.index)
        if len(both) >= 3 and (a[both] == b[both]).all():
            candidates.append((q,len(both)))
    assert len(candidates) == 1, (p,candidates)
    best,matched_days = candidates[0]
    names.append(dict(dump_name=p, aggregate_name=best, matched_days=matched_days, candidate_count=len(candidates)))
names = pd.DataFrame(names)
names.to_csv("results/platform_names.csv", index=False)
out["renamed_platforms"] = int(names.aggregate_name.notna().sum())
out["unmatched_platforms"] = int(names.aggregate_name.isna().sum())

rows, kwrows = [], []
for day in days:
    dd = d[d.d == day]
    kk = k[k.d == day]
    cnt = Counter()
    for t, n in zip(dd.kws, dd.n):
        for x in t:
            cnt[x] += n
    vis_specific = sum(v for x, v in cnt.items() if x in agg_cols and x != "KEYWORD_OTHER")
    all_specific = sum(v for x, v in cnt.items() if x != "KEYWORD_OTHER")
    rec_spec = dd[dd.spec_any].n.sum()
    rec_spec_vis = dd[dd.kws.map(lambda t: any(x in agg_cols and x != "KEYWORD_OTHER" for x in t))].n.sum()
    diffs = [abs(cnt.get(x, 0) - kk[x].sum()) for x in agg_cols]
    listed = float(idx.loc[idx.date == pd.Timestamp(day).strftime("%Y-%m-%d"), "statements"].iloc[0])
    rows.append(dict(d=pd.Timestamp(day).date(), post=bool(pd.Timestamp(day) >= CUT), records_listed=listed, records_dump=float(dd.n.sum()),
                     records_agg=float(kk.n.sum()), max_abs_diff_shared_kw=float(max(diffs)),
                     agg_any_kw=float(kk.any_kw.sum()), rec_specific=float(rec_spec), rec_specific_visible=float(rec_spec_vis),
                     mentions_specific=float(all_specific), mentions_specific_visible=float(vis_specific)))
    for x, v in cnt.items():
        kwrows.append(dict(d=pd.Timestamp(day).date(), post=bool(pd.Timestamp(day) >= CUT), kw=x, n=float(v), in_aggregate=x in agg_cols))
val = pd.DataFrame(rows)
val["hidden_record_share"] = 1 - val.rec_specific_visible / val.rec_specific
val["hidden_mention_share"] = 1 - val.mentions_specific_visible / val.mentions_specific
val["rel_diff_records"] = (val.records_dump - val.records_agg).abs() / val.records_agg
val.to_csv("results/validation_days.csv", index=False)
kw = pd.DataFrame(kwrows)
kw.to_csv("results/validation_keywords.csv", index=False)

# by category, pooled over post migration days
post = d[d.d >= CUT]
hc = []
for c, g in post.groupby("c"):
    spec = g[g.spec_any].n.sum()
    vis = g[g.kws.map(lambda t: any(x in agg_cols and x != "KEYWORD_OTHER" for x in t))].n.sum()
    hc.append(dict(c=c, records=float(g.n.sum()), rec_specific=float(spec), rec_specific_visible=float(vis)))
hc = pd.DataFrame(hc).sort_values("records", ascending=False)
hc["hidden_share"] = 1 - hc.rec_specific_visible / hc.rec_specific
hc.to_csv("results/hidden_by_category.csv", index=False)

# category additions: the complete aggregates carry one boolean column per category addition value of the old schema
allcols = pd.read_csv("data/derived/complete_all_columns.csv")
add_cols = set(allcols[allcols.column.str.startswith("STATEMENT_CATEGORY_")].column)
cats = lambda s: tuple(sorted(set(re.findall(r"STATEMENT_CATEGORY_[A-Z_]+", s)))) if isinstance(s, str) else ()
post_add = post.assign(adds=post.c_add.map(cats))
post_add = post_add[post_add.adds.map(len) > 0]
hid_any = post_add.adds.map(lambda t: any(x not in add_cols for x in t))
hid_all = post_add.adds.map(lambda t: all(x not in add_cols for x in t))
hidden_vals = Counter()
for t, n in zip(post_add[hid_any].adds, post_add[hid_any].n):
    kinds = set("renamed residual" if x == "STATEMENT_CATEGORY_OTHER_VIOLATION_TC" else
                "renamed products" if x == "STATEMENT_CATEGORY_UNSAFE_AND_PROHIBITED_PRODUCTS" else "new"
                for x in t if x not in add_cols)
    for kd in kinds:
        hidden_vals[kd] += n
# keyword mentions by platform in the four weeks before and after the cutoff (for the examples in the text)
wk = d[(d.d >= CUT - pd.Timedelta(days=28)) & (d.d < CUT + pd.Timedelta(days=28))]
kwp = Counter()
for p_, dd_, t, n in zip(wk.p, wk.d, wk.kws, wk.n):
    for x in t:
        kwp[(p_, x, bool(dd_ >= CUT))] += n
kwp = pd.DataFrame([dict(p=a, kw=b, post=c_, n=float(v)) for (a, b, c_), v in kwp.items()])
kwp.to_csv("results/keyword_platform_window.csv", index=False)
out.update({"add_hidden_renamed_residual": float(hidden_vals["renamed residual"]),
            "add_hidden_renamed_products": float(hidden_vals["renamed products"]), "add_hidden_new": float(hidden_vals["new"])})
out.update({"add_columns": len(add_cols), "post_statements": float(post.n.sum()), "post_with_addition": float(post_add.n.sum()),
            "post_addition_some_hidden": float(post_add[hid_any].n.sum()), "post_addition_all_hidden": float(post_add[hid_all].n.sum()),
            "records_reduced_total": float(sum(pd.read_parquet(f).n.sum() for f in sorted(glob.glob("data/derived/dump_20*.parquet"))))})

pre_v, post_v = val[~val.post], val[val.post]
kp = kw[kw.post].groupby(["kw", "in_aggregate"]).n.sum().reset_index().sort_values("n", ascending=False)
val["rel_diff_records"] = (val.records_dump - val.records_agg).abs() / val.records_agg
out.update({"records_equal_all_days": bool((val.records_dump == val.records_agg).all()),
            "records_equal_days": int((val.records_dump == val.records_agg).sum()),
            "max_rel_diff_records": float(val.rel_diff_records.max()), "max_abs_diff_records": float((val.records_dump - val.records_agg).abs().max()),
            "max_abs_diff_shared_kw": float(val.max_abs_diff_shared_kw.max()),
            "shared_kw_exact_all_days": bool((val.max_abs_diff_shared_kw == 0).all()),
            "shared_kw_exact_days": int((val.max_abs_diff_shared_kw == 0).sum()),
            "agg_equals_listed_days": int((val.records_agg == val.records_listed).sum()),
            "max_rel_diff_agg_listed": float(((val.records_agg - val.records_listed).abs() / val.records_listed).max()),
            "agg_anykw_equals_visible": bool((val.agg_any_kw == val.rec_specific_visible).all()),
            "pre_hidden_record_share_max": float(pre_v.hidden_record_share.max()),
            "post_hidden_record_share_mean": float((post_v.rec_specific - post_v.rec_specific_visible).sum() / post_v.rec_specific.sum()),
            "post_hidden_mention_share_mean": float((post_v.mentions_specific - post_v.mentions_specific_visible).sum() / post_v.mentions_specific.sum()),
            "post_hidden_record_share_min": float(post_v.hidden_record_share.min()), "post_hidden_record_share_max": float(post_v.hidden_record_share.max()),
            "post_keywords_seen": int(kp.kw.nunique()), "post_keywords_hidden": int((~kp.in_aggregate).sum()),
            "post_hidden_records_total": float((post_v.rec_specific - post_v.rec_specific_visible).sum()),
            "post_days": int(len(post_v)), "pre_days": int(len(pre_v))})
json.dump(out, open("results/validation.json", "w"), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
print(val.round(4).to_string())
print(kp.head(30).to_string())
print(hc.round(3).to_string())
