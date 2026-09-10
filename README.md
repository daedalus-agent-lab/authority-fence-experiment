# Authority Fence: a runnable NOT_APPLIED experiment

This repository contains a stdlib-only experiment for the article **A Fresh Read Cannot Prove It Did Not Happen**.

It demonstrates four bounded outcomes:

- an unfenced delayed apply can succeed after revocation;
- a store-enforced epoch fence refuses the delayed apply and emits a scoped `NOT_APPLIED` witness;
- a read-only observer must return `UNKNOWN` with `permit_retry: false`, because absence is not impossibility;
- an epoch refusal does not seal the request key: presenting the same key under a fresh epoch is admitted, so one key can carry a REFUSED row and an APPLIED row — two receipts, not one renamed receipt (arm D).

The model is intentionally small and does not claim end-to-end exactly-once. It has no network, crash window, partitions, or independent store operator.

Idempotency is scoped by the tuple `(subject, request_key)`: the same request key may be applied independently for different subjects. A store-issued `NOT_APPLIED` witness is narrower still: it proves refusal at this store and log position for the presented subject/epoch. It does not seal or reserve the request key, and a later call (including one under a fresh epoch) is evaluated afresh. `permit_retry: true` authorizes retry of the refused admission, not a claim that no effect occurred elsewhere.

## Run

```bash
python3 -m unittest test_authority_fence -v
python3 authority_fence.py --fuzz 200 --seed 7
```

Expected: 14 tests pass; the deterministic report has `all_expectations_met: true`. The fuzz control reports zero post-revocation admissions for the fenced store and nonzero violations for the deliberately broken check-then-act store.

## Integrity

- `authority_fence.py`: SHA-256 `71e6b9178354a2c8fd5241076458295e32175451e9638b00904ac0a228855380`
- `test_authority_fence.py`: SHA-256 `c66a9f0f9394c72d94e1379523b748fbeb98c1d7b1084454a4aeafed4ff8c425`
- `out.json`: deterministic sample report

The experiment is a model, not evidence about any specific production system.
