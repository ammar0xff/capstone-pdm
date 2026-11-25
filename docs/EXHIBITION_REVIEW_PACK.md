# حزمة المعرض والمراجعة — G12 Capstone 2026/27

**الحالة:** جاهزة للعرض والمراجعة محلياً · **التاريخ:** 2026-11-25
**القاعدة:** كل رقم إما مُقاس وموثّق في المستودع، أو موسوم صراحةً بأنه benchmark
عام/محاكاة. لا يوجد رقم تكلفة أو زمن بقاء لموتور المشروع.

## 1) ورقة دفاع من صفحة واحدة

| السؤال | الإجابة الآمنة | الدليل |
|---|---|---|
| النظام بيعمل إيه دلوقتي؟ | يقرأ ثلاثة حساسات على الراسبري، بوابة SPC ثم تصنيف الحالة الحالية إلى أربع فئات، ويعرض القرار على الداشبورد ويرآيه على Firebase. | `README.md`، `edge/edge_daq.py`، `public/index.html` |
| الدقة 100% معناها إيه؟ | دقة الـ benchmark **الصناعي** فقط على 1,400 نافذة مولّدة. **ليست** دقة على موتور حقيقي. | `ml/ai_report.md` §5، `tests/test_evaluation.py` |
| فيه RUL شغال؟ | نعم على **benchmark عام بمحامل حقيقية** (PRONOSTIA/FEMTO-ST): آخر نافذة MAE **182.91 ثانية** وRMSE **335.26 ثانية**، أفضل من baseline ثابت RMSE **8902.25 ثانية**. **لا** نقول إنها ساعات بقاء لموتورنا. | `ml/rul_pronostia.py`، `ml/rul_pronostia_report.json`، `data/pronostia/README.md` |
| البيانات حقيقية؟ | نعم في Benchmarks العامة: CWRU عيّنة موتور حقيقي بعيوب مِصَنعة، وPRONOSTIA ست تجارب run-to-failure حقيقية لمحامل. لا، ليست من ريج المشروع. | `data/cwru/README.md`، `data/pronostia/README.md` |
| الداشبورد بيعمل إيه بالظبط؟ | عرض حالة مباشرة، قرار المشغّل، رسوم بيانية، روابط المعايرة والشرح، وكتم الإنذار. **مفيش** أزرار محاكاة ولا أوامر كتابة ولا تحكّم في الـ DAQ. | `public/index.html`، `tests/test_evaluation.py` |
| المعايرة اتمّت؟ | الإجراء موثّق وقابل للتشغيل على الراسبري فقط؛ نتيجة موقّعة/سجل تشغيل فعلي غير متوفر. لا يُقال «PASS». | `docs/CALIBRATION_RUNBOOK.md`، `edge/calibrate.py` |
| فيه توفير CPU/تكلفة مقاس؟ | لا. سُحب ادعاء توفير الموارد. المقاس فقط زمن الاستدلال: 26.19 ms على الجهاز و29.99 ms على الراسبري للنافذة الواحدة. | `docs/PI_DEPLOYMENT_EVIDENCE.md` |
| إيه المطلوب للخطوة الجاية؟ | `[NEED: run-to-failure series with timestamps and failure labels from our rig]`، `[NEED: measured degradation curve]`، `[NEED: real operator failure threshold]`. | `README.md`، `ml/ai_report.md` §11 |

**الجملة الآمنة للمعرض:**
> «النظام يكتشف ويصنّف الحالة الآن ويقترح إجراءً؛ التنبؤ بالبقاء شغال كـ benchmark على محامل حقيقية عامة، ومحتاج بيانات run-to-failure من موتورنا قبل أي ادعاء ميداني.»

## 2) تسلسل العرض (Demo) — 5 دقائق

1. **الداشبورد المباشر:** افتح `https://castpone2026.web.app/` → بيّن الحالةLive،
   قرار المشغّل، الرسوم، ورابط الشرح. لا تضغط أي أداة محاكاة (غير موجودة أصلاً).
2. **الشرح بالشرائح:** افتح `https://castpone2026.web.app/guide.html` → شريحة
   البنية ثم شريحة الأسئلة. اقرأ إجابة RUL كما هي: benchmark عام، مش موتورنا.
3. **الراسبري (قراءة فقط):** `systemctl status pdm-daq.service pdm-cloud.service
   pdm-dashboard.service` → الثلاثة active. لا تعدّل الكود أو الكاليبريشن وقت العرض.
4. **القراءة الخام:** اعرض نموذج CSV مسجّل من `edge/raw_measuree.py` فيه قيم
   ADXL الخام وكلمة MAX6675 وRMS الصوت. إن أردت تشغيله حياً، أوقف `pdm-daq`
   مؤقتاً ثم أعد تشغيله؛ لا تكتب `cal.json`.
5. **الـ RUL الحقيقي على benchmark:** افتح `ml/rul_pronostia_report.json` وبيّن
   الأرقام والـ label `not our motor, not field-validated`. لإعادة الإنتاج:
   `python3 ml/rul_pronostia.py --report /tmp/rul_pronostia_report.json`
   (نحو 41 ثانية على جهاز المراجعة).
6. **الاختبارات:** `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest
   discover -s tests` → العدد النهائي و`OK` يُذكر في تقرير التسليم، لا يُختلق.

## 3) فهرس الأدلة

| what | where |
|---|---|
| تشخيص 4 فئات + بوابة | `ml/rf_predictor.py`، `edge/edge_daq.py`، `ml/ai_report.md` |
| 100% صناعي فقط | `ml/ai_report.md` §5، `tests/test_evaluation.py` |
| Firebase/الداشبورد | `docs/FIREBASE_SETUP.md`، `docs/PI_DEPLOYMENT_EVIDENCE.md` |
| RUL على C-MAPSS (محاكاة) | `data/cmapss/`، `ml/train_rul_cmapss.py`، `tests/test_rul_cmapss.py` |
| RUL على محامل حقيقية | `data/pronostia/`، `ml/rul_pronostia.py`، `tests/test_rul_pronostia.py` |
| موتور حقيقي بعيوب مِصَنعة | `data/cwru/`، `tests/test_cwru_data.py` |
| سجل الردود على G12 | `docs/G12_REQUEST_RESPONSE_REGISTER.md` |
| حزمة العرض دي | `docs/EXHIBITION_REVIEW_PACK.md` |
| شريحة الويب | `https://castpone2026.web.app/guide.html` |

## 4) أسئلة شائعة بالمعرض

**س: طالما الـ RUL شغال، هل الموتور هيشتغل كذا ساعة؟**
لا. الرقم محسوب على محامل PRONOSTIA بموتور 250 W وجيربوكس، وموعّف بآخر قراءة
اهتزاز قبل حد الـ 20 g. لا علاقة له بموتورنا ولا بحساساتنا. `[NEED: run-to-failure
series with timestamps and failure labels from our rig]`.

**س: ليه all-window RMSE كبير (9557 ثانية) والـ last-window صغير (335)؟**
لأن التنبؤ المبكر بالعمر الكامل أصعب بكثير من تقدير القرب من نهاية التجربة.
نعرض الرقمين معاً ولا ننتقي الأفضل فقط. الـ baseline الثابت كان 8902 ثانية على
آخر نافذة، فالنموذج أفضل منه بوضوح عند نهاية العمر.

**س: data حقيقية يعني من موتورنا؟**
لا. «حقيقي» هنا يعني مقيس في تجارب منشورة وموثّقة، لا مولّدة. مصدرها CWRU أو
PRONOSTIA/FEMTO-ST، وكلٌّ له ريج وظروف مختلفة عن ريجنا.

**س: الرخصة واضحة؟**
نسخة figshare معلنة CC BY 4.0 (DOI `10.6084/m9.figshare.30595484.v1`)، لكن صفحات
FEMTO-ST/NASA لا تذكر رخصة صريحة: `[NEED: explicit FEMTO-ST dataset licence]`.
لا ندّعي رخصة غير موجودة.

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
- `[NEED: measured degradation curve]`
- `[NEED: real operator failure threshold]`
- `[NEED: signed calibration run record]`
- `[NEED: explicit FEMTO-ST dataset licence]`
- `[NEED: auth decision]` — قواعد RTDB الحالية public read/write ولم يتغير شيء.
