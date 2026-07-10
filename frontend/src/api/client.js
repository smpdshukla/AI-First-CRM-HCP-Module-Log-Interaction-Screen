const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

async function handleResponse(res) {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      // response wasn't JSON, keep statusText
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json();
}

export async function createInteraction() {
  const res = await fetch(`${BASE_URL}/interactions/new`, { method: 'POST' });
  return handleResponse(res);
}

export async function sendChatMessage(interactionId, message) {
  const res = await fetch(`${BASE_URL}/interactions/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ interaction_id: interactionId, message }),
  });
  return handleResponse(res);
}

export async function getInteraction(interactionId) {
  const res = await fetch(`${BASE_URL}/interactions/${interactionId}`);
  return handleResponse(res);
}

// Direct form save -- bypasses the LLM entirely, so manual form edits
// don't cost any Groq tokens. Requires the /interactions/{id}/save
// endpoint added to main.py (see backend instructions).
export async function saveInteractionForm(interactionId, formState) {
  const res = await fetch(`${BASE_URL}/interactions/${interactionId}/save`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(formState),
  });
  return handleResponse(res);
}
