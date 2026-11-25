// Навигация по вкладкам
document.querySelectorAll('.tab').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach((b) => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach((p) => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
  });
});

// Форматирование байтов
function formatBytes(bytes) {
  if (bytes === 0) return '0 Б';
  const k = 1024;
  const sizes = ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
}

// Загрузка системных метрик
async function fetchSystem() {
  try {
    const res = await fetch('/api/system');
    const data = await res.json();

    document.getElementById('sys-meta').textContent = `${data.hostname} · ${data.os} (${data.arch}) · IP: ${data.local_ip}`;
    document.getElementById('uptime-badge').textContent = `Аптайм: ${data.uptime}`;

    document.getElementById('cpu-pct').textContent = `${data.cpu.percent}%`;
    document.getElementById('cpu-bar').style.width = `${data.cpu.percent}%`;
    const freq = data.cpu.freq_mhz ? ` · ${data.cpu.freq_mhz} МГц` : '';
    document.getElementById('cpu-sub').textContent = `Ядра: ${data.cpu.cores_physical || '?'} физ / ${data.cpu.cores_logical || '?'} лог${freq}`;

    document.getElementById('ram-pct').textContent = `${data.memory.percent}%`;
    document.getElementById('ram-bar').style.width = `${data.memory.percent}%`;
    document.getElementById('ram-sub').textContent = `${data.memory.used_gb} / ${data.memory.total_gb} ГБ (свободно ${data.memory.available_gb} ГБ)`;

    document.getElementById('disk-pct').textContent = `${data.disk.percent}%`;
    document.getElementById('disk-bar').style.width = `${data.disk.percent}%`;
    document.getElementById('disk-sub').textContent = `${data.disk.used_gb} / ${data.disk.total_gb} ГБ (свободно ${data.disk.free_gb} ГБ)`;

    if (data.battery) {
      const plugged = data.battery.power_plugged ? '⚡ От сети' : '🔋 От батареи';
      document.getElementById('bat-pct').textContent = `${data.battery.percent}%`;
      document.getElementById('bat-sub').textContent = plugged;
    } else {
      document.getElementById('bat-pct').textContent = 'От сети';
      document.getElementById('bat-sub').textContent = 'Датчик батареи не обнаружен';
    }
    document.getElementById('net-sub').textContent = `Сеть: ↑ ${data.network.sent_mb} МБ / ↓ ${data.network.recv_mb} МБ`;
  } catch (e) {
    console.error(e);
  }
}

// Загрузка процессов
async function fetchProcesses() {
  const q = document.getElementById('proc-search').value || '';
  try {
    const res = await fetch(`/api/processes?limit=15&q=${encodeURIComponent(q)}`);
    const list = await res.json();
    const tbody = document.getElementById('proc-body');
    if (!list.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="muted">Процессы не найдены</td></tr>';
      return;
    }
    tbody.innerHTML = list
      .map(
        (p) => `
      <tr>
        <td>${p.pid}</td>
        <td><strong>${p.name}</strong></td>
        <td>${p.cpu}%</td>
        <td>${p.memory}%</td>
        <td class="muted">${p.status}</td>
      </tr>`
      )
      .join('');
  } catch (e) {
    console.error(e);
  }
}

document.getElementById('proc-search').addEventListener('input', fetchProcesses);

// Сканер диска
document.getElementById('btn-scan').addEventListener('click', async () => {
  const path = document.getElementById('scan-path').value.trim() || '~';
  const statusEl = document.getElementById('scan-status');
  const resultsEl = document.getElementById('scan-results');
  statusEl.textContent = 'Сканирование...';
  resultsEl.innerHTML = '';

  try {
    const res = await fetch('/api/disk-scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, limit: 15 }),
    });
    const data = await res.json();
    if (!res.ok) {
      statusEl.textContent = data.detail || 'Ошибка сканирования';
      return;
    }
    statusEl.textContent = `Папка: ${data.path} (топ-${data.items.length} по размеру)`;
    resultsEl.innerHTML = data.items
      .map(
        (item) => `
      <div class="scan-item">
        <span>${item.type === 'dir' ? '📁' : '📄'} ${item.name}</span>
        <strong>${formatBytes(item.size_bytes)}</strong>
      </div>`
      )
      .join('');
  } catch (e) {
    statusEl.textContent = 'Ошибка соединения с сервером';
  }
});

// Pomodoro-таймер
let timerSeconds = 25 * 60;
let timerInterval = null;

function renderTimer() {
  const m = String(Math.floor(timerSeconds / 60)).padStart(2, '0');
  const s = String(timerSeconds % 60).padStart(2, '0');
  document.getElementById('timer-display').textContent = `${m}:${s}`;
}

document.querySelectorAll('.timer-modes .btn-sm').forEach((btn) => {
  btn.addEventListener('click', () => {
    clearInterval(timerInterval);
    timerInterval = null;
    document.getElementById('timer-toggle').textContent = 'Старт';
    document.querySelectorAll('.timer-modes .btn-sm').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    timerSeconds = Number(btn.dataset.mins) * 60;
    renderTimer();
  });
});

document.getElementById('timer-toggle').addEventListener('click', () => {
  const toggleBtn = document.getElementById('timer-toggle');
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
    toggleBtn.textContent = 'Старт';
  } else {
    toggleBtn.textContent = 'Пауза';
    timerInterval = setInterval(() => {
      if (timerSeconds > 0) {
        timerSeconds -= 1;
        renderTimer();
      } else {
        clearInterval(timerInterval);
        timerInterval = null;
        toggleBtn.textContent = 'Старт';
        alert('⏰ Время вышло!');
      }
    }, 1000);
  }
});

document.getElementById('timer-reset').addEventListener('click', () => {
  clearInterval(timerInterval);
  timerInterval = null;
  document.getElementById('timer-toggle').textContent = 'Старт';
  const activeMode = document.querySelector('.timer-modes .btn-sm.active');
  timerSeconds = Number(activeMode ? activeMode.dataset.mins : 25) * 60;
  renderTimer();
});

// Задачи и заметки
let state = { tasks: [], notes: [{ text: '' }] };

async function loadNotes() {
  try {
    const res = await fetch('/api/notes');
    const data = await res.json();
    state.tasks = data.tasks || [];
    state.notes = data.notes && data.notes.length ? data.notes : [{ text: '' }];
    document.getElementById('quick-note').value = state.notes[0].text || '';
    renderTasks();
  } catch (e) {
    console.error(e);
  }
}

async function saveNotes() {
  document.getElementById('note-saved').textContent = 'Сохранение...';
  try {
    await fetch('/api/notes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(state),
    });
    document.getElementById('note-saved').textContent = 'Сохранено локально';
  } catch (e) {
    document.getElementById('note-saved').textContent = 'Ошибка сохранения';
  }
}

function renderTasks() {
  const ul = document.getElementById('task-list');
  ul.innerHTML = state.tasks
    .map(
      (t, idx) => `
    <li class="task-item ${t.done ? 'done' : ''}">
      <label style="display:flex;gap:8px;align-items:center;cursor:pointer;flex:1;">
        <input type="checkbox" ${t.done ? 'checked' : ''} onchange="toggleTask(${idx})" />
        <span>${t.text}</span>
      </label>
      <button onclick="deleteTask(${idx})">✕</button>
    </li>`
    )
    .join('');
}

window.toggleTask = (idx) => {
  state.tasks[idx].done = !state.tasks[idx].done;
  renderTasks();
  saveNotes();
};

window.deleteTask = (idx) => {
  state.tasks.splice(idx, 1);
  renderTasks();
  saveNotes();
};

document.getElementById('btn-add-task').addEventListener('click', () => {
  const input = document.getElementById('task-input');
  const text = input.value.trim();
  if (!text) return;
  state.tasks.unshift({ text, done: false });
  input.value = '';
  renderTasks();
  saveNotes();
});

let noteTimeout;
document.getElementById('quick-note').addEventListener('input', (e) => {
  state.notes[0] = { text: e.target.value };
  clearTimeout(noteTimeout);
  noteTimeout = setTimeout(saveNotes, 400);
});

// Генератор паролей
function generatePassword(len = 16) {
  const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*_-+=';
  let out = '';
  const arr = new Uint32Array(len);
  crypto.getRandomValues(arr);
  for (let i = 0; i < len; i++) {
    out += chars[arr[i] % chars.length];
  }
  return out;
}

const pwLen = document.getElementById('pw-len');
const pwOut = document.getElementById('pw-output');
function updatePw() {
  document.getElementById('pw-len-val').textContent = pwLen.value;
  pwOut.value = generatePassword(Number(pwLen.value));
}
pwLen.addEventListener('input', updatePw);
document.getElementById('btn-gen-pw').addEventListener('click', updatePw);
document.getElementById('btn-copy-pw').addEventListener('click', () => {
  navigator.clipboard.writeText(pwOut.value);
  document.getElementById('btn-copy-pw').textContent = 'Скопировано!';
  setTimeout(() => (document.getElementById('btn-copy-pw').textContent = 'Копировать'), 1200);
});

// Конвертер объёма данных
function updateBytesConv() {
  const val = parseFloat(document.getElementById('bytes-val').value) || 0;
  const unit = document.getElementById('bytes-unit').value;
  const mult = { B: 1, KB: 1024, MB: 1024 ** 2, GB: 1024 ** 3, TB: 1024 ** 4 };
  const bytes = val * mult[unit];
  document.getElementById('bytes-results').innerHTML = `
    <div>Байты: <strong>${bytes.toLocaleString('ru-RU')} Б</strong></div>
    <div>Килобайты: <strong>${(bytes / 1024).toFixed(2)} КБ</strong></div>
    <div>Мегабайты: <strong>${(bytes / 1024 ** 2).toFixed(4)} МБ</strong></div>
    <div>Гигабайты: <strong>${(bytes / 1024 ** 3).toFixed(6)} ГБ</strong></div>
    <div>Терабайты: <strong>${(bytes / 1024 ** 4).toFixed(8)} ТБ</strong></div>
  `;
}
document.getElementById('bytes-val').addEventListener('input', updateBytesConv);
document.getElementById('bytes-unit').addEventListener('change', updateBytesConv);

// Инициализация
updatePw();
updateBytesConv();
loadNotes();
fetchSystem();
fetchProcesses();
setInterval(fetchSystem, 2500);
setInterval(fetchProcesses, 5000);
