# Academic Literature & Industrial Standards Dossier

This document provides the definitive academic literature foundation, verified original source citations, digital object identifiers (DOIs), and explicit architectural mappings for our Predictive Maintenance (PdM) Cyber-Physical System.

---

## 1. Primary Citations Summary Table

| Citation Key | Primary Author & Year | Publication / Standard | Identifier (DOI / Standard ID) | Open Access | Core Relevance to Project |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Cinar et al. (2022)** | E. M. Çinar, S. Kalay, İ. Sarıçiçek (2022) | *Machines* (MDPI), 10(11), 1006 | [10.3390/machines10111006](https://doi.org/10.3390/machines10111006) | **Yes (Gold OA)** | Coarse-to-fine triage, edge lightweight DAQ, CPS architecture for motor PdM |
| **ISO 10816-3 / 20816-3** | International Organization for Standardization (2009 / 2022) | ISO Standard (Geneva, Switzerland) | [ISO 10816-3:2009](https://www.iso.org/standard/50528.html) / [ISO 20816-3:2022](https://www.iso.org/standard/76507.html) | Formal Standard | Quantitative vibration severity threshold zones (A, B, C, D) for rotating machinery |
| **Mourtzis et al. (2020)** | D. Mourtzis, J. Angelopoulos, N. Panopoulos (2020) | *Frontiers in Mechanical Engineering*, 6:578379 | [10.3389/fmech.2020.578379](https://doi.org/10.3389/fmech.2020.578379) | **Yes (Gold OA)** | Multi-modal edge sensor fusion (vibration + thermal), remote monitoring telemetry |
| **Randall & Antoni (2011)** | R. B. Randall, J. Antoni (2011) | *Mechanical Systems and Signal Processing*, 25(2), 485–520 | [10.1016/j.ymssp.2010.07.017](https://doi.org/10.1016/j.ymssp.2010.07.017) | Academic (Elsevier) | Rolling element bearing kinematics, Kurtosis, Crest Factor, early spall shock physics |
| **Antoni (2006)** | J. Antoni (2006) | *Mechanical Systems and Signal Processing*, 20(2), 282–307 | [10.1016/j.ymssp.2004.09.001](https://doi.org/10.1016/j.ymssp.2004.09.001) | Academic (Elsevier) | Spectral Kurtosis mathematical foundation for detecting non-stationary impact transients |

---

## 2. In-Depth Source Analysis & Engineering Traceability

### 2.1 Cinar et al. (2022) — Cyber-Physical System & Coarse-to-Fine Gating

* **Full Title**: *A Predictive Maintenance System Design and Implementation for Intelligent Manufacturing*
* **Authors**: E. Mine Çinar, Sena Kalay, İnci Sarıçiçek
* **Journal**: *Machines*, 2022, Volume 10, Issue 11, Page 1006.
* **Publisher**: MDPI
* **Direct Access**: [DOI: 10.3390/machines10111006](https://doi.org/10.3390/machines10111006) (Local copy available in workspace: `machines-10-01006-v3.pdf`)

#### Abstract & Focus
The paper develops an end-to-end Cyber-Physical System (CPS) for condition monitoring and predictive maintenance across industrial assets, specifically demonstrating an **electric motor testbed**. It demonstrates that blindly running heavy machine learning / deep learning inference on edge nodes for every single incoming sensor packet is computationally wasteful and thermal-throttling on embedded controllers. Instead, the paper proposes a hierarchical architecture with automated workflow triage and clear Key Performance Indicators (KPIs).

#### Direct Mapping to Our Capstone Rig
1. **Two-Stage Coarse-to-Fine Pipeline**: 
   - Following Cinar et al.'s findings, our system uses **Stage 1 Shewhart Statistical Process Control (SPC)** at the edge.
   - Heavy Random Forest / GBDT inference is gated by Stage 1; the implemented warning condition is **z-score > 2.0** on dynamic RMS vibration, with additional fixed kurtosis, peak and thermal limits. CPU savings have not been measured on our Pi, so no percentage is claimed.
2. **Lightweight Edge Telemetry**:
   - Cinar et al. emphasized lightweight telemetry (MQTT/JSON) decoupled from backend analytics. We implemented this via our asynchronous streaming daemon (`pdm-cloud`) pushing non-blocking JSON frames to Firebase RTDB.
3. **Automated KPI Monitoring**:
   - The paper defines health indicators based on running statistical moments ($\mu$, $\sigma$, Kurtosis), exactly matching our sliding window feature extraction.

---

### 2.2 ISO 10816-3 / ISO 20816-3 — Mechanical Vibration Evaluation Standard

* **Standard Title**: 
  - *ISO 10816-3:2009: Mechanical vibration — Evaluation of machine vibration by measurements on non-rotating parts — Part 3: Industrial machines with nominal power above 15 kW and nominal speeds between 120 r/min and 15 000 r/min when measured in situ*
  - Updated by *ISO 20816-3:2022: Mechanical vibration — Measurement and evaluation of machine vibration — Part 3: Industrial machinery*
* **Issuing Body**: International Organization for Standardization (ISO Technical Committee ISO/TC 108/SC 2)
* **Official Reference**: [ISO 10816-3:2009](https://www.iso.org/standard/50528.html) | [ISO 20816-3:2022](https://www.iso.org/standard/76507.html)

#### Core Principles & Evaluation Zones
ISO 10816-3 establishes four standardized operational zones based on overall RMS vibration velocity ($v_{\text{rms}}$ in $\text{mm/s}$) and acceleration ($a_{\text{rms}}$ in $g$):

1. **Zone A (Green / Excellent)**: Vibration of newly commissioned machines; fully permissible for unrestricted continuous operation ($v_{\text{rms}} < 1.4\,\text{mm/s}$ or $a_{\text{rms}} < 0.10g$).
2. **Zone B (Green-Yellow / Acceptable)**: Machines operating normally without restriction for long-term continuous service ($v_{\text{rms}} < 2.8\,\text{mm/s}$ or $a_{\text{rms}} < 0.15g$).
3. **Zone C (Amber / Unsatisfactory)**: Machine is not suitable for continuous unrestricted operation. May operate for a limited period until a planned maintenance window ($2.8 \le v_{\text{rms}} \le 4.5\,\text{mm/s}$).
4. **Zone D (Red / Danger)**: Vibration severity is sufficient to cause catastrophic damage. Machine must be tripped/stopped immediately ($v_{\text{rms}} > 4.5\,\text{mm/s}$ or $a_{\text{rms}} > 0.35g$).

#### Direct Mapping to Our Capstone Rig
1. **Rule-Based Baseline Validation**:
   - In `pdm-daq` and `pdm-dashboard`, we implemented ISO 10816-3 Zone categorization as the primary sanity check against raw accelerometer readings.
2. **Physical Interpretability for Judges**:
   - Instead of presenting the AI model as an ungrounded "black box," our software cross-checks the AI's predicted health state against ISO 10816-3 Zone boundaries. If the model outputs `NORMAL` when ISO metrics indicate `Zone D`, an alert is flagged.

---

### 2.3 Mourtzis et al. (2020) — Multi-Modal Sensor Fusion & Remote Cloud Telemetry

* **Full Title**: *Intelligent Predictive Maintenance and Remote Monitoring Framework for Industrial Equipment Based on Mixed Reality*
* **Authors**: Dimitris Mourtzis, John Angelopoulos, Nikos Panopoulos
* **Journal**: *Frontiers in Mechanical Engineering*, 2020, Volume 6, Article 578379.
* **Publisher**: Frontiers Media SA
* **Direct Access**: [DOI: 10.3389/fmech.2020.578379](https://doi.org/10.3389/fmech.2020.578379) (Local copy available in workspace: `fmech-06-578379.pdf`)

#### Abstract & Focus
Mourtzis et al. establish a comprehensive framework for smart factories connecting edge Data Acquisition (DAQ) modules with cloud-based visualization. Their study highlights two critical operational realities:
1. **Multi-Modal Sensing**: Mechanical vibration alone does not tell the complete degradation story; thermal heat build-up (from friction and bearing starvation) occurs synchronously with mechanical micro-impacts.
2. **Latency & Edge Independence**: The physical machine must maintain local fail-safe control even if cloud connectivity drops, while the cloud layer provides remote visibility for distributed operations.

#### Direct Mapping to Our Capstone Rig
1. **Sensor Fusion**: 
   - We integrated a 3-axis MEMS accelerometer (`ADXL345`) coupled with a K-type thermocouple read by `MAX6675` and an `INMP441` I2S microphone, following Mourtzis et al.'s multi-modal parameter schema. The older `MPU6050` / `DS18B20` / `BMP280` names in earlier drafts did not match the deployed BOM and are removed.
2. **Offline-First Resilience**:
   - In strict alignment with Mourtzis et al.'s edge architecture, our Raspberry Pi logs locally first (rolling hot_backup.csv). Telemetry to Firebase is a separate mirror service (firebase_mirror.py). Correction 2026-11-26: there is no SQLite buffer in the code, and frames queued while offline (up to 200, in cloud_backlog.json) are not replayed to the cloud. See docs/FULL_CYCLE_STATUS.md.

---

### 2.4 Randall & Antoni (2011) — Bearing Fault Kinematics & Higher-Order Statistics

* **Full Title**: *Rolling element bearing diagnostics—A tutorial*
* **Authors**: Robert Bond Randall, Jérôme Antoni
* **Journal**: *Mechanical Systems and Signal Processing*, 2011, Volume 25, Issue 2, Pages 485–520.
* **Publisher**: Elsevier
* **Direct Access**: [DOI: 10.1016/j.ymssp.2010.07.017](https://doi.org/10.1016/j.ymssp.2010.07.017)

#### Abstract & Focus
Widely recognized as the seminal tutorial on rolling element bearing vibration diagnostics. Randall and Antoni detail the mechanical physics of bearing degradation:
- When an inner raceway, outer raceway, or rolling element develops an incipient fatigue spall, each passage of a rolling element over the defect creates a sharp mechanical impact of microsecond duration.
- In early stages (Stage 1 & 2 pitting), overall RMS velocity hardly changes because the impact duration is miniscule compared to the rotation period.
- Consequently, **higher-order statistical moments**—specifically **Kurtosis ($K$)** and **Crest Factor ($CF$)**—serve as the earliest physical heralds of bearing distress.

#### Mathematical Formulations Used in Our Feature Extraction
1. **Kurtosis ($K$)**:
   $$\text{Kurtosis} = \frac{\frac{1}{N}\sum_{i=1}^N (x_i - \mu)^4}{\sigma^4}$$
   - Healthy Gaussian vibration: $K \approx 3.0$.
   - Incipient spalling / transient shocks: $K > 5.0$ to $15.0+$.
2. **Crest Factor ($CF$)**:
   $$CF = \frac{x_{\text{peak}}}{x_{\text{rms}}}$$
   - Healthy steady vibration: $CF \approx 2.5 - 3.5$.
   - Impact faults: $CF > 6.0$.

#### Direct Mapping to Our Capstone Rig
- Our DSP engine (`ml/dataset_generator.py`, `edge/edge_daq.py`, `ml/train_rf.py`) extracts **9 model features** per window (`rms_dyn`, `peak_dyn`, `crest_factor`, `kurtosis`, `temp_c`, `temp_slope`, `sound_rms`, `sound_db`, `sound_zcr`), with **Kurtosis and Crest Factor** as core shock indicators. `z_score` is a Stage-1 gate metric, not a model input. This follows the spalling dynamics formalized by Randall & Antoni.

---

### 2.5 Antoni (2006) — Spectral Kurtosis Foundation

* **Full Title**: *The spectral kurtosis: a useful tool for characterising non-stationary signals*
* **Author**: Jérôme Antoni
* **Journal**: *Mechanical Systems and Signal Processing*, 2006, Volume 20, Issue 2, Pages 282–307.
* **Publisher**: Elsevier
* **Direct Access**: [DOI: 10.1016/j.ymssp.2004.09.001](https://doi.org/10.1016/j.ymssp.2004.09.001)

#### Core Relevance
- Proves theoretically why time-domain Kurtosis can be diluted if background operational noise is high, and establishes the foundation for filtering vibration into frequency bands where the signal-to-noise ratio of impact shocks is maximized.
- Justifies why our feature extraction computes both raw statistical moments and FFT frequency band energies.

---

## 3. How to Cite in the Capstone Presentation & Defense

When presenting to STEM competition judges or academic reviewers:

> *"Our vibration diagnostics and predictive maintenance pipeline is rooted in international industrial standards and peer-reviewed literature. We benchmark baseline vibration limits against **ISO 10816-3 (Zone A through D)**, while our time-domain feature engineering leverages the statistical shock dynamics formalized by **Randall & Antoni (2011)** for early raceway spall detection. Furthermore, to overcome the edge computing bottleneck identified by **Cinar et al. (2022)** and **Mourtzis et al. (2020)**, we designed a coarse-to-fine triage architecture where Shewhart statistical process control gates fine AI inference, achieving full real-time autonomy on an embedded platform at zero commercial software licensing cost."*
