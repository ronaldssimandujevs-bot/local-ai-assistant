const chatEl = document.getElementById('chat');
const formEl = document.getElementById('chat-form');
const inputEl = document.getElementById('message');
const voiceButtonEl = document.getElementById('voice-button');
const allowCodeEl = document.getElementById('allow-code');
const allowShellEl = document.getElementById('allow-shell');
const allowSelfUpdateEl = document.getElementById('allow-self-update');

let recognition;

function addMessage(sender, text) {
  const message = document.createElement('div');
  message.className = `message ${sender}`;
  message.textContent = text;
  chatEl.appendChild(message);
  chatEl.scrollTop = chatEl.scrollHeight;
}

async function sendMessage(text) {
  addMessage('user', text);

  const payload = {
    message: text,
    allow_code_changes: allowCodeEl.checked,
    allow_shell: allowShellEl.checked,
    approved_self_update: allowSelfUpdateEl.checked,
    self_update_files: []
  };

  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  const data = await response.json();
  addMessage('assistant', data.response);

  if (data.actions && data.actions.length) {
    const actionList = data.actions.map((action) => JSON.stringify(action)).join('\n');
    addMessage('system', `Actions:\n${actionList}`);
  }
}

formEl.addEventListener('submit', async (event) => {
  event.preventDefault();
  const value = inputEl.value.trim();
  if (!value) return;
  inputEl.value = '';
  await sendMessage(value);
});

if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
  const SpeechRecognitionClass = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognitionClass();
  recognition.lang = 'en-US';
  recognition.interimResults = false;
  recognition.continuous = false;

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    inputEl.value = transcript;
    sendMessage(transcript);
  };

  recognition.onerror = () => {
    addMessage('assistant', 'I could not hear the microphone properly.');
  };

  voiceButtonEl.addEventListener('click', () => {
    recognition.start();
    addMessage('assistant', 'Listening...');
  });
} else {
  voiceButtonEl.textContent = 'Voice unavailable';
  voiceButtonEl.disabled = true;
}

addMessage('assistant', 'Welcome. I run locally on your computer and can help with voice, search, file work, and explicit self-updates.');
