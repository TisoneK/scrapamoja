# Reply: market and period coverage for all scopes

Answer to the consumer's request for totals lines on every subject x period
combination, unambiguous labelling, period scores in H2H history, and honest
gaps. Evidence is from the local odds store (459 basketball events, 8 runs of
2026-10-02, betwinner/melbet) plus live probes on 2026-10-03. Nothing here
changes scraper code yet.

## 0. The two findings that matter most

1. **The 18 "period scopes with no line" are not a source gap.** A default
   scrape never fetches sub-games (`--subgames` is off), so those markets are
   *never requested*. Today "the source doesn't have it" and "we didn't look"
   are stored identically (no rows). Section 5 fixes that.
2. **The 101 full-match skips (no usable H2H) are mostly our loss, not the
   source's.** The store holds H2H for 128 of 459 events (28%). Re-asking the
   source for events with no stored H2H returned data for 15 of 16 (random
   sample) and 41 of 60 (run through the scraper's own enrichment code); the
   rest answered 204 (no data). So roughly 70% of events can have H2H and we
   keep ~28%. Cause: H2H is requested once, when a match is first stored; a
   failed or skipped attempt is never retried, because `--skip-processed`
   treats any stored match as done. Neon and this local store differ in size;
   the pattern should be the same, but I measured the local one.

## 1. Feasibility: which of the 21 basketball combinations exist

Source: per-match sub-games. Every period has its own game id; its
`GetGameZip` carries that period's own `Total`, `Individual Total Home` and
`Individual Total Away` (each a ladder of lines; Over prices were printed in
the probe, and Under prices exist on the full-time versions of the same
markets, but Under on the period versions is not yet confirmed).

Verified live on two events: one with all six sub-games (Q1-Q4, 1st half,
2nd half) returned all three subjects for all six periods = **21/21**.
The other event offered only Q1 and 1st half (6 of 21).

How often a period's sub-game is listed per event (459 stored events):

| Period | Events listing it | Notes |
|---|---|---|
| Full time: match total | 458 (99.8%) | main game |
| Full time: home / away team total | 386 (84%) | 16% of events have no team-total market, matching your 54 of 333 |
| 1st quarter | 364 (79%) | |
| 1st half | 230 (50%) | |
| 2nd half | 141 (31%) | |
| 2nd / 3rd / 4th quarter | 144 / 142 / 142 (31%) | |

Availability is by league, not random: Q2-Q4 and 2nd half appear for the
better-covered leagues (ACB, BBL, LNB, Euroleague, Bundesliga 2) and mostly
not for the rest. Within a listed period, all three subjects were present in
both probes; I have not yet confirmed that for every league.

## 2. Gaps: stop expecting these

- Q2/Q3/Q4 and 2nd-half lines for roughly 70% of events (lower leagues).
- Team totals at full time for 16% of events.
- Halves in H2H history: the source reports quarters (99% of finished games
  have all four) and an overtime entry, but **no half scores**. Per your
  "do not derive" rule they will be absent, not summed from quarters.
- Overtime totals lines: never seen.

## 3. Labelling proposal

Two fixed fields on every line, instead of one combined scope:

- `subject`: `MATCH` | `HOME_TEAM` | `AWAY_TEAM`
- `period`, basketball: `FULL_TIME` | `HALF_1` | `HALF_2` | `QUARTER_1`..`QUARTER_4`
- `period`, other sports (same pattern, from each sport module's period
  structure): football `FULL_TIME` | `HALF_1` | `HALF_2` (regular time);
  ice hockey `FULL_TIME` | `PERIOD_1`..`PERIOD_3`; tennis `SET_1`..`SET_5`.
- Overtime in results: `OVERTIME_1`, `OVERTIME_2`.

Note the existing scope names fold subject and period together
(`FULL_MATCH` = match + full time; `HOME_TEAM_TOTAL` = home team + full time).
They stay as a derived column for compatibility; `FULL_TIME` is the period
word, `FULL_MATCH` is not reused as a period name.

Normalisation happens at our layer: source market names (`Total`,
`Individual Total Home`, `1 Half`, `2 Half`, `1st quarter`) map to these
values once; consumers never see the source strings as labels.

## 4. Effort and order

1. **H2H completeness (do first, ~1 day).** Backfill pass for stored upcoming
   events with no H2H and no recorded "source said none"; retry failures.
   This is the largest loss the consumer reported and needs no schema change
   beyond the coverage record below.
2. **Coverage record (~1 day).** One row per event, subject, period and run
   with status `offered` | `not_offered` | `not_attempted` | `fetch_failed`.
   Gives you the "honest gaps" distinction and makes (1) auditable.
3. **Sub-games on by default for basketball, with subject/period lines
   (~2 days).** Writes a `totals_lines` view/table: subject, period, line,
   over odds, under odds, bookmaker, captured_at. Per-team period markets are
   already parsed; only the labelling and storage are new.
4. **Period scores in H2H (~0.5 day).** Already stored per quarter; add the
   overtime relabel and keep absent halves absent.
5. **Other sports** follow once basketball is stable.

Hard or flaky:
- Cost: one extra request per listed period, up to 7 per event. At 3 req/s a
  ~300-event pass is roughly 2,000 requests (about 11 minutes) instead of ~300;
  the shared rest/budget guards already bound the risk of source refusals.
- The set of listed periods may change between runs (not yet measured); the
  coverage record has to be per run, not once.
- Period lines move; capture time matters more than for full time.

## 5. What changes in existing output

- **Additive:** new rows with `scope` `QUARTER_n` / `*_HALF` for team-total
  markets; new `subject`/`period` columns; new coverage table.
- **Changed meaning, none today** except: rows currently stored as scope
  `FULL_MATCH` stay as they are. Stored `period_name` "4th period" (period key
  4 in 162 H2H games) is really **overtime** (home+away quarters plus that
  entry equal the final score); it will be relabelled `OVERTIME_1`, which
  changes that string for new rows only.
- **Legacy:** six stored events listed as "Home (Points)" / "Away (Points)"
  carry totals in the hundreds to thousands (placeholder listings, since
  excluded at discovery). Ignore them; they can be deleted from the store.
- **Consumer side, flagged not built:** the engine's scope list has nine
  combined values and no per-team period scopes, so using the new lines means
  extending its scope model. That is outside the scraper's boundary.
