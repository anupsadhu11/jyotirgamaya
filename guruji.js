const gurujiForm = document.getElementById('guruji-form');
const gurujiInput = document.getElementById('guruji-input');
const gurujiMessages = document.getElementById('guruji-messages');
const gurujiSendBtn = document.getElementById('guruji-send-btn');

let gurujiHistory = [];

function appendGurujiMessage(role, text) {
  const wrapper = document.createElement('div');
  wrapper.className = `guruji-message guruji-message-${role === 'user' ? 'user' : 'bot'}`;

  const bubble = document.createElement('div');
  bubble.className = 'guruji-bubble';
  bubble.textContent = text;

  wrapper.appendChild(bubble);
  gurujiMessages.appendChild(wrapper);
  gurujiMessages.scrollTop = gurujiMessages.scrollHeight;
  return bubble;
}

function getCurrentReading() {
  const raw = sessionStorage.getItem('jyotirgamayaReading');
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch (error) {
    return null;
  }
}

async function askGuruji(message) {
  appendGurujiMessage('user', message);
  const historyBeforeThisTurn = gurujiHistory.slice();
  gurujiHistory.push({ role: 'user', content: message });

  gurujiInput.disabled = true;
  gurujiSendBtn.disabled = true;
  const replyBubble = appendGurujiMessage('bot', 'Guruji is reflecting...');
  replyBubble.classList.add('guruji-bubble-thinking');

  try {
    const response = await fetch('/api/guruji/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        history: historyBeforeThisTurn,
        reading: getCurrentReading()
      })
    });

    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(body.error || 'Guruji is unavailable right now.');
    }

    replyBubble.textContent = body.reply;
    replyBubble.classList.remove('guruji-bubble-thinking');
    gurujiHistory.push({ role: 'assistant', content: body.reply });
  } catch (error) {
    replyBubble.textContent = error.message;
    replyBubble.classList.remove('guruji-bubble-thinking');
    replyBubble.classList.add('guruji-bubble-error');
    gurujiHistory = historyBeforeThisTurn; // don't remember a turn that failed
  } finally {
    gurujiInput.disabled = false;
    gurujiSendBtn.disabled = false;
    gurujiInput.focus();
  }
}

gurujiForm.addEventListener('submit', (event) => {
  event.preventDefault();
  const message = gurujiInput.value.trim();
  if (!message) return;
  gurujiInput.value = '';
  askGuruji(message);
});
