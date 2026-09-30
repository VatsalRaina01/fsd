---
status: current
summary: The working contract: Claude never runs pipeline/networked scripts and hands the user run-books instead; still the operative rule in CLAUDE.md.
---

# Spec 24 — working contract: I don't run scripts; you run run-books

**Status:** SIGNED OFF + IMPLEMENTED (C1 pytest-ok, C2 `runbooks/`, C3 ok, C4 25→26, C5 ok).
Landed: `CLAUDE.md` (run policy + model-split/effort + handoff) + `fsd/runbooks/TEMPLATE.md`.
**Why:** the spec-23 tiny-download run went wrong in ways that were *process* failures, not code
failures — I launched a long download, you couldn't stop it or see progress, and I burned your
tokens polling its log. This codifies a safer division of labour. Small + self-contained.

## Locked decisions (from the interview)

- **D1 — Run policy.** I **never** run pipeline / long / networked / side-effecting scripts (demos,
  downloads, snakemake, anything more than a few seconds, anything that touches the network or
  writes real data). I **may** still run fast, read-only, un-babysat checks: `ruff`, `pytest`,
  `grep`/`rg`, `ls`, `git status`, file reads. I **never** background (`nohup`/`&`) a script and
  **never** poll a running process's logs.
- **D2 — Results via a compact `_result.json`.** Anything you run emits a small machine-readable
  result file; you paste that (or the traceback). I diff it against the run-book's success criteria.
  I do **not** read live logs.
- **D3 — Model split.** Opus (me) does interview → spec → sign-off → debug → review. Implementation
  happens in a **Sonnet** session you switch to (`/model`). No subagent spawning for coding (that
  re-derives context and costs tokens — the thing we're fixing).
- **D5 — Effort & token policy** (from the Anthropic docs review). Effort is set per session with
  `/effort` (levels: low, medium, high=default, max, plus xhigh). Ours:
  | role | model | effort |
  |---|---|---|
  | interview / spec / **debug** | Opus 4.8 | **high** (xhigh/max only for a genuinely hard bug) |
  | implement a signed-off spec | Sonnet 5 | **medium** (following a clear spec is mechanical) |
  | review / lint-fix | Sonnet 5 | medium |
  Principle: **never pay Opus-max for boilerplate, never pay Sonnet-high for spec-following code** —
  a signed-off spec is what lets Sonnet run at medium safely. Plus: context window is *the*
  constraint (quality degrades as it fills) → `_result.json` not live logs (D2); handoff between
  sessions via **files** (specs / `PROGRESS.md` / `MEMORY.md`), not chat; `/compact` or a fresh
  session between workstreams.
- **D6 — Handoff protocol (uses the installed `/handoff` skill).** At a session boundary (context
  getting heavy, or plan→implement handoff, or Opus→Sonnet switch), the **user** runs
  `/handoff <what the next session does>` (the skill is user-invocable only — Claude cannot trigger
  it). It writes a distilled handoff doc (to the OS temp dir) that *references* the spec/PROGRESS/
  MEMORY by path rather than duplicating them, and lists suggested skills. The user then starts a
  **fresh** session (clean context = no rot), switches model/effort per D5, and points it at the
  handoff doc + the spec. **Durable state stays in `PROGRESS.md` / `MEMORY.md` / `specs/`** (the
  system of record); the handoff doc is the *ephemeral baton*, not a replacement for those.
- **D4 — This is spec 24, the first of a small series.** Next, separately: **spec 25** (download +
  jp2→COG redesign — conversion currently runs inline on the transfer threads and GDAL holds the
  GIL, starving downloads) and **spec 26** (a `--dry-run`/`--stop-file`/progress "safe runner"
  wrapper for the e2e). Not in this spec.

## SO-1 — Run policy in CLAUDE.md (hard rule)

Add to `CLAUDE.md` "Working style & preferences":
> **Claude never runs pipeline/long/networked/side-effecting scripts (demos, downloads, snakemake,
> anything > a few seconds or with network/side effects), and never backgrounds a script or polls
> its logs.** Claude may run fast read-only checks it doesn't babysit (`ruff`, `pytest`, `grep`,
> `ls`, `git status`, reads). Everything else is handed to the user as a **run-book** (below); the
> user runs it and pastes back the `_result.json` / error.

## SO-2 — Run-book format

Runnable work ships as a Markdown run-book (in `fsd/runbooks/<name>.md`, or the task's doc). Each has:
1. **Purpose** (one line) + **prerequisites** (venv, creds, inputs).
2. **Commands, in order** — copy-pasteable, one block per step, each with the **expected output** and
   an explicit **PASS/FAIL** condition.
3. **Success criteria** — the `_result.json` fields that must hold (SO-3), so success is *determined*,
   not eyeballed.
4. **Stop / observe** — how to see progress and how to abort cleanly (SO-4).

## SO-3 — The `_result.json` contract

Every runnable step writes (or appends to) `<outdir>/_result.json`:
```json
{ "step": "download", "status": "ok|fail", "pass": true,
  "metrics": { "granules": 7, "tiles": 1, "gb": 2.1 },
  "expected": { "tiles": 1, "granules_max": 12 },
  "error": null }
```
- `pass` = the step met its `expected`. `status` = did it complete without crashing.
- You paste this file (small); I diff `metrics` vs `expected` and report PASS/FAIL per step.
- A run writes one `_result.json` per step (array) or a top-level `{steps:[...], pass: all}`.

## SO-4 — Progress + termination requirements (for any script we ship)

Any script a run-book asks you to run **must**:
- print a **live progress line with ETA** (already the norm — `[[long-process-progress]]`);
- support **`--dry-run`/`--plan`**: print the counts + GB + ETA it *would* incur and exit **with
  zero network bytes**, so you can see the cost before committing;
- be **Ctrl-C safe** (atomic writes; a re-run resumes) **and** honor a **`--stop-file PATH`** (checks
  each iteration; exits cleanly if the file appears) so a background run is stoppable without hunting
  a PID;
- run **foreground by default** and print its PID, so you always have a kill handle.

*(The e2e already had atomic/idempotent download + progress; it was missing `--dry-run`, a stop-file,
and a compact result — those land in spec 26. Spec 24 only sets the contract.)*

## SO-5 — Model split in CLAUDE.md

Add:
> **Opus** does interview/spec/sign-off/debug/review. **Implementation runs in a Sonnet session**
> the user switches to (`/model sonnet`), against a signed-off spec; switch back to Opus for review
> and debugging. Don't spawn subagents just to write code.

## SO-6 — Effort & token policy in CLAUDE.md (D5)

Add the D5 effort table + the "context is the constraint" line to `CLAUDE.md`: Opus@high for
plan/spec/debug (xhigh/max only for hard bugs), Sonnet@medium for spec-following implementation,
`/effort` to set; `_result.json` not logs; handoff via files.

## SO-7 — Handoff protocol in CLAUDE.md (D6)

Document the `/handoff` flow in `CLAUDE.md`: **user** runs `/handoff <next-session goal>` at a
session boundary → fresh session → set model/effort (D5) → point it at the handoff doc + the spec.
Durable state stays in `PROGRESS.md`/`MEMORY.md`/`specs/`; the handoff doc is the ephemeral baton.
A tiny **handoff checklist** goes at the top of the run-book template (SO-2).

## SO-8 — Deliverables

- Edit `CLAUDE.md`: SO-1 (run policy), SO-5 (model split), SO-6 (effort/token), SO-7 (handoff) +
  note the run-book/`_result.json` contract.
- Add `fsd/runbooks/TEMPLATE.md` (the SO-2/SO-3 skeleton + the SO-7 handoff checklist).
- No code run. No pipeline touched. (Spec 25/26 do the download + runner work.)

## Confirm at sign-off (small, so nothing's missed)

- **C1** `pytest` is on my "may run" list — OK? (It's local + seconds; but it *can* import heavy
  modules. Say if you'd rather I never run it either — that was your "never run anything" option.)
- **C2** Run-book location = `fsd/runbooks/`? (vs the task's own doc, e.g. `demos/E2E_AUSTRIA.md`.)
- **C3** `_result.json` shape above good enough, or do you want a stricter schema?
- **C4** Order after this: **spec 25 (download/convert redesign)** before **spec 26 (safe runner)**?
- **C5** Handoff (D6): split right — `/handoff` doc = ephemeral baton, `PROGRESS.md`/`MEMORY.md`/
  `specs/` = durable system of record?

---

## Amendment A1 — run-books are notebooks you can read (2026-09-30)

**Status:** SIGNED OFF 2026-09-30 (A-C1 yes, A-C2 yes, A-C3 this Opus session builds it). A1.5's kernel rule was added at sign-off, from the user's own confusion over `export PYTHONPATH=src`.

**Why.** Run-books so far are a Markdown page plus a separate driver script
(`runbooks/scripts/*.py`) plus shell environment variables (`$PY`, `$OUT`, `$RB`, `PYTHONPATH`).
The prose says what a step tests; the code that actually tests it lives elsewhere, behind generic
plumbing (result writers, stdout tees, `try/except` around everything, one-line `bool(a and b and
…)` pass conditions). The user ran the commands but could not *read* the test — which defeats the
point of a run-book: the person running it should be able to verify, from the code in front of
them, what "PASS" means (user, 2026-09-30). This amendment trades a little run convenience for
that readability. **D1 (Claude never runs these) is unchanged.**

### Decisions

- **A1.1 — Format.** A run-book is **one notebook**, `runbooks/<NN>-<name>.ipynb`. Markdown cells
  explain (what, why, which AC, expected result, time/disk estimate); code cells do the work. **No
  separate driver script.** Replaces SO-2's Markdown-plus-script shape.
- **A1.2 — Code you can read.** Cells call fsd's public verbs (`fsd.download`,
  `create_training_data`, …) or documented module functions **directly, with keyword arguments
  spelled out**. A helper function is allowed only when short (~15 lines), defined in the notebook
  just above its first use, with a one-line docstring. **No generic plumbing** — no result-file
  writers, no stdout capture, no `try/except` wrapped around a whole step (let the error show).
- **A1.3 — PASS is an `assert`.** Each check is a plain `assert <condition>, "<expected X, found
  Y>"`. The Markdown above the cell states the PASS condition in words; the assert must say the same
  thing. A step that records an outcome rather than gating (e.g. "does a killed blob upload leave a
  partial file?") prints its outcome and does not assert.
- **A1.4 — No environment variables as glue.** The first code cell, **Settings**, holds every path,
  date, ROI, collection and credential-*file* path as a plain Python variable. Paths are derived from
  the notebook's own location, never a hard-coded home directory. Private values (anything
  `tests/test_notebooks.py` forbids) come from `fsd.config.load()` (spec 54), as the demo notebooks
  already do. Environment variables remain legitimate for what they are for — secrets and
  per-machine/per-deploy config the user's machine already supplies (e.g. an `az login` session) — and
  a cell that must set tool config does it through fsd's own API (e.g. `configure_storage("azure")`),
  never through an `export` the user has to remember.
- **A1.5 — Say which kernel and which code.** Two separate facts, both the run-book's job, never
  the user's to guess:
  - **Kernel** (which Python runs the cells). The first Markdown cell names it — the main
    checkout's `fsd/.venv` (`.venv`, Python 3.11; the only kernel with fsd's dependencies) — and says
    how to pick it in VS Code, including from a worktree, whose folder has no `.venv` of its own.
    The notebook's metadata carries the same kernel so an editor pre-selects it. The first code cell
    **asserts** it: `sys.prefix` must be a `.venv` that sits inside an fsd checkout.
  - **Code** (which `fsd` gets imported). `fsd` is installed *editable* from the **main** checkout,
    so a plain `import fsd` inside a worktree silently runs `main`'s code. Every run-book therefore
    puts **its own checkout's** `src/` first on `sys.path` before importing `fsd` — derived from the
    notebook's location, so the same cell is right in `main` and in any worktree — and asserts that
    `fsd.__file__` lies inside it (which also catches a kernel that imported `fsd` earlier: restart
    it). This replaces `export PYTHONPATH=src`, which did the same thing invisibly: `src` there was
    a relative folder path, resolved against whatever directory the shell happened to be in.
- **A1.6 — Steps survive a kernel restart.** Each step reads what it needs from **disk** (catalogs,
  files) and the Settings cell, never from variables created by an earlier step. After a crash:
  run Settings + the which-code cell, then continue at any step.
- **A1.7 — Big or dangerous steps.** Before a step that moves more than ~1 GB, a **plan** cell shows
  counts and estimated GB without transferring anything, where fsd offers a way to measure; where it
  does not, the Markdown says the number is an unmeasured estimate. **Stop** = interrupt the kernel;
  **resume** = re-run the cell (the verbs write atomically and skip what is already published).
  **Progress** = the verbs' own printed progress lines. A step that must kill a process on purpose
  runs it as a **child process** (`subprocess.run([sys.executable, "-c", CHILD])`) with the child's
  code visible in the cell — `os._exit` inside the notebook would kill the kernel itself.
- **A1.8 — What you paste back.** Either the failing cell's assert message / traceback, or the
  output of the final **Summary** cell (a small dict: the numbers each step measured). Same purpose
  as SO-3's `_result.json` — small, no logs — so SO-3's per-step result files are dropped for
  run-books.
- **A1.9 — Commit hygiene.** Run-book notebooks are committed with **outputs and execution counts
  cleared** (Restart & Clear All Outputs). `tests/test_notebooks.py`'s guards — no saved outputs, no
  hard-coded identifiers — are extended to `runbooks/*.ipynb` **by glob** (a new run-book is
  guarded the moment it exists); the identifier ban is what keeps private values out, so a run-book
  that needs one reads it from `fsd.config.load()`. Two run-book-only tests enforce A1.5: the
  metadata names the `.venv` kernel, and the source checks `sys.prefix` and `fsd.__file__`. Running a run-book therefore leaves the tracked file
  modified until it is cleared — accepted.
- **A1.10 — Scope.** New run-books only. Existing Markdown run-books stay as they are (they are
  point-in-time evidence, not a design constraint). SO-4's flags (`--dry-run`, `--stop-file`, print
  the PID) keep applying to **CLI scripts shipped in `src/`**, not to run-books. The first
  conversion is 59-P2 (never run); its `runbooks/scripts/59_p2_window_a.py` is deleted by it.

### Best-practice alignment / sources

- **The Twelve-Factor App, "III. Config"** (https://12factor.net/config) — supplied A1.4's line
  between legitimate and illegitimate environment variables: env vars are for config "likely to vary
  between deploys" (resource handles, credentials), while config that "does not vary between
  deploys … is best done in the code." A run-book's dates, ROI and output folder are the latter.
- **CPython `os._exit` (docstring, Python 3.11 in the project venv)** — "Exit to the system with
  specified status, without normal exit processing." Supplied A1.7's rule: a deliberate kill must run
  in a child process, since the call would end the kernel process itself. (The docs.python.org page
  was fetched but came back truncated before the entry; the in-interpreter docstring is CPython's
  own text.)
- **In-repo precedent** — `tests/test_notebooks.py` + `.gitignore` (tracked-notebook leak guard;
  blob paths allowed, user 2026-09-29) supplied A1.9; spec 54's `fsd.config.load()` supplied A1.4's
  source for private values.
- Searched and **not relied on:** nbconvert's docs (the fetched page does not cover clearing outputs
  in place, and nbconvert is not in the venv), so A1.9 names Jupyter's own menu action instead of a
  command.

### Deliverables (after sign-off)

1. `runbooks/TEMPLATE.ipynb` (replaces `TEMPLATE.md`, which gets a one-line pointer).
2. `tests/test_notebooks.py`: extend the guards to `runbooks/*.ipynb`.
3. `CLAUDE.md` run-policy bullet + `runbooks/README.md` header: "run-book = notebook, paste the
   assert or the Summary cell".
4. Convert 59-P2 to `runbooks/59-p2-window-a.ipynb`; delete its `.md` + driver script.

### Confirm at sign-off

- **A-C1** Unmerged-branch code via a visible `sys.path` cell (A1.5) — OK, vs. merging first?
- **A-C2** Running leaves the tracked notebook modified until you clear outputs (A1.9) — OK?
- **A-C3** Who builds deliverables 1–4: this Opus session (context already loaded, ~1 h), or a
  Sonnet session per D3/D5? The contract says Sonnet for implementation.
