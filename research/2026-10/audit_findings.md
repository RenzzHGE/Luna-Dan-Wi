# BlazePhoenix DEX — Swap-Path Audit (Router + Solver + Core)

Scope: `src/BlazePhoenixRouter.sol` (full read of entries, `_execute`, `_execScaled`, `_v3Callback`, `unlockCallback`, fee/floor machinery), `src/BlazePhoenixSolver.sol` (route assembly, hop build, quotes), `src/BlazePhoenixCore.sol` (math library: outV2/outV3/solidlyAskOut, floors, fee helpers), `src/BlazePhoenixHub.sol` (recordSwap, control model). All line numbers below are real and verified against the tree.

## Verdict

**No exploitable critical or high found on the swap path.** This codebase is unusually hardened — it contains explicit, measured fixes (with tests and reporter attribution) for essentially every class in the tasking: minOut bypass, callback auth, fee-to-zero, route-integrity drain, V4 hook reentrancy, FoT tokens, rebase tokens, stranded-balance sweep, registry poisoning. I looked specifically for the seams between those fixes; what I found is listed below, all Low/Info. Honest result: solid.

## Confirmed protections (what I checked and why it holds)

- **minOut/slippage**: `userMinOut == 0` with `amountIn > 0` reverts (RouterE(10)) on all four entry points (Router 473, 484, 556, 593). Final guard is on the *measured recipient balance delta* (line 1617-1621), not nominal `net` — a transfer-tax tokenOut cannot slip a user past minOut. The secondary protocol floor is derived on-chain from in-frame quotes, never from caller `route.totalOut` (lines 1544-1581).
- **Callback auth**: `_v3Callback` (2085) checks `msg.sender == tload(TSLOT_POOL)` and is single-shot (context cleared before paying — checks-effects-interactions, no multi-pull reentrancy). `owed > maxAmt` cap bounds a hostile pool to the leg's own budget. `unlockCallback` (2122) is manager-only, single-shot, `owe > amt` capped. `receive()` is gated by `TSLOT_ETHOK` to exactly one sender for one call (2079-2083). Fallback callback layout ambiguity is defeated because auth is by `msg.sender`, not selector.
- **Route integrity**: hop continuity enforced (`hop.tokenIn == prev.tokenOut`, hop tokenIn ≠ route tokenIn — line 1163); per-leg pair binding `legIn/legOut must equal hop.tokenIn/tokenOut` (line 1311) closes the stranded-balance drain (their `LegDivergentStrandedDrain.t.sol` measures the pre-fix theft); input-token revisits refused; cyclic-route residual returns to `payer` not recipient (1172-1175); residual sweeps are all baseline-delta (`baseIn`, `toutStart`, `bridgeBase`), so stranded Router balances can never be swept by a crafted route.
- **Fee rounding**: both fee sites round UP (`mulDivUp`, lines 788, 1602), fee ledger (TSLOT_FEE) refuses a settled swap that paid nothing (RouterE(15)) and double-payment in anchored regime (16). Attacker-controlled `totalOut`/`singleOutFloor` cannot shrink the fee base (in-frame quote replaces it, coverage gate min 50%).
- **Per-leg floor**: `bound = max(attested_pro_rata, measured·coverage)` then `got ≥ mulDivUp(bound, 80%, BPS)` (line 1857); attestation can't be deflated to opt out (measurement lifts the floor); FoT re-pricing by measured ratio only shrinks the discount conservatively.
- **MathLib**: `outV2`/`outV3`/`outSolidly` guard zero reserves, fee ≥ 100%, sqrtNew overflow/crossing; V3 quote truncates at range boundary (never over-promises); `ironFloorBpsShv` has no underflow (`total >= base` branch); Router line 1480 `_bal(tokenOut) - toutStart` is deliberately *checked* — a route that eats the baseline reverts safely.
- **Solver**: only produces route shape; Router re-validates every field on execution, so solver bugs are bounded by the Router's floors. `recordSwap` is Router-only; V4 registry rows re-derive poolId from executed key; pair rows require token0/token1 proof; depth is measured (`registryDepth18`), not caller-claimed.
- **Reentrancy**: `nrEntrant` transient lock on all entry doors; hooks admitted only if `hookAltersDeltas == false` (address-bit, immutable) or not paused; non-delta hooks running inside the unlock are bounded by the PoolManager's own flash-accounting (unsettled delta reverts the unlock).

## Findings (all low / informational)

1. **[Low — informational, documented residual] Fee-anchor value-injection leak, accepted by owner.**
   Router 729-743 (comment), 1101-1105. A route whose hop-0 spends 2 wei of a bridge coin through an attacker-owned pool that pays out real bridge coin lets the real trade cross fee-free (fee charged on 2 wei). The code documents this as a measured, owner-accepted residual ("No user is harmed; the treasury loses the rate on that trade") with the exhaustion-regime fallback as the backstop. No theft of user funds; protocol-fee evasion only, cost bounded by gas. PoC: `FeeAnchorValueInjectingPrefix.t.sol` measures it. Severity: Low (revenue leak, no user loss).

2. **[Low] FoT floor-discount is route-global, not per-hop (self-documented scoping gap).**
   Router 1557-1568. TSLOT_FOT holds one compounded ratio for the whole route; the authors themselves note it can only over-discount the *secondary* protocol floor (more permissive), while the primary `userMinOut` (checked on delivered delta) and per-leg 80% floor remain intact. Not exploitable below the hard 80% clamp. Severity: Low, acknowledged in-source.

3. **[Info] Router floor's leg-concentration term uses declared calldata amounts.**
   Router 1513-1526 (`legShaveBps` over `ls[i].amountIn`) vs. Solver's identical computation over post-clamp committed amounts. An execution where hop scaling shrank legs slightly diverges in floor tightness from what the Solver attested, but only in the direction of the attested figure; `a * a` at line 1521 is checked arithmetic so overflow just reverts the attacker's own route. Severity: Info.

4. **[Info] Fallback-based V3 callback surface.**
   Router 2051-2061: ANY 4-byte selector with `(int256,int256,bytes)` layout from the transient-pool address enters `_v3Callback`. This is by design (multi-venue compatibility) and safe because auth is `msg.sender == tload(TSLOT_POOL)` with single-shot clearing — but it is a wide surface to reason about if transient slots are ever set in a new code path. Severity: Info.

5. **[Info] `executeRescue` pays `balanceOf - owed` to admin after 48h timelock.**
   Router 430-441. Control-gated, timelocked, dies with `renounceControl`, and the held-nothing invariant means the Router should be empty at rest. If a swap ever stranded funds (a bug elsewhere), this door converts that into an admin withdrawal rather than a public refund. Design choice, not a bug.

## Recommended bounty-use notes

- The juiciest remaining surface is *compositional*: two accepted residuals (fee-anchor prefix leak, FoT route-global discount) plus the last-leg clamp / coverage-gate interaction (Router 1326-1329 + 1801-1805, where `amt < legAmt` makes the coverage rescale intentionally "fail open"). If hunting further, fuzz the **seams between fixes** (e.g., FoT marking on `_execPairAmt` realIn path vs. `_noteFot` compounding vs. per-leg `fotBefore/after` difference recovery at 1842-1847) rather than the individual guards, which are all pinned by tests.
- No findings warrant the critical bounty range; nothing here is a theft/freeze/insolvency/signed-trade-below-minOut path.
