# حزمة المعرض والمراجعة — G12 Capstone 2026/27

**الحالة:** جاهزة للعرض والمراجعة محلياً · **التاريخ:** 2026-11-25
**القاعدة:** كل رقم إما مُقاس وموثّق في المستودع، أو موسوم صراحةً بأنه benchmark
عام/محاكاة. لا يوجد رقم تكلفة أو زمن بقاء لموتور المشروع.

## 1) ورقة دفاع من صفحة واحدة

| السؤال | الإجابة الآمنة | الدليل |
|---|---|---|
| النظام بيعمل إيه دلوقتي؟ | يقرأ ثلاثة حساسات على الراسبري، بوابة SPC ثم تصنيف الحالة الحالية إلى أربع فئات، ويعرض القرار على الداشبورد ويرآيه على Firebase. | `README.md`، `edge/edge_daq.py`، `public/index.html` |
| الدقة 100% معناها إيه؟ | دقة الـ benchmark **الصناعي** فقط على 1,400 نافذة مولّدة. **ليست** دقة على موتور حقيقي. | `ml/ai_report.md` §5، `tests/test_evaluation.py` |
| الـ 100% بتاعة CWRU معناها إيه؟ | benchmark **تشخيص** على موتور CWRU حقيقي 2 hp: **1.000 (100.0%)** على 1,039 نافذة بفصل blocks متصلة غير متداخلة، ومقابل majority baseline **0.4004 (40.04%)**. الأربع فئات حالة محمل وليست فئات الـ runtime؛ `OFFLINE RESULT / NAMED PUBLIC DATASET`، وليست RUL. | `ml/diagnosis_cwru.py`، `ml/diagnosis_cwru_report.json`، `tests/test_diagnosis_cwru.py`، `ml/ai_report.md` §16 |
| فيه RUL شغال؟ | **No RUL number is shown or supported for the rig.** Our rig has no run-to-failure data and no operator failure labels, so no RUL number is shown or supported for it. What exists is offline benchmark work on public data, labelled as offline results on named public datasets. Regression error (MAE/RMSE) and warning classification metrics are different measures. On the real 160 kW induction-motor dataset (Zenodo DOI `10.5281/zenodo.15637023`, CC BY 4.0, four runs, leave-one-run-out) the model is worse than simple baselines: MAE 141.716 h vs 69.185 h for constant zero, RMSE 204.069 h vs 106.164 h, and 24-hour warning accuracy 0.677 vs 0.686 for never warning, with recall 0.029. On XJTU-SY bearings tail MAE is 134.924 min vs 136.558 min for a constant baseline (RMSE 171.776 vs 160.859 min, worse). NASA IMS (MAE 9165.28 vs 17011.8 min) and PRONOSTIA (last-window MAE 182.91 s vs 8900 s, six bearings) are better than their constant baselines on bearing benchmarks only. The 0.940 warning accuracy is on simulated NASA C-MAPSS turbofan data, a different task. None of this is our motor. | `ml/rul_fmcg.py`، `ml/rul_fmcg_report.json`، `data/fmcg_induction_rul/README.md`، `ml/rul_pronostia_report.json`، `ml/rul_xjtu_sy_report.json`، `ml/rul_nasa_ims_report.json`، `public/index.html` |
| لو كان عندنا موتورنا، المشروع هيبقى predictive maintenance كامل؟ | المسار مجهّز: `ml/rul_from_rig.py` يقرأ CSV بـ `failure_timestamp` من المشغّل، يقيّم بفصل الـ run، ويحفظ نموذجاً ويتنبأ بـ RUL. **لا** نقول إنه اتختبر ميدانياً. | `docs/REAL_MOTOR_READINESS.md`، `ml/rul_from_rig.py`، `tests/test_rul_from_rig.py` |
| البيانات حقيقية؟ | نعم في Benchmarks العامة: سجل FMCG لموتور حقيقي 160 kW ثلاثي الأطوار بـ RUL بالساعات، وCWRU عيّنة موتور حقيقي بعيوب مِصَنعة، وPRONOSTIA ست تجارب وXJTU-SY 15 تجربة وNASA IMS 4 حالات فشل موثّقة run-to-failure حقيقية لمحامل. لا، ليست من ريج المشروع. | `data/fmcg_induction_rul/README.md`، `data/cwru/README.md`، `data/pronostia/README.md`، `data/xjtu_sy_mendeley/README.md`، `data/nasa_ims/README.md` |
| المصادر والرخص موثّقة؟ | الداشبورد يعرض لوحة أدلة مع رخص CC BY 4.0 الصريحة لـ FMCG والنسخة المشتقة وmetadata بتاع NASA IMS (`usa.gov/government-works`)؛ الرخصة الصريحة لأصل XJTU-SY وFEMTO-ST وCWRU ورقم كتالوج Reliance غير متوفرة ومكتوبة `[NEED: ...]`، لا نخترعها. | `docs/DATA_PROVENANCE_LICENSES.md`، `tests/test_dashboard_benchmark_evidence.py` |
| الداشبورد بيعمل إيه بالظبط؟ | عرض حالة مباشرة، قرار المشغّل، رسوم بيانية، روابط المعايرة والشرح، وكتم الإنذار. **مفيش** أزرار محاكاة ولا أوامر كتابة ولا تحكّم في الـ DAQ. | `public/index.html`، `tests/test_evaluation.py` |
| المصدر الحي منين؟ | **REMOVE SIMULATOR, ALL FROM DEVICE**: أداة `stream_live.py` متوقفة، والداشبورد يعرض `DEVICE TELEMETRY ONLY`؛ القيم الغايبة/القديمة تظهر `NO DATA`/`AWAITING DATA`. | `edge/stream_live.py`، `tests/test_device_only_telemetry.py`، `public/index.html` |
| المعايرة اتمّت؟ | الإجراء موثّق وقابل للتشغيل على الراسبري فقط؛ نتيجة موقّعة/سجل تشغيل فعلي غير متوفر. لا يُقال «PASS». | `docs/CALIBRATION_RUNBOOK.md`، `edge/calibrate.py` |
| فيه توفير CPU/تكلفة مقاس؟ | لا. سُحب ادعاء توفير الموارد. المقاس فقط زمن الاستدلال: 26.19 ms على الجهاز و29.99 ms على الراسبري للنافذة الواحدة. | `docs/PI_DEPLOYMENT_EVIDENCE.md` |
| إيه المطلوب للخطوة الجاية؟ | `[NEED: run-to-failure series with timestamps and failure labels from our rig]`، `[NEED: measured degradation curve]`، `[NEED: real operator failure threshold]`. | `README.md`، `ml/ai_report.md` §11 |

**الجملة الآمنة للمعرض:**
> «النظام يكتشف ويصنّف الحالة الآن ويقترح إجراءً؛ أعلى رقم حقيقي لدينا هو **1.000 (100.0%)** على benchmark تشخيص CWRU بأربع فئات حالة محمل، مقابل **0.4004 (40.04%)** baseline، وهو `OFFLINE RESULT / NAMED PUBLIC DATASET` وليس فئات ريجنا. أما التنبؤ بالبقاء فشغال كـ benchmark على موتور حقيقي عام بـ RUL بالساعات، ودقة إنذار 24 ساعة فيه 67.7% نقولها كما هي لأنها تحت 80%؛ مسار `ml/rul_from_rig.py` جاهز لبيانات موتورنا، ومحتاج بيانات run-to-failure وتوقيع نهاية العمر قبل أي ادعاء ميداني.»

## 2) تسلسل العرض (Demo) — 5 دقائق

1. **الداشبورد المباشر:** افتح `https://castpone2026.web.app/` → بيّن الحالةLive،
   قرار المشغّل، الرسوم، ولوحة الـ benchmark الموسومة `OFFLINE RESULT / NAMED PUBLIC DATASET` مع أدلة المصادر. لا تضغط أي أداة محاكاة (غير موجودة أصلاً).
2. **الشرح بالشرائح:** افتح `https://castpone2026.web.app/guide.html` → شريحة
   البنية ثم شريحة الأسئلة. اقرأ إجابة RUL كما هي: benchmark عام، مش موتورنا.
3. **الراسبري (قراءة فقط):** `systemctl status pdm-daq.service pdm-cloud.service
   pdm-dashboard.service` → الثلاثة active. لا تعدّل الكود أو الكاليبريشن وقت العرض.
4. **القراءة الخام:** اعرض نموذج CSV مسجّل من `edge/raw_measuree.py` فيه قيم
   ADXL الخام وكلمة MAX6675 وRMS الصوت. إن أردت تشغيله حياً، أوقف `pdm-daq`
   مؤقتاً ثم أعد تشغيله؛ لا تكتب `cal.json`.
5. **التشخيص على موتور حقيقي:** افتح `ml/diagnosis_cwru_report.json` وبيّن
   **1.000 (100.0%)** على 1,039 نافذة مقابل **0.4004 (40.04%)** baseline، مع
   فصل الـ blocks من غير تداخل. قل فوراً: أربع فئات حالة محمل، مش فئات ريجنا،
   ومش RUL. Label: `OFFLINE RESULT / NAMED PUBLIC DATASET`.
   لإعادة الإنتاج: `python3 ml/diagnosis_cwru.py --report /tmp/diagnosis_cwru.json`.
6. **الـ RUL الحقيقي على benchmark:** افتح `ml/rul_fmcg_report.json` في اللوحة
   وبيّن **141.716 h MAE** و**204.069 h RMSE** و**67.7%** دقة إنذار 24 ساعة،
   مع إنها أقل من 80% وأسوأ من الـ baselines. Label:
   `OFFLINE RESULT / NAMED PUBLIC DATASET`. لإعادة الإنتاج:
   `python3 ml/rul_fmcg.py --report /tmp/rul_fmcg_report.json`. للمصادر المستقلة
   افتح `ml/rul_pronostia_report.json` و`ml/rul_xjtu_sy_report.json` و
   `ml/rul_nasa_ims_report.json` وبيّن نفس الـ label، مع دقائق التسجيل الاسمية.
7. **الاختبارات:** `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest
   discover -s tests` → العدد النهائي و`OK` يُذكر في تقرير التسليم، لا يُختلق.

## 3) فهرس الأدلة

| what | where |
|---|---|
| تشخيص 4 فئات + بوابة | `ml/rf_predictor.py`، `edge/edge_daq.py`، `ml/ai_report.md` |
| 100% صناعي فقط | `ml/ai_report.md` §5، `tests/test_evaluation.py` |
| RUL على موتور حقيقي 160 kW (مش موتورنا) | `data/fmcg_induction_rul/`، `ml/rul_fmcg.py`، `ml/rul_fmcg_report.json`، `tests/test_rul_fmcg.py` |
| Firebase/الداشبورد | `docs/FIREBASE_SETUP.md`، `docs/PI_DEPLOYMENT_EVIDENCE.md` |
| RUL مستمر على C-MAPSS (محاكاة) | `data/cmapss/`، `ml/train_rul_cmapss.py`، `tests/test_rul_cmapss.py` |
| إنذار RUL فوق 80% على C-MAPSS (محاكاة، 30 دورة، تسميات RUL صريحة، مش موتورنا) | `ml/rul_cmapss_warning.py`، `ml/rul_cmapss_warning_report.json`، `tests/test_rul_cmapss_warning.py`؛ الدقة 0.940 مقابل baseline 0.750 |
| RUL على محامل حقيقية | `data/pronostia/`، `ml/rul_pronostia.py`، `tests/test_rul_pronostia.py` |
| RUL على محامل XJTU-SY (15 مساراً، مش موتورنا) | `data/xjtu_sy_mendeley/`، `ml/rul_xjtu_sy.py`، `ml/rul_xjtu_sy_report.json`، `tests/test_rul_xjtu_sy.py` |
| RUL على NASA IMS (4 حالات فشل موثّقة، مش موتورنا) | `data/nasa_ims/`، `ml/rul_nasa_ims.py`، `ml/rul_nasa_ims_report.json`، `tests/test_rul_nasa_ims.py` |
| مصادر الرخص وأدلة النسخ | `docs/DATA_PROVENANCE_LICENSES.md`، `tests/test_dashboard_benchmark_evidence.py` |
| جاهزية RUL على موتورنا (مش نتيجة ميدانية) | `docs/REAL_MOTOR_READINESS.md`، `ml/rul_from_rig.py`، `tests/test_rul_from_rig.py` |
| موتور حقيقي بعيوب مِصَنعة | `data/cwru/`، `tests/test_cwru_data.py` |
| تشخيص 4 فئات على موتور CWRU حقيقي (مش موتورنا) | `ml/diagnosis_cwru.py`، `ml/diagnosis_cwru_report.json`، `tests/test_diagnosis_cwru.py` |
| سجل الردود على G12 | `docs/G12_REQUEST_RESPONSE_REGISTER.md` |
| حزمة العرض دي | `docs/EXHIBITION_REVIEW_PACK.md` |
| شريحة الويب | `https://castpone2026.web.app/guide.html` |

## 4) أسئلة شائعة بالمعرض

**س: طالما الـ RUL شغال، هل الموتور هيشتغل كذا ساعة؟**
لا. العنوان الرئيسي محسوب على موتور FMCG عام 160 kW ثلاثي الأطوار بـ RUL
بالساعات من سجلات الصيانة، وZero/No-warning baselines أفضل منه؛ ومع benchmarks
محامل PRONOSTIA وXJTU-SY وNASA IMS لكل منها ريج وظروف مختلفة. لا علاقة لأي
رقم بموتورنا أو حساساتنا. `[NEED: run-to-failure series with timestamps and
failure labels from our rig]`.

**س: فين نتيجة RUL فوق 80%؟**
موجودة كـ **إنذار RUL خلال 30 دورة** على بيانات NASA C-MAPSS FD001 المحاكاة،
بتسميات RUL صريحة: دقة **0.940 (94.0%)** على 100 وحدة في آخر دورة مقابل
baseline **0.750**، ومتوسط خمس folds لا تتشارك الوحدات **0.9705**. مش دقة RUL
مستمرة، مش موتورنا، مش عتبة إنذار للمشغّل ومش validation ميداني. نتيجة RUL على
موتور حقيقي (FMCG) لسه **67.7%** تحت 80% ومُعلَنة كما هي؛ لا تعديل ولا انتقاء.

**س: طالما مفيش موتور، إيه اللي جاهز عشان نكمل predictive maintenance؟**
المسار كامل على الورق والكود: `ml/rul_from_rig.py` يستقبل CSV فيه تسع خصائص الـ runtime و`failure_timestamp` يحدّده المشغّل، يبني نوافذ causal، يقيّم بفصل الـ run كاملاً، ويحفظ نموذجاً للتنبؤ. لسه محتاج `[NEED: run-to-failure series with timestamps and failure labels from our rig]` و`[NEED: operator-accepted failure endpoint and reviewed metric report]` قبل أي كلام ميداني.

**س: ليه all-window RMSE كبير (9557 ثانية) والـ last-window صغير (335)؟**
لأن التنبؤ المبكر بالعمر الكامل أصعب بكثير من تقدير القرب من نهاية التجربة.
نعرض الرقمين معاً ولا ننتقي الأفضل فقط. الـ baseline الثابت كان 8902 ثانية على
آخر نافذة، فالنموذج أفضل منه بوضوح عند نهاية العمر.

**س: data حقيقية يعني من موتورنا؟**
لا. «حقيقي» هنا يعني مقيس في تجارب منشورة وموثّقة، لا مولّدة. مصدرها FMCG أو
CWRU أو PRONOSTIA/FEMTO-ST أو XJTU-SY أو NASA IMS، وكلٌّ له ريج وظروف مختلفة عن
ريجنا. رخصة FMCG صريحة CC BY 4.0 على Zenodo DOI `10.5281/zenodo.15637023`.

**س: الـ 100% بتاعة CWRU تعني إن نموذجنا على موتورنا 100%؟**
لا. الرقم **1.000 (100.0%)** محسوب على أربع فئات حالة محمل في عيّنة CWRU
بمقارنة **0.4004 (40.04%)** baseline، بفصل blocks متصلة غير متداخلة. فئات
الـ runtime عندنا مختلفة، والريج مختلف، ولا يوجد validation ميداني؛ لذلك
الوصف الإلزامي `OFFLINE RESULT / NAMED PUBLIC DATASET`.

**س: الرخصة واضحة؟**
FMCG على Zenodo معلنة CC BY 4.0 (DOI `10.5281/zenodo.15637023`)، ونسخة figshare
معلنة CC BY 4.0 (DOI `10.6084/m9.figshare.30595484.v1`)، لكن صفحات FEMTO-ST لا
تذكر رخصة صريحة: `[NEED: explicit FEMTO-ST licence]`، وأصل XJTU-SY:
`[NEED: explicit XJTU-SY reuse licence]`، وCWRU/Reliance:
`[NEED: explicit CWRU licence; exact catalogue number]`. لا ندّعي رخصة غير موجودة.

**س: المعايرة انتهت؟**
الإجراء مكتوب ومُوى على الراسبري، لكن لا يوجد سجل تشغيل موقّع من المشغّل:
`[NEED: signed run record]`. لذلك لا يُقال «معايرة معتمدة».

**س: هل الـ dashboard بيكتب في Firebase؟**
لا. النسخة المستضافة للعرض قراءة فقط من RTDB؛ كتابة الحالة تتم من خدمة الـ mirror
على الراسبري عبر `pdm-cloud.service`. الداشبورد نفسه بلا endpoints للكتابة.

## 5) كلمات/أرقام ممنوعة في العرض

- ❌ «الموتور هيبقى بعد شهر/سنة» أو أي hours-to-failure لموتورنا.
- ❌ «الدقة 100% على موتور حقيقي» أو «النموذج اتدرب على بياناتنا الحقيقية».
- ❌ «RUL ميداني / field-validated» أو «الـ 20 g هي عتبتنا».
- ❌ «توفير CPU / تكلفة / زمن استجابة كامل ≤5 s» دون قياس جديد.
- ❌ «معايرة PASS» دون سجل تشغيل موقّع.
- ❌ أي ادعاء أن CWRU أو C-MAPSS أو PRONOSTIA بيانات ريج المشروع.

## 6) `[NEED: ...]` المتبقية صراحةً

- `[NEED: run-to-failure series with timestamps and failure labels from our rig]`
- `[NEED: operator-accepted failure endpoint and reviewed metric report]`
- `[NEED: measured degradation curve]`
- `[NEED: real operator failure threshold]`
- `[NEED: signed calibration run record]`
- `[NEED: explicit FEMTO-ST dataset licence]`
- `[NEED: auth decision]` — قواعد RTDB الحالية public read/write ولم يتغير شيء.
