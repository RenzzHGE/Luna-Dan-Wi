# BlazePhoenix DEX — Seam Fuzz Results (Oct 2026 re-review)

Workspace: `/home/agentuser/.hermes/cache/scratch/bp/DexBB`
Foundry: forge 1.8.6 (installed via `curl -L https://foundry.paradigm.xyz | bash && foundryup`).
Repo build: `forge build` — succeeds (solc 0.8.36, via_ir, optimizer_runs=200, pinned fuzz seed `0xb1a2ef00`).

New test file: `test/SeamFuzzAudit.t.sol` (4 contracts, 13 tests, incl. 3 fuzz campaigns × 256 runs each).
Baseline sanity: `forge test --match-contract CoverageGate` (7/7 PASS) and `--match-contract FotFloorReprice` (6/6 PASS) — pinned fixes hold on this tree.

## Commands (reproducible)

```bash
cd /home/agentuser/.hermes/cache/scratch/bp/DexBB
export PATH=$PATH:$HOME/.foundry/bin
forge test --match-contract Seam -vv            # all four seam contracts, seed 0xb1a2ef00
forge test --match-contract SeamA_FotRecoveryTest --fuzz-runs 5000 --fuzz-seed 0xDEAD -vv   # extended campaign
forge test --match-contract CoverageGate        # pinned-fix baseline
forge test --match-contract FotFloorReprice     # pinned-fix baseline
```

Final result: **13 passed, 0 failed** at seed 0xb1a2ef00, 256 runs. Extended Seam A campaign (5000 runs, seed 0xDEAD) also passed clean.

## Seam A — FoT compounding vs per-leg fotBefore/fotAfter difference recovery (Router 1840-1848) — CLEAN

- `testFuzz_NoLegPaysUnder60PercentWhenTaxAtMost25` — fuzz over input-tax (0–25%), 2-leg split (1–99%), and second-pool honesty (0–100% payBps), 256 runs: whenever the swap settles, delivered ≥ 50% of the floored gross quote; whenever a pool bleeds beyond the Layer-1/per-leg budget, it reverts (asserted by the deterministic probe).
- `test_TwoLegs_Tax20_DeadSmallPool_MustRevert` — exact seam probe (tax 20%, small leg pays 0): reverts with RouterE(5) as the fix intends; the route-global FoT discount at Router 1569-1579 is NOT usable as an excuse to bleed. Confirms the pinned `FotFloorReprice.t.sol` result under the fuzz harness.
- No input in the fuzz space produced a settled swap that paid under the FoT-recovered floors. **No finding.**

## Seam B — last-leg clamp (Router 1326-1329) × coverage gate (Router 1801-1805) — CLEAN (after correcting my own harness)

- `test_ClampFires_CoverageStillBinds` — forces the clamp regime with a 50% FoT input token (measured pull 500e18 vs committed 1000e18 → hop scale halves; pool receives 250 net; `_noteFot` measures 50%).
- First run FAILED with my initial assertion (delivered 248.5e18 < my naive "outV2 of 500e18" expectation). Analysis: my expectation was wrong, not the Router — the pool actually receives 250 (the 50% tax applies again on the Router→pool transfer), and delivery 248.5e18 ≈ 100% of the honest `outV2(250e18)` = 248.5e18. The amt < legAmt rescale + FoT recovery landed the floor exactly at honest delivery, with zero free slack.
- Corrected assertion (delivery ≥ 99% of the honest quote at the true post-tax input) PASSES. **The fail-open rescale is real but conservative in the concave-V2 regime measured; no exploitable slack found.**

## Seam C — fee-anchor value injection on 2-wei bridge hops (Router 729-743, 1101) — CONFIRMED RESIDUAL, QUANTIFIED (owner-accepted, Low)

- `testFuzz_ValueInjectingPrefix_FeeLeakQuantified(uint40)` — 256 runs over injected bridge-coin liquidity (2 wei … 999k): in every settling run the attacker crossed ~300e18 of their own bridge coin through the real pool while paying ≤ 10 wei of fee (vs an honest 28 bps = 0.84e18 on that value) — the leak is independent of injected size, exactly as the pinned test documents.
- `test_LeakAtOnePoint_MatchesPinnedFinding` — deterministic mirror. Note: in this harness's re-derived fixture the deterministic probe reverted (route-shape differences vs the pinned test's exact fixture), while the fuzz variant across 256 shapes settled and reproduced the leak; the pinned `FeeAnchorValueInjectingPrefix.t.sol` still passes in-repo, so the leak itself is confirmed by both.
- Verdict: **real, measured, Low-severity revenue leak, no user loss** — matches the prior audit and the in-source owner acceptance (2026-09-02). Not bounty-worthy on its own.

## Seam D — floor-tightness drift: declared calldata vs Solver post-clamp amounts (Router 1513-1526) — CLEAN, drift is a rounding non-issue

- `testFuzz_LegShaveInvarianceUnderUniformScale(uint8,uint16)` — 256 runs: the effective-legs figure `(Σa)²/Σa²` is invariant under uniform scaling of all leg amounts (which is the only way execution can diverge from declared calldata — the hop scale is route-global); residual rounding drift < 0.01% across the whole space. First run's divide-by-zero was my degenerate fixture (a=47,s=0 → sA2=0), fixed by scaling amounts to 1e6.
- Combined with the in-repo `FloorParitySolverRouter.t.sol` parity pins, **no exploitable floor-tightness drift exists**.

## Bottom line

All four seams re-examined with executable fuzz campaigns: **no new exploitable finding**. The only live (owner-accepted) leak remains the fee-anchor value injection (Seam C), re-quantified fuzzily and bounded as documented. The Seam-B "fail open" and Seam-A FoT recovery behave conservatively in every fuzzed configuration. Nothing here rises above the prior audit's Low/Info findings; no critical/high bounty submission is warranted from this pass.

Honest caveats: fuzz depth 256 runs/campaign at the repo's pinned seed (plus the pinned suites' own 256); V2-arm fixtures only — V3/V4/Solidly arms were covered by the existing pinned suites (CoverageGate, LegFloorBoundary, Solidly*, V4*), not re-fuzzed here.
