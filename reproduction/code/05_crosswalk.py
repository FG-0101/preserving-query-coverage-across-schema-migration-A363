"""Where the removed categories went, and how much of them the keywords recover.

For every platform that filed statements under the two categories removed by the migration (pornography or sexualized
content, non consensual behaviour) in the 28 days before the cutoff, the script compares the daily share of those
categories before the cutoff with the share of statements carrying a sexual keyword after it, from the record level
archives (all keywords) and as the published aggregates show it (keywords with a column only). It also records which
categories absorbed the platform's statements, after mapping the two renamed categories to their new names. Platforms
need at least 100 statements per day in the removed categories before the cutoff and 100 statements per day in total
after it.
Run from the package root after code/03:  python3 code/05_crosswalk.py
Outputs: results/crosswalk_platform.csv, results/crosswalk_destinations.csv, results/category_shift.csv,
results/crosswalk.json
"""
import json
import numpy as np
import pandas as pd
from common import load_dumps, CUT, REMOVED, SEXUAL_KW, RENAMED_CAT

H = 28
d = load_dumps()
agg_cols = set(pd.read_csv("data/derived/complete_columns.csv", header=None).iloc[0, 3].split("|"))
w = d[(d.d >= CUT - pd.Timedelta(days=H)) & (d.d < CUT + pd.Timedelta(days=H))].copy()
w["post"] = w.d >= CUT
w["sex_all"] = w.kws.map(lambda t: any(k in SEXUAL_KW for k in t))
w["sex_vis"] = w.kws.map(lambda t: any(k in SEXUAL_KW and k in agg_cols for k in t))
w["removed"] = w.c.isin(REMOVED)
rows, dest = [], []
for p, g in w.groupby("p"):
    pre, post = g[~g.post], g[g.post]
    if pre[pre.removed].n.sum() < 28 * 100 or post.n.sum() < 28 * 100:
        continue
    r = {"p": p, "pre_n": float(pre.n.sum()), "post_n": float(post.n.sum()),
         "pre_removed_share": float(pre[pre.removed].n.sum() / pre.n.sum()),
         "pre_porn_share": float(pre[pre.c == REMOVED[0]].n.sum() / pre.n.sum()),
         "pre_ncb_share": float(pre[pre.c == REMOVED[1]].n.sum() / pre.n.sum()),
         "pre_sexkw_share": float(pre[pre.sex_all].n.sum() / pre.n.sum()),
         "post_sexkw_share_all": float(post[post.sex_all].n.sum() / post.n.sum()),
         "post_sexkw_share_visible": float(post[post.sex_vis].n.sum() / post.n.sum())}
    r["recovery_all"] = r["post_sexkw_share_all"] / r["pre_removed_share"]
    r["recovery_visible"] = r["post_sexkw_share_visible"] / r["pre_removed_share"]
    rows.append(r)
    # categories renamed by the migration are mapped to their new names before shares are compared
    pc = pre.groupby("c").n.sum() / pre.n.sum()   # categories are already mapped to their new names in load_dumps
    qc = post.groupby("c").n.sum() / post.n.sum()
    for c in sorted(set(pc.index) | set(qc.index)):
        dest.append(dict(p=p, c=c, pre_share=float(pc.get(c, 0.0)), post_share=float(qc.get(c, 0.0))))
cw = pd.DataFrame(rows).sort_values("pre_n", ascending=False)
cw.to_csv("results/crosswalk_platform.csv", index=False)
de = pd.DataFrame(dest)
de["change"] = de.post_share - de.pre_share
de.to_csv("results/crosswalk_destinations.csv", index=False)
# where the removed volume went: for each platform the new category with the largest gain in share
top = de[de.change > 0].sort_values("change", ascending=False).groupby("p").head(1)
out = {"platforms": int(len(cw)), "recovery_all_median": float(cw.recovery_all.median()),
       "recovery_visible_median": float(cw.recovery_visible.median()),
       "recovery_all_ge_half": int((cw.recovery_all >= 0.5).sum()), "recovery_all_lt_tenth": int((cw.recovery_all < 0.1).sum()),
       "recovery_visible_lt_tenth": int((cw.recovery_visible < 0.1).sum()),
       "pooled_pre_removed": float((cw.pre_removed_share * cw.pre_n).sum() / cw.pre_n.sum()),
       "pooled_post_sexkw_all": float((cw.post_sexkw_share_all * cw.post_n).sum() / cw.post_n.sum()),
       "pooled_post_sexkw_visible": float((cw.post_sexkw_share_visible * cw.post_n).sum() / cw.post_n.sum()),
       "top_destination_counts": top.c.value_counts().to_dict()}
json.dump(out, open("results/crosswalk.json", "w"), indent=1)
print(json.dumps(out, indent=1))
print(cw.round(4).to_string())

# Shift of the whole category distribution: Jensen and Shannon divergence (base 2) between the 28 days before and after
# the cutoff, renamed categories mapped to their new names, for every platform with at least 1,000 statements per day on
# both sides. Benchmark: the same divergence between two adjacent 28 day windows before the migration (8 April to
# 5 May 2025 against 6 May to 2 June 2025), from the complete aggregates.
from common import load_agg


def jsd(p, q):
    keys = sorted(set(p.index) | set(q.index))
    p = p.reindex(keys).fillna(0).values
    q = q.reindex(keys).fillna(0).values
    mm = 0.5 * (p + q)
    kl = lambda a, b: float(np.sum(np.where(a > 0, a * np.log2(np.where(a > 0, a, 1) / np.where(b > 0, b, 1)), 0)))
    return 0.5 * kl(p, mm) + 0.5 * kl(q, mm)


def dist(g):
    s = g.assign(c=g.c.map(lambda x: RENAMED_CAT.get(x, x))).groupby("c").n.sum()
    return s / s.sum()


k = load_agg(["2025-04", "2025-05", "2025-06"])
names = pd.read_csv("results/platform_names.csv")
k["p"] = k.p.map(lambda x: dict(zip(names.aggregate_name, names.dump_name)).get(x, x))
b1 = k[(k.d >= "2025-04-08") & (k.d <= "2025-05-05")]
b2 = k[(k.d >= "2025-05-06") & (k.d <= "2025-06-02")]
js = []
for p, g in w.groupby("p"):
    pre, post = g[~g.post], g[g.post]
    if pre.n.sum() < 28 * 1000 or post.n.sum() < 28 * 1000:
        continue
    r = {"p": p, "jsd_migration": jsd(dist(pre), dist(post))}
    x1, x2 = b1[b1.p == p], b2[b2.p == p]
    r["jsd_benchmark"] = jsd(dist(x1), dist(x2)) if x1.n.sum() >= 28 * 1000 and x2.n.sum() >= 28 * 1000 else np.nan
    js.append(r)
js = pd.DataFrame(js).sort_values("jsd_migration", ascending=False)
js.to_csv("results/category_shift.csv", index=False)
both = js.dropna()
out.update({"jsd_platforms": int(len(js)), "jsd_median": float(js.jsd_migration.median()),
            "jsd_benchmark_median": float(both.jsd_benchmark.median()), "jsd_benchmark_platforms": int(len(both)),
            "jsd_exceeds_benchmark": int((both.jsd_migration > both.jsd_benchmark).sum()),
            "jsd_over_0_1": int((js.jsd_migration > 0.1).sum()), "jsd_benchmark_over_0_1": int((both.jsd_benchmark > 0.1).sum()),
            "jsd_common_median": float(both.jsd_migration.median()), "jsd_common_over_0_1": int((both.jsd_migration > 0.1).sum())})
json.dump(out, open("results/crosswalk.json", "w"), indent=1)
print(js.round(4).to_string())
print({k_: out[k_] for k_ in out if k_.startswith("jsd")})
