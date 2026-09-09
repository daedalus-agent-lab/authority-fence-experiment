# Authority Fence: a runnable NOT_APPLIED experiment

This repository contains a stdlib-only experiment for the article **A Fresh Read Cannot Prove It Did Not Happen**.

It demonstrates three bounded outcomes:

- an unfenced delayed apply can succeed after revocation;
- a store-enforced epoch fence refuses the delayed apply and emits a scoped `NOT_APPLIED` witness;
- a read-only observer must return `UNKNOWN` with `permit_retry: false`, because absence is not impossibility.

The model is intentionally small and does not claim end-to-end exactly-once. It has no network, crash window, partitions, or independent store operator.

## Run

```bash
python3 -m unittest test_authority_fence -v
python3 authority_fence.py --fuzz 200 --seed 7
```

Expected: 11 tests pass; the deterministic report has `all_expectations_met: true`. The fuzz control reports zero post-revocation admissions for the fenced store and nonzero violations for the deliberately broken check-then-act store.

## Integrity

- `authority_fence.py`: SHA-256 `973830d4111e8c33f427e190b38a73d86d256b02cda2b3ff5ec80333b27d7363`
- `test_authority_fence.py`: SHA-256 `95d1bf639f6f0390f7c05193a24bb2b34e9812b96cbec240cf7e9063a8f373fe`
- `out.json`: deterministic sample report

The experiment is a model, not evidence about any specific production system.
