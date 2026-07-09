import { useEffect, useRef, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { sendMessage } from '../store/interactionSlice';

export default function ChatPanel() {
  const dispatch = useDispatch();
  const interactionId = useSelector((s) => s.interaction.interactionId);
  const chatMessages = useSelector((s) => s.interaction.chatMessages);
  const status = useSelector((s) => s.interaction.status);

  const [input, setInput] = useState('');
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [chatMessages]);

  const handleSend = () => {
    if (!input.trim() || !interactionId || status === 'loading') return;
    dispatch(sendMessage({ interactionId, message: input.trim() }));
    setInput('');
  };

  return (
    <div className="card chat-panel">
      <div className="card-header chat-header">
        <span className="dot" />
        <div>
          AI Assistant
          <span className="chat-subtitle">Log interactions via chat</span>
        </div>
      </div>

      <div className="chat-messages" ref={scrollRef}>
        {chatMessages.length === 0 && (
          <div className="chat-empty">
            Log interaction details here (e.g., "Met Dr. Smith, discussed Product X efficacy,
            positive sentiment, shared brochure") or ask for help.
          </div>
        )}
        {chatMessages.map((m, i) => (
          <div key={i} className={`chat-bubble ${m.role}`}>
            {m.content}
          </div>
        ))}
      </div>

      <div className="chat-input-row">
        <input
          type="text"
          placeholder="Describe interaction…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          disabled={status === 'loading'}
        />
        <button
          type="button"
          className="chat-send-btn"
          onClick={handleSend}
          disabled={status === 'loading' || !input.trim()}
        >
          Log
        </button>
      </div>
    </div>
  );
}
