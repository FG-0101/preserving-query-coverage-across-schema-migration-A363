"""Regression discontinuity in time at the 1 July 2025 schema migration, platform by platform and pooled.

Outcomes per platform and day, from the record level archives (H days on each side of the cutoff):
  resid    share of statements in a residual category (scope of platform service before, other violation of terms and
           conditions or not specified notice after);
  spec     share of statements with at least one keyword other than KEYWORD_OTHER (all keywords, old and new);
  inform   share of statements with a non residual category or such a keyword;
  eff      effective number of categories, the exponential of the Shannon entropy of the category distribution;
  spec_vis the keyword share as the published aggregates show it (keywords with an aggregate column only).
Model: y = a + b post + c t + d t post + day of week effects, t in days from the cutoff, ordinary least squares with
heteroskedasticity and autocorrelation consistent standard errors (Newey and West, 7 lags). b is the jump.
Two pooled series: all statements of all platforms (statement weighted) and the unweighted mean over the platforms kept
for the platform analysis (platform weighted).
Placebo: the same model at every day from 29 January to 3 June 2025 as a fake cutoff, on the complete aggregates of
January to June 2025 (days before the cutoff only), which contain all keywords of the old schema. Fake cutoffs whose
window would not be complete are skipped. The placebo tail fraction value is the share of placebo jumps
at least as large in absolute value as the actual jump (with one added to numerator and denominator). A platform jump
counts as material when p < 0.05 and its size is at least one percentage point (0.1 for the effective number). The
number of platforms that remain significant after the Benjamini and Hochberg correction at q = 0.05 is also reported.
Bandwidths 14, 21 and 28 days; 28 is the main specification.
Run from the package root after code/01 to code/03:  python3 code/04_rd.py
Outputs: results/rd_platform.csv, results/rd_pooled.csv, results/rd_placebo.csv, results/rd_placebo_nopin.csv,
results/rd_series.csv, results/rd_robustness.csv, results/pinterest_gap.json,
results/rd_bandwidth.csv, results/rd.json
"""
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from common import load_dumps, load_agg, CUT, RESIDUAL, entropy_effective

HS = [28, 21, 14]
H = 28
MIN_N = 1000
HAC_LAGS = 7
BH_Q = 0.05
OUTS = ["resid", "spec", "inform", "eff", "spec_vis"]
MATERIAL = {"resid": 0.01, "spec": 0.01, "inform": 0.01, "eff": 0.1, "spec_vis": 0.01}
d = load_dumps()
agg_cols = set(pd.read_csv("data/derived/complete_columns.csv", header=None).iloc[0, 3].split("|"))
d["spec_vis"] = d.kws.map(lambda t: any(k in agg_cols and k != "KEYWORD_OTHER" for k in t))
win = d[(d.d >= CUT - pd.Timedelta(days=H)) & (d.d < CUT + pd.Timedelta(days=H))]


def measures_dump(g):
    n = g.n.sum()
    return pd.Series({"n": n, "resid": g[g.resid].n.sum() / n, "spec": g[g.spec_any].n.sum() / n,
                      "inform": g[(~g.resid) | g.spec_any].n.sum() / n, "eff": entropy_effective(g.groupby("c").n.sum().values),
                      "spec_vis": g[g.spec_vis].n.sum() / n})


def design(dates, cut):
    t = ((dates - cut).dt.days).values.astype(float)
    post = (t >= 0).astype(float)
    dow = np.zeros((len(t), 6))
    for j in range(6):
        dow[:, j] = (dates.dt.dayofweek.values == j + 1).astype(float)
    return np.column_stack([np.ones_like(t), post, t, t * post, dow])


def rd(y, dates, cut):
    """Jump and HAC standard error."""
    X = design(dates, cut)
    ok = np.isfinite(y)
    if ok.sum() < 20:
        return np.nan, np.nan
    m = sm.OLS(y[ok], X[ok]).fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS})
    return float(m.params[1]), float(m.bse[1])


def rd_b(y, dates, cut):
    """Jump only, for the placebo distribution."""
    X = design(dates, cut)
    ok = np.isfinite(y)
    if ok.sum() < 20:
        return np.nan
    return float(np.linalg.lstsq(X[ok], y[ok], rcond=None)[0][1])


panel = win.groupby(["p", "d"]).apply(measures_dump, include_groups=False).reset_index()
pooled = win.groupby("d").apply(measures_dump, include_groups=False).reset_index()
pooled["p"] = "All platforms"

keep = []
for p, g in panel.groupby("p"):
    pre, post = g[g.d < CUT], g[g.d >= CUT]
    if len(g) < 2 * H - 6 or pre.n.mean() < MIN_N or post.n.mean() < MIN_N:
        continue
    keep.append(p)
avg = panel[panel.p.isin(keep)].groupby("d")[OUTS].mean().reset_index()
avg["n"] = panel[panel.p.isin(keep)].groupby("d").n.sum().values
avg["p"] = "Platform average"

# placebo series from the complete aggregates of the old schema
names = pd.read_csv("results/platform_names.csv")
to_dump = dict(zip(names.aggregate_name, names.dump_name))
k = load_agg(["2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06"])
k = k[k.d < CUT]
k["p"] = k.p.map(lambda x: to_dump.get(x, x))
k["resid"] = k.c.isin(RESIDUAL)


def measures_agg(g):
    n = g.n.sum()
    spec = g.any_kw.fillna(0).sum()
    inform = g[~g.resid].n.sum() + g[g.resid].any_kw.fillna(0).sum()
    return pd.Series({"n": n, "resid": g[g.resid].n.sum() / n, "spec": spec / n, "inform": inform / n,
                      "eff": entropy_effective(g.groupby("c").n.sum().values), "spec_vis": spec / n})


kp = k[k.p.isin(keep)].groupby(["p", "d"]).apply(measures_agg, include_groups=False).reset_index()
kall = k.groupby("d").apply(measures_agg, include_groups=False).reset_index()
kall["p"] = "All platforms"
kavg = kp.groupby("d")[OUTS].mean().reset_index()
kavg["p"] = "Platform average"
fakes = pd.date_range("2025-01-29", "2025-06-03")


def placebo(series, h):
    out = []
    for p, g in series.groupby("p"):
        g = g.sort_values("d")
        for fc in fakes:
            w = g[(g.d >= fc - pd.Timedelta(days=h)) & (g.d < fc + pd.Timedelta(days=h))]
            if len(w) < 2 * h - 6:
                continue
            r = {"p": p, "cut": fc, "h": h}
            for o in OUTS:
                r[o] = rd_b(w[o].values.astype(float), w.d, fc)
            out.append(r)
    return pd.DataFrame(out)


def perm_p(plc, p, o, jump):
    z = plc[plc.p == p][o].dropna().abs()
    return ((1 + (z >= abs(jump)).sum()) / (1 + len(z)) if len(z) else np.nan), len(z)


all_plc, bw_rows, res_main, pool_main = [], [], None, None
for h in HS:
    lo, hi = CUT - pd.Timedelta(days=h), CUT + pd.Timedelta(days=h)
    plc = placebo(pd.concat([kp, kall, kavg]), h)
    all_plc.append(plc)
    rows = []
    for p in keep:
        g = panel[(panel.p == p) & (panel.d >= lo) & (panel.d < hi)].sort_values("d")
        pre, post = g[g.d < CUT], g[g.d >= CUT]
        row = {"p": p, "h": h, "days": len(g), "n_pre": float(pre.n.mean()), "n_post": float(post.n.mean())}
        for o in OUTS:
            b, se = rd(g[o].values.astype(float), g.d, CUT)
            pv, npl = perm_p(plc, p, o, b)
            row.update({f"{o}_jump": b, f"{o}_se": se, f"{o}_pre": float(pre[o].mean()), f"{o}_post": float(post[o].mean()),
                        f"{o}_p_perm": pv, f"{o}_n_placebo": npl})
        rows.append(row)
    res = pd.DataFrame(rows)
    prow = []
    for name, ser in [("All platforms", pooled), ("Platform average", avg)]:
        g = ser[(ser.d >= lo) & (ser.d < hi)].sort_values("d")
        for o in OUTS:
            b, se = rd(g[o].values.astype(float), g.d, CUT)
            pv, npl = perm_p(plc, name, o, b)
            prow.append({"series": name, "h": h, "outcome": o, "jump": b, "se": se, "p_perm": pv, "n_placebo": npl,
                         "pre": float(g[g.d < CUT][o].mean()), "post": float(g[g.d >= CUT][o].mean())})
    prow = pd.DataFrame(prow)
    for o in OUTS:
        mat = (res[f"{o}_p_perm"] < 0.05) & (res[f"{o}_jump"].abs() >= MATERIAL[o])
        bw_rows.append({"h": h, "outcome": o, "material_up": int((mat & (res[f"{o}_jump"] > 0)).sum()),
                        "material_down": int((mat & (res[f"{o}_jump"] < 0)).sum()),
                        "p05_up": int(((res[f"{o}_p_perm"] < 0.05) & (res[f"{o}_jump"] > 0)).sum()),
                        "p05_down": int(((res[f"{o}_p_perm"] < 0.05) & (res[f"{o}_jump"] < 0)).sum()),
                        **{f"{s}_{c}": float(prow[(prow.series == s) & (prow.outcome == o)][c].iloc[0])
                           for s in ["All platforms", "Platform average"] for c in ["jump", "se", "p_perm"]}})
    if h == H:
        res_main, pool_main = res, prow
bw = pd.DataFrame(bw_rows)
bw.to_csv("results/rd_bandwidth.csv", index=False)
res_main.to_csv("results/rd_platform.csv", index=False)
pool_main.to_csv("results/rd_pooled.csv", index=False)
pd.concat(all_plc).to_csv("results/rd_placebo.csv", index=False)
pd.concat([panel, pooled, avg]).to_csv("results/rd_series.csv", index=False)


# Robustness at the main bandwidth.
# 1. placebo cutoffs whose windows touch 14 to 19 March 2025 dropped (Google Shopping is absent from the aggregates on
#    these days), and in addition those whose windows contain 30 May 2025 (change in Google Shopping submissions);
# 2. the cutoff day itself dropped from every series, with the placebo jumps computed the same way;
# 3. Pinterest, which had a reporting gap from 14 to 23 June 2025 followed by a backlog, removed from every day of the
#    window and of the placebo series (also at bandwidths 21 and 14);
# 4. the calendar days from 14 to 27 June 2025 dropped for all platforms.
OUTAGE = (pd.Timestamp("2025-03-14"), pd.Timestamp("2025-03-19"))
GS_CHANGE = pd.Timestamp("2025-05-30")
GAP = ("Pinterest", pd.Timestamp("2025-06-14"), pd.Timestamp("2025-06-27"))
lo, hi = CUT - pd.Timedelta(days=H), CUT + pd.Timedelta(days=H)
plc_main = all_plc[0]
touch_outage = (plc_main.cut - pd.Timedelta(days=H) <= OUTAGE[1]) & (plc_main.cut + pd.Timedelta(days=H) > OUTAGE[0])
has_change = (plc_main.cut - pd.Timedelta(days=H) <= GS_CHANGE) & (plc_main.cut + pd.Timedelta(days=H) > GS_CHANGE)
plc_clean1 = plc_main[~touch_outage]
plc_clean2 = plc_main[~touch_outage & ~has_change]


def placebo_donut(series, h):
    out = []
    for p, g in series.groupby("p"):
        g = g.sort_values("d")
        for fc in fakes:
            w = g[(g.d >= fc - pd.Timedelta(days=h)) & (g.d < fc + pd.Timedelta(days=h)) & (g.d != fc)]
            if len(w) < 2 * h - 7:
                continue
            r = {"p": p, "cut": fc, "h": h}
            for o in OUTS:
                r[o] = rd_b(w[o].values.astype(float), w.d, fc)
            out.append(r)
    return pd.DataFrame(out)


plc_donut = placebo_donut(pd.concat([kp, kall, kavg]), H)
pooled_nopin = win[win.p != GAP[0]].groupby("d").apply(measures_dump, include_groups=False).reset_index()
avg_nopin = panel[panel.p.isin(keep) & (panel.p != GAP[0])].groupby("d")[OUTS].mean().reset_index()
kall_nopin = k[k.p != GAP[0]].groupby("d").apply(measures_agg, include_groups=False).reset_index()
kall_nopin["p"] = "All platforms"
kavg_nopin = kp[kp.p != GAP[0]].groupby("d")[OUTS].mean().reset_index()
kavg_nopin["p"] = "Platform average"
plc_nopin = {h: placebo(pd.concat([kall_nopin, kavg_nopin]), h) for h in HS}
daymask = lambda ser: ser[~((ser.d >= GAP[1]) & (ser.d <= GAP[2]))]
REL = ((GAP[1] - CUT).days, (GAP[2] - CUT).days)


def placebo_reldrop(series, h):
    """Placebo jumps with the same days relative to the fake cutoff dropped as in the variant without 14 to 27 June."""
    out = []
    for p, g in series.groupby("p"):
        g = g.sort_values("d")
        for fc in fakes:
            rel = (g.d - fc).dt.days
            w = g[(rel >= -h) & (rel < h) & ~((rel >= REL[0]) & (rel <= REL[1]))]
            if len(w) < 2 * h - 6 - (REL[1] - REL[0] + 1):
                continue
            r = {"p": p, "cut": fc, "h": h}
            for o in OUTS:
                r[o] = rd_b(w[o].values.astype(float), w.d, fc)
            out.append(r)
    return pd.DataFrame(out)


plc_days = placebo_reldrop(pd.concat([kall, kavg]), H)
variants = [("main", H, pooled, avg, plc_main, False), ("placebo without March outage", H, pooled, avg, plc_clean1, False),
            ("placebo without March outage and 30 May change", H, pooled, avg, plc_clean2, False),
            ("without the cutoff day", H, pooled, avg, plc_donut, True),
            ("without Pinterest", H, pooled_nopin, avg_nopin, plc_nopin[H], False),
            ("without 14 to 27 June", H, daymask(pooled), daymask(avg), plc_days, False)]
for h in HS:
    if h != H:
        variants.append(("bandwidth", h, pooled, avg, all_plc[HS.index(h)], False))
        variants.append(("without Pinterest", h, pooled_nopin, avg_nopin, plc_nopin[h], False))
rob = []
for vname, h, ser_all, ser_avg, plc_v, donut in variants:
    lo_h, hi_h = CUT - pd.Timedelta(days=h), CUT + pd.Timedelta(days=h)
    for name, ser in [("All platforms", ser_all), ("Platform average", ser_avg)]:
        g = ser[(ser.d >= lo_h) & (ser.d < hi_h)].sort_values("d")
        if donut:
            g = g[g.d != CUT]
        for o in OUTS:
            b, se = rd(g[o].values.astype(float), g.d, CUT)
            pv, npl = perm_p(plc_v, name, o, b)
            rob.append({"variant": vname, "h": h, "series": name, "outcome": o, "jump": b, "se": se, "p_perm": pv, "n_placebo": npl})
rob = pd.DataFrame(rob)
rob.to_csv("results/rd_robustness.csv", index=False)
# platform jumps without the cutoff day
for o in OUTS:
    jd, pdn = [], []
    for p in res_main.p:
        g = panel[(panel.p == p) & (panel.d >= lo) & (panel.d < hi) & (panel.d != CUT)].sort_values("d")
        b, _ = rd(g[o].values.astype(float), g.d, CUT)
        jd.append(b)
        pdn.append(perm_p(plc_donut, p, o, b)[0])
    res_main[f"{o}_jump_donut"] = jd
    res_main[f"{o}_p_donut"] = pdn
res_main.to_csv("results/rd_platform.csv", index=False)
# Pinterest diagnostics
pin = win[win.p == GAP[0]]
pd_ = pin.groupby("d").n.sum()
in_gap = (pd_.index >= GAP[1]) & (pd_.index <= GAP[2])
pin_pre, pin_post = pin[pin.d < CUT], pin[pin.d >= CUT]
sexw = pin[(pin.d >= GAP[1]) & (pin.d <= GAP[2]) & (pin.d <= pd.Timestamp("2025-06-23"))]
PIN = {"gap_first": "2025-06-14", "gap_last_low": "2025-06-23", "backlog_first": "2025-06-25", "backlog_last": "2025-06-27",
       "daily_pre_gap_min": float(pd_[(pd_.index < GAP[1])].min()), "daily_pre_gap_max": float(pd_[(pd_.index < GAP[1])].max()),
       "daily_gap_min": float(pd_["2025-06-14":"2025-06-23"].min()), "daily_gap_max": float(pd_["2025-06-14":"2025-06-23"].max()),
       "daily_backlog_min": float(pd_["2025-06-25":"2025-06-27"].min()), "daily_backlog_max": float(pd_["2025-06-25":"2025-06-27"].max()),
       "removed_share_gap": float(sexw[sexw.c.isin(["STATEMENT_CATEGORY_PORNOGRAPHY_OR_SEXUALIZED_CONTENT", "STATEMENT_CATEGORY_NON_CONSENSUAL_BEHAVIOUR"])].n.sum() / sexw.n.sum()),
       "spec_pooled_pre": float(pin_pre[pin_pre.spec_any].n.sum() / pin_pre.n.sum()),
       "spec_pooled_post": float(pin_post[pin_post.spec_any].n.sum() / pin_post.n.sum())}
json.dump(PIN, open("results/pinterest_gap.json", "w"), indent=1)


def bh(pv, q):
    """Benjamini and Hochberg rejections for a vector of p values (NaN never rejected)."""
    pv = np.asarray(pv, dtype=float)
    ok = np.isfinite(pv)
    out = np.zeros(len(pv), dtype=bool)
    p_ok = pv[ok]
    order = np.argsort(p_ok)
    m_ = len(p_ok)
    passed = np.where(p_ok[order] <= q * np.arange(1, m_ + 1) / m_)[0]
    if len(passed):
        rej = np.zeros(m_, dtype=bool)
        rej[order[:passed.max() + 1]] = True
        out[np.where(ok)[0]] = rej
    return out


S = {"platforms": int(len(res_main)), "window_days": 2 * H, "min_daily_n": MIN_N, "placebo_cutoffs": int(len(fakes)),
     "hac_lags": HAC_LAGS, "bh_q": BH_Q,
     "platforms_with_placebo": int((res_main.resid_n_placebo > 0).sum()), "material": MATERIAL}
for o in OUTS:
    b = bw[(bw.h == H) & (bw.outcome == o)].iloc[0]
    S[o] = {"material_up": int(b.material_up), "material_down": int(b.material_down), "p05_up": int(b.p05_up),
            "p05_down": int(b.p05_down), "median_jump": float(res_main[f"{o}_jump"].median())}
    rej = bh(res_main[f"{o}_p_perm"].values, BH_Q)
    S[o]["bh_up"] = int((rej & (res_main[f"{o}_jump"] > 0).values).sum())
    S[o]["bh_down"] = int((rej & (res_main[f"{o}_jump"] < 0).values).sum())
    mat = ((res_main[f"{o}_p_perm"] < 0.05) & (res_main[f"{o}_jump"].abs() >= MATERIAL[o])).values
    S[o]["bh_material_up"] = int((rej & mat & (res_main[f"{o}_jump"] > 0).values).sum())
    S[o]["bh_material_down"] = int((rej & mat & (res_main[f"{o}_jump"] < 0).values).sum())
    S[o]["material_not_bh"] = sorted(res_main.p[mat & ~rej].tolist())
    dmat = ((res_main[f"{o}_p_donut"] < 0.05) & (res_main[f"{o}_jump_donut"].abs() >= MATERIAL[o])).values
    S[o]["material_up_donut"] = int((dmat & (res_main[f"{o}_jump_donut"] > 0).values).sum())
    S[o]["material_down_donut"] = int((dmat & (res_main[f"{o}_jump_donut"] < 0).values).sum())
npl = res_main.resid_n_placebo
S["placebo_per_platform_min"] = int(npl[npl > 0].min())
S["placebo_per_platform_max"] = int(npl.max())
S["platforms_without_placebo"] = sorted(res_main.p[npl == 0].tolist())
S["platforms_short_placebo"] = int(((npl > 0) & (npl < len(fakes))).sum())
S["placebo_clean1"] = int(plc_clean1.cut.nunique())
S["placebo_clean2"] = int(plc_clean2.cut.nunique())
pd.concat(plc_nopin.values()).to_csv("results/rd_placebo_nopin.csv", index=False)
S["placebo_max_abs_all_specvis"] = float(plc_main[plc_main.p == "All platforms"].spec_vis.abs().max())
S["placebo_max_abs_all_specvis_nopin"] = float(plc_nopin[H][plc_nopin[H].p == "All platforms"].spec_vis.abs().max())
S["placebo_period_spec_all"] = float(kall.spec.mean())
S["placebo_period_spec_all_nopin"] = float(kall_nopin.spec.mean())
S["placebo_short_max"] = int(npl[(npl > 0) & (npl < len(fakes))].max())
S["min_days_placebo_window"] = 2 * H - 6
for p0 in S["platforms_without_placebo"]:
    S[f"first_day_aggregates_{p0}"] = str(k[k.p == p0].d.min().date()) if (k.p == p0).any() else "none"
    S[f"days_aggregates_{p0}"] = int(k[k.p == p0].d.nunique())
json.dump(S, open("results/rd.json", "w"), indent=1, default=float)
print(json.dumps(S, indent=1, default=float))
print(pool_main.round(4).to_string())
print(bw.round(4).to_string())
print(res_main[["p", "n_pre", "resid_pre", "resid_post", "resid_jump", "resid_p_perm", "spec_pre", "spec_post", "spec_jump",
                "spec_p_perm", "eff_pre", "eff_post", "eff_jump", "eff_p_perm"]].round(3).to_string())
