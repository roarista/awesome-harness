#!/usr/bin/env python3
# Hebbian "used"-counter side-store for memgraph recall (shortlist item #5).
# ADDITIVE + FAIL-OPEN: this module never raises to its callers. If the store is
# missing/corrupt or anything goes wrong, callers fall back to plain relevance
# order and recall keeps working. It touches NO index schema — just a small JSON
# at state/memory-usage.json mapping record-name -> surface count.
#
# Ranking effect is a BOUNDED tiebreaker, not a reorder: a frequently-hit record
# climbs at most ~1 slot in the relevance-ordered candidate list (see rerank).
# bm25 rank gaps here are tiny (~1e-8), so we tiebreak on POSITION, not score,
# which is independent of bm25 magnitude and can't drown relevance.
import json, math, os, tempfile

STATE = os.path.expanduser("~/.claude/tools/memgraph/state/memory-usage.json")


def load(path=None):
    try:
        with open(path or STATE) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def rerank(names, usage=None, cap=1.5, k=0.5):
    """names: list ordered by relevance (best first). Return reordered list.
    effective_score = index - min(cap, k*log1p(used)); sort ascending, stable.
    cap=1.5 => a record can overtake at most the one immediately above it
    (needs ~20 surfacings for a full 1-slot climb). Never reorders more."""
    try:
        if usage is None:
            usage = load()

        def bump(n):
            return min(cap, k * math.log1p(int(usage.get(n, 0) or 0)))

        scored = [(i - bump(n), i, n) for i, n in enumerate(names)]
        scored.sort()
        return [n for _, _, n in scored]
    except Exception:
        return list(names)


def bump_used(names, path=None):
    """Increment the surface counter for each record name. Atomic replace.
    Fail-open: swallow every error so recall is never broken by the counter."""
    try:
        p = path or STATE
        usage = load(p)
        for n in names:
            usage[n] = int(usage.get(n, 0) or 0) + 1
        d = os.path.dirname(p)
        os.makedirs(d, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=d)
        with os.fdopen(fd, "w") as f:
            json.dump(usage, f)
        os.replace(tmp, p)
        return usage
    except Exception:
        return {}


def _selftest():
    import tempfile as _t
    d = _t.mkdtemp()
    p = os.path.join(d, "memory-usage.json")

    # 1. counter increments and persists
    bump_used(["a", "b"], path=p)
    bump_used(["a"], path=p)
    u = load(p)
    assert u == {"a": 2, "b": 1}, u
    print("PASS increment/persist:", u)

    # 2. higher-count record wins a tiebreak (climbs exactly one slot)
    #    candidates in relevance order: x(best), y. y has many uses -> overtakes x.
    usage = {"y": 30, "x": 0}
    order = rerank(["x", "y"], usage=usage)
    assert order == ["y", "x"], order
    print("PASS tiebreak (high-count climbs 1 slot):", order)

    # 3. bounded: a high-count record cannot climb more than one slot
    usage = {"z": 999}
    order = rerank(["p", "q", "z"], usage=usage)  # z is 3rd/worst relevance
    assert order == ["p", "z", "q"], order        # climbs to 2nd, not 1st
    print("PASS bounded (climbs at most 1 slot):", order)

    # 4. small usage difference does NOT reorder (stays relevance order)
    usage = {"m": 1, "n": 0}
    order = rerank(["n", "m"], usage=usage)
    assert order == ["n", "m"], order
    print("PASS small-usage keeps relevance order:", order)

    # 5. fail-open: missing/corrupt store -> empty dict, original order
    assert load("/nonexistent/xyz.json") == {}
    with open(p, "w") as f:
        f.write("{ this is not json")
    assert load(p) == {}
    assert rerank(["a", "b", "c"]) == ["a", "b", "c"]
    print("PASS fail-open on missing/corrupt store")
    print("ALL SELFTESTS PASSED")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(json.dumps(load(), indent=2))
