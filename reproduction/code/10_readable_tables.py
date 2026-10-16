"""Reflow wide generated tables without changing any numerical results.
Run after 07_report.py. Final table type is 8 pt with compact padding.
"""
from pathlib import Path
from collections import Counter
import re,json,hashlib
tex=Path('tex');receipt=[]
def data_rows(s):
    return [line.removesuffix('\\\\').split(' & ') for line in s.splitlines() if line.endswith('\\\\') and not any(x in line for x in ['multicolumn','Outcome','Variant'])]
def write(name,old,new):
    old_data='\n'.join(' & '.join(r) for r in data_rows(old))
    new_data='\n'.join(' & '.join(r) for r in data_rows(new))
    assert Counter(re.findall(r'\d+\.\d+',old_data))==Counter(re.findall(r'\d+\.\d+',new_data)),name
    (tex/name).write_text(new)
    receipt.append({'file':name,'source_sha256':hashlib.sha256(old.encode()).hexdigest(),'reflow_sha256':hashlib.sha256(new.encode()).hexdigest(),'all_decimal_values_and_multiplicities_unchanged':True})
name='tab_bandwidth.tex';old=(tex/name).read_text();rows=data_rows(old)
assert len(rows)==5 and all(len(r)==10 for r in rows)
out=['{\\fontsize{8}{10}\\selectfont\\setlength{\\tabcolsep}{3pt}',r'\begin{tabular}{p{3.0cm}rrrrr}\toprule',r'Outcome & Days & Statement jump ($p$) & Platform jump ($p$) & Up & Down\\\midrule']
short={'Residual category share':'Residual category','Keyword share, all keywords':'All keywords','Keyword share, as aggregated':'Visible keywords','Effective number of categories':'Effective categories'}
for r in rows:
    for j,window in enumerate([28,21,14]):
        up,down=r[7+j].split(', ')
        out.append(' & '.join([short.get(r[0],r[0]),str(window),r[1+j],r[4+j],up,down])+r'\\')
out.append(r'\bottomrule\end{tabular}}'+'\n');write(name,old,'\n'.join(out))
name='tab_robust.tex';old=(tex/name).read_text();rows=data_rows(old)
assert len(rows)==8 and all(len(r)==9 for r in rows)
short={'Main specification':'Main','Placebo without windows touching 14 to 19 March 2025':'March exclusions','Placebo also without windows containing 30 May 2025':'March/May exclusions','Cutoff day 1 July 2025 dropped':'Cutoff date excluded','Pinterest removed':'Pinterest excluded','Days 14 to 27 June 2025 dropped':'June gap excluded'}
out=['{\\fontsize{8}{10}\\selectfont\\setlength{\\tabcolsep}{3pt}',r'\begin{tabular}{p{3.4cm}rrrrrr}\toprule',r'\multicolumn{7}{l}{A. Platform-weighted estimates: jump ($p$)}\\',r'Variant & Days & Cutoffs & Keyword & Visible & Informative & Effective\\\midrule']
for r in rows:out.append(' & '.join([short[r[0]],*r[1:7]])+r'\\')
out.extend([r'\bottomrule\end{tabular}\par\medskip',r'\begin{tabular}{p{3.4cm}rrrr}\toprule',r'\multicolumn{5}{l}{B. Statement-weighted estimates: jump ($p$)}\\',r'Variant & Days & Cutoffs & Keyword & Visible\\\midrule'])
for r in rows:out.append(' & '.join([short[r[0]],r[1],r[2],r[7],r[8]])+r'\\')
out.extend([r'\bottomrule\end{tabular}\par\smallskip',r'\raggedright Keyword denotes all specific keywords. Visible denotes those with aggregate columns. March exclusions remove placebo windows touching 14--19 March 2025. March/May exclusions also remove windows containing 30 May. June gap excludes 14--27 June 2025.}',''])
write(name,old,'\n'.join(out))
Path('results/readable_table_validation.json').write_text(json.dumps({'tables':receipt,'font_pt':8,'data_values_changed':False},indent=2))
print('two wide tables reflowed; decimal values unchanged')

from layout_tables import format_generated_tables
format_generated_tables('P06')
