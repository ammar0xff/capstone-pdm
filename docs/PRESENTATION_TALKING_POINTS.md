# G12 PDM: committee talking points

Keep these honest. Every number below comes from public benchmark data, not from our motor.

## 1. What we built (30 s)
- A condition-monitoring system on a Raspberry Pi: vibration (ADXL345), temperature (MAX6675) and sound (INMP441).
- Stage 1: rule layer. Vibration against a learned baseline, kurtosis, temperature and sound level. Output: No rule / Warning / Fault.
- Stage 2: a Random Forest that runs only when Stage 1 flags something.
- Live dashboard, a recorded-data replay dashboard, and a baseline "commissioning" step (10-minute run on a motor the operator confirms is normal).

## 2. What is real and what is a stand-in
- The hardware chain, the dashboard, the rule layer and the commissioning flow are real and run on the Pi.
- The replay screen shows PRONOSTIA public bearing recordings. It is labeled "Recorded data: PRONOSTIA, replay". It is not our motor.
- Our motor is faulty. We have no healthy baseline and no fault labels from it. We did not train or validate anything on it.

## 3. Numbers we can state (held-out public data only)
| Item | Result | Limit |
|---|---|---|
| Fault detection, KAIST induction-motor rig, 5 classes | 74% balanced accuracy (whole recordings held out), 81% (load held out), majority guess 40% | Different machine, not deployed |
| Fault detection, HUST bearings, healthy vs fault | 99.9% on held-out bearings | Bearing test rig, different machine |
| Remaining life, 25 run-to-failure bearings (XJTU-SY, NASA IMS, PRONOSTIA) | Error in the last 20% of life 0.29 of the run vs 0.40 for a constant guess. 19 of 25 bearings warned with under 30% life left. 9.6% false early warnings | Weak trend indicator. Percent of life, not hours. Not validated on our fan |
Do not say "accuracy of our system". Say "accuracy of the method on public data".

## 4. Likely questions
- Does it work on your motor? Not shown. The motor was faulty and its data is noisy (reboots, temperature jumps), which looks like a power or wiring problem. Plan: fix the motor, commission a baseline, then evaluate.
- Why is the replay on screen? It shows the interface working on trusted recorded data. The label on screen says so.
- Is the RUL number reliable? No. It is an indicative trend with a stated error range, trained on other machines.
- Why not train on your own data? We have no run-to-failure data and no labeled faults from our motor.
- Why Random Forest? Small, fast on a Pi, and explainable by features.

## 5. Next steps
1. Repair the motor and the power or wiring noise.
2. Commission a baseline on the fixed, confirmed-normal motor.
3. Record real runs, then evaluate the rules and model on our own data.
4. Only then claim anything about our motor.
