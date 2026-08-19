(() => {
  const form = document.getElementById('evaluationForm');
  if (!form) return;

  const storageKey = form.dataset.storageKey;
  const radios = [...form.querySelectorAll('input[type="radio"]')];
  const groups = [...new Set(radios.map(radio => radio.name))];
  const countEl = document.getElementById('answeredCount');
  const missingEl = document.getElementById('missingMessage');
  const confirmEl = document.getElementById('confirmFinal');
  const submitEl = document.getElementById('submitButton');

  function selectedAnswers() {
    const data = {};
    groups.forEach(name => {
      const checked = form.querySelector(`input[name="${name}"]:checked`);
      if (checked) data[name] = checked.value;
    });
    return data;
  }

  function update() {
    const data = selectedAnswers();
    const answered = Object.keys(data).length;
    const remaining = groups.length - answered;
    const complete = remaining === 0;

    countEl.textContent = String(answered);
    missingEl.classList.toggle('complete', complete);
    missingEl.textContent = complete
      ? 'Alle Aussagen sind beantwortet. Prüfe jetzt deine Auswahl.'
      : `Noch ${remaining} ${remaining === 1 ? 'Aussage' : 'Aussagen'} offen.`;

    submitEl.disabled = !(complete && confirmEl.checked);
    localStorage.setItem(storageKey, JSON.stringify(data));
  }

  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) || '{}');
    Object.entries(saved).forEach(([name, value]) => {
      const input = form.querySelector(`input[name="${name}"][value="${value}"]`);
      if (input) input.checked = true;
    });
  } catch (_) {
    localStorage.removeItem(storageKey);
  }

  radios.forEach(radio => radio.addEventListener('change', update));
  confirmEl.addEventListener('change', update);

  form.addEventListener('submit', event => {
    const unanswered = groups.find(name => !form.querySelector(`input[name="${name}"]:checked`));
    if (unanswered || !confirmEl.checked) {
      event.preventDefault();
      if (unanswered) {
        document.getElementById(`card-${unanswered}`)?.scrollIntoView({behavior: 'smooth', block: 'center'});
      } else {
        confirmEl.focus();
      }
      return;
    }
    if (!window.confirm('Jetzt verbindlich absenden? Danach kannst du die Antworten nicht selbst erneut ändern.')) {
      event.preventDefault();
      return;
    }
    submitEl.disabled = true;
    submitEl.textContent = 'Wird gespeichert …';
  });

  update();
})();
