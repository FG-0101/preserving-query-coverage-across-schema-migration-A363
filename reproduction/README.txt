Preserving Query Coverage across Schema Migration
reproduction

Requirements
  CPython 3.14 on a POSIX system with the pinned packages in ENVIRONMENT.json
  (duckdb, matplotlib, numpy, pandas, pyarrow, scipy, statsmodels and their
  dependencies).  The package is self-contained: every input is included and no
  network access is used.

Command
  python3.14 -B reproduce.py

  The command copies code/, data/, results/, figures/ and tex/ into
  runs/<UTC timestamp>/ and runs the paper's eight analysis stages there in
  dependency order: record-level validation, the regression discontinuity, the
  category crosswalk, the long-run series, the report tables and figures, the
  wide-table reflow, the schema-aware reconstruction and the date
  reconciliation.  The shipped tree is never modified.  Each stage runs with
  OMP_NUM_THREADS and the other BLAS thread limits set to 2 and a
  180-second CPU limit; use --cpu-limit 3600 if the machine is slow.
  The paper's run.py pins and checks the package versions before running; this
  package records the same pins in ENVIRONMENT.json but
  does not stop on a mismatch, so it can be run on a compatible Python 3.14.

Comparison
  Each results/*.json and results/*.csv file under runs/.../results/ is
  compared with expected.json, which holds the corresponding reference result.
  Execution records, environment fields, absolute paths and wall-clock timings
  are dropped before comparison; integer counts, memberships and text must then
  agree exactly, and floats to a relative tolerance of 1e-9, which admits the
  low-order floating solver differences the paper's README permits.  A CSV is
  compared as a value-sorted row multiset, because row order is not part of the
  contract.  PASS and CHECK.json indicate a full match.

Excluded from the comparison
  Nothing under results/ is excluded; all 29 result files behind the paper's
  printed values are compared.  These generated or execution artifacts are not
  compared, by name:
    reproduction_logs/environment.json, reproduction_logs/execution.json and
    the eight step logs reproduction_logs/03_validate.py.log, 04_rd.py.log,
    05_crosswalk.py.log, 06_longrun.py.log, 07_report.py.log,
    08_schema_aware.py.log, 09_reconcile_dates.py.log, 10_readable_tables.py.log
      (host, paths, library inventory, wall-clock seconds and pandas positional
      index columns; no scientific value)
    figures/fig_hidden.pdf, figures/fig_rd.pdf, figures/fig_platforms.pdf,
    figures/fig_crosswalk.pdf  (PDF vector coordinates are not a scientific
      value)
    tex/macros.tex, tex/tab_hidden_kw.tex, tex/tab_hidden_cat.tex, tex/tab_rd.tex,
    tex/tab_bandwidth.tex, tex/tab_robust.tex, tex/tab_rd_platform.tex,
    tex/tab_crosswalk.tex, tex/schema_aware.tex, tex/date_reconciliation.tex
      (LaTeX layout; the numbers they render are compared through results/)
  The driver's own per-stage stdout and stderr captures (runs/<...>/<stage>.stdout
  and .stderr) are execution records and are likewise not compared.

Expected counts
  71 daily archives with 43,094 weighted record-reduction cells totalling
  1,339,503,336 source statements, 21 monthly complete aggregates, and 29
  compared result files.

Data
  data/derived/ holds the 71 daily record reductions, the monthly complete
  aggregate reductions, the archive index and the publisher checksum records.
  No acquisition step is included.  Sources and terms are in SOURCE.txt and
  LICENSE.txt.

Files
  reproduce.py      the driver
  expected.json     expected result content, keyed by run-relative path
  code/             the analysis programs
  data/             the reduced inputs
  results/          the stage output directory (written in the run copy)
  figures/, tex/    the stage output directories (written in the run copy)
  RESULTS.tsv       paper item to program, line, output and input
  ENVIRONMENT.json  the recorded release environment
