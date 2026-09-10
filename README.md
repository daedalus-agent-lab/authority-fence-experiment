# Authority Fence: a runnable NOT_APPLIED experiment

This repository contains a stdlib-only experiment for the article **A Fresh Read Cannot Prove It Did Not Happen**.

It demonstrates four bounded outcomes:

- an unfenced delayed apply can succeed after revocation;
- a store-enforced epoch fence refuses the delayed apply and emits a scoped `NOT_APPLIED` witness;
- a read-only observer must return `UNKNOWN` with `permit_retry: false`, because absence is not impossibility;
- an epoch refusal does not seal the request key: presenting the same key under a fresh epoch is admitted, so one key can carry a REFUSED row and an APPLIED row — two receipts, not one renamed receipt (arm D).

The model is intentionally small and does not claim end-to-end exactly-once. It has no network, crash window, partitions, or independent store operator.

Two idempotency tables, on purpose:

- **Admission** is keyed by `(subject, request_key)`. An APPLIED receipt seals that key for that subject.
- **Refusal** is keyed by `(subject, request_key, presented_epoch)`. A same-epoch retry returns the *same* `NOT_APPLIED` witness at a stable log index (`replay: true`). A fresh epoch is evaluated afresh — that is arm D: an epoch refusal is not a key seal. The precise label is `NOT_APPLIED_FOR_PRESENTED_EPOCH`.

`permit_retry: true` on a store refusal authorizes retry of that admission; a reader's `UNKNOWN` keeps `permit_retry: false`. Those two must stay opposite.

**Why there is no "crash between effect and log":** `_admit` appends APPLIED and updates `effects` in one critical section. The effect store *is* the admission store — a derived shadow, not a second durable world. An uncovered crash between the two is structurally absent from this fixture, not merely untested. End-to-end exactly-once across a separate effect world is a different problem.

## Run

```bash
python3 -m unittest test_authority_fence -v
python3 authority_fence.py --fuzz 200 --seed 7
```

Expected: 14 tests pass; the deterministic report has `all_expectations_met: true`. The fuzz control reports zero post-revocation admissions for the fenced store and nonzero violations for the deliberately broken check-then-act store.

## Integrity

- `authority_fence.py`: SHA-256 `1d885815d036c218ffb6722edfbc36c8ffd3ba3095720d50176343469af09e1e`
- `test_authority_fence.py`: SHA-256 `46989aed2af89b6f883445bb14714b914f0e97696992968dc42db5c010f54ea3`
- `out.json`: deterministic sample report

The experiment is a model, not evidence about any specific production system.
