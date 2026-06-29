# NP2 Drift & Freshness Report

## Freshness (two dated snapshots)
Data-dependent answers change between snapshots; rule answers stay stable.


| Question | kind | snapshot 1 | snapshot 2 | changed? |
|---|---|---|---|---|
| CMPUT 174 Fall Term 2026 seats | data | cap 144 | cap 0 | ✅ yes |
| CMPUT 291 Winter Term 2027 lecture time | data | 11:00 | 13:00 | ✅ yes |
| CMPUT 304 offered in Fall Term 2026? | data | True | False | ✅ yes |
| CMPUT 461 offered in Winter Term 2027? | data | False | True | ✅ yes |
| CMPUT 204 prerequisite | rule | CMPUT 175 or 275, and CMPUT 272; and one of MATH 100, 114, 117, 134, 144, or 154. | CMPUT 175 or 275, and CMPUT 272; and one of MATH 100, 114, 117, 134, 144, or 154. | — no |
| CMPUT 291 prerequisite | rule | CMPUT 175 or 274, and 272. | CMPUT 175 or 274, and 272. | — no |
| CMPUT 401 prerequisite | rule | CMPUT 301. Credit may be obtained in only one of CMPUT 401, BTM 419, or MIS 419. | CMPUT 301. Credit may be obtained in only one of CMPUT 401, BTM 419, or MIS 419. | — no |

**4/4 data-dependent facts changed; 3/3 rule facts stable.**

## Router drift
Paraphrase decision-flip rate: **0/8 = 0.00**.


| base route | paraphrase | route | flipped |
|---|---|---|---|
| rag | Which terms does CMPUT 174 run in? | rag | no |
| rag | Is CMPUT 174 available next term? | rag | no |
| rag | What's the schedule for CMPUT 174? | rag | no |
| cag | What do I need before taking CMPUT 204? | cag | no |
| cag | Which courses are required to enrol in CMPUT 204? | cag | no |
| cag | CMPUT 204 prereqs? | cag | no |
| compound | Does CMPUT 415 run in the winter term, and what are its prerequisites? | compound | no |
| compound | Winter availability and prereqs for CMPUT 415? | compound | no |

**Threshold sweep (compound_margin → share routed compound):** 0→0.182, 1→0.273, 2→0.273
