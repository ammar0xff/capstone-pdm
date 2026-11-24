# G12 follow-up work plan (read-only chat, local edits only)

Scope: answer all 13 forwarded G12 requests locally. Never contact WhatsApp, never change
model/gate behaviour, never invent physical/RUL/cost measurements.

- [x] P0 Run existing tests before edits (baseline: 13 tests OK on 2026-11-24)
- [x] P1 Create `docs/G12_REQUEST_RESPONSE_REGISTER.md` with all 13 requests, statuses, evidence and `[NEED: ...]` gaps
- [x] P2 Answer #1 honestly: ranges exist in code; physical provenance is missing
- [x] P3 Decide #2: synthetic benchmark kept; real labelled dataset required for field claims; write collection protocol
- [x] P4 #3 equation/unit/reference audit; fix wrong docs (8→9 features, ZCR units, 3σ wording, sensor names, unmeasured CPU-saving claim)
- [x] P5 #4 and #5 explainers: model files/training and ordinary-person dataset building
- [x] P6 #7 runtime truth: 10 Hz classifier call, internal SPC skip, no measured CPU saving, badge caveat
- [x] P7 #8 Pi autorun: systemd units, enable at boot, "not every uploaded file runs"
- [x] P8 #9/#10 evidence: simulator removed; results-table locations
- [x] P9 #11/#13 blocked honestly: real rig, RUL and cost need measurements; MathWorks links as external goals only
- [x] P10 #12 marked N/A (relative "tomorrow", no verifiable date)
- [x] P11 Add tests for the register and the resource-claim fixes
- [x] P12 Run full suite + `git diff --check`; commit and push; report in Arabic
