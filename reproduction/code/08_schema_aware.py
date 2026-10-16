"""Schema-aware categorical export of the verified daily record reductions.
All observed identifiers are retained. Only publisher-documented aliases are merged.
Counts with no keyword are retained in the record table, avoiding loss from explode.
This representation covers sampled archive days; it does not recover missing semantics.
"""
import json
from pathlib import Path
import pandas as pd
from common import load_dumps,RENAMED_KW,parse_spec
idx=pd.read_csv('data/derived/dump_index.csv')
expected=set(idx.date);available={p.stem.removeprefix('dump_') for p in Path('data/derived').glob('dump_20*.parquet')}
assert available==expected,(expected-available,available-expected)
d=load_dumps();d['keyword_ids']=d.kws.map(lambda v:tuple(sorted({RENAMED_KW.get(k,k) for k in v})))
original_ids=set(d.kws.explode().dropna())
expected_canonical={RENAMED_KW.get(k,k) for k in original_ids}
assert set(d.keyword_ids.explode().dropna())==expected_canonical
cols=['p','d','c_raw','c','c_add','spec','spec_other_text','keyword_ids','n']
d[cols].to_parquet('data/derived/schema_aware_records.parquet',index=False)
k=d[['p','d','c','keyword_ids','n']].explode('keyword_ids').dropna(subset=['keyword_ids'])
k=k.groupby(['p','d','c','keyword_ids'],as_index=False).n.sum().rename(columns={'keyword_ids':'keyword'})
k.to_parquet('data/derived/schema_aware_keywords.parquet',index=False)
back=pd.read_parquet('data/derived/schema_aware_records.parquet')
# Parquet may use milliseconds while pandas parsed whole days in seconds.
# Compare dates before matching representation units for index assertions.
pd.testing.assert_series_equal(d.d.dt.date,back.d.dt.date,check_dtype=False)
back['d']=back.d.astype(d.d.dtype)
plain=[x for x in cols if x!='keyword_ids']
pd.testing.assert_frame_equal(d[plain],back[plain],check_dtype=False)
pd.testing.assert_series_equal(d.keyword_ids,back.keyword_ids.map(tuple),check_dtype=False)
assert list(back.spec.map(parse_spec))==list(d.kws)
left=d.groupby(['p','d']).n.sum().sort_index();right=back.groupby(['p','d']).n.sum().sort_index()
pd.testing.assert_series_equal(left,right)
for a,b in RENAMED_KW.items():assert len({RENAMED_KW.get(x,x) for x in (a,b)})==1
# Independently query each keyword from the record lists and compare the long table.
for kw,g in k.groupby('keyword'):
 expected_n=int(d[d.keyword_ids.map(lambda v:kw in v)].n.sum())
 assert int(g.n.sum())==expected_n,(kw,g.n.sum(),expected_n)
res={'archive_days':len(expected),'statements':int(d.n.sum()),'reduced_records':len(d),'keyword_identifiers_original':int(d.kws.explode().nunique()),'keyword_identifiers_canonical':int(k.keyword.nunique()),'all_record_fields_roundtrip_match':True,'all_platform_day_totals_match':True,'all_keyword_queries_match':True,'official_aliases_only':True,'scope':'verified sampled daily archive reductions; structured fields only'}
json.dump(res,open('results/schema_aware_validation.json','w'),indent=2)
with open('tex/schema_aware.tex','w') as f:
 f.write('\\subsection{A schema-aware reconstruction}\\label{sec:schema-aware}\n')
 f.write(f'We implement a repair on the {len(expected)} sampled daily archives. A record-count table retains the exact keyword list, original category, category additions and a normalized category alongside the count; a long table stores every observed keyword identifier. Only the four documented keyword renamings are merged, with duplicate aliases within a record removed before counting. Empty keyword lists remain represented in the record table. ')
 f.write(f'The export retains {res["keyword_identifiers_original"]} original and {res["keyword_identifiers_canonical"]} canonical keyword identifiers. An independent round-trip check reproduces every platform-day total and every canonical keyword count exactly. ')
 f.write('This representation prevents a fixed list of pivot columns from dropping new values. It repairs structured query coverage on the sampled days; identification of a retired content concept still requires suitable reporting fields or validated labels.\n')
print(json.dumps(res,indent=2))
