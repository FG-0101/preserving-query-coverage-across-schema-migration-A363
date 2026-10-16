"""Decompose archive-date versus creation-date discrepancies without inventing causes.
Requires every indexed archive and complete aggregate. Export every nonzero
platform-date/category/count and shared-keyword cell, plus date assignment counts.
The retained reductions cannot diagnose record-level revision or omission causes.
"""
from pathlib import Path
import json
import pandas as pd
from common import load_agg,parse_spec
idx=pd.read_csv('data/derived/dump_index.csv');days=set(idx.date)
files={p.stem.removeprefix('dump_'):p for p in Path('data/derived').glob('dump_20*.parquet')}
assert set(files)==days,(days-set(files),set(files)-days)
frames=[]
for day,p in sorted(files.items()):
 f=pd.read_parquet(p);f['archive_day']=pd.Timestamp(day);f['d']=pd.to_datetime(f.d);frames.append(f)
d=pd.concat(frames,ignore_index=True);k=load_agg(sorted({day[:7] for day in days}));k=k[k.d.isin(pd.to_datetime(sorted(days)))].copy()
names=pd.read_csv('results/platform_names.csv');rename=dict(zip(names.dump_name,names.aggregate_name));d['p']=d.p.replace(rename)
# Totals by archive label, and by creation date. Retain the full off-date movements.
off=d[d.d!=d.archive_day].groupby(['p','archive_day','d'],as_index=False).n.sum()
off.to_csv('results/archive_creation_date_movements.csv',index=False)
archive=d.groupby(['p','archive_day']).n.sum().rename_axis(['p','d'])
created=d[d.d.isin(pd.to_datetime(sorted(days)))].groupby(['p','d']).n.sum()
agg=k.groupby(['p','d']).n.sum();cells=pd.concat([archive.rename('archive_count'),created.rename('creation_count'),agg.rename('aggregate_count')],axis=1).fillna(0)
cells['archive_minus_aggregate']=cells.archive_count-cells.aggregate_count
cells['creation_minus_aggregate']=cells.creation_count-cells.aggregate_count
cells['date_assignment_component']=cells.archive_count-cells.creation_count
assert (cells.archive_minus_aggregate==cells.date_assignment_component+cells.creation_minus_aggregate).all()
cells.reset_index().to_csv('results/count_reconciliation_cells.csv',index=False)
# Category cells retain raw category identifiers. Normalization is not used to hide differences.
cat=pd.concat([d[d.d.isin(pd.to_datetime(sorted(days)))].groupby(['p','d','c']).n.sum().rename('record_count'),k.groupby(['p','d','c']).n.sum().rename('aggregate_count')],axis=1).fillna(0)
cat['difference']=cat.record_count-cat.aggregate_count
cat[cat.difference!=0].reset_index().to_csv('results/category_reconciliation_nonzero.csv',index=False)
kwcols=[c for c in k if c.startswith('KEYWORD_')];records=d[d.d.isin(pd.to_datetime(sorted(days)))].copy();records['kw']=records.spec.map(parse_spec)
records=records[['p','d','kw','n']].explode('kw');records=records[records.kw.isin(kwcols)]
rc=records.groupby(['p','d','kw']).n.sum().rename('record_count')
ak=k.groupby(['p','d'])[kwcols].sum().rename_axis(columns='kw').stack().rename('aggregate_count')
kw=pd.concat([rc,ak],axis=1).fillna(0);kw['difference']=kw.record_count-kw.aggregate_count
kw[kw.difference!=0].reset_index().to_csv('results/keyword_reconciliation_nonzero.csv',index=False)
tot=cells.groupby(level='d').sum();res={'archive_days':len(days),'record_statements':int(d.n.sum()),'off_archive_date_statements':int(off.n.sum()),'off_archive_date_platform_cells':len(off),'max_abs_date_assignment_component_daily':int(tot.date_assignment_component.abs().max()),'archive_equals_aggregate_days':int((tot.archive_minus_aggregate==0).sum()),'creation_equals_aggregate_days':int((tot.creation_minus_aggregate==0).sum()),'max_abs_creation_residual_daily':int(tot.creation_minus_aggregate.abs().max()),'max_abs_archive_residual_daily':int(tot.archive_minus_aggregate.abs().max()),'platform_day_creation_residual_cells':int((cells.creation_minus_aggregate!=0).sum()),'shared_keyword_residual_cells':int((kw.difference!=0).sum()),'category_residual_cells':int((cat.difference!=0).sum()),'cause_identified':False,'scope':'arithmetic date-assignment decomposition; remaining source-version/record-level cause not identified from reductions'}
json.dump(res,open('results/date_reconciliation.json','w'),indent=2)
with open('tex/date_reconciliation.tex','w') as f:
 f.write('\\subsection{Archive-date reconciliation}\\label{sec:date-reconciliation}\n')
 f.write(f'Across the {len(days)} archives, {res["off_archive_date_statements"]:,} statements have a creation date different from the archive label. Grouping by archive label and grouping by creation date are therefore distinct comparisons. For each platform-day, we decompose the archive-minus-aggregate count into the archive-minus-creation component and the creation-minus-aggregate residual; the identity holds exactly for every cell. ')
 f.write(f'The daily creation-date totals agree on {res["creation_equals_aggregate_days"]} days. The largest remaining daily count discrepancy is {res["max_abs_creation_residual_daily"]:,} statements; {res["platform_day_creation_residual_cells"]} platform-day cells have a nonzero residual. We export every nonzero category and shared-keyword cell, including {res["shared_keyword_residual_cells"]} shared-keyword cells, for inspection. ')
 f.write('The remaining discrepancy cannot be assigned to record revisions, omissions or another publisher-side process from the retained reductions. These counts establish the measured agreement of shared fields; they do not prove that every stage of the publishing pipeline is correct.\n')
print(json.dumps(res,indent=2))
