# Run-books

A run-book is a check a person runs because it needs credentials, the cloud, real data or human
eyes (gate 4 in `CONTRIBUTING.md`). An agent writes it; the maintainer runs it and pastes back the
result.

**Write a new one as a notebook:** copy [`TEMPLATE.ipynb`](TEMPLATE.ipynb). Markdown cells say what
each step does and what PASS means; each PASS is a plain `assert`; a Settings cell holds every input
(no environment variables); commit it with outputs cleared (`scripts/clear_notebook_outputs.py`).

What is here:

- `TEMPLATE.ipynb` — the starting point.
- `58-redownload-austria-mpc.md` + `scripts/58_redownload_austria.py` — the last Markdown run-book,
  kept only until #119 turns it into a notebook for spec 59's Austria re-download.

Finished run-books (26–59) were deleted in spec 102 P3c. Their outcomes are in the specs and
`docs/history.md`; the files are readable at tag `docs-archive-2026`.
