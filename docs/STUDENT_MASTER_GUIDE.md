# The 15-Year-Old's Guide to Our AI Predictive Maintenance Machine
**Grade 12 STEM Capstone 2026/2027 | Grand Challenge: Industrial Base of Egypt**  
**Live Web Dashboard:** [https://castpone2026.web.app](https://castpone2026.web.app)  
**Live Interactive Guide:** [https://castpone2026.web.app/guide.html](https://castpone2026.web.app/guide.html)  

---

## 1. What Is This Machine, and Why Did We Build It?

Imagine a giant electric motor pumping clean drinking water to an entire city or powering a conveyor belt in a food factory in 10th of Ramadan City. 

Inside that motor are steel ball bearings spinning at 1,500 RPM. One day, a microscopic crack forms on one of the steel rings. Nobody can see it because it's buried inside a sealed metal casing. A few hours later, the ball bearing shatters, the motor shaft seizes, sparks fly, the motor burns out, and the entire factory comes to a screeching halt.

In Egypt, unexpected factory shutdowns cost billions of Egyptian pounds every year. 

### The Doctor Analogy: 3 Ways to Maintain a Machine
1. **Reactive Maintenance (The Old Way):**  
   *Analogy:* You only go to the doctor when you collapse and faint on the floor.  
   *Problem:* The machine is already destroyed, and secondary damage has ruined the shaft.
2. **Preventive Maintenance (The Wasteful Way):**  
   *Analogy:* You take antibiotics every single Monday morning even when you feel completely fine.  
   *Problem:* Factories throw away healthy, expensive parts on a calendar schedule just in case.
3. **Predictive Maintenance (Our Capstone Way):**  
   *Analogy:* You wear a smartwatch that monitors your heart rate, skin temperature, and breathing 24/7. It notices your body temperature creeping up 2 hours before you even feel a fever, and tells you to rest before you collapse.  
   *Result:* Zero unexpected downtime, zero wasted parts!

---

## 2. The 3 Physical Senses (Hardware & Sensors)

A human doctor uses a stethoscope, a thermometer, and their hands. Our Raspberry Pi uses 3 specialized sensors:

### 1. The Sense of Touch: ADXL345 Accelerometer
- **What it does:** Measures how violently the motor is shaking.
- **How it works inside:** Inside the chip is a microscopic silicon diving board (MEMS). When the motor vibrates, the diving board bends back and forth. This bending changes electrical capacitance, which a microchip converts into digital acceleration numbers ($g$).
- **How fast it talks:** It talks to the Raspberry Pi over the **I2C bus** (2 wires: SDA and SCL) **270 times every single second**!

### 2. The Sense of Heat: K-Type Thermocouple & MAX6675
- **What it does:** Measures the exact temperature of the motor's metal casing.
- **How it works inside (The Seebeck Effect):** Two completely different metal wires (Chromel and Alumel) are welded together at the tip. When you heat that tip, electrons get excited and flow, creating a tiny electrical voltage (microvolts). The MAX6675 chip amplifies this microscopic voltage and converts it into temperature numbers with $0.25^\circ\text{C}$ precision.
- **How it talks:** It talks over high-speed **SPI** (Serial Peripheral Interface). It also has a built-in wire-break detector (Bit 2) so if a wire snaps, it warns us instantly!

### 3. The Sense of Hearing: INMP441 Microphone
- **What it does:** Listens to high-frequency acoustic squeals and metal-on-metal rubbing.
- **How it works inside:** A digital MEMS microphone that converts sound waves into a direct stream of 32-bit digital numbers at **48,000 Hz**.
- **How it talks:** It talks over **I2S** (Inter-IC Sound) straight into the Raspberry Pi’s direct memory access (DMA), giving crystal-clear audio with zero analog hiss.

### 4. The Brain: Raspberry Pi 4 Model B (4GB RAM)
- **Why not an Arduino?** An Arduino is like a basic pocket calculator—it can only run one simple loop and has tiny memory (2 KB). The Raspberry Pi 4 is a real quad-core computer running Linux. It samples sensors at 270 Hz, calculates advanced statistical calculus, runs 300 decision trees of machine learning, and hosts a web server all at the same time!

---

## 3. The Math Made Simple (No Jargon!)

Raw sensor numbers are just chaotic noise. We turn that noise into medical intelligence using 6 equations:

### 1. Dynamic RMS (Total Shaking Energy)
$$\text{RMS} = \sqrt{\frac{1}{N}\sum a_i^2}$$
- **Plain English:** Think of a washing machine. If an unbalanced blanket is inside, the whole machine wobbles violently. RMS calculates the total continuous shaking energy. If RMS rises above $0.15g$, something is loose or out of balance.

### 2. Kurtosis (The Pinprick Detector)
$$\kappa = \frac{\mu_4}{\sigma^4}$$
- **Plain English:** Imagine sitting in a quiet classroom, and someone suddenly pops a balloon. That sharp sudden spike is what Kurtosis detects. When a steel bearing ball rolls over a microscopic crack, it creates a tiny sharp click. A healthy motor has a Kurtosis of $\approx 3.0$ (smooth bell curve). A cracked bearing spikes Kurtosis to $> 5.0$, catching the fault weeks before the motor breaks!

### 3. Crest Factor (Shock vs Steady)
$$\text{CF} = \frac{\text{Peak}}{\text{RMS}}$$
- **Plain English:** Is the vibration a continuous smooth hum (low Crest Factor), or is it quiet with violent hammer strikes (high Crest Factor)?

### 4. Shewhart SPC Z-Score (The Nightwatchman)
$$Z = \frac{\text{RMS} - \mu_0}{\sigma_0}$$
- **Plain English:** How weird is the machine acting compared to its healthy morning baseline? If $Z$ is between $-2$ and $+2$, the machine is behaving normally. If $Z$ jumps past $+2.0$ (95.4% confidence), the alarm sounds!

### 5. Thermal Derivative $\Delta T/\Delta t$ (The Fever Rate)
$$\frac{\Delta T}{\Delta t} = \frac{T_{\text{now}} - T_{\text{past}}}{\Delta t / 60} \quad [^\circ\text{C/min}]$$
- **Plain English:** If a motor is $45^\circ\text{C}$, that's normal. But if its temperature jumps by $5^\circ\text{C}$ in just 60 seconds, friction is melting the bearings! Watching the slope lets us stop the motor 20 minutes before it catches fire.

### 6. Acoustic Zero Crossing Rate (ZCR)
- **Plain English:** How fast does the sound wave wiggle across zero? A low rumble has low ZCR. A dry metal-on-metal squeal has thousands of wiggles per second (high ZCR).

---

## 4. The Artificial Intelligence (How It Diagnoses Diseases)

### The Two-Stage Gatekeeper (Cinar et al. 2022)
Running heavy artificial intelligence models 24 hours a day is like driving your car with the gas pedal floored while parked—it wastes electricity, heats up the CPU, and wears out components. We use a **two-stage hybrid monitoring system**:

```
[Sensors 270 Hz] ───> [Stage 1: Statistical Gate (SPC)]
                                │
               Is Z <= 2.0? ────┴──── Is Z > 2.0? (Anomaly!)
                     │                                │
             (Stay in Low Power)             (Wake up Stage 2 AI!)
             CPU usage < 8%                           │
                                         [Stage 2: Random Forest]
                                         300 Decision Trees Vote:
                                         • Normal Operation
                                         • Mechanical Imbalance
                                         • Bearing Defect
                                         • Thermal Runaway
```

### Why a Random Forest?
Imagine asking a single doctor what disease you have—they might make a human error. Instead, imagine putting **300 doctors** in a room and having them vote. That is a Random Forest!
- We created **300 decision trees**.
- We trained them on **1,400 multi-modal machine windows**.
- When an anomaly occurs, all 300 trees analyze the vibration, heat, and acoustics simultaneously and cast their vote in **under 1.5 milliseconds**!
- Our model achieved **100.00% accuracy** on the test dataset!

---

## 5. The Cloud & Web Dashboard: Zero-Cost Magic

The Capstone rubric demanded **"Wireless to Cloud + IoT"**, but our budget allowed **0 EGP cloud spend**. Here is how we achieved enterprise-grade cloud telemetry for free:

1. **Google Firebase Realtime Database (Spark Free Tier):**
   - The Raspberry Pi acts like an IoT messenger. Every 15 seconds, it sends the latest machine state to `https://castpone2026-default-rtdb.firebaseio.com/motor1.json`.
2. **The Quota Guard Algorithm:**
   - Google gives 20,000 free writes per day. Sending data every 15 seconds uses only $\approx 5,760$ writes per day. An internal counter on the Pi guarantees we never exceed 15,000 writes/day, keeping it 100% free forever!
3. **Google Firebase Hosting:**
   - We published our entire dashboard to Google's worldwide CDN at **`https://castpone2026.web.app`**.
   - Anyone in the world can open the link on their phone and watch the live motor telemetry in real-time with zero server costs!
4. **Offline-First Resilience:**
   - If someone cuts the Wi-Fi cable, the Pi does not crash. It keeps running locally on its own Wi-Fi hotspot (`http://192.168.4.1:5000`) and buffers failed frames to its SD card (`hot_backup.csv`). When Wi-Fi returns, it flushes the backlog to the cloud automatically!

---

## 6. How to Explain This to the Judges in 3 Minutes

When you stand before the judges at the Capstone Exhibition, follow this winning demonstration sequence:

| Time | Action | What to Say to the Judges |
|---|---|---|
| **0:00 - 0:30** | Open [`https://castpone2026.web.app`](https://castpone2026.web.app) on your smartphone. | *"Welcome, judges. Our Capstone project solves Egypt's industrial downtime challenge using edge AI and multi-modal sensing. Here on my phone, you can see our live machine telemetry streaming from our Raspberry Pi via Firebase at zero cloud cost."* |
| **0:30 - 1:00** | Point to the Stage 1 Badge. | *"Notice our two-stage architecture from Cinar et al. (2022). We don't waste power running heavy neural nets continuously. Stage 1 Shewhart SPC monitors the baseline for free at under 8% CPU load."* |
| **1:00 - 1:45** | **Inject Fault 1:** Attach the small weight to the motor shaft. | *"Now, watch what happens when I simulate a mechanical unbalance. The RMS vibration spikes, breaches our 2-sigma gate in under 1.5 seconds, awakens Stage 2, and our 300-tree Random Forest instantly classifies 'Mechanical Imbalance' with 98% confidence!"* |
| **1:45 - 2:15** | **Inject Fault 2:** Tap the mounting base with a screwdriver. | *"Now I simulate a bearing raceway crack. Look at the Kurtosis equation on the dashboard: it spikes from 3.0 to over 5.5, identifying a 'Bearing Defect' before overall RMS rises!"* |
| **2:15 - 3:00** | **Prove Offline Survival:** Turn off phone Wi-Fi or show the offline local panel. | *"Finally, our system is strictly offline-first. Even if factory internet is cut, the Raspberry Pi logs 100% of data to its SD card and serves the technician locally. All of this was built inside a 9,370 EGP budget with zero paid cloud subscriptions."* |

---
*Created for Grade 12 STEM Capstone 2026/2027*
