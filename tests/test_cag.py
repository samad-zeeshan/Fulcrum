from llm.provider import StubProvider
from planner import Gold
from cag import CagContext, answer_rules_query, build_rules_slice

def test_rules_slice_is_deterministic():
    g = Gold.load()
    a = build_rules_slice(g).text
    b = build_rules_slice(g).text
    assert a == b

def test_rules_slice_has_key_clauses():
    rs = build_rules_slice(Gold.load())
    assert "[group:senior_required]" in rs.text
    assert "[note:note1_275_blocks_201]" in rs.text
    assert "[prereq:CMPUT 204]" in rs.text
    assert "[exclusion]" in rs.text

    assert "ineligible" in rs.text

def test_cag_answer_extracts_citations_and_usage():
    g = Gold.load()
    ctx = CagContext.from_gold(g)

    stub = StubProvider(responder=lambda s, u: "Prereq is CMPUT 175 or 275 and 272 [prereq:CMPUT 204].")
    ans = answer_rules_query("prereq for CMPUT 204?", ctx, stub)
    assert "prereq:CMPUT 204" in ans.cited_clauses
    assert ans.response.usage.prompt_tokens > 0

def test_cag_system_prefix_is_stable_across_queries():
    ctx = CagContext.from_gold(Gold.load())

    s1 = ctx.system
    s2 = CagContext.from_gold(Gold.load()).system
    assert s1 == s2 and s1.startswith("PROGRAM:")
