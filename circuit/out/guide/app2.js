/* ============================================================================
   APP MODULE — PART 2 (additional handlers)
   markLessonComplete, achievements modal, simulation check wiring
   ============================================================================ */

/* --------------------------------------------------------------------------
   Mark lesson complete
   -------------------------------------------------------------------------- */
function markLessonComplete() {
  const lid = state.currentLevel;
  const lessonId = state.currentLesson;
  if (!lid || !lessonId) { toast('No lesson selected 💖'); return; }
  const level = CONTENT.LEVELS.find(l => l.id === lid);
  const lesson = level.lessons.find(ln => ln.id === lessonId);

  // Check all checklist items are checked
  const allChecked = lesson.checklist.every((_, i) => {
    const cb = document.getElementById(`chk-${lessonId}-${i}`);
    return cb && cb.checked;
  });
  if (!allChecked) {
    toast('Please check off all checklist items first ✔️');
    return;
  }

  markLessonDone(lid, lessonId);
  showScreen('level');
}

window.markLessonComplete = markLessonComplete;

/* --------------------------------------------------------------------------
   Achievements modal
   -------------------------------------------------------------------------- */
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
window.showAchievementsModal = showAchievementsModal;

/* --------------------------------------------------------------------------
   Wire up all missing global references
   -------------------------------------------------------------------------- */
// Already exposed in app.js part 1:
// showLevel, closeCelebration, closeModal, answerQuiz, runSimulator, stopSimulator, toggleWire
