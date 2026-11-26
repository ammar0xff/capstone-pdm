# AI path offline test, 2026-11-26

Scope: synthetic features and fake hardware only. The motor was stopped, no fault was injected, nothing ran on the rig for this test. Results show how the software behaves, not how the motor is.

## What was run
- `pi_deployed/tests/g24_ai_path_test.py`: gate and Random Forest on synthetic feature dicts.
- `pi_deployed/tests/g23_fullloop_test.py edge_daq.py.g23 normal|dead 6`: the real `main()` loop with fake I2C/SPI, reading the packet file.
- Dashboard render of the live Pi page and the hosted page (screenshots, 08:58).

## Results
| Step | Result |
|---|---|
| Quiet features | Stage 1 gate passes, RF not run (`rf_executed` false). |
| High vibration features | Gate trips, RF runs, class "Mechanical Imbalance / Shaft Looseness", probability 0.49. Synthetic input, not a diagnosis. |
| Thermal slope features | Gate trips and RF runs but says Normal (0.48). The daq thermal rule carries the alert through, so the packet state is not driven by the RF alone. |
| Loud-sound only | Gate does not trip, RF not run. |
| 1023.75 sentinel | Gate trips, RF runs. The sentinel is not confirmed as a fault cause. |
| NaN kurtosis | Gate does not trip (NaN compares false). The daq marks `input_valid` false before this matters. |
| Fake healthy loop | Healthy, `rf_executed` false, `fault_proba` null, source `rule_derived_no_probability`, no NaN or Infinity tokens, seq advancing. |
| Fake dead accelerometer | State Unknown, `input_valid` false, vibration values null, no NaN tokens, seq advancing, file handles closed. |
| Dashboard | Shows rule result, "RF ran (unvalidated)" or "RF not run", confidence "n/a (rule-based, no probability)". No RUL field is read or shown. |
| RUL | The packet carries no RUL field and the dashboard shows "NONE: RUL not demonstrated". No RUL number exists for this rig. |

## Misleading fields (not changed, daq left as deployed)
- `ai.predicted_class` and `ai.predicted_class_id` read "Normal Operation" / 0 when the RF did not run, including for an Unknown (invalid input) packet. The dashboard does not display them and uses `rf_executed` and `ai.gate_status`. Any other consumer must do the same.
- Proposed small fix (needs a daq restart): set both to null when `rf_executed` is false. Not applied.
- The model file was saved with scikit-learn 1.4.2. The Pi has 1.4.2, so it loads clean there. Newer scikit-learn only warns.
