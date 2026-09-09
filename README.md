# Authority Fence: a runnable NOT_APPLIED experiment

This repository contains a stdlib-only experiment for the article **A Fresh Read Cannot Prove It Did Not Happen**.

It demonstrates three bounded outcomes:

- an unfenced delayed apply can succeed after revocation;
- a store-enforced epoch fence refuses the delayed apply and emits a scoped `NOT_APPLIED` witness;
- a read-only observer must return `UNKNOWN` with `permit_retry: false`, because absence is not impossibility.

The model is intentionally small and does not claim end-to-end exactly-once. It has no network, crash window, partitions, or independent store operator.

Idempotency is scoped by the tuple `(subject, request_key)`: the same request key may be applied independently for different subjects. A store-issued `NOT_APPLIED` witness is narrower still: it proves refusal at this store and log position for the presented subject/epoch. It does not seal or reserve the request key, and a later call (including one under a fresh epoch) is evaluated afresh. `permit_retry: true` authorizes retry of the refused admission, not a claim that no effect occurred elsewhere.

## Run

```bash
python3 -m unittest test_authority_fence -v
python3 authority_fence.py --fuzz 200 --seed 7
```

Expected: 13 tests pass; the deterministic report has `all_expectations_met: true`. The fuzz control reports zero post-revocation admissions for the fenced store and nonzero violations for the deliberately broken check-then-act store.

## Integrity

- `authority_fence.py`: SHA-256 `12a80c590366c5c65b56a1dc0eb9d5bad04036e4821dc48a674e74bb36201d23`
- `test_authority_fence.py`: SHA-256 `7ca76f10ffdb3c86e89ddcdd453990e826e4cd20ebec89017445bdc7db215559`
- `out.json`: deterministic sample report

The experiment is a model, not evidence about any specific production system.
