/*
 * ============================================================================
   PDM RIG WIRING GUIDE — APP MODULE (EXPANDED EDITION)
   Complete interactive application logic: routing, rendering, gamification,
   drag-and-drop wiring, breadboard simulator, quizzes, confetti, persistence,
   troubleshooting, parts gallery, net summary, comfort-wiring rules, BOM.
   ============================================================================
*/

'use strict';

/* --------------------------------------------------------------------------
   Utilities
   -------------------------------------------------------------------------- */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
const on = (el, ev, fn) => el.addEventListener(ev, fn);
const html = (el, str) => { el.innerHTML = str; return el; };

function clsToggle(el, cls, force) {
  if (force === undefined) el.classList.toggle(cls);
  else if (force) el.classList.add(cls); else el.classList.remove(cls);
}

/* --------------------------------------------------------------------------
   State & Persistence
   -------------------------------------------------------------------------- */
const STORAGE_KEY = 'pdm_wiring_guide_v2';
const DEFAULT_STATE = {
  xp: 0,
  hearts: 3,
  streak: 0,
  lastStudy: null,
  completedLessons: {},
  completedLevels: {},
  wrongAnswers: 0,
  totalAnswers: 0,
  achievements: {},
  sound: true,
  wiresPlaced: {},
  simulatorActive: false,
  currentLevel: 1,
  currentLesson: null,
  simChecks: {}
};

let state = { ...DEFAULT_STATE };

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const p = JSON.parse(raw);
      state = {
        ...DEFAULT_STATE,
        ...p,
        completedLessons: p.completedLessons || {},
        completedLevels: p.completedLevels || {},
        achievements: p.achievements || {},
        wiresPlaced: p.wiresPlaced || {},
        simChecks: p.simChecks || {}
      };
    }
  } catch (e) { console.warn('load failed', e); }
}
function saveState() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch (e) {}
}

function addXP(n, reason = '') {
  state.xp += n;
  saveState();
  renderHeader();
  toast(`+${n} XP${reason ? ' — ' + reason : ''} ✨`);
  checkAchievements();
}

function addHeart(n = 1) {
  state.hearts = Math.min(3, state.hearts + n);
  saveState();
  renderHeader();
}
function loseHeart() {
  state.hearts = Math.max(0, state.hearts - 1);
  saveState();
  renderHeader();
  if (state.hearts === 0) {
    showModal('Out of hearts 💔', 'Take a break, then come back! Your progress is saved.');
  }
}

function todayKey() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}

function isLessonDone(id) { return !!state.completedLessons[id]; }
function isLevelDone(id) { return !!state.completedLevels[id]; }
function markLessonDone(levelId, lessonId, xp = 25) {
  if (isLessonDone(lessonId)) return;
  state.completedLessons[lessonId] = true;
  addXP(xp, lessonId);
  const level = CONTENT.LEVELS.find(l => l.id === levelId);
  const allLessonsDone = level.lessons.every(ln => isLessonDone(ln.id));
  if (allLessonsDone && !isLevelDone(levelId)) {
    state.completedLevels[levelId] = true;
    addXP(level.xp, `Level ${levelId} complete!`);
    state.currentLevel = Math.min(CONTENT.LEVELS.length, levelId + 1);
    showCelebration(`Level ${levelId} Complete! 🎉`, level.xp);
  }
  saveState();
  renderAll();
}

function checkAchievements() {
  const ach = CONTENT.ACHIEVEMENTS;
  const newly = [];
  ach.forEach(a => {
    if (state.achievements[a.id]) return;
    let earned = false;
    switch (a.id) {
      case 'first-wire': earned = Object.keys(state.completedLessons).length >= 1; break;
      case 'rails-master': earned = isLessonDone('l1-1') && isLessonDone('l1-2'); break;
      case 'i2c-detective': earned = isLessonDone('l2-1'); break;
      case 'spi-sleuth': earned = isLessonDone('l3-1'); break;
      case 'i2s-listener': earned = isLessonDone('l4-1'); break;
      case 'thermo-pro': earned = isLessonDone('l3-2'); break;
      case 'rig-complete': earned = CONTENT.LEVELS.every(l => isLevelDone(l.id)); break;
      case 'perfect-score': earned = state.totalAnswers > 0 && state.wrongAnswers === 0; break;
      case 'streak-3': earned = state.streak >= 3; break;
      case 'comfort-wiring': earned = Object.keys(state.completedLessons).length >= 5; break;
    }
    if (earned) {
      state.achievements[a.id] = true;
      addXP(a.xp, `Achievement: ${a.name}`);
      newly.push(a);
    }
  });
  if (newly.length) showAchievementsToast(newly);
  saveState();
}

/* --------------------------------------------------------------------------
   Rendering — Header / Dashboard
   -------------------------------------------------------------------------- */
function renderHeader() {
  $('#stat-hearts').textContent = '❤'.repeat(state.hearts);
  $('#stat-xp').textContent = state.xp;
  $('#stat-streak').textContent = state.streak;
}

function renderDashboard() {
  const levels = CONTENT.LEVELS;
  const steps = $$('.path-step');
  steps.forEach((step, i) => {
    const lvl = levels[i];
    const done = isLevelDone(lvl.id);
    const current = !done && i === (state.currentLevel - 1);
    step.classList.toggle('done', done);
    step.classList.toggle('current', current);
    const node = step.querySelector('.node');
    if (done) {
      node.classList.add('done');
      node.querySelector('.badge-done').textContent = '✓';
    } else {
      node.classList.remove('done');
    }
    if (!done) {
      step.style.cursor = 'pointer';
      step.onclick = () => {
        if (i === 0 || isLevelDone(levels[i-1].id)) {
          showLevel(lvl.id);
        } else {
          toast('Finish the previous level first 💖');
        }
      };
    }
  });
}

function renderAll() {
  renderHeader();
  renderDashboard();
}

/* --------------------------------------------------------------------------
   Toast & Notifications
   -------------------------------------------------------------------------- */
function toast(msg, ms = 2600) {
  const el = document.createElement('div');
  el.className = 'toast';
  el.innerHTML = `<span class="em">✨</span><div><b>${msg}</b></div>`;
  $('#toast').appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 300); }, ms);
}

/* --------------------------------------------------------------------------
   Screen Router
   -------------------------------------------------------------------------- */
const SCREENS = {
  dashboard: '#screen-dashboard',
  level: '#screen-level',
  lesson: '#screen-lesson',
  simulator: '#screen-simulator',
  nets: '#screen-nets',
  troubleshooting: '#screen-troubleshooting',
  parts: '#screen-parts',
  comfort: '#screen-comfort',
  bom: '#screen-bom',
  celebration: '#screen-celebration'
};

function showScreen(name) {
  $$('.screen').forEach(s => s.classList.remove('active'));
  const target = $(SCREENS[name]);
  if (target) target.classList.add('active');
  if (name === 'dashboard') renderDashboard();
  else if (name === 'nets') renderNets();
  else if (name === 'troubleshooting') renderTroubleshooting();
  else if (name === 'parts') renderParts();
  else if (name === 'comfort') renderComfort();
  else if (name === 'bom') renderBOM();
}

/* --------------------------------------------------------------------------
   Level Screen
   -------------------------------------------------------------------------- */
function showLevel(levelId) {
  state.currentLevel = levelId;
  saveState();
  const level = CONTENT.LEVELS.find(l => l.id === levelId);
  if (!level) return;

  const t = level.theme;
  document.documentElement.style.setProperty('--uc', t.uc);
  document.documentElement.style.setProperty('--ucd', t.ucd);
  document.documentElement.style.setProperty('--ue', level.mascot);

  $('#lv-num').textContent = level.id;
  $('#lv-title').textContent = level.title;
  $('#lv-sub').textContent = level.subtitle;
  $('#lv-mascot').textContent = level.mascot;
  $('#lv-icon').textContent = level.icon;
  $('#lv-xp').textContent = level.xp;
  $('#lv-est').textContent = level.estimated;
  $('#lv-desc').textContent = level.description;

  const list = $('#lv-lessons');
  list.innerHTML = '';
  level.lessons.forEach(ln => {
    const done = isLessonDone(ln.id);
    const item = document.createElement('div');
    item.className = 'lesson-item' + (done ? ' done' : '');
    item.innerHTML = `
      <div class="li-mascot">${ln.emoji}</div>
      <div class="li-info">
        <div class="li-title">${ln.title}</div>
        <div class="li-goal">${ln.goal}</div>
      </div>
      <div class="li-status">${done ? '✓ Done' : 'Start'}</div>
    `;
    item.onclick = () => {
      const prev = getPrevLessonId(level, ln);
      if (!prev || isLessonDone(prev)) {
        showLesson(levelId, ln.id);
      } else {
        toast('Complete the previous lesson first 💖');
      }
    };
    list.appendChild(item);
  });

  const doneCount = level.lessons.filter(ln => isLessonDone(ln.id)).length;
  $('#lv-prog-text').textContent = `${doneCount} / ${level.lessons.length}`;
  $('#lv-prog-bar').style.width = `${(doneCount / level.lessons.length) * 100}%`;

  showScreen('level');
}

function getPrevLessonId(level, lesson) {
  const idx = level.lessons.findIndex(l => l.id === lesson.id);
  return idx > 0 ? level.lessons[idx - 1].id : null;
}

/* --------------------------------------------------------------------------
   Lesson Rendering
   -------------------------------------------------------------------------- */
function showLesson(levelId, lessonId) {
  state.currentLesson = lessonId;
  saveState();
  const level = CONTENT.LEVELS.find(l => l.id === levelId);
  const lesson = level.lessons.find(l => l.id === lessonId);
  if (!lesson) return;

  document.title = `${lesson.title} — ${CONTENT.meta.title}`;

  $('#les-mascot').textContent = lesson.emoji;
  $('#les-title').textContent = lesson.title;
  $('#les-goal').textContent = lesson.goal;
  $('#les-content').innerHTML = lesson.content;

  const tbl = $('#les-wires');
  tbl.innerHTML = '';
  lesson.wires.forEach((w, i) => {
    const ci = CONTENT.COLORS[w.net] || { hex: '#b2bec3', name: w.net, emoji: '⚪' };
    const tr = document.createElement('tr');
    tr.className = 'wire-row' + (state.wiresPlaced[`${lessonId}-${i}`] ? ' done' : '');
    tr.innerHTML = `
      <td><span class="pin">${w.from}</span></td>
      <td><span class="net" style="background:${ci.hex}22;color:${ci.hex};border-color:${ci.hex}">
        <span class="color-swatch" style="background:${ci.hex}"></span>${ci.emoji} ${w.net}
      </span></td>
      <td><span class="why">${w.to}</span></td>
      <td><span class="wire-color" style="color:${ci.hex}">${ci.hex}</span></td>
    `;
    tr.onclick = () => toggleWire(lessonId, i, tr);
    tbl.appendChild(tr);
  });

  $('#les-tips').innerHTML = `
    <div class="k"><span class="em">💡</span>Comfort Wiring</div>
    <p>${lesson.tips}</p>
  `;

  const cl = $('#les-checklist');
  cl.innerHTML = '';
  lesson.checklist.forEach((c, i) => {
    const item = document.createElement('div');
    item.className = 'check-item';
    item.innerHTML = `
      <input type="checkbox" id="chk-${lessonId}-${i}" ${isLessonDone(lessonId) ? 'checked' : ''}>
      <label for="chk-${lessonId}-${i}" class="txt">${c}</label>
      <span class="badge">${isLessonDone(lessonId) ? 'done' : 'todo'}</span>
    `;
    item.querySelector('input').onchange = (e) => {
      if (e.target.checked) markLessonDone(levelId, lessonId);
      else toast('Unchecking removes completion 💖');
    };
    cl.appendChild(item);
  });

  const qz = $('#les-quiz');
  qz.innerHTML = '';
  if (lesson.quiz && lesson.quiz.length) {
    lesson.quiz.forEach((q, qi) => {
      const qiEl = document.createElement('div');
      qiEl.className = 'quiz-item';
      qiEl.innerHTML = `
        <div class="q-question">Q${qi + 1}. ${q.q}</div>
        <div class="q-options">${q.options.map((o, oi) => `
          <button class="q-opt" onclick="answerQuiz('${lessonId}', ${qi}, '${o}', '${q.a}')">${o}</button>
        `).join('')}</div>
        <div class="q-hint" id="hint-${lessonId}-${qi}" style="display:none">${q.hint}</div>
      `;
      qz.appendChild(qiEl);
    });
  } else {
    qz.innerHTML = '<div class="quiz-none">No quiz for this lesson — hands-on wiring only!</div>';
  }

  const sim = $('#les-simulator');
  const simScen = CONTENT.SIMULATOR.levels[levelId];
  if (simScen) {
    sim.innerHTML = `
      <h4><span class="em">🧪</span>Simulator: ${simScen.name}</h4>
      <p>${simScen.successMsg}</p>
      <div class="sim-checks">${simScen.checks.map(c => `<span class="sim-chip sim-unchecked">⭕ ${c}</span>`).join('')}</div>
      <button class="btn primary wide" onclick="runSimulator(${levelId})">Run Simulation ✨</button>
    `;
  } else {
    sim.innerHTML = '<div class="sim-none">No simulator for this lesson.</div>';
  }

  showScreen('lesson');
}

function toggleWire(lessonId, wireIdx, trEl) {
  const key = `${lessonId}-${wireIdx}`;
  if (state.wiresPlaced[key]) {
    delete state.wiresPlaced[key];
    trEl.classList.remove('done');
    toast('Wire removed 🔧');
  } else {
    state.wiresPlaced[key] = true;
    trEl.classList.add('done');
    toast('Wire placed ✨');
    addXP(5, 'wire placed');
    const lesson = CONTENT.LEVELS.find(l => l.id === state.currentLevel).lessons.find(ln => ln.id === lessonId);
    const allPlaced = lesson.wires.every((_, i) => state.wiresPlaced[`${lessonId}-${i}`]);
    if (allPlaced) {
      toast('All wires placed! Complete the checklist to finish the lesson 🎉');
    }
  }
  saveState();
}

function answerQuiz(lessonId, qIdx, selected, correct) {
  const lesson = CONTENT.LEVELS.find(l => l.id === state.currentLevel).lessons.find(ln => ln.id === lessonId);
  const q = lesson.quiz[qIdx];
  const opts = $$('.q-opt');
  opts.forEach(o => {
    o.disabled = true;
    if (o.textContent === correct) o.classList.add('correct');
    if (o.textContent === selected && selected !== correct) o.classList.add('wrong');
  });

  state.totalAnswers++;
  if (selected === correct) {
    addXP(10, 'correct answer');
    toast('Correct! 💖');
  } else {
    state.wrongAnswers++;
    loseHeart();
    toast(`Not quite. The answer is: ${correct}`);
  }
  saveState();
  checkAchievements();
}

/* --------------------------------------------------------------------------
   Nets Summary Rendering
   -------------------------------------------------------------------------- */
function renderNets() {
  const container = $('#nets-content');
  container.innerHTML = `
    <h3 style="margin-bottom:16px;font-size:20px;font-weight:800;color:var(--ink)">🎨 Net Colour Reference</h3>
    <p style="color:var(--ink-soft);margin-bottom:18px">All 15 nets in the Fritzing sketch, with colours from design.py.</p>
    <table class="wire">
      <thead>
        <tr><th style="width:12%">Net</th><th style="width:10%">Colour</th><th style="width:24%">Name</th><th style="width:14%">Category</th><th style="width:40%">Description</th></tr>
      </thead>
      <tbody>
        ${CONTENT.NETS.map(n => `
          <tr>
            <td><span class="pin">${n.name}</span></td>
            <td><span class="net" style="background:${n.hex}22;color:${n.hex};border-color:${n.hex}">
              <span class="color-swatch" style="background:${n.hex}"></span>${n.hex}
            </span></td>
            <td>${n.name}</td>
            <td><span class="pill ${n.kind}">${n.kind}</span></td>
            <td>${n.desc}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
  showScreen('nets');
}

/* --------------------------------------------------------------------------
   Troubleshooting Rendering
   -------------------------------------------------------------------------- */
function renderTroubleshooting() {
  const container = $('#troubleshooting-content');
  container.innerHTML = `
    <h3 style="margin-bottom:16px;font-size:20px;font-weight:800;color:var(--ink)">🩺 Troubleshooting Guide</h3>
    <p style="color:var(--ink-soft);margin-bottom:18px">Common issues and how to fix them.</p>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px">
      ${CONTENT.TROUBLESHOOTING.map(t => `
        <div class="photo-card" style="padding:16px">
          <div style="font-weight:800;color:var(--rose-dark);margin-bottom:6px">${t.symptom}</div>
          <div style="font-size:13px;color:var(--ink-soft);margin-bottom:6px"><strong>Cause:</strong> ${t.cause}</div>
          <div style="font-size:13px;color:var(--green-dark);font-weight:700"><strong>Fix:</strong> ${t.fix}</div>
        </div>
      `).join('')}
    </div>
  `;
  showScreen('troubleshooting');
}

/* --------------------------------------------------------------------------
   Parts Gallery Rendering
   -------------------------------------------------------------------------- */
function renderParts() {
  const container = $('#parts-content');
  container.innerHTML = `
    <h3 style="margin-bottom:16px;font-size:20px;font-weight:800;color:var(--ink)">📦 Parts Catalog</h3>
    <p style="color:var(--ink-soft);margin-bottom:18px">Every part in the rig, with photos, Fritzing artwork, and specs.</p>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:20px">
      ${Object.values(CONTENT.PARTS).map(p => `
        <div class="photo-card">
          <div class="photo-media">
            <img src="${p.photo}" alt="${p.name}" onerror="this.style.display='none';this.parentElement.querySelector('.photo-fallback').style.display='flex'">
            <div class="photo-fallback"><div class="em">${p.emoji}</div>${p.name}</div>
          </div>
          <div class="photo-cap">${p.emoji} ${p.name}</div>
          <div class="photo-desc">${p.description}</div>
          <div style="padding:0 18px 10px;font-size:12.5px;color:var(--muted)">
            <div style="font-weight:800;color:var(--ink-soft);margin-bottom:4px">Specs:</div>
            ${(p.specs ? Object.entries(p.specs).map(([k,v]) => `<div style="font-size:12px">${k}: ${v}</div>`).join('') : '')}
            ${p.tips ? `<div style="margin-top:8px"><strong>Tip:</strong> ${p.tips}</div>` : ''}
          </div>
        </div>
      `).join('')}
    </div>
  `;
  showScreen('parts');
}

/* --------------------------------------------------------------------------
   Comfort Wiring Rules Rendering
   -------------------------------------------------------------------------- */
function renderComfort() {
  const container = $('#comfort-content');
  container.innerHTML = `
    <h3 style="margin-bottom:16px;font-size:20px;font-weight:800;color:var(--ink)">🎨 Comfort-Wiring Rules</h3>
    <p style="color:var(--ink-soft);margin-bottom:18px">Rules baked into the .fzz file and verified by the geometric auditor (0 problems).</p>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px">
      ${CONTENT.COMFORT_RULES.map(r => `
        <div class="love-note ${r.id === 'c7' ? 'violet' : (r.id === 'c6' ? 'amber' : 'rose')}" style="padding:16px">
          <div class="k"><span class="em">${r.icon}</span>${r.title}</div>
          <p>${r.desc}</p>
        </div>
      `).join('')}
    </div>
  `;
  showScreen('comfort');
}

/* --------------------------------------------------------------------------
   BOM Rendering
   -------------------------------------------------------------------------- */
function renderBOM() {
  const b = CONTENT.BOM;
  $('#bom-ceiling').textContent = b.ceiling.toLocaleString();
  $('#bom-planned').textContent = b.planned.toLocaleString();
  $('#bom-headroom').textContent = b.headroom.toFixed(2);
  $('#bom-quotes').textContent = b.realQuotes.toLocaleString();
  $('#bom-fan').textContent = b.fanGlandsShrink.toLocaleString();
  $('#bom-allowance').textContent = b.max6675Allowance.toLocaleString();
  $('#bom-maxquote').textContent = b.max6675MaxQuote.toFixed(2);
  $('#bom-note').textContent = b.note;
  showScreen('bom');
}

/* --------------------------------------------------------------------------
   Simulator
   -------------------------------------------------------------------------- */
function runSimulator(levelId) {
  const level = CONTENT.LEVELS.find(l => l.id === levelId);
  const scen = CONTENT.SIMULATOR.levels[levelId];
  if (!scen) return;

  state.simulatorActive = true;
  saveState();

  const container = $('#sim-content');
  container.innerHTML = `
    <div class="sim-header">
      <div class="sim-title">${scen.name}</div>
      <div class="sim-status" id="sim-status">Initializing...</div>
    </div>
    <div class="sim-visual" id="sim-visual">
      <div class="sim-board">
        <div class="sim-part sim-pi" id="sim-pi">🍓 Pi 4</div>
        <div class="sim-part sim-adxl" id="sim-adxl">📳 ADXL345</div>
        <div class="sim-part sim-max" id="sim-max">🌡️ MAX6675</div>
        <div class="sim-part sim-mic" id="sim-mic">🎤 INMP441</div>
        <div class="sim-part sim-led" id="sim-led">💡 LED</div>
        <div class="sim-part sim-fan" id="sim-fan">🌀 Fan</div>
      </div>
      <div class="sim-readings" id="sim-readings">
        <div class="reading"><span class="r-label">Vibration</span><span class="r-value" id="r-vib">--</span> g</div>
        <div class="reading"><span class="r-label">Temperature</span><span class="r-value" id="r-temp">--</span> °C</div>
        <div class="reading"><span class="r-label">Sound</span><span class="r-value" id="r-sound">--</span> dB</div>
        <div class="reading"><span class="r-label">Status</span><span class="r-value" id="r-status">--</span></div>
      </div>
    </div>
    <div class="sim-checks" style="margin-top:14px">
      ${scen.checks.map(c => `<span class="sim-chip sim-unchecked">⭕ ${c}</span>`).join('')}
    </div>
    <div class="sim-controls" style="margin-top:18px">
      <button class="btn rose wide" onclick="stopSimulator()">Stop Simulation</button>
    </div>
  `;

  showScreen('simulator');

  const checksContainer = container.querySelector('.sim-checks');
  let checkIdx = 0;
  const interval = setInterval(() => {
    if (checkIdx >= scen.checks.length) {
      clearInterval(interval);
      $('#sim-status').textContent = scen.successMsg;
      $('#sim-status').className = 'sim-status sim-success';
      addXP(20, 'simulator completed');
      toast('Simulation passed! ✨');
      state.simulatorActive = false;
      saveState();
      return;
    }
    const chip = checksContainer.children[checkIdx];
    chip.classList.remove('sim-unchecked');
    chip.classList.add('sim-checked');
    chip.textContent = `✅ ${scen.checks[checkIdx]}`;

    const readings = {
      1: { vib: '0.02', temp: '24.5', sound: '32', status: 'Idle' },
      2: { vib: '0.15', temp: '25.1', sound: '35', status: 'Vibration detected' },
      3: { vib: '0.45', temp: '68.3', sound: '41', status: 'HOT — fan ON' },
      4: { vib: '0.10', temp: '45.0', sound: '52', status: 'Noise anomaly' },
      5: { vib: '0.08', temp: '41.2', sound: '38', status: 'All systems OK' }
    };
    const r = readings[levelId] || readings[1];
    $('#r-vib').textContent = r.vib;
    $('#r-temp').textContent = r.temp;
    $('#r-sound').textContent = r.sound;
    $('#r-status').textContent = r.status;

    const partMap = { 1: 'sim-pi', 2: 'sim-adxl', 3: 'sim-max', 4: 'sim-mic', 5: 'sim-led' };
    const p = document.getElementById(partMap[levelId]);
    if (p) {
      p.classList.add('sim-active');
      setTimeout(() => p.classList.remove('sim-active'), 600);
    }

    checkIdx++;
  }, 900);

  state.simInterval = interval;
}

function stopSimulator() {
  if (state.simInterval) clearInterval(state.simInterval);
  state.simulatorActive = false;
  saveState();
  showScreen('lesson');
}

/* --------------------------------------------------------------------------
   Celebration & Achievements
   -------------------------------------------------------------------------- */
function showCelebration(msg, xp) {
  $('#celebrate-title').textContent = msg;
  $('#celebrate-xp-text').textContent = `+${xp} XP`;
  $('#celebrate').classList.add('active');
  confetti();
}

function closeCelebration() {
  $('#celebrate').classList.remove('active');
  showScreen('dashboard');
}

function showAchievementsToast(list) {
  const html = list.map(a => `<span class="pill ${a.icon.includes('🔥')?'amber':(a.icon.includes('💯')?'violet':'green'))}">${a.icon} ${a.name}</span>`).join(' ');
  toast(`Achievement unlocked! ${html}`, 4000);
}

function showAchievementsModal() {
  const title = $('#modal-title');
  const body = $('#modal-body');
  title.textContent = '🏆 Achievements';
  const achs = CONTENT.ACHIEVEMENTS;
  const html = achs.map(a => {
    const done = state.achievements[a.id];
    return `
      <div style="display:flex;align-items:center;gap:12px;padding:12px 0;border-bottom:1px solid #F0F3F7">
        <span style="font-size:24px">${a.icon}</span>
        <div style="flex:1">
          <div style="font-weight:800;color:var(--ink)">${a.name}</div>
          <div style="font-size:12px;color:var(--muted)">${a.desc} <span style="color:var(--green-dark)">+${a.xp} XP</span></div>
        </div>
        <span style="font-weight:800;color:${done ? 'var(--green-dark)' : 'var(--muted)'}">${done ? '✓ Unlocked' : '🔒 Locked'}</span>
      </div>
    `;
  }).join('');
  body.innerHTML = `<div style="text-align:left">${html}</div>`;
  $('#modal').classList.remove('hidden');
  $('#modal').classList.add('active');
}

/* --------------------------------------------------------------------------
   Confetti
   -------------------------------------------------------------------------- */
function confetti() {
  const canvas = $('#fx');
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  const parts = [];
  for (let i = 0; i < 120; i++) {
    parts.push({
      x: Math.random() * W, y: Math.random() * H - 100,
      vx: (Math.random() - 0.5) * 8, vy: Math.random() * 6 + 2,
      size: Math.random() * 8 + 4,
      color: `hsl(${Math.random() * 60 + 300}, 100%, 70%)`
    });
  }
  let t = 0;
  function frame() {
    ctx.clearRect(0, 0, W, H);
    t++;
    parts.forEach(p => {
      p.x += p.vx; p.y += p.vy; p.vy += 0.15;
      ctx.fillStyle = p.color;
      ctx.beginPath(); ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2); ctx.fill();
    });
    if (t < 160) requestAnimationFrame(frame);
    else ctx.clearRect(0, 0, W, H);
  }
  requestAnimationFrame(frame);
}

/* --------------------------------------------------------------------------
   Modal
   -------------------------------------------------------------------------- */
function showModal(title, body) {
  $('#modal-title').textContent = title;
  $('#modal-body').textContent = body;
  $('#modal').classList.add('active');
}
function closeModal() {
  $('#modal').classList.add('hidden');
  setTimeout(() => $('#modal').classList.remove('active'), 300);
}

/* --------------------------------------------------------------------------
   Global handlers
   -------------------------------------------------------------------------- */
window.answerQuiz = answerQuiz;
window.runSimulator = runSimulator;
window.stopSimulator = stopSimulator;
window.toggleWire = toggleWire;
window.showLevel = showLevel;
window.closeCelebration = closeCelebration;
window.closeModal = closeModal;
window.markLessonComplete = markLessonComplete;
window.showAchievementsModal = showAchievementsModal;

/* --------------------------------------------------------------------------
   Init
   -------------------------------------------------------------------------- */
function init() {
  loadState();
  renderHeader();
  renderDashboard();

  $('#btn-dashboard').onclick = () => showScreen('dashboard');
  $('#btn-back-dash').onclick = () => showScreen('dashboard');
  $('#btn-celebrate-dash').onclick = closeCelebration;
  $('#btn-modal-ok').onclick = closeModal;

  $('#modal').onclick = (e) => { if (e.target === $('#modal')) closeModal(); };

  setTimeout(() => toast('Welcome to the Robot-Doctor Rig wiring guide! 🩺', 3000), 800);
}

document.addEventListener('DOMContentLoaded', init);
