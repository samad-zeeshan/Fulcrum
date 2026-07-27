window.DEMO_DATA = window.DEMO_DATA || {};
window.DEMO_DATA["fulcrum"] = {
  "recorded_on": "2026-07-27",
  "commit": "d2db13f",
  "commit_full": "d2db13f853c593115bb207746fbc2bea31c86a4a",
  "what_ran": "The constraint engine in planner/, run on this machine. No model was called and no network was used.",
  "engine": {
    "command": "python -m planner --snapshot eval/snapshots/2026-06-28/offerings.json validate eval/plans/near_miss_units_short.plan.yaml",
    "exit_code": 1,
    "stdout": "plan: near_miss_units_short\nsnapshot: 2026-06-28\nVERDICT: INVALID\n  FAIL requirement_shortfall: unmet requirement 'senior_cmput_400' (6.0u matching {'subject': 'CMPUT', 'level_in': [400]}): have 3u, short 3u [CMPUT 401]"
  },
  "snapshot": {
    "date": "2026-06-28",
    "file": "eval/snapshots/2026-06-28/offerings.json",
    "terms_listed": [
      "Spring Term 2026",
      "Summer Term 2026",
      "Fall Term 2026",
      "Winter Term 2027"
    ]
  },
  "degree": {
    "id": "cmput-major",
    "name": "Computing Science Major",
    "catalog_year": "2026-2027",
    "total_units": 54,
    "places": 18,
    "file": "eval/gold/cs_major.gold.yaml"
  },
  "plan": {
    "id": "near_miss_units_short",
    "file": "eval/plans/near_miss_units_short.plan.yaml",
    "course_count": 17,
    "units_total": 51.0,
    "terms": [
      {
        "term": "Fall Term 2026",
        "courses": [
          "CMPUT 174",
          "MATH 125",
          "MATH 154",
          "STAT 151"
        ]
      },
      {
        "term": "Winter Term 2027",
        "courses": [
          "CMPUT 175",
          "CMPUT 272",
          "MATH 136"
        ]
      },
      {
        "term": "Fall Term 2027",
        "courses": [
          "CMPUT 201",
          "CMPUT 204",
          "CMPUT 200",
          "CMPUT 291"
        ]
      },
      {
        "term": "Winter Term 2028",
        "courses": [
          "CMPUT 301",
          "CMPUT 333",
          "CMPUT 355"
        ]
      },
      {
        "term": "Fall Term 2028",
        "courses": [
          "CMPUT 303",
          "CMPUT 401",
          "CMPUT 402"
        ]
      }
    ],
    "units": {
      "CMPUT 174": 3.0,
      "MATH 125": 3.0,
      "MATH 154": 3.0,
      "STAT 151": 3.0,
      "CMPUT 175": 3.0,
      "CMPUT 272": 3.0,
      "MATH 136": 3.0,
      "CMPUT 201": 3.0,
      "CMPUT 204": 3.0,
      "CMPUT 200": 3.0,
      "CMPUT 291": 3.0,
      "CMPUT 301": 3.0,
      "CMPUT 333": 3.0,
      "CMPUT 355": 3.0,
      "CMPUT 303": 3.0,
      "CMPUT 401": 3.0,
      "CMPUT 402": 3.0
    },
    "valid": false
  },
  "requirements": [
    {
      "group_id": "foundation_core",
      "plain": "First year computing and algebra",
      "target": "3 named courses",
      "places": 3,
      "required_units": 9.0,
      "earned_units": 9.0,
      "shortfall_units": 0.0,
      "assigned": [
        "CMPUT 174",
        "CMPUT 175",
        "MATH 125"
      ]
    },
    {
      "group_id": "foundation_calc_1",
      "plain": "Calculus, first course",
      "target": "3 units from a set of 3",
      "places": 1,
      "required_units": 3.0,
      "earned_units": 3.0,
      "shortfall_units": 0.0,
      "assigned": [
        "MATH 154"
      ]
    },
    {
      "group_id": "foundation_calc_2",
      "plain": "Calculus, second course",
      "target": "3 units from a set of 3",
      "places": 1,
      "required_units": 3.0,
      "earned_units": 3.0,
      "shortfall_units": 0.0,
      "assigned": [
        "MATH 136"
      ]
    },
    {
      "group_id": "foundation_stat",
      "plain": "Statistics",
      "target": "3 units from a set of 3",
      "places": 1,
      "required_units": 3.0,
      "earned_units": 3.0,
      "shortfall_units": 0.0,
      "assigned": [
        "STAT 151"
      ]
    },
    {
      "group_id": "senior_required",
      "plain": "Algorithms and logic",
      "target": "2 named courses",
      "places": 2,
      "required_units": 6.0,
      "earned_units": 6.0,
      "shortfall_units": 0.0,
      "assigned": [
        "CMPUT 204",
        "CMPUT 272"
      ]
    },
    {
      "group_id": "senior_choice",
      "plain": "Two from a set of three",
      "target": "6 units from a set of 3",
      "places": 2,
      "required_units": 6.0,
      "earned_units": 6.0,
      "shortfall_units": 0.0,
      "assigned": [
        "CMPUT 201",
        "CMPUT 291"
      ]
    },
    {
      "group_id": "senior_ethics",
      "plain": "Ethics of computing",
      "target": "3 units from a set of 2",
      "places": 1,
      "required_units": 3.0,
      "earned_units": 3.0,
      "shortfall_units": 0.0,
      "assigned": [
        "CMPUT 200"
      ]
    },
    {
      "group_id": "senior_cmput_300_400",
      "plain": "Computing at 300 or 400 level",
      "target": "15 units",
      "places": 5,
      "required_units": 15.0,
      "earned_units": 15.0,
      "shortfall_units": 0.0,
      "assigned": [
        "CMPUT 301",
        "CMPUT 303",
        "CMPUT 333",
        "CMPUT 355",
        "CMPUT 402"
      ]
    },
    {
      "group_id": "senior_cmput_400",
      "plain": "Computing at 400 level only",
      "target": "6 units",
      "places": 2,
      "required_units": 6.0,
      "earned_units": 3.0,
      "shortfall_units": 3.0,
      "assigned": [
        "CMPUT 401"
      ]
    }
  ],
  "failure": {
    "code": "requirement_shortfall",
    "detail_short": "senior_cmput_400: have 3u, short 3u",
    "group_id": "senior_cmput_400",
    "plain": "Computing at 400 level only",
    "detail": "unmet requirement 'senior_cmput_400' (6.0u matching {'subject': 'CMPUT', 'level_in': [400]}): have 3u, short 3u",
    "required_units": 6.0,
    "earned_units": 3.0,
    "shortfall_units": 3.0,
    "diverted_course": "CMPUT 402",
    "diverted_to": "senior_cmput_300_400"
  },
  "fix": {
    "plan_id": "valid_174_stream",
    "file": "eval/plans/valid_174_stream.plan.yaml",
    "adds": [
      "CMPUT 331"
    ],
    "command": "python -m planner --snapshot eval/snapshots/2026-06-28/offerings.json validate eval/plans/valid_174_stream.plan.yaml",
    "stdout": "plan: valid_174_stream\nsnapshot: 2026-06-28\nVERDICT: VALID",
    "exit_code": 0,
    "valid": true
  },
  "second_example": {
    "plan_id": "fail_prereq_order",
    "file": "eval/plans/fail_prereq_order.plan.yaml",
    "command": "python -m planner --snapshot eval/snapshots/2026-06-28/offerings.json validate eval/plans/fail_prereq_order.plan.yaml",
    "stdout": "plan: fail_prereq_order\nsnapshot: 2026-06-28\nVERDICT: INVALID\n  FAIL prereq_unsatisfied: CMPUT 204 prereq not met before Fall Term 2026: \"CMPUT 175 or 275, and CMPUT 272; and one of MATH 100, 114, 117, 134, 144, or 154.\" [CMPUT 204]",
    "exit_code": 1,
    "detail": "CMPUT 204 prereq not met before Fall Term 2026: \"CMPUT 175 or 275, and CMPUT 272; and one of MATH 100, 114, 117, 134, 144, or 154.\""
  },
  "eval": {
    "source_file": "reports/results.json",
    "n_queries": 47,
    "snapshot": "2026-06-28",
    "provider": "deepseek",
    "model": "deepseek-v4-flash",
    "is_stub": false,
    "question_mix": {
      "is this course offered in this term": 20,
      "what do I need before this course": 16,
      "is this plan valid": 7,
      "build me a plan": 4
    },
    "configs": [
      {
        "key": "RAG-always",
        "plain": "Always search the course pages",
        "quality_overall": 0.6489,
        "citation_pass_rate": 0.9,
        "cost_usd_total": 0.001557,
        "latency_p50": 1.0113,
        "plan_construction": 0.0
      },
      {
        "key": "CAG-always",
        "plain": "Always read the fixed rule sheet",
        "quality_overall": 0.4468,
        "citation_pass_rate": 1,
        "cost_usd_total": 0.00415,
        "latency_p50": 1.2157,
        "plan_construction": 0.0
      },
      {
        "key": "Routed",
        "plain": "Pick whichever suits the question",
        "quality_overall": 0.7234,
        "citation_pass_rate": 0.9,
        "cost_usd_total": 0.004294,
        "latency_p50": 1.1067,
        "plan_construction": 0.0
      }
    ]
  },
  "steps": [
    {
      "id": "plan",
      "status": "Plan read: 17 courses, 51 units, 5 terms.",
      "caption": "Seventeen courses over five terms, as the student wrote them. On the right, what the degree asks for."
    },
    {
      "id": "dupes",
      "status": "Counted twice: none. Cancelling each other out: none.",
      "caption": "Check one: no course counted twice, and no two courses that cancel each other out. This plan passes."
    },
    {
      "id": "offered",
      "status": "Placed in a term it does not run in: none.",
      "caption": "Check two: every course actually runs in the term it was put in. All seventeen pass."
    },
    {
      "id": "order",
      "status": "Taken before the courses it needs: none.",
      "caption": "Check three: nothing is taken before the courses it needs first. All seventeen pass."
    },
    {
      "id": "match",
      "status": "Handing out 17 courses across 18 places.",
      "caption": "Last check: every course is handed to one requirement and one only, never counted twice."
    },
    {
      "id": "gap",
      "status": "Short 3 units on: Computing at 400 level only.",
      "caption": "One place is left open. CMPUT 402 went to the 300 or 400 line, so only CMPUT 401 is left for 400 level."
    },
    {
      "id": "verdict",
      "status": "VERDICT: INVALID",
      "caption": "Three units short on one requirement. That is the whole reason this plan does not graduate you."
    }
  ]
};
