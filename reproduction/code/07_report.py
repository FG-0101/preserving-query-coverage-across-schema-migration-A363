"""Tables, figures and macros for the manuscript. Every number in the text comes from here.
Run from the package root after code/03 to code/06:  python3 code/07_report.py
Outputs: tex/macros.tex, tex/tab_*.tex, figures/fig_*.pdf
"""
from paper_style import save_figure
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys
sys.path.insert(0, "code")
from common import load_dumps, V2_KW, V2_CAT, RENAMED_KW, REMOVED_KW, ADDED_CAT, RENAMED_CAT, REMOVED

plt.rcParams.update({"font.family": "Linux Libertine O", "font.serif": ["Linux Libertine O"], "font.size": 8,
                     "axes.linewidth": 0.6, "pdf.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False})
J = lambda p: json.load(open(p))
val, rd, cw, lr = J("results/validation.json"), J("results/rd.json"), J("results/crosswalk.json"), J("results/longrun.json")
vd = pd.read_csv("results/validation_days.csv", parse_dates=["d"])
vk = pd.read_csv("results/validation_keywords.csv")
hc = pd.read_csv("results/hidden_by_category.csv")
rp = pd.read_csv("results/rd_platform.csv")
rpool = pd.read_csv("results/rd_pooled.csv")
rbw = pd.read_csv("results/rd_bandwidth.csv")
rs = pd.read_csv("results/rd_series.csv", parse_dates=["d"])
cwp = pd.read_csv("results/crosswalk_platform.csv")
lrd = pd.read_csv("results/longrun_days.csv", parse_dates=["d"])
lra = pd.read_csv("results/longrun_agg_daily.csv", parse_dates=["d"])
idx = pd.read_csv("data/derived/dump_index.csv")
actual_record_rows = int(load_dumps().n.sum())
m = {}
c = lambda x: f"{int(round(x)):,}".replace(",", "{,}")
pct = lambda x, d=0: f"{100 * x:.{d}f}"
CUT = pd.Timestamp("2025-07-01")


def longdate(x):
    t = pd.Timestamp(x)
    return f"{t.day} {t:%B %Y}"


def nice(cat):
    if cat == "STATEMENT_CATEGORY_OTHER_VIOLATION_TC":
        return "other violation of terms and conditions"
    if cat == "STATEMENT_CATEGORY_SCOPE_OF_PLATFORM_SERVICE":
        return "scope of platform service"
    return cat.replace("STATEMENT_CATEGORY_", "").replace("KEYWORD_", "").replace("_", " ").lower()


SHORT = {"willhaben internet service GmbH & Co KG": "willhaben", "Discord Netherlands B.V.": "Discord", "Quora Ireland Limited": "Quora",
         'SIA "JOOM"': "Joom", "Meetic SAS": "Meetic", "Vinted UAB": "Vinted", "www.gutefrage.net": "gutefrage.net"}
short = lambda x: SHORT.get(x, x).replace("&", "\\&")


# data
m.update({"nArchives": str(len(idx)), "nArchiveWindow": str(int(((pd.to_datetime(idx.date) >= CUT - pd.Timedelta(days=28)) &
                                                                  (pd.to_datetime(idx.date) < CUT + pd.Timedelta(days=28))).sum())),
          "nArchiveLater": str(int((pd.to_datetime(idx.date) >= CUT + pd.Timedelta(days=28)).sum())),
          "archStatements": c(actual_record_rows), "archBillion": f"{actual_record_rows / 1e9:.2f}",
          "archListedStatements": c(idx.statements.sum()),
          "aggKwCols": str(val["agg_keyword_columns"]), "nMonths": str(pd.read_csv("data/derived/complete_checksums.csv", header=None)[0].nunique()),
          "archZipGb": f"{idx.light_zip_gb.sum():.0f}", "archCsvGb": f"{idx.light_csv_gb.sum():.0f}",
          "julyCsvGb": f"{idx.set_index('date').loc['2025-07-01', 'light_csv_gb']:.1f}",
          "julyZipGb": f"{idx.set_index('date').loc['2025-07-01', 'light_zip_gb']:.1f}"})
# schema
agg_cols = pd.read_csv("data/derived/complete_columns.csv", header=None).iloc[0, 3].split("|")
no_col = [x for x in V2_KW if x not in agg_cols]
new_kw = [x for x in no_col if x not in RENAMED_KW.values()]
m.update({"vTwoKw": str(len(V2_KW)), "vTwoNoCol": str(len(no_col)), "vTwoNew": str(len(new_kw)), "renamedKw": str(len(RENAMED_KW)),
          "removedKw": str(len(REMOVED_KW)), "vOneOnly": str(len([x for x in agg_cols if x not in V2_KW])),
          "sharedKw": str(len([x for x in V2_KW if x in agg_cols])), "addedCat": str(len(ADDED_CAT)),
          "renamedCat": str(len(RENAMED_CAT)), "removedCat": str(len(REMOVED))})
# validation
m.update({"valDays": str(val["days"]), "valEqualDays": str(val["records_equal_days"]), "valMaxRel": f"{100 * val['max_rel_diff_records']:.2f}",
          "valMaxAbs": c(val["max_abs_diff_records"]), "valMaxKw": c(val["max_abs_diff_shared_kw"]),
          "valKwExactDays": str(val["shared_kw_exact_days"]), "valListedDays": str(val["agg_equals_listed_days"]),
          "valMaxRelListed": f"{100 * val['max_rel_diff_agg_listed']:.2f}",
          "hidMean": pct(val["post_hidden_record_share_mean"]), "hidMin": pct(val["post_hidden_record_share_min"]),
          "hidMax": pct(val["post_hidden_record_share_max"]), "kwSeenPost": str(val["post_keywords_seen"]),
          "kwHiddenPost": str(val["post_keywords_hidden"]), "hidRecords": c(val["post_hidden_records_total"]),
          "postDays": str(val["post_days"]), "preDays": str(val["pre_days"]), "renamedPlatforms": str(val["renamed_platforms"])})
# hidden keywords table
kp = vk[vk.post].groupby(["kw", "in_aggregate"]).n.sum().reset_index()
tot_spec = kp[kp.kw != "KEYWORD_OTHER"].n.sum()
hk = kp[~kp.in_aggregate].sort_values("n", ascending=False)
with open("tex/tab_hidden_kw.tex", "w") as o:
    inv = {v: k_ for k_, v in RENAMED_KW.items()}
    o.write("\\begin{tabular}{llrr}\\toprule\nKeyword without an aggregate column & Origin & Mentions & Share of keyword mentions (\\%)\\\\\\midrule\n")
    for _, r in hk.head(14).iterrows():
        org = ("renamed from " + nice(inv[r.kw])) if r.kw in inv else "new"
        o.write(f"{nice(r.kw)} & {org} & {c(r.n)} & {pct(r.n / tot_spec, 2)}\\\\\n")
    o.write(f"All {len(hk)} keywords without a column & & {c(hk.n.sum())} & {pct(hk.n.sum() / tot_spec, 1)}\\\\\n")
    o.write("\\bottomrule\\end{tabular}\n")
m["hidKwShare"] = pct(hk.n.sum() / tot_spec)
oldpost = vk[vk.post & ~vk.kw.isin(V2_KW)].n.sum()
m["oldKwPost"] = c(oldpost)
m["hidTopKw"] = nice(hk.kw.iloc[0])
m["hidTopKwShare"] = pct(hk.n.iloc[0] / tot_spec)
# hidden by category
h2 = hc[hc.rec_specific > 1000].sort_values("rec_specific", ascending=False)
with open("tex/tab_hidden_cat.tex", "w") as o:
    o.write("\\begin{tabular}{lrrr}\\toprule\nCategory & Statements & With a keyword & Hidden in aggregates (\\%)\\\\\\midrule\n")
    for _, r in h2.iterrows():
        o.write(f"{nice(r.c)} & {c(r.records)} & {c(r.rec_specific)} & {pct(r.hidden_share, 1)}\\\\\n")
    o.write("\\bottomrule\\end{tabular}\n")
hci = hc.set_index("c").hidden_share
for cat, tag in [("UNSAFE_AND_PROHIBITED_PRODUCTS", "Unsafe"), ("CONSUMER_INFORMATION", "Consumer"),
                 ("NEGATIVE_EFFECTS_ON_CIVIC_DISCOURSE_OR_ELECTIONS", "Civic"), ("CYBER_VIOLENCE", "Cyber"), ("SCAMS_AND_FRAUD", "Scams"),
                 ("ILLEGAL_OR_HARMFUL_SPEECH", "Speech"), ("OTHER_VIOLATION_TC", "Other")]:
    m[f"hidCat{tag}"] = pct(hci["STATEMENT_CATEGORY_" + cat], 1)
full_hidden = h2[h2.hidden_share > 0.999]
m["catFullyHidden"] = ", ".join(nice(x) for x in full_hidden.c) if len(full_hidden) else "none"
m["catFullyHiddenN"] = str(len(full_hidden))
# RD pooled table
labels = {"resid": "Residual category share", "spec": "Keyword share, all keywords", "spec_vis": "Keyword share, as aggregated",
          "inform": "Informative share", "eff": "Effective number of categories"}
SER = [("All platforms", "All"), ("Platform average", "Avg")]
pv_ = lambda x: f"{x:.3f}"
with open("tex/tab_rd.tex", "w") as o:
    o.write("\\begin{tabular}{lrrrrrrrrrr}\\toprule\n & \\multicolumn{4}{c}{Statement weighted} & \\multicolumn{4}{c}{Platform weighted} & \\multicolumn{2}{c}{Platforms}\\\\\n")
    o.write("\\cmidrule(lr){2-5}\\cmidrule(lr){6-9}\\cmidrule(lr){10-11}\nOutcome & Before & After & Jump (s.e.) & $p$ & Before & After & Jump (s.e.) & $p$ & Up & Down\\\\\\midrule\n")
    for k_ in ["resid", "spec", "spec_vis", "inform", "eff"]:
        fm = (lambda x: f"{x:.3f}") if k_ != "eff" else (lambda x: f"{x:.2f}")
        cells = []
        for sname, _ in SER:
            r = rpool[(rpool.series == sname) & (rpool.outcome == k_)].iloc[0]
            cells += [fm(r.pre), fm(r.post), f"{fm(r.jump)} ({fm(r.se)})", pv_(r.p_perm)]
        o.write(f"{labels[k_]} & " + " & ".join(cells) + f" & {rd[k_]['material_up']} & {rd[k_]['material_down']}\\\\\n")
    o.write("\\bottomrule\\end{tabular}\n")
for k_, tag in [("resid", "Resid"), ("spec", "Spec"), ("spec_vis", "SpecVis"), ("inform", "Inform"), ("eff", "Eff")]:
    for sname, st in SER:
        r = rpool[(rpool.series == sname) & (rpool.outcome == k_)].iloc[0]
        if k_ == "eff":
            m.update({f"rd{st}{tag}Pre": f"{r.pre:.2f}", f"rd{st}{tag}Post": f"{r.post:.2f}", f"rd{st}{tag}Jump": f"{r.jump:.2f}",
                      f"rd{st}{tag}Se": f"{r.se:.2f}"})
        else:
            m.update({f"rd{st}{tag}Pre": pct(r.pre, 1), f"rd{st}{tag}Post": pct(r.post, 1), f"rd{st}{tag}Jump": pct(r.jump, 1),
                      f"rd{st}{tag}Se": pct(r.se, 1)})
        m[f"rd{st}{tag}P"] = pv_(r.p_perm)
    m[f"rd{tag}Up"] = str(rd[k_]["material_up"])
    m[f"rd{tag}Down"] = str(rd[k_]["material_down"])
    m[f"rd{tag}UpAny"] = str(rd[k_]["p05_up"])
    m[f"rd{tag}DownAny"] = str(rd[k_]["p05_down"])
    m[f"rd{tag}BhUp"] = str(rd[k_]["bh_up"])
    m[f"rd{tag}BhDown"] = str(rd[k_]["bh_down"])
m.update({"rdH": str(rd["window_days"] // 2), "hacLags": str(rd["hac_lags"]), "bhQ": f"{rd['bh_q']:.2f}",
          "rdPlatforms": str(rd["platforms"]), "rdMinN": c(rd["min_daily_n"]), "rdPlacebo": str(rd["placebo_cutoffs"]),
          "rdPlaceboPlatforms": str(rd["platforms_with_placebo"]), "rdPmin": f"{1 / (1 + rd['placebo_cutoffs']):.3f}"})
# bandwidth table
with open("tex/tab_bandwidth.tex", "w") as o:
    o.write("\\begin{tabular}{lrrrrrrrrr}\\toprule\n & \\multicolumn{3}{c}{Statement weighted jump ($p$)} & \\multicolumn{3}{c}{Platform weighted jump ($p$)} & \\multicolumn{3}{c}{Platforms up, down}\\\\\n")
    o.write("\\cmidrule(lr){2-4}\\cmidrule(lr){5-7}\\cmidrule(lr){8-10}\nOutcome & 28 days & 21 days & 14 days & 28 days & 21 days & 14 days & 28 days & 21 days & 14 days\\\\\\midrule\n")
    for k_ in ["resid", "spec", "spec_vis", "inform", "eff"]:
        fm = (lambda x: f"{x:.3f}") if k_ != "eff" else (lambda x: f"{x:.2f}")
        z = rbw[rbw.outcome == k_].set_index("h")
        cells = [f"{fm(z.loc[h, 'All platforms_jump'])} ({pv_(z.loc[h, 'All platforms_p_perm'])})" for h in [28, 21, 14]]
        cells += [f"{fm(z.loc[h, 'Platform average_jump'])} ({pv_(z.loc[h, 'Platform average_p_perm'])})" for h in [28, 21, 14]]
        cells += [f"{int(z.loc[h, 'material_up'])}, {int(z.loc[h, 'material_down'])}" for h in [28, 21, 14]]
        o.write(f"{labels[k_]} & " + " & ".join(cells) + "\\\\\n")
    o.write("\\bottomrule\\end{tabular}\n")
for h, tag in [(21, "TwentyOne"), (14, "Fourteen")]:
    z = rbw[(rbw.outcome == "spec") & (rbw.h == h)].iloc[0]
    m[f"bwAllSpec{tag}"] = pct(z["All platforms_jump"], 1)
    m[f"bwAllSpec{tag}P"] = pv_(z["All platforms_p_perm"])
    m[f"bwAvgSpec{tag}"] = pct(z["Platform average_jump"], 1)
    m[f"bwAvgSpec{tag}P"] = pv_(z["Platform average_p_perm"])
    zv = rbw[(rbw.outcome == "spec_vis") & (rbw.h == h)].iloc[0]
    m[f"bwAllSpecVis{tag}"] = pct(zv["All platforms_jump"], 1)
    m[f"bwAllSpecVis{tag}P"] = pv_(zv["All platforms_p_perm"])
    ze = rbw[(rbw.outcome == "eff") & (rbw.h == h)].iloc[0]
    m[f"bwAvgEff{tag}"] = f"{ze['Platform average_jump']:.2f}"
    zi = rbw[(rbw.outcome == "inform") & (rbw.h == h)].iloc[0]
    m[f"bwAvgInform{tag}"] = pct(zi["Platform average_jump"], 1)
m["bwAvgSpecMin"] = pct(rbw[rbw.outcome == "spec"]["Platform average_jump"].min(), 1)
m["bwAvgSpecMax"] = pct(rbw[rbw.outcome == "spec"]["Platform average_jump"].max(), 1)
# platform table, largest platforms
MAT = {"resid": 0.01, "spec": 0.01}
top = rp.sort_values("n_pre", ascending=False).head(22)
with open("tex/tab_rd_platform.tex", "w") as o:
    o.write("\\begin{tabular}{lrrrrrrr}\\toprule\n & & \\multicolumn{3}{c}{Residual category share} & \\multicolumn{3}{c}{Keyword share} \\\\\\cmidrule(lr){3-5}\\cmidrule(lr){6-8}\n")
    o.write("Platform & Statements per day & Before & After & Jump & Before & After & Jump\\\\\\midrule\n")
    star = lambda r, o_: ("$^{*}$" if (r[f"{o_}_p_perm"] < 0.05 and abs(r[f"{o_}_jump"]) >= MAT[o_]) else "") + \
        ("$^{\\dagger}$" if (r.p == "Pinterest" and o_ == "spec") else "")
    for _, r in top.iterrows():
        o.write(f"{short(r.p)} & {c(r.n_pre)} & {r.resid_pre:.3f} & {r.resid_post:.3f} & {r.resid_jump:.3f}{star(r, 'resid')} & "
                f"{r.spec_pre:.3f} & {r.spec_post:.3f} & {r.spec_jump:.3f}{star(r, 'spec')}\\\\\n")
    o.write("\\bottomrule\\end{tabular}\n")
m["rdTableN"] = str(len(top))
adopt = rp[(rp.spec_pre < 0.01) & (rp.spec_post >= 0.1)]
m["adoptN"] = str(len(adopt))
m["adoptList"] = ", ".join(short(x) for x in adopt.sort_values("n_pre", ascending=False).p)
nouse = rp[(rp.spec_pre == 0) & (rp.spec_post == 0)]
m["noUseN"] = str(len(nouse))
big_resid = rp[(rp.resid_p_perm < 0.05) & (rp.resid_jump.abs() >= 0.2)].sort_values("resid_jump")
m["bigResidN"] = str(len(big_resid))
m["rdAvgEffDrop"] = f"{-rpool[(rpool.series == 'Platform average') & (rpool.outcome == 'eff')].jump.iloc[0]:.2f}"
m["residMaxUp"] = f"{100 * big_resid.resid_jump.max():.0f}"
m["residMaxDown"] = f"{100 * -big_resid.resid_jump.min():.0f}"
m["bigResidList"] = ", ".join(f"{short(r.p)} (${100 * r.resid_jump:+.0f}$)" for _, r in big_resid.iterrows())
for nm, tag in [("Temu", "Temu"), ("Google Play", "GPlay"), ("Amazon Store", "Amazon"), ("Pinterest", "Pinterest"),
                ("Snapchat", "Snap"), ("TikTok", "TikTok"), ("Instagram", "Insta"), ("Google Shopping", "GShop")]:
    r = rp[rp.p == nm].iloc[0]
    for o_ in ["resid", "spec", "eff"]:
        f_ = (lambda x: f"{x:.2f}") if o_ == "eff" else (lambda x: pct(x, 1))
        m[f"pl{tag}{o_.capitalize()}Pre"] = f_(r[f"{o_}_pre"])
        m[f"pl{tag}{o_.capitalize()}Post"] = f_(r[f"{o_}_post"])
        m[f"pl{tag}{o_.capitalize()}Jump"] = f_(r[f"{o_}_jump"])
# platforms that stopped or nearly stopped submitting in the four weeks after the cutoff
pn = rs[~rs.p.isin(["All platforms", "Platform average"])]
pre_m = pn[pn.d < CUT].groupby("p").n.sum() / 28
post_m = pn[pn.d >= CUT].groupby("p").n.sum().reindex(pre_m.index).fillna(0) / 28
drop = pre_m[(pre_m >= 1000) & (post_m < 0.1 * pre_m)]
m["dropN"] = str(len(drop))
m["dropList"] = ", ".join(drop.index).replace("&", "\\&")
m["xPre"] = c(pre_m.get("X", 0))
allpre = rs[(rs.p == "All platforms") & (rs.d < CUT)].n.mean()
m["gshopShare"] = pct(rp.set_index("p").loc["Google Shopping", "n_pre"] / allpre)
m["allPerDay"] = f"{allpre / 1e6:.1f}"
m["xPost"] = c(post_m.get("X", 0))
# crosswalk
m.update({"cwPlatforms": str(cw["platforms"]), "cwGeHalf": str(cw["recovery_all_ge_half"]), "cwLtTenth": str(cw["recovery_all_lt_tenth"]),
          "cwPreRemoved": pct(cw["pooled_pre_removed"], 1), "cwPostAll": pct(cw["pooled_post_sexkw_all"], 1),
          "cwPostVis": pct(cw["pooled_post_sexkw_visible"], 1),
          "cwTopDest": str(cw["top_destination_counts"].get("STATEMENT_CATEGORY_OTHER_VIOLATION_TC", 0)),
          "cwTopDestCyber": str(cw["top_destination_counts"].get("STATEMENT_CATEGORY_CYBER_VIOLENCE", 0)),
          "cwTopDestScams": str(cw["top_destination_counts"].get("STATEMENT_CATEGORY_SCAMS_AND_FRAUD", 0))})
big = cwp.sort_values("pre_n", ascending=False)
cwd = pd.read_csv("results/crosswalk_destinations.csv")
dest = cwd[cwd.change > 0].sort_values("change", ascending=False).groupby("p").head(1).set_index("p")
with open("tex/tab_crosswalk.tex", "w") as o:
    o.write("\\begin{tabular}{lrrrrl}\\toprule\n & \\multicolumn{2}{c}{Before (\\%)} & \\multicolumn{2}{c}{After (\\%)} & \\\\\\cmidrule(lr){2-3}\\cmidrule(lr){4-5}\n")
    o.write("Platform & Removed categories & Sexual keywords & Sexual keywords & As aggregated & Largest gain in category share\\\\\\midrule\n")
    for _, r in big.iterrows():
        dd = dest.loc[r.p] if r.p in dest.index else None
        dtxt = f"{nice(dd.c)} ({pct(dd.change, 1)})" if dd is not None else ""
        o.write(f"{short(r.p)} & {pct(r.pre_removed_share, 2)} & {pct(r.pre_sexkw_share, 2)} & {pct(r.post_sexkw_share_all, 2)} & "
                f"{pct(r.post_sexkw_share_visible, 2)} & {dtxt}\\\\\n")
    o.write("\\bottomrule\\end{tabular}\n")
m.update({"jsdPlatforms": str(cw["jsd_platforms"]), "jsdMedian": f"{cw['jsd_median']:.3f}", "jsdBenchMedian": f"{cw['jsd_benchmark_median']:.3f}",
          "jsdCommonMedian": f"{cw['jsd_common_median']:.3f}", "jsdCommonOver": str(cw["jsd_common_over_0_1"]),
          "jsdBenchN": str(cw["jsd_benchmark_platforms"]), "jsdExceeds": str(cw["jsd_exceeds_benchmark"]), "jsdOver": str(cw["jsd_over_0_1"]),
          "jsdBenchOver": str(cw["jsd_benchmark_over_0_1"])})
jsdt = pd.read_csv("results/category_shift.csv").head(5)
m["jsdTop"] = ", ".join(f"{short(r.p)} ({r.jsd_migration:.2f})" for _, r in jsdt.iterrows())
m["cwNoKwAfter"] = str(int((cwp.post_sexkw_share_all == 0).sum()))
m["cwNoKwBoth"] = str(int(((cwp.pre_sexkw_share < 0.001) & (cwp.post_sexkw_share_all < 0.001)).sum()))
m["cwRemovedVolume"] = c(cwp.eval("pre_removed_share * pre_n").sum())
m["cwRemovedVolumeNoKw"] = c(cwp[(cwp.post_sexkw_share_all == 0)].eval("pre_removed_share * pre_n").sum())
m["cwRemovedShareNoKw"] = pct(cwp[(cwp.post_sexkw_share_all == 0)].eval("pre_removed_share * pre_n").sum() / cwp.eval("pre_removed_share * pre_n").sum())
m["cwRobloxPre"] = pct(cwp.set_index("p").loc["Roblox", "pre_removed_share"], 1)
m["cwInstaPre"] = pct(cwp.set_index("p").loc["Instagram", "pre_removed_share"], 1)
m["cwPinPre"] = pct(cwp.set_index("p").loc["Pinterest", "pre_removed_share"], 1)
m["cwPinPreKw"] = pct(cwp.set_index("p").loc["Pinterest", "pre_sexkw_share"], 1)
m["cwPinPost"] = pct(cwp.set_index("p").loc["Pinterest", "post_sexkw_share_all"], 1)
zero_big = big[(big.recovery_all < 0.1)].head(6)
m["cwZeroBig"] = ", ".join(short(x) for x in zero_big.p)
# long run
m.update({"lrDays": str(lr["days"]), "lrHidMin": pct(lr["hidden_of_spec_min"]), "lrHidMax": pct(lr["hidden_of_spec_max"]),
          "lrHidMed": pct(lr["hidden_of_spec_median"]), "lrPlatNew": str(lr["platforms_new_kw_max"]),
          "lrPlatNewMin": str(lr["platforms_new_kw_min"]), "lrPlatMin": str(lr["platforms_min"]), "lrPlatMax": str(lr["platforms_max"]),
          "lrXmin": c(lr["x_n_min"]), "lrXmax": c(lr["x_n_max"]), "lrXfirst": c(lr["x_n_first"]),
          "lrSpecMed": pct(lr["spec_share_median"], 1), "lrSpecVisMed": pct(lr["spec_visible_share_median"], 1),
          "lrFirst": longdate(lr["first_day"]), "lrLast": longdate(lr["last_day"])})
# schema extras, records, additions
m["nCatVTwo"] = str(len(V2_CAT))
m["archRecords"] = c(val["records_reduced_total"])
m["addCols"] = str(val["add_columns"])
m["addPost"] = c(val["post_with_addition"])
m["addHidden"] = c(val["post_addition_some_hidden"])
m["addHiddenShare"] = pct(val["post_addition_some_hidden"] / val["post_with_addition"])
m["hidKwShown"] = str(min(14, len(hk)))
m["monthsAfter"] = str(int(round((pd.Timestamp(lr["last_day"]) - CUT).days / 30.44)))
# renamed keywords: mentions under the old name before and under the new name after, archive window days
win_pre = vk[(~vk.post) & (pd.to_datetime(vk.d) >= CUT - pd.Timedelta(days=28))]
win_post = vk[vk.post & (pd.to_datetime(vk.d) < CUT + pd.Timedelta(days=28))]
for old, newk in RENAMED_KW.items():
    tag = {"KEYWORD_ONLINE_BULLYING_INTIMIDATION": "Bully", "KEYWORD_INSUFFICIENT_INFORMATION_TRADERS": "Traders",
           "KEYWORD_DISINFORMATION": "Disinfo", "KEYWORD_NON_CONSENSUAL_ITEMS_DEEPFAKE": "Deepfake"}[old]
    m[f"ren{tag}PreOld"] = c(win_pre[win_pre.kw == old].n.sum())
    m[f"ren{tag}PostOld"] = c(win_post[win_post.kw == old].n.sum())
    m[f"ren{tag}PostNew"] = c(win_post[win_post.kw == newk].n.sum())
m["renUsedPre"] = str(sum(win_pre[win_pre.kw == old].n.sum() > 0 for old in RENAMED_KW))
mis_pre = win_pre[win_pre.kw == "KEYWORD_MISINFORMATION"].n.sum()
m["misPre"] = c(mis_pre)
m["misPost"] = c(win_post[win_post.kw == "KEYWORD_MISINFORMATION"].n.sum())
m["misDisPost"] = c(win_post[win_post.kw == "KEYWORD_MISINFORMATION_DISINFORMATION"].n.sum())
# multiple testing restricted to material jumps, placebo coverage
for k_, tag in [("resid", "Resid"), ("inform", "Inform"), ("spec", "Spec"), ("eff", "Eff")]:
    m[f"rd{tag}BhMatUp"] = str(rd[k_]["bh_material_up"])
    m[f"rd{tag}BhMatDown"] = str(rd[k_]["bh_material_down"])
    m[f"rd{tag}NotBh"] = ", ".join(short(x) for x in rd[k_]["material_not_bh"]) or "none"
    m[f"rd{tag}UpDonut"] = str(rd[k_]["material_up_donut"])
    m[f"rd{tag}DownDonut"] = str(rd[k_]["material_down_donut"])
m["plcMin"] = str(rd["placebo_per_platform_min"])
m["plcMax"] = str(rd["placebo_per_platform_max"])
m["plcShortN"] = str(rd["platforms_short_placebo"])
m["plcMaxSpecVis"] = pct(rd["placebo_max_abs_all_specvis"], 1)
m["plcMaxSpecVisNoPin"] = pct(rd["placebo_max_abs_all_specvis_nopin"], 1)
m["plcSpecAll"] = pct(rd["placebo_period_spec_all"], 2)
m["plcSpecAllNoPin"] = pct(rd["placebo_period_spec_all_nopin"], 2)
m["plcShortMax"] = str(rd["placebo_short_max"])
m["minDaysWindow"] = str(rd["min_days_placebo_window"])
m["happnFirst"] = longdate(rd["first_day_aggregates_happn"])
m["happnDays"] = str(rd["days_aggregates_happn"])
m["addHidResid"] = c(val["add_hidden_renamed_residual"])
m["addHidProducts"] = c(val["add_hidden_renamed_products"])
m["addHidNew"] = c(val["add_hidden_new"])
kpw = pd.read_csv("results/keyword_platform_window.csv")
kq = lambda p_, kw, post: kpw[(kpw.p == p_) & (kpw.kw == kw) & (kpw.post == post)].n.sum()
bully = kpw[(kpw.kw == "KEYWORD_ONLINE_BULLYING_INTIMIDATION") & ~kpw.post].sort_values("n", ascending=False)
m["bullyTop"] = short(bully.p.iloc[0])
m["bullyTopN"] = c(bully.n.iloc[0])
m["bullyTopHarass"] = c(kq(bully.p.iloc[0], "KEYWORD_CYBER_HARASSMENT", True))
m["bullyTopNew"] = c(kq(bully.p.iloc[0], "KEYWORD_CYBER_BULLYING_INTIMIDATION", True))
mis = kpw[(kpw.kw == "KEYWORD_MISINFORMATION") & ~kpw.post]
m["misUsersPre"] = str(mis.p.nunique())
m["misUserPre"] = ", ".join(short(x) for x in mis.p)
md = kpw[(kpw.kw == "KEYWORD_MISINFORMATION_DISINFORMATION") & kpw.post].sort_values("n", ascending=False)
m["misDisTop"] = short(md.p.iloc[0])
m["misDisTopN"] = c(md.n.iloc[0])
m["misDisTopOld"] = c(kq(md.p.iloc[0], "KEYWORD_MISINFORMATION", False) + kq(md.p.iloc[0], "KEYWORD_DISINFORMATION", False))
m["plcNone"] = ", ".join(short(x) for x in rd["platforms_without_placebo"])
m["plcPminWorst"] = f"{1 / (1 + rd['placebo_per_platform_min']):.3f}"
m["plcCleanOne"] = str(rd["placebo_clean1"])
m["plcCleanTwo"] = str(rd["placebo_clean2"])
hp = rp.set_index("p")
m["happnResidJump"] = pct(hp.loc["happn", "resid_jump"])
m["specDownTwentyOne"] = str(int(rbw[(rbw.outcome == "spec") & (rbw.h == 21)].material_down.iloc[0]))
m["specDownFourteen"] = str(int(rbw[(rbw.outcome == "spec") & (rbw.h == 14)].material_down.iloc[0]))
m["rdMedianSpec"] = pct(rd["spec"]["median_jump"], 1)
near = rp[rp.spec_post >= 0.9].sort_values("n_pre", ascending=False)
m["nearAllN"] = str(len(near))
m["nearAllList"] = " and ".join(short(x) for x in near.p)
# platform jumps without the cutoff day
for nm, tag in [("TikTok", "TikTok"), ("www.gutefrage.net", "Gute"), ("Dailymotion", "Daily")]:
    m[f"dn{tag}Resid"] = pct(hp.loc[nm, "resid_jump_donut"], 1)
    m[f"pl{tag}ResidJumpMain"] = pct(hp.loc[nm, "resid_jump"], 1)
tt = rs[(rs.p == "TikTok")].set_index("d")
m["tiktokCutResid"] = pct(tt.loc[CUT, "resid"], 1)
m["tiktokCutN"] = c(tt.loc[CUT, "n"])
m["tiktokPreN"] = c(tt.loc[CUT - pd.Timedelta(days=1), "n"])
# robustness table
rob = pd.read_csv("results/rd_robustness.csv")
VROWS = [("main", 28, "Main specification"), ("placebo without March outage", 28, "Placebo without windows touching 14 to 19 March 2025"),
         ("placebo without March outage and 30 May change", 28, "Placebo also without windows containing 30 May 2025"),
         ("without the cutoff day", 28, "Cutoff day 1 July 2025 dropped"), ("without Pinterest", 28, "Pinterest removed"),
         ("without Pinterest", 21, "Pinterest removed"), ("without Pinterest", 14, "Pinterest removed"),
         ("without 14 to 27 June", 28, "Days 14 to 27 June 2025 dropped")]
gr = lambda v, h, srs, oc, col: rob[(rob.variant == v) & (rob.h == h) & (rob.series == srs) & (rob.outcome == oc)][col].iloc[0]
with open("tex/tab_robust.tex", "w") as o:
    o.write("\\begin{tabular}{lrrrrrrrr}\\toprule\n & & & \\multicolumn{4}{c}{Platform weighted jump ($p$)} & \\multicolumn{2}{c}{Statement weighted jump ($p$)}\\\\\n")
    o.write("\\cmidrule(lr){4-7}\\cmidrule(lr){8-9}\nVariant & Window & Placebo cutoffs & Keyword share & As aggregated & Informative share & Effective categories & Keyword share & As aggregated\\\\\\midrule\n")
    for v, h, lab in VROWS:
        cells = []
        for srs, oc in [("Platform average", "spec"), ("Platform average", "spec_vis"), ("Platform average", "inform"), ("Platform average", "eff"),
                        ("All platforms", "spec"), ("All platforms", "spec_vis")]:
            fm = (lambda x: f"{x:.2f}") if oc == "eff" else (lambda x: f"{x:.3f}")
            cells.append(f"{fm(gr(v, h, srs, oc, 'jump'))} ({gr(v, h, srs, oc, 'p_perm'):.3f})")
        o.write(f"{lab} & {h} & {int(gr(v, h, 'All platforms', 'spec', 'n_placebo'))} & " + " & ".join(cells) + "\\\\\n")
    o.write("\\bottomrule\\end{tabular}\n")
for v, h, tag in [("without Pinterest", 28, "NoPin"), ("without Pinterest", 21, "NoPinTwentyOne"), ("without Pinterest", 14, "NoPinFourteen"),
                  ("without the cutoff day", 28, "Donut"), ("without 14 to 27 June", 28, "NoDays"),
                  ("placebo without March outage", 28, "CleanOne"), ("placebo without March outage and 30 May change", 28, "CleanTwo")]:
    for srs, st in [("All platforms", "All"), ("Platform average", "Avg")]:
        for oc, ot in [("spec", "Spec"), ("spec_vis", "SpecVis"), ("inform", "Inform"), ("resid", "Resid")]:
            m[f"rob{tag}{st}{ot}"] = pct(gr(v, h, srs, oc, "jump"), 1)
            m[f"rob{tag}{st}{ot}P"] = f"{gr(v, h, srs, oc, 'p_perm'):.3f}"
# share of the keyword jump that the aggregates show, over every specification (bandwidths and robustness checks)
spec_rows = rob[rob.outcome == "spec"].set_index(["variant", "h", "series"])
vis_rows = rob[rob.outcome == "spec_vis"].set_index(["variant", "h", "series"])
ratio = (vis_rows.jump / spec_rows.jump).rename("ratio").to_frame().join(spec_rows.p_perm.rename("p_spec"))
ra = ratio.xs("Platform average", level="series")
rs_ = ratio.xs("All platforms", level="series")
rs_sig = rs_[rs_.p_spec < 0.05]
m["visRatioAvgMin"] = pct(ra.ratio.min())
m["visRatioAvgMax"] = pct(ra.ratio.max())
m["visRatioAllMin"] = pct(rs_sig.ratio.min())
m["visRatioAllMax"] = pct(rs_sig.ratio.max())
m["visRatioAllMain"] = pct(rs_.loc[("main", 28), "ratio"])
m["nSpecs"] = str(len(ra))
m["nSpecsAllSig"] = str(len(rs_sig))
# Pinterest reporting gap
pin = json.load(open("results/pinterest_gap.json"))
m.update({"pinPreMin": f"{pin['daily_pre_gap_min'] / 1e6:.2f}", "pinPreMax": f"{pin['daily_pre_gap_max'] / 1e6:.2f}",
          "pinGapMin": f"{pin['daily_gap_min'] / 1e6:.2f}", "pinGapMax": f"{pin['daily_gap_max'] / 1e6:.2f}",
          "pinBackMin": f"{pin['daily_backlog_min'] / 1e6:.1f}", "pinBackMax": f"{pin['daily_backlog_max'] / 1e6:.1f}",
          "pinGapRemoved": pct(pin["removed_share_gap"], 1), "pinSpecPooledPre": pct(pin["spec_pooled_pre"], 1),
          "pinSpecPooledPost": pct(pin["spec_pooled_post"], 1)})
# X after the window
lx = lrd.set_index("d").x_n
mid = lx[(lx.index >= "2025-09-01") & (lx.index <= "2026-03-31")]
m["lrXmidMin"] = c(mid.min())
m["lrXmidMax"] = c(mid.max())
m["lrXsep"] = c(lx[lx.index >= "2025-09-01"].iloc[0])
# proper minus signs in all generated tables
import glob, re
for f in glob.glob("tex/tab_*.tex"):
    t = open(f).read()
    open(f, "w").write(re.sub(r"(?<![\w$.])-(\d)", r"$-$\1", t))
with open("tex/macros.tex", "w") as o:
    for k_, v in m.items():
        v = re.sub(r"^-(\d)", r"$-$\1", v)
        o.write("\\newcommand{\\" + k_ + "}{" + v + "}\n")

import matplotlib.dates as mdates
fmt = mdates.DateFormatter("%b %Y")


def datefmt(a, rot=30):
    a.xaxis.set_major_formatter(fmt)
    for lab_ in a.get_xticklabels():
        lab_.set_rotation(rot); lab_.set_ha("right")


# Figure 1: keyword share in the published aggregates and in the record level archives
fig, ax = plt.subplots(1, 2, figsize=(5.6, 2.8))
ax[0].plot(lra.d, 100 * lra.spec_visible_share, color="black", lw=0.5, label="Published aggregates (daily)")
arch = vd.copy()
arch["true"] = arch.rec_specific / arch.records_dump
arch["vis"] = arch.rec_specific_visible / arch.records_dump
ap = arch[arch.post]
ax[0].vlines(ap.d, 100 * ap.vis, 100 * ap["true"], color="black", lw=0.6)
ax[0].plot(arch.d, 100 * arch["true"], "o", ms=2.4, mfc="white", mec="black", mew=0.6, label="Record level archives")
ax[0].axvline(CUT, color="black", lw=0.5, ls=":")
ax[0].set_ylabel("Statements with a keyword (%)")
ax[0].legend(frameon=False, fontsize=8, loc="upper left")
ax[0].set_title("A. Keyword share", fontsize=8, loc="left")
datefmt(ax[0])
ax[1].plot(ap.d, 100 * ap.hidden_record_share, "o", ms=2.6, mfc="white", mec="black", mew=0.6)
ax[1].set_ylabel("Keyword statements invisible in aggregates (%)", fontsize=8)
ax[1].set_ylim(0, 70)
ax[1].set_title("B. Hidden share after the migration", fontsize=8, loc="left")
datefmt(ax[1])
fig.tight_layout(); save_figure(fig, "figures/fig_hidden.pdf", metadata={"Creator": None, "Producer": None, "CreationDate": None, "ModDate": None}, bbox_inches="tight", pad_inches=0.06); plt.close(fig)

# Figure 2: daily series around the cutoff, statement weighted (top) and platform weighted (bottom)
fig, ax = plt.subplots(4, 2, figsize=(5.6, 6.2), sharex=True)
panels = [("resid", "Residual share (%)"), ("spec", "Keyword share (%)"), ("inform", "Informative share (%)"), ("eff", "Effective categories")]
for i, sname in enumerate(["All platforms", "Platform average"]):
    ser = rs[rs.p == sname].sort_values("d")
    for j, (k_, lab) in enumerate(panels):
        a = ax[j, i]
        sc = 100 if k_ != "eff" else 1
        a.plot(ser.d, sc * ser[k_], "o", ms=1.8, mfc="white", mec="black", mew=0.5)
        for side in [ser.d < CUT, ser.d >= CUT]:
            z = ser[side]
            t = (z.d - CUT).dt.days.values
            bb = np.polyfit(t, sc * z[k_].values, 1)
            a.plot(z.d, np.polyval(bb, t), color="black", lw=0.8)
        if k_ == "spec":
            a.plot(ser.d, sc * ser["spec_vis"], "x", ms=2.0, color="black", mew=0.5)
            zz = ser[ser.d >= CUT]
            t = (zz.d - CUT).dt.days.values
            a.plot(zz.d, np.polyval(np.polyfit(t, sc * zz["spec_vis"].values, 1), t), color="black", lw=0.8, ls="--")
        a.axvline(CUT, color="black", lw=0.5, ls=":")
        a.tick_params(labelsize=8)
        a.set_title(lab + ("; statement weights" if i == 0 else "; platform weights"), fontsize=8)
        a.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
        a.xaxis.set_major_locator(mdates.DayLocator(bymonthday=[1, 15]))
        for lab_ in a.get_xticklabels():
            lab_.set_rotation(45); lab_.set_ha("right")
fig.tight_layout(); save_figure(fig, "figures/fig_rd.pdf", metadata={"Creator": None, "Producer": None, "CreationDate": None, "ModDate": None}, bbox_inches="tight", pad_inches=0.06); plt.close(fig)

# Figure 3: platform jumps with 95 percent intervals
fig, ax = plt.subplots(1, 2, figsize=(5.6, 6.8))
for a, k_, lab in [(ax[0], "resid", "Jump in residual category share (fraction)"), (ax[1], "spec", "Jump in keyword share (fraction)")]:
    z = rp.sort_values(f"{k_}_jump")
    yy = np.arange(len(z))
    mat = (z[f"{k_}_p_perm"] < 0.05) & (z[f"{k_}_jump"].abs() >= 0.01)
    a.errorbar(z[f"{k_}_jump"], yy, xerr=1.96 * z[f"{k_}_se"], fmt="none", ecolor="black", elinewidth=0.6, capsize=0)
    a.plot(z[f"{k_}_jump"][~mat], yy[~mat.values], "o", ms=2.6, mfc="white", mec="black", mew=0.6)
    a.plot(z[f"{k_}_jump"][mat], yy[mat.values], "o", ms=2.6, color="black")
    a.axvline(0, color="black", lw=0.5)
    a.set_yticks(yy)
    a.set_yticklabels([SHORT.get(x, x) + (" (reporting gap)" if (x == "Pinterest" and k_ == "spec") else "") for x in z.p], fontsize=8)
    a.set_xlabel("Residual-share jump" if k_ == "resid" else "Keyword-share jump", fontsize=8); a.set_ylim(-1, len(z))
fig.tight_layout(); save_figure(fig, "figures/fig_platforms.pdf", metadata={"Creator": None, "Producer": None, "CreationDate": None, "ModDate": None}, bbox_inches="tight", pad_inches=0.06); plt.close(fig)

# Figure 4: removed categories against sexual keywords after the cutoff
fig, ax = plt.subplots(figsize=(3.4, 3.0))
x = 100 * cwp.pre_removed_share
y = 100 * cwp.post_sexkw_share_all
ax.scatter(x, y, s=12, facecolor="white", edgecolor="black", lw=0.6)
ax.plot([0, 100], [0, 100], color="black", lw=0.5, ls=":")
for _, r in cwp.iterrows():
    if r.pre_removed_share > 0.3 or r.post_sexkw_share_all > 0.08:
        ax.annotate(SHORT.get(r.p, r.p), (100 * r.pre_removed_share, 100 * r.post_sexkw_share_all), fontsize=5,
                    xytext=(3, -1 if r.post_sexkw_share_all < 0.01 else 2), textcoords="offset points",
                    rotation=60 if r.post_sexkw_share_all < 0.01 else 0, ha="left", va="bottom")
ax.set_xlim(-3, 103); ax.set_ylim(-3, 103)
ax.set_xlabel("Removed categories before (% of statements)"); ax.set_ylabel("Sexual keywords after (% of statements)")
fig.tight_layout(); save_figure(fig, "figures/fig_crosswalk.pdf", metadata={"Creator": None, "Producer": None, "CreationDate": None, "ModDate": None}, bbox_inches="tight", pad_inches=0.06); plt.close(fig)
print(json.dumps(m, indent=1))

