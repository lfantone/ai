#!/usr/bin/env python3
"""Regenerate the mag-* cases from plan-TK-412.md.

Each defective case applies one mutation to the clean plan. Every replacement must match
exactly once, so a fixture edit that breaks a mutation fails loudly here instead of
silently producing a case that tests nothing.
"""
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
SUITE = HERE.parent
PLAN = (HERE / "plan-TK-412.md").read_text()

FRONT = """---
max_turns: 8
timeout_seconds: 480
allowed_tools: [Agent]
model: sonnet
runs: 5
---
"""

VERIFY_PLAIN = """Structurally verify the implementation plan below with a sub-agent. Do not verify it yourself and do not look for the repository; the plan text is the only input. Return the sub-agent's verdict verbatim and nothing else: one line per step (`OK` or `structural error — <specific violation>`), then a final line that is exactly `VALID` or `INVALID`.

---

"""

VERIFY_HANDOFF = """Phase 3 — Structural verification. Spawn a sub-agent with the full authored plan below to validate contract completeness, stable ids, dependency-graph integrity, mode rules, and file-disjoint waves. It must not read repository anchors. Relay its output verbatim with no additions: one line per step (`OK` or `structural error — <specific violation>`), followed by a final `VALID` or `INVALID`.

---

"""


def replace_once(text: str, old: str, new: str) -> str:
    n = text.count(old)
    assert n == 1, f"expected exactly one match, found {n}: {old[:60]!r}"
    return text.replace(old, new)


def grader(case: Path, name: str, body: str) -> None:
    (case / "graders").mkdir(parents=True, exist_ok=True)
    (case / "graders" / f"{name}.md").write_text(body)


def regex(pattern: str, match: str = "contains", flags: str | None = None) -> str:
    fm = f"---\ntype: regex\ntarget: last_message\nmatch: {match}\n"
    if flags:
        fm += f"flags: {flags}\n"
    return fm + f"---\n{pattern}\n"


def llm(rubric: str) -> str:
    return f"---\ntype: llm\nfocus: last_message\n---\n{rubric.strip()}\n"


# Routing is a trajectory check, reported for visibility but kept out of Δ: evaluated in the
# with arm only (the without arm has no Magneton to route to) with a token weight, since the
# runner rejects weight 0.
ROUTED = "---\ntype: tool_used\ntool: Agent\ninput_match: Magneton\nmin: 1\narm: with-only\nweight: 0.01\n---\n"
NOT_ROUTED = "---\ntype: tool_used\ntool: Agent\ninput_match: Magneton\nmin: 0\nmax: 0\narm: both\n---\n"

# Magneton's return format (since 2026-09-23) is one line per step, prefixed with the step id:
# `S<N> — OK` or `S<N> — structural error — <violation>`. Exactly four such lines for a
# four-step plan.
STRICT_VERDICT = regex(r"^(VALID|INVALID)\s*$", flags="m")
STRICT_FOUR_LINES = regex(r"^\W*S[1-4]\b\W*(OK\W*$|structural error)", match="count:4", flags="m")

ONLY_VERDICT_LINES = """
The answer relays a structural verification verdict. All claims must hold to pass.

1. The answer consists of the verdict lines (one per step S1..S4) and the final VALID/INVALID line, optionally preceded by at most one short framing sentence. It does NOT echo the plan, propose fixes, rewrite contracts, or add commentary about the code.
2. It does NOT claim to have checked the repository, source files, or that Before blocks match the working tree.
"""


def fire_case(slug: str, intro: str, plan: str, extra: dict[str, str]) -> None:
    case = SUITE / slug
    shutil.rmtree(case, ignore_errors=True)
    case.mkdir(parents=True)
    (case / "prompt.md").write_text(FRONT + intro + plan)
    grader(case, "strict-verdict-line", STRICT_VERDICT)
    grader(case, "strict-four-step-lines", STRICT_FOUR_LINES)
    grader(case, "routed-to-magneton", ROUTED)
    for name, body in extra.items():
        grader(case, name, body)


def neg_case(slug: str, question: str, extra: dict[str, str]) -> None:
    case = SUITE / slug
    shutil.rmtree(case, ignore_errors=True)
    case.mkdir(parents=True)
    (case / "prompt.md").write_text(FRONT + question + "\n\n---\n\n" + PLAN)
    grader(case, "no-verdict", regex(r"^(VALID|INVALID)\s*$", match="not_contains", flags="m"))
    grader(case, "not-routed-to-magneton", NOT_ROUTED)
    for name, body in extra.items():
        grader(case, name, body)


def defect_rubric(defect: str, culprits: str, clean: str, either: str = "none") -> str:
    return llm(f"""
The answer relays a structural verification verdict for a four-step plan (S1..S4) that contains exactly one planted defect. All claims must hold to pass.

1. The verdict is INVALID.
2. The defect is identified correctly: {defect}. At least one error line names {culprits}.
3. The steps unrelated to the defect ({clean}) are reported as OK. Inventing a structural error on one of those steps fails this claim. Steps that are involved in the defect but not required to be flagged ({either}) may be reported either as OK or as an error describing the same defect; neither choice fails this claim.
4. The answer is verdict lines only: no plan echo, no proposed fix, no rewritten contract.
""")


# 01 — clean plan
fire_case(
    "mag-01-clean-valid",
    VERIFY_PLAIN,
    PLAN,
    {
        "verdict-valid": regex(r"^VALID\s*$", flags="m"),
        "no-errors": regex(r"INVALID|structural error", match="not_contains"),
        "four-ok-lines": regex(r"^\W*S[1-4]\b\W*OK\W*$", match="count:4", flags="m"),
        "only-verdict-lines": llm(ONLY_VERDICT_LINES),
    },
)

# 02 — cycle S1 -> S2 -> S4 -> S1
p = PLAN
p = replace_once(p, "S1 → S2\nS1 → S3\nS2 → S4\n", "S1 → S2\nS1 → S3\nS2 → S4\nS4 → S1\n")
p = replace_once(p, "- **Depends on:** none   **Enables:** S2, S3", "- **Depends on:** S4   **Enables:** S2, S3")
p = replace_once(p, "- **Depends on:** S2   **Enables:** none", "- **Depends on:** S2   **Enables:** S1")
fire_case(
    "mag-02-cycle",
    VERIFY_HANDOFF,
    p,
    {
        "verdict-invalid": regex(r"^INVALID\s*$", flags="m"),
        "names-cycle": regex(r"cycl|circular", flags="i"),
        "defect-identified": defect_rubric(
            "a dependency cycle S1 → S2 → S4 → S1 (S1 depends on S4 and S4 enables S1, while S4 depends on S2 which depends on S1; the edge S4 → S1 also points from Wave 3 back to Wave 1)",
            "S1 or S4 and describes the cycle",
            "S3",
            either="S1, S2 and S4, whichever were not the flagged one",
        ),
    },
)

# 03 — S3 shares S2's file inside Wave 2
p = PLAN
p = replace_once(
    p,
    "- **Files:** `src/cache/__tests__/session-store.test.ts`",
    "- **Files:** `src/http/session-middleware.ts`",
)
fire_case(
    "mag-03-wave-file-collision",
    VERIFY_PLAIN,
    p,
    {
        "verdict-invalid": regex(r"^INVALID\s*$", flags="m"),
        "names-shared-file": regex(r"session-middleware\.ts"),
        "defect-identified": defect_rubric(
            "S2 and S3 are both in Wave 2 and both list `src/http/session-middleware.ts` under Files, so the wave is not file-disjoint (the judge may also accept flagging that S3's Files no longer matches its create_file path)",
            "S3 (and optionally S2)",
            "S1 and S4",
        ),
    },
)

# 04 — S2 depends on a step that does not exist
p = PLAN
p = replace_once(p, "- **Depends on:** S1   **Enables:** S4", "- **Depends on:** S1, S5   **Enables:** S4")
p = replace_once(p, "S1 → S2\nS1 → S3\nS2 → S4\n", "S1 → S2\nS5 → S2\nS1 → S3\nS2 → S4\n")
fire_case(
    "mag-04-dangling-dependency",
    VERIFY_HANDOFF,
    p,
    {
        "verdict-invalid": regex(r"^INVALID\s*$", flags="m"),
        "names-missing-step": regex(r"\bS5\b"),
        "defect-identified": defect_rubric(
            "S2 depends on S5, but no step S5 exists in the checklist, waves, or contracts",
            "S2 (and the missing S5)",
            "S1, S3 and S4",
        ),
    },
)

# 05 — S2's replace_exact has no After block
p = PLAN
p = replace_once(
    p,
    """**After:**

```ts
    const now = clock.now();
    store.evictIdle(now);
    const session = store.get(sessionId);
    if (!session) return res.status(401).end();
    store.touch(sessionId, now);
    req.session = session;
    next();
```

""",
    "",
)
fire_case(
    "mag-05-missing-after-block",
    VERIFY_PLAIN,
    p,
    {
        "verdict-invalid": regex(r"^INVALID\s*$", flags="m"),
        "names-after-block": regex(r"\bAfter\b"),
        "defect-identified": defect_rubric(
            "S2's only operation is a replace_exact with a Before block but no After block, so the exact contract is incomplete",
            "S2",
            "S1, S3 and S4",
        ),
    },
)

# 06 — guided contract in a precise plan
p = PLAN
p = replace_once(
    p,
    "### S3 — Store tests: eviction, touch refresh, default TTL\n\n- **Execution class:** exact",
    "### S3 — Store tests: eviction, touch refresh, default TTL\n\n- **Execution class:** guided",
)
fire_case(
    "mag-06-guided-in-precise",
    VERIFY_HANDOFF,
    p,
    {
        "verdict-invalid": regex(r"^INVALID\s*$", flags="m"),
        "names-guided": regex(r"\bguided\b"),
        "defect-identified": defect_rubric(
            "S3 is declared `Execution class: guided`, but the plan header says `mode: precise`, which permits only exact contracts (the judge may also accept flagging that S3 lacks a Target state / Instructions, which a guided contract requires)",
            "S3",
            "S1, S2 and S4",
        ),
    },
)

# 07 — negative: summarize
neg_case(
    "mag-07-neg-summarize",
    "Summarize this implementation plan's objective and acceptance criteria in five bullets. Do not verify or critique it.",
    {
        "mentions-idle-ttl": regex(r"SESSION_IDLE_TTL_MS|lastSeenAt|idle", flags="i"),
        "summary-only": llm("""
The answer is a summary of an implementation plan. All claims must hold to pass.

1. It contains about five bullets (four to six is fine) that restate the plan's goal (evict idle sessions from the in-memory session store after an idle TTL) and its acceptance criteria (eviction on next lookup with a debug log, lastSeenAt refreshed per request, sessions within the TTL untouched, default TTL of 30 minutes).
2. It does NOT contain a structural verification verdict (no per-step OK / structural error lines, no VALID or INVALID line) and does not critique the plan.
"""),
    },
)

# 08 — negative: parallelism question
neg_case(
    "mag-08-neg-parallelism",
    "Which steps of this implementation plan can run at the same time, and which must wait? Answer from the execution plan; do not verify the plan.",
    {
        "names-wave-2-steps": regex(r"S2[^\n]*S3|S3[^\n]*S2"),
        "reads-execution-plan": llm("""
The answer explains the plan's parallelism. All claims must hold to pass.

1. It states that S2 and S3 can run at the same time (Wave 2, both depend only on S1).
2. It states that S1 runs first (Wave 1) and that S4 waits for S2 (Wave 3).
3. It does NOT contain a structural verification verdict (no per-step OK / structural error lines, no VALID or INVALID line).
"""),
    },
)

print("generated:", sorted(p.name for p in SUITE.iterdir() if p.name.startswith("mag-")))
