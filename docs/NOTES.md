# Notes for the demo page

Working notes behind `docs/index.html`. Everything on that page comes from a file
in this repository. Wherever a number appears, the file it came from is named,
both here and in an HTML comment next to the number itself.

## What this actually does, in one sentence

You write down the courses you plan to take, term by term, and it tells you
whether that list actually earns you the degree, and if it does not, exactly
which requirement is left unfilled.

## Who has the problem, and the moment they are stuck

A second year Computing Science student at the University of Alberta, on the
Friday before registration opens. They have five terms sketched out on paper.
The degree requirements are spread across a dozen calendar pages, several of
them overlap, and a few of them cancel each other out (take CMPUT 174 and you
cannot also get credit for CMPUT 274). The advising office will answer, in about
three weeks. Registration opens on Monday. So the student registers on a guess,
and finds out in fourth year that one line of the degree was never filled.

## What people did before this existed

Three things, all of them slow or unreliable.

- **Read the calendar and count by hand.** The failure mode is the one this page
  demonstrates: you count "lots of senior computing courses" and miss that a
  single course cannot be credited to two different requirement lines at once.
- **Book an advising appointment.** Correct, and the answer arrives weeks after
  the decision had to be made.
- **Ask a language model.** This repository measured that. It scored 0.0 out of
  1 on the four questions that asked for a plan to be built from scratch. The
  plans read well and the checker rejected all of them.

## The numbers in this repository, and how they were measured

### The recorded run on the page

The step player replays one run of the constraint engine in `planner/`. It is
deterministic, needs no API key, and makes no network call. It was captured on
2026-07-27 at commit `d2db13f853c593115bb207746fbc2bea31c86a4a` with:

```
python -m planner --snapshot eval/snapshots/2026-06-28/offerings.json \
       validate eval/plans/near_miss_units_short.plan.yaml
```

The `--snapshot` argument matters. Without it the CLI picks the alphabetically
last directory under `eval/snapshots/`, which is `synthetic_demo`, the
deliberately perturbed copy used for the freshness demo. The page uses the real
2026-06-28 snapshot throughout.

The captured output, the per requirement assignment, and the step captions are
all in `docs/data/fulcrum.json`, which is also what the recorded-run badge links
to. `docs/data/fulcrum.js` is the same object emitted as a classic script so the
page works when `docs/index.html` is opened straight off disk.

| Number on the page | Value | Where it comes from |
| --- | --- | --- |
| Courses in the plan | 17 | `eval/plans/near_miss_units_short.plan.yaml`, counted across its five terms |
| Terms in the plan | 5 | same file |
| Units in the plan | 51 | every course is 3.0 units, from the scraped `credits` field, see `plan.units` in `docs/data/fulcrum.json` |
| Units the degree asks for | 54 | `eval/gold/cs_major.gold.yaml`, `program.total_units` |
| Places on the right column | 18 | the nine gold requirement groups total 54 units and every course here is 3 units, so 18 courses |
| Units short | 3 | the engine printed `have 3u, short 3u`, see `failure` in `docs/data/fulcrum.json` |
| Checks the engine runs | 5 | `planner/validate.py` module docstring |
| Course records scraped | 954 | `corpus/courses.jsonl`, one record per line |
| Courses with a hand checked prerequisite | 31 | `eval/gold/cs_major.gold.yaml`, the `prerequisites` list |
| Snapshot date | 2026-06-28 | `eval/snapshots/2026-06-28/offerings.json`, `snapshot_date` |
| Terms in the snapshot | 4 | same file, `term_order`, spring 2026 through winter 2027 |

The gap the page shows is real and it is the interesting part. `senior_cmput_400`
needs 6 units of 400 level computing and `senior_cmput_300_400` needs 15 units of
300 or 400 level computing, and a course may only be credited to one of them. The
plan holds CMPUT 401 and CMPUT 402 at the 400 level and only four courses at the
300 level, so the solver has to spend CMPUT 402 on the wider line, which leaves
the 400 only line holding one course where it needs two. Adding one 300 level
course (CMPUT 331, which is what `eval/plans/valid_174_stream.plan.yaml` has)
frees CMPUT 402 and the plan passes. Both verdicts were produced by running the
engine, not by reasoning about it.

### The question set numbers

| Number on the page | Value | Where it comes from |
| --- | --- | --- |
| Questions | 47 | `reports/results.json`, `meta.n_queries`, and 47 entries in `eval/queries/queries.yaml` |
| Question mix | 20 / 16 / 7 / 4 | counted from `eval/queries/queries.yaml` by `type`: `factual_offered`, `factual_prereq`, `plan_validity`, `plan_construction` |
| Score, search the course pages | 0.6489 | `reports/results.json`, `RAG-always.quality_overall` |
| Score, fixed rule sheet | 0.4468 | `reports/results.json`, `CAG-always.quality_overall` |
| Score, pick per question | 0.7234 | `reports/results.json`, `Routed.quality_overall` |
| Lead over the next best | 0.07 | 0.7234 minus 0.6489 is 0.0745 |
| Timetable answers with nothing made up | 18, 20, 18 of 20 | `citation_pass_rate` of 0.9, 1 and 0.9 in `reports/results.json`, taken over the 20 `factual_offered` questions |
| Cost for all 47 | $0.001557, $0.004150, $0.004294 | `reports/results.json`, `cost_usd_total`, summed from the token counts the provider reported |
| Middle answer time | 1.01 s, 1.22 s, 1.11 s | `reports/results.json`, `latency_p50` |
| Build a plan from scratch | 0.0 for all three | `reports/results.json`, `quality_by_type.plan_construction`, and the `plan_construction` column of `reports/results.csv` |

`reports/results.json` records `provider: deepseek`, `model: deepseek-v4-flash`,
`is_stub: false` and `snapshot_synthetic: false`, so those figures are from a
real paid run against the real model over the real snapshot. **No API call was
made while building this page.** The numbers were read out of the committed
report files.

The word "middle answer time" on the page is `latency_p50`, the time at which
half the answers had come back.

### What was deliberately not used

`eval/logs/RAG-always.jsonl`, `CAG-always.jsonl` and `Routed.jsonl` are on disk
but they are **not** the run those totals came from. Each holds 6 rows, every
answer is prefixed `[stub:...]`, and every `cost_usd` is 0. They are the leftover
output of a later offline run against the stand-in provider, and the directory is
git ignored. Nothing on the page cites them.

`reports/DRIFT_REPORT.md` is real, but its second snapshot is the synthetic one
(`eval/snapshots/synthetic_demo/`), which the repository README already flags as
a demonstration rather than a second real scrape. It is not cited on the page.

## What it does not do, the honest limits

The page carries three, and the first is the important one.

1. **It cannot build a plan for you.** Measured at 0.0 out of 1 across all three
   setups on the four `plan_construction` questions. This is the strongest single
   fact the repository holds and it is an argument against its own headline half,
   so it goes in the limits box in plain words rather than in a footnote.
2. **One degree, one calendar year.** The Computing Science major, 2026 to 2027.
   Only 31 courses have a prerequisite rule that a person verified by hand, so a
   plan drawn from courses beyond that set gets a note saying the prerequisite is
   unverified, not a verdict.
3. **The timetable is a photograph dated 2026-06-28,** and it lists only four
   terms. Terms after winter 2027 are judged by which season a course usually
   runs in, because no real timetable for them exists yet.

Two further limits from the repository README that the page does not have room
for: prerequisites outside the program (the maths chain behind some statistics
courses) are not enforced, and the graded plans draw from a fixed set of 31
courses rather than the whole catalogue.

## Signature

**The thread board.** The plan's 17 courses in one column, the degree's nine
requirement lines in the other, and one hairline thread drawn from each course to
the single line it pays for, with one terminal per course each line needs and the
terminal that never gets a thread left as an open brass ring. It fits because the
one design decision this project is built on is that requirement satisfaction is
a single global assignment, not a per group tally: a course may be credited once
and once only (`planner/matching.py`). A thread from each course to exactly one
terminal is that rule drawn literally, and the failure becomes a hole you can
point at, one thread visibly spent on the wrong line. It is not bars against a
value rule, not intervals on a time axis, not a matrix of counts, and not named
slots holding text.

## Verification performed on this page

Chrome, served over http from the subpath `/Fulcrum/` and opened from `file://`.

- **Demo runs end to end.** All 7 steps, forward and backward, wires drawn at
  step 5, the diverted thread and the open terminal at step 6, the engine's own
  verdict at step 7.
- **Subpath.** Four requests, all relative and all under `/Fulcrum/`: `kit.css`,
  `data/fulcrum.js`, `kit.js`, `data/fulcrum.json`. Nothing leaked to the origin
  root.
- **`file://`.** Fully functional. Zero resource requests, the data resolved from
  `window.DEMO_DATA`, all 17 threads drawn, zero console messages.
- **No runtime network.** The four same origin files above are the only requests
  the page ever makes. No CDN, no font, no image, no analytics.
- **Layout shift.** The stage measured 528px on every one of the 7 steps at both
  1280px and 360px, and the caption box 99px and 120px respectively on every
  step. `--k-player-stage-min` is set to 33rem, which covers the 360px case where
  the board's own horizontal scrollbar adds its height.
- **360px.** `document.documentElement.scrollWidth` is exactly 360 with no
  element outside a scroll container wider than the viewport. The board and the
  results table scroll inside their own boxes.
- **Focus and tab order.** 17 focusable controls, all real `<button>` or
  `<a href>`, document order, no positive `tabindex` anywhere.
- **Headings.** One `h1`, then `h2` per section with `h3` beneath, no level
  skipped.
- **Reduced motion.** The page adds no animation and no transition of its own.
  The only motion on the page is the kit's hero wash, which the kit disables
  under `prefers-reduced-motion: reduce` and never attaches on a touch device.
- **Contrast.** Every pairing is one the kit already measured, except ink on the
  signal wash used by the winning row of the results table, computed here at
  14.61:1 in light and 14.43:1 in dark.
- **Em dashes.** Zero occurrences of U+2014 or U+2013 in any file under `docs/`.
- **Secrets.** No file under `docs/` contains anything matching the provider's
  API key prefix, and every file under `docs/` is plain ASCII. `.env` was never
  opened, read, copied, or referenced while building this page, and no paid API
  call was made.
- **Weight.** The page's own assets total 113,234 bytes, about 111 KB, well
  under the 2 MB budget: `index.html` 41,192, `kit.css` 28,034, `kit.js` 24,341,
  `data/fulcrum.js` 9,871, `data/fulcrum.json` 9,796. Nothing from `corpus/` was
  copied into `docs/`.
