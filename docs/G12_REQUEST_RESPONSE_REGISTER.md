# سجل الرد على طلبات فريق G12 — مراجعة محلية فقط

**تاريخ المراجعة:** 2026-11-24 · **مصدر الطلبات:** الجدول الوارد في
`/tmp/opencode/textinstinct_chat.txt:1340-1354` (طلبات منقولة للتحليل، لا تصريح تنفيذ).
**قيد ثابت:** لم تُرسل أي رسالة لأي طرف، ولم يتغير أي شيء في مجموعة WhatsApp. التفريغ الصوتي
مؤقت وغير مؤكد الأسماء/التوقيتات، لذلك لا يُبنى عليه إلا كطلب منقول لا كدليل تقني.

**القاعدة الحاكمة:** كل رقم يُقال هنا إما مُقاس وموثّق في المستودع، أو مُصنّف صراحةً كمحاكاة.
نسبة 100% خاصة بـ **benchmark صناعي صنعه الـ generator** فقط، وليست دقة على موتور حقيقي.
لا يوجد RUL ولا زمن بقاء متبقٍ ولا تكلفة فعلية مقيسة.

## 1) جدول حالات الطلبات الثلاثة عشر

| # | الطلب (مختصر) | الحالة | ما أُنجز محلياً | الدليل | المتبقي / `[NEED: ...]` |
|---|---|---|---|---|---|
| 1 | تأكيد/نفي: كود بُني على ملفات بلا رينجات ولا سطر عنها | ◐ تم الرد | رُصدت كل الرينج الموجودة في الكود وسُجّلت، ووُضح أن غياب **المصدر الفيزيائي** هو المشكلة الحقيقية | `ml/dataset_generator.py:58-72,82-84,228-230`; `docs/DATASET_RANGE_TRACEABILITY.md` | `[NEED: motor nameplate, bearing part number, raw calibration logs]` |
| 2 | generator مقبول أم داتا سيت جديدة بقراءات حقيقية؟ | ◐ قرار + بروتوكول | اعتُبر الـ generator مقبولاً كـ benchmark للتحقق من الكود فقط، وكُتب بروتوكول جمع داتا حقيقية في §3 | §3 أدناه; `docs/DATASET_RANGE_TRACEABILITY.md:3-5` | `[NEED: labelled real-motor windows before any field-accuracy claim]` |
| 3 | مراجعة المعادلات والوحدات والمراجع | ✅ تم | جدول تدقيق في §4 + تصحيح وثائق خاطئة (8→9 features، وحدة ZCR، صياغة 3σ، أسماء حساسات، ادعاء توفير CPU غير مقاس) | §4 أدناه; `docs/LITERATURE_REFERENCES.md`; `docs/CAPSTONE_MASTER_HANDBOOK.md:191-221` | `[NEED: MAX6675 datasheet link and acoustic calibration reference]` |
| 4 | شرح أساسيات الـ AI model (فايلات/تجميع/training) | ✅ تم | §5 يشرح الملفات وترتيب التدريب والنشر بلغة بسيطة | §5 أدناه; `ml/ai_report.md` §1–§4 | لا شيء محلياً |
| 5 | كيف يبني الشخص العادي داتا سيت دون ادعاء أن الـ AI صنع الملفات | ✅ تم | §6 خطوات عملية بلا أي ادعاء تملك/توليد | §6 أدناه; `docs/SENSOR_CALIBRATION.md` | `[NEED: physical collection session]` |
| 6 | تعديل مصادر الداتا لمصادر موثوقة أو قياس جزئي | ⛔ متوقف | سُجّل كل رينج ومصدره وكل فجوة بعلامة `[NEED: ...]`؛ لم يُخترع مصدر | `docs/DATASET_RANGE_TRACEABILITY.md`; §4 أدناه | `[NEED: manufacturer ranges / old paper values / partial real measurements]` |
| 7 | سلوك `edge.daq`: هل كل قراءة تنادي Stage 2 بدون Stage 1؟ وأثره على ادعاء توفير الموارد | ✅ تم التوضيح | §7 يشرح الاستدعاء كل 100 ms، والبوابة الداخلية في wrapper، واختلاف البوابتين، وسحب ادعاء توفير CPU | §7 أدناه; `edge/edge_daq.py:405-406,482-520,530-573`; `ml/rf_predictor.py:130-191` | `[NEED: approval + CPU measurement before gating the call at edge level]` |
| 8 | تشغيل ملفات الراسبري تلقائياً وهل كل ملف مرفوع يعمل؟ | ✅ تم | §8 يشرح systemd والـ enable عند الإقلاع ويوضح أن ليس كل ملف يعمل | §8 أدناه; `edge/*.service`; `docs/PI_DEPLOYMENT_EVIDENCE.md:5-13` | لا شيء محلياً |
| 9 | تأكيد إزالة أوبشنز الحالات الأربعة وبيانات الـ simulation | ✅ تم | أُزيلت أدوات المحاكاة من الداشبورد، ويوجد اختبار يمنع رجوعها | `public/index.html`; `tests/test_evaluation.py::TeamFollowUpTest::test_dashboard_has_no_simulation_controls` | لا شيء محلياً |
| 10 | تجهيز جداول النتائج الإجمالية قبل المعرض | ✅ تم | §10 يحدد أماكن جداول Totals وطريقة إعادة إنتاجها | §10 أدناه; `ml/ai_report.md` §5.4–§5.5; `docs/CAPSTONE_MASTER_HANDBOOK.md` §5.3, §10 | لا شيء محلياً؛ النتائج صناعية فقط |
| 11 | التيست الحقيقي على موتور ثم prediction/RUL (لينكي MathWorks) | ⛔ متوقف | كُتب بروتوكول الاختبار، ووُثّق أن RUL هدف خارجي وليس مطبقاً في النظام | §11 أدناه; `ml/ai_report.md:11,206-210` | `[NEED: motor rig access, calibrated raw readings, run-to-failure series]` |
| 12 | الرد سريعاً لأن الشغل مكمل «بكرة» | — لا ينطبق | لا يوجد تاريخ قابل للتحقق؛ اعتُبر كأولوية لا كطلب هندسي | `/tmp/opencode/textinstinct_chat.txt:1258-1260` | `[NEED: actual exhibition date if a deadline must be quoted]` |
| 13 | مخرجات أكثر تدرّجاً + مكان المشكلة وتكلفتها ومدة بقاء الموتور | ◐ جزئي | يوجد `response_plan` بأربع أولويات وإجراءات، لكن المدد ثابتة لكل فئة وليست تنبؤاً؛ لا تكلفة ولا زمن بقاء مقيسان | `ml/rf_predictor.py:37-72`; `edge/edge_daq.py:604`; `ml/ai_report.md` §5.5 | `[NEED: degradation curve, part prices, downtime cost and failure labels]` |

**الخلاصة:** كل ما يمكن تنفيذه محلياً دون قياس فيزيائي أُنجز. البنود 6 و11 والجزء المتعلق
بـ RUL/التكلفة من 13 تبقى متوقفة على بيانات حقيقية؛ لم يُملأ أي منها بقيم مخترعة.

---

## 2) الرد المباشر على السؤال #1: «صح كده؟»

**لا، ليس صحيحاً كما ورد.** يوجد سطر/سطور رينجات صريحة في `ml/dataset_generator.py`:

- `:58-72` ثوابت فيزيائية: `F_R_NOMINAL = 30.0 Hz`، `FS_VIB = 3200 Hz`، هندسة محمل 6205، `F_RES = 2400 Hz`، `ZETA = 0.045`.
- `:16-19` مناطق الشدة A/B/C/D، `:82-84` ضجيج الحساس، `:90-145` بصمات كل فئة،
  `:150-171` المسارات الحرارية، `:181-217` الصوت، `:228-230` خط أساس SPC للمولّد.
- `docs/DATASET_RANGE_TRACEABILITY.md` يسجّل كل رينج مع موقعه وحالته (simulated / configured / مفقود).

**نعم، صحيح جزئياً:** لا يوجد سطر يثبت أن هذه الأرقام جاءت من اسم موتور أو منشور ورقة أو
سجل كاليبريشن للموتور الموجود عندنا. الكود كُتب فوق قيم مفترضة. `[NEED: motor nameplate,
bearing part number, raw calibration logs, and a measured rig resonance/noise floor]`

الصياغة الآمنة للإجابة في المعرض: *«رينجاتنا موثّقة سطرياً في الكود وفي سجل المصادر،
لكنها قيم محاكاة/تهيئة وليست قياساً من موتورنا؛ لذلك لا ندّعي دقة ميدانية.»*

## 3) قرار #2: هل نقبل الـ generator؟

- **مقبول:** كـ benchmark صناعي لاختبار الأنابيب والتدريب والتحقق من عدم تسرب الـ run بين
  train/test. هذا بالضبط ما تقيسه اختبارات `tests/test_evaluation.py`.
- **غير مقبول:** كدليل على أن النظام يعمل بدقة 100% على موتور حقيقي، أو أنه يتنبأ بالعطل.

**بروتوكول الداتا الحقيقية (يُنفّذ عند توفر الموتور):**
1. تركيب ADXL345/MAX6675/INMP441 وتثبيت الكاليبريشن (`docs/SENSOR_CALIBRATION.md`، handbook §6).
2. تسجيل نوافذ `raw` لكل حالة مع `run_id` وطابع زمني وحالة معلومة (صحي / imbalance / bearing / thermal).
3. حساب نفس الـ 9 features من الإشارات الخام؛ لا يُستخدم `z_score` كـ feature (بوابة فقط).
4. تقسيم 70/15/15 بـ whole runs ثم `StratifiedGroupKFold`، وإعادة التدريب والتقييم.
5. مقارنة Rule-only مقابل RF على نفس النوافذ قبل quote أي نسبة.
6. `[NEED: labelled real-motor windows + calibration certificate + rig access]`

## 4) #3 تدقيق المعادلات والوحدات والمراجع

| العنصر | موقع الكود | الوحدة الصحيحة | المرجع | تصحيح/ملاحظة |
|---|---|---|---|---|
| Dynamic RMS | `edge/edge_daq.py:425-439`; `ml/dataset_generator.py:263` | `g` بعد طرح متوسط الجاذبية | ISO 20816-3; README §Engineering corrections | الكود يطرح متوسط كل محور ثم يأخذ norm؛ الصيغة scalars في الوثائق تبسيط مقبول |
| Kurtosis | `edge/edge_daq.py:441-450`; generator `:267-271` | بلا وحدة (`m4 / var² = m4 / σ⁴`) | Randall & Antoni 2011 | صحيح الآن في README/ai_report/handbook؛ لا تكتب `σ²` |
| Crest Factor | `edge:437-439`; generator `:265` | بلا وحدة (`peak/rms`) | Randall & Antoni 2011 | صحيح |
| BPFO/BPFI | generator `:64-69,87-88` | `Hz` | Randall & Antoni 2011 | `[NEED: installed bearing part number]` |
| Thermal ODE | generator docstring `:27-31` | `°C/min` للمنحدر | Blok & Jaeger / Newton cooling | التنفيذ الفعلي `:155-171` يولّد قيم normal لكل فئة، **لا يحل ODE**؛ صُحّح الدوكسترنج |
| Temperature | `edge:393-403,655-678` | `°C` (MAX6675 0.25°C/LSB ثم `a·T+b`) | MAX6675 datasheet | `[NEED: datasheet link]` |
| Thermal slope | `edge:452-464` | `°C/min` = `(T₂-T₁)/(Δt/60)` | handbook §4.4 | صحيح |
| SPC z-score | `edge:327-330,466-467`; `rf_predictor.py:134` | بلا وحدة (σ) | Shewhart; Cinar et al. 2022 | بوابة التشغيل `2σ` تحذير / `3σ` خطأ؛ الـ CSV يستخدم μ=0.038/σ=0.014 بينما Runtime يستخدم 0.080/0.025 — موثّق كـ mismatch |
| Acoustic SPL | generator `:212-213`; `edge:238-241` | dB SPL (تقديري) | acoustic theory | `120+20log10(RMS)` بمعامل غير معاير؛ `[NEED: acoustic calibration reference]` |
| ZCR | generator `:214-215`; `edge:243-245,691-697` | **crossings/sample** (كسر بلا وحدة) | ZCR theory | كان مكتوباً `crossings/s` في handbook §5.2؛ صُحّح. للتحويل إلى crossings/s اضرب في `fs` |

المستندات المُصحّحة في هذه الجولة: `docs/CAPSTONE_MASTER_HANDBOOK.md` (9 features، أسماء
features، وحدة ZCR، وصف النافذة)، `docs/LITERATURE_REFERENCES.md` (MAX6675 بدل DS18B20/BMP280،
9 بدل 10 features)، `docs/PROJECT_COMPLETE_TUTORIAL.md` (سحب ادعاء نسبة CPU غير مقاسة)،
`ml/dataset_generator.py` (صياغة SPC والـ ODE).

## 5) #4 إزاي الـ AI model اتعمل؟ (شرح مبسّط)

الملفات بالترتيب:

1. `ml/dataset_generator.py` كتب 1,400 نافذة صناعية (350 لكل فئة، 28 `run_id`) في `ml/windows.csv`.
2. `ml/train_rf.py` قرأ 9 أعمدة (`rms_dyn, peak_dyn, crest_factor, kurtosis, temp_c,
   temp_slope, sound_rms, sound_db, sound_zcr`) وقسّمها بـ whole runs، ثم درّب 300 شجرة
   (`max_depth=12`, `class_weight="balanced"`, `random_state=42`).
3. النتيجة: `ml/model.joblib` (النموذج) + `ml/model_meta.json` (الإعدادات والنتائج).
4. `ml/rf_predictor.py` يلفّ النموذج: بوابة SPC أولاً، ثم `predict_proba` عند الاختراق،
   ثم `response_plan` للمشغّل.
5. `edge/edge_daq.py` يستدعي الـ wrapper على Raspberry Pi وينشر النتيجة للداشبورد.
6. `"إزاي اتعمل"` باختصار: **بيانات → features → تقسيم بالـ run → تدريب 300 شجرة → حفظ
   الفايل → نشر على الراسبري → بوابة ثم تصنيف**. البيانات هنا مولّدة، وليست من موتور،
   والـ AI لم يكتب files بنفسه؛ نحن من كتبنا الكود وقررنا الأعمدة.

## 6) #5 كيف يبني الشخص العادي داتا سيت بنفسه؟

1. يحدّد 4 حالات واضحة ويسمّيها (`healthy`, `imbalance`, `bearing`, `thermal`).
2. يركّب الحساسات ويعايرها ويسجّل نتائج المعايرة (`docs/SENSOR_CALIBRATION.md`).
3. يشغّل الموتور في كل حالة ويسجّل **قراءات خام** مع اسم الحالة ورقم الجلسة والوقت.
4. يحسب نفس الـ 9 features من كل نافذة ويحفظها في CSV مع `run_id`.
5. يفصل الجلسات كاملة بين train/test (لا يخلط نوافذ من نفس الجلسة).
6. يدرّب النموذج ويقارنه بقواعد if/else على نفس الاختبار.
7. يقول الحقيقة: *«هذه قراءات جمعناها نحن، والـ AI تعلّم منها»* — لا *«الـ AI عمل الملفات»*.

## 7) #7 الحقيقة الكاملة عن `edge.daq` وادعاء توفير الموارد

- عند توفر 64 عيّنة على الأقل يتحدّث النظام كل **100 ms** (`edge/edge_daq.py:405-406`)،
  ويبني `feature_dict` في `:499-509`.
- **الاستدعاء في `:511-520` غير مشروط**: كل تحديث حالة ينادي `classifier.predict(...)`.
  لا يوجد `if Stage 1 breached` قبل هذا الاستدعاء على مستوى `edge_daq`.
- داخل `ml/rf_predictor.py:130-155` توجد بوابة SPC **خاصة بالـ wrapper**؛ إذا كانت القراءة
  طبيعية يعيد `rf_executed=False` ولا يستدعي `predict_proba`. عند الاختراق فقط `(157-191)`
  يعمل الـ RF. إذن الـ RF لا يعمل في كل قراءة، لكن **دالة الـ classifier تُستدعى** في كل قراءة.
- بوابة `edge_daq` نفسها (`:482-497`) تُحسب بعد الاستدعاء وتُستخدم في قرار العرض (`:530-573`)
  فقط. البوابتان مختلفتان: مثال thermal warn عند edge `>50°C` بينما wrapper يستخدم `>55°C`،
  وedge يضيف معيار صوت لا يوجد في بوابة wrapper. لا يوجد دليل على تكافؤهما.
- حقل `ai.gate_status` في الحزمة (`:598-600`) مشتق من `state != "Healthy"` وليس من
  `gate_info["gate_status"]`؛ قد يظهر «Stage 2 Triggered» بينما `rf_executed=False`.
  لا نغيّر هذا السلوك في هذه المراجعة الآمنة.

**الخلاصة للادعاء:** «نقلّل استهلاك الموارد الحسابية» **ادعاء غير مثبت وسُحب**. ما تقيسه الأدلة
هو: (أ) الـ wrapper يتخطى `predict_proba` في النافذة الطبيعية (smoke test على Pi:
`rf_executed=false`, `0.02 ms`)، (ب) استنتاج الـ RF وحده ~29.99 ms على Pi. لم يُقس استهلاك
CPU كلي قبل/بعد، ولم يُقس زمن inject→alert.
`[NEED: approval to add an edge-level gate + measured CPU/wall-time comparison before
restating any resource-saving claim]`

## 8) #8 ليه الفايلات تشتغل لوحدها على الراسبري؟

- systemd يقرأ وحدات من `/etc/systemd/system/*.service`. الوحدة الموجودة في
  `edge/pdm-daq.service` لها `[Install] WantedBy=multi-user.target`، وبعد
  `systemctl enable pdm-daq.service` يربطها systemd بدخول النظام، فيبدأ `ExecStart` تلقائياً.
- الوحدات المُتحقّق منها على Pi: `pdm-daq` و`pdm-cloud` و`pdm-dashboard` وكلها active
  (`docs/PI_DEPLOYMENT_EVIDENCE.md:5-13`) مع `Restart=always` و`RestartSec=3`.
- **ليس كل ملف يُرفع يعمل.** الذي يعمل فقط هو الملف المذكور في `ExecStart=` لوحدة مُفعّلة
  (أو cron/timer). نسخ `foo.py` إلى مجلد المشروع لا يشغّله. بعد تعديل unit يلزم
  `systemctl daemon-reload`، وبعد تعديل الكود يلزم `systemctl restart <service>`.
- هذا هو الفرق بين «تحط ملف» و«تسجّل خدمة عند النظام». لا يوجد سحر ولا تشغيل تلقائي لكل فايل.

## 9) #9 تأكيد إزالة محاكاة الداشبورد

أُزيلت أدوات الـ simulation وأوبشنز الحالات الأربعة كأدوات تجريبية من `public/index.html`
في الالتزام `da5f62a`. الاختبار
`tests/test_evaluation.py::TeamFollowUpTest::test_dashboard_has_no_simulation_controls`
يفشل إذا رجعت رموز مثل `toggleSimulator` أو `simScenario` أو `Physics Simulator`.
انتباه: الفئات الأربع نفسها تظهر كـ **نتيجة تصنيف حقيقية للنموذج**، وهذا ليس simulation data؛
الذي أُزيل هو التحكم اليدوي/البيانات المُصنّعة للعرض.

## 10) #10 أين جداول النتائج النهائية؟

| الجدول | المكان |
|---|---|
| Results Register (5 صفوف totals + جدول if/else لكل فئة) | `ml/ai_report.md` §5.4 |
| دور الـ AI ومقارنة RF/if-else | `ml/ai_report.md` §5.5 |
| ملخص المتركسات M1–M6 | `docs/CAPSTONE_MASTER_HANDBOOK.md` §5.3 و§10 |
| الصور الداعمة | `ml/confusion_matrix.png`, `ml/roc_curves.png`, `ml/feature_importance.png` |
| إعادة الإنتاج | `./.venv/bin/python -m unittest discover -s tests -v` ثم `python ml/benchmark_latency.py` |

كل الأرقام أعلاه synthetic benchmark فقط. لا يوجد جدول نتائج موتور حقيقي.

## 11) #11 و#13: ما الذي لا يمكن تنفيذه محلياً بصدق؟

- لينكا MathWorks (`Remaining Useful Life Estimation`, `Rolling Element Bearing Fault
  Diagnosis`) مراجع تعليمية خارجية توضّح ما هو الـ RUL، وليست دليلاً على أن نظامنا ينفّذه.
- أُضيفت أداة تحليل offline (`ml/degradation_rul.py`) تمدّ منحنى تدهور خطّياً أو
  أُسّياً إلى عتبة يُدخلها المشغّل صراحةً (`--threshold`)؛ لا توجد عتبة فيزيائية
  مخزّنة، ولا ربط بالـ runtime أو الداشبورد، وكل نتيجة موسومة
  `not field-validated` و`operator-supplied`. لذلك هي أداة تقدير مشروحة فقط،
  وليست RUL حقيقياً ولا دليلاً على زمن بقاء الموتور.
- التنفيذ الحالي يصنّف **الحالة الحالية** ويُصدر `response_plan` بأربع أولويات
  (`ROUTINE/SCHEDULE/URGENT/CRITICAL`) وإجراءات ثابتة لكل فئة. هذا «تدرّج في القرار»،
  لكنه **ليس** تدرّجاً محسوباً من منحنى تدهور، ولا تكلفة/زمن بقاء.
- `[NEED: run-to-failure series with timestamps and failure labels]` قبل أي تنبؤ بالعطل.
- `[NEED: part prices, labour rate and downtime cost rate]` قبل أي رقم تكلفة.
- `[NEED: measured degradation curve]` قبل استبدال المدد الثابتة بمدد متغيرة لكل حالة.
- لذلك لا يُقال للمشرفين: «الموتور هيشتغل شهرين/سنة» ولا «العطل بعد كذا» ولا «التكلفة كذا».
  يُقال: «النظام يكتشف ويصنّف الحالة الآن ويقترح إجراءً؛ التنبؤ بالبقاء محطة تالية محتاجة بيانات».

## 12) ملاحظة على #12 و مصادر التفريغ

كلمة «بكرة» وردت في فويس وقته الأصلي مجهول، فلا تُحوّل إلى تاريخ. تم إعداد هذا السجل
والوثائق في أقرب فرصة محلية. أسماء المرسلين، خصوصاً الاسم الذي سُمع «مروان»، غير مؤكدة؛
التفريغ الصوتي فيه مواضع `[غير واضح]` ولا يُستخدم لإثبات تكليف أو موعد.
