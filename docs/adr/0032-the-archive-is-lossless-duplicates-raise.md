# The imagery archive is lossless: duplicate acquisitions raise, they never replace

**Status:** accepted (grilling session, 2026-09-29 — confirmed by the user; [spec 59](../../specs/59-imagery-archive-layout.md))

**Context.** One acquisition can reach an fsd archive more than once: from two sources (MPC and
CDSE), or from one source that reprocessed it between two downloads. The copies are not always the
same bytes. MPC's 2018 Sentinel-2 L2A is Sen2Cor run by Esri in 2020 at baseline 02.12 (offset 0);
CDSE serves ESA's Collection-1 reprocessing at baseline 05.00 (offset −1000). The first sketch keyed
folders on the acquisition and let the latest processing replace the older one. That is a silent
change of radiometry under an existing catalog — the class of bug that already cost fsd the Austria
archive's ~1000 DN offset debt, and one that only shows up in model output.

**Decision.** The archive never overwrites or hides one processing with another. A granule folder is
named by its **canonical granule name**, which keeps the processing fields and drops the provider's,
so the *same processing* from two sources collides (and is stored once) while *two processings* of
one acquisition coexist. Duplicates are **detected** through a stored **acquisition key** and
surface as an **error at build time**, where they would otherwise be double-counted. The user
resolves them per acquisition with `processing=` (`"latest"` or a PEP 440 specifier), explicitly.
`download` takes the same `processing=` to choose what to fetch. Its default, `"latest"`, is the one
automatic choice left — made only among what one provider offers in one search, where the provider
itself calls the older products superseded — and every skip is printed, as is any acquisition a
download leaves with more than one processing in the archive.

**Considered options.** **Collide on acquisition, latest replaces** (Earth Search's Landsat model) —
rejected: silent, and Earth Search's own README concedes historical items still pointing at
superseded processings. **Archive the old processing, hide it from queries** (Open Data Cube's
`dataset archive`) — lossless, but the hiding is the same silent choice made one step later.
**Provider priority at search** (EODAG) — chooses a provider, not a processing; the user's rule is
"the raw data matters, not the source". **Keep provider item ids** — the same ESA product from two
sources would be stored twice under two names, and the collision could not be seen from the path.

**Consequences.** A build over a mixed archive can fail where it used to succeed — deliberately; the
message names each duplicate group and the argument that resolves it. Cross-source comparison is done
by downloading into two roots, not by keeping sources apart inside one. A catalog `id` is now the
canonical granule name, so every pre-59 catalog is re-downloaded (no shim, spec 58 D12's policy).
Provenance (which granules and processing versions a cube used) is recorded but not enforced here;
the train-versus-inference guard that consumes it is
[#101](https://github.com/nikhilsrajan/fsd/issues/101).
