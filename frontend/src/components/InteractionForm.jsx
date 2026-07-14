import { useDispatch, useSelector } from 'react-redux';
import { updateField } from '../store/interactionSlice';

const SENTIMENTS = [
  { value: 'Positive', icon: '😊', color: '#2E7D32' },
  { value: 'Neutral', icon: '😐', color: '#F9A825' },
  { value: 'Negative', icon: '🙁', color: '#C62828' },
];

export default function InteractionForm() {
  const dispatch = useDispatch();
  const form = useSelector((s) => s.interaction.form);
  const suggestedFollowups = useSelector((s) => s.interaction.suggestedFollowups);

  const set = (field) => (e) => dispatch(updateField({ field, value: e.target.value }));

  return (
    <div className="card">
      <div className="card-header">Interaction Details</div>

      <div className="field-group">
        <div className="field-row">
          <div className="field">
            <label htmlFor="hcp_name">HCP Name</label>
            <input
              id="hcp_name"
              type="text"
              placeholder="Search or select HCP…"
              value={form.hcp_name || ''}
              readOnly
            />
          </div>
          <div className="field">
            <label htmlFor="interaction_type">Interaction Type</label>
            <select id="interaction_type" value={form.interaction_type || 'Meeting'} style={{ pointerEvents: 'none' }} onChange={() => {}}>
              <option>Meeting</option>
              <option>Call</option>
              <option>Email</option>
            </select>
          </div>
        </div>

        <div className="field-row">
          <div className="field">
            <label htmlFor="date">Date</label>
            <input id="date" type="date" value={form.date || ''} onChange={set('date')} />
          </div>
          <div className="field">
            <label htmlFor="time">Time</label>
            <input id="time" type="time" value={form.time || ''} onChange={set('time')} />
          </div>
        </div>

        <div className="field">
          <label>Attendees</label>
          <input
            type="text"
            placeholder="Enter names or search…"
            value={(form.attendees || []).join(', ')}
            readOnly
          />
        </div>
      <button type="button" className="voice-note-btn" style={{ pointerEvents: 'none' }}>
          ⚡ Summarize from Voice Note (Requires Consent)
        </button>

        {form.voice_note_summary && (
          <div className="suggested-followups-inline">
            <p className="suggested-label">Voice Note Summary:</p>
            <p style={{ fontSize: '13.5px', color: 'var(--color-text)', margin: 0 }}>
              {form.voice_note_summary}
            </p>
          </div>
        )}

        <div className="field">
          <label htmlFor="topics">Topics Discussed</label>
          <textarea
            id="topics"
            placeholder="Enter key discussion points…"
            value={form.topics_discussed || ''}
            readOnly
          />
        </div>

        <div className="field">
          <label>Materials Shared / Samples Distributed</label>

          <div className="sub-field-row">
            <span className="sub-label">Materials Shared</span>
            <button type="button" className="add-btn" style={{ pointerEvents: 'none' }}>🔍 Search/Add</button>
          </div>
          {form.materials_shared?.filter((m) => m.type === 'material').length > 0 ? (
            <div className="chip-list">
              {form.materials_shared
                .filter((m) => m.type === 'material')
                .map((m, i) => (
                  <span className="chip" key={i}>{m.name}</span>
                ))}
            </div>
          ) : (
            <p className="muted-text">No materials added.</p>
          )}

          <div className="sub-field-row">
            <span className="sub-label">Samples Distributed</span>
            <button type="button" className="add-btn" style={{ pointerEvents: 'none' }}>⚙️ Add Sample</button>
          </div>
          {form.materials_shared?.filter((m) => m.type === 'sample').length > 0 ? (
            <div className="chip-list">
              {form.materials_shared
                .filter((m) => m.type === 'sample')
                .map((m, i) => (
                  <span className="chip" key={i}>
                    {m.name}{m.quantity ? ` (${m.quantity})` : ''}
                  </span>
                ))}
            </div>
          ) : (
            <p className="muted-text">No samples added.</p>
          )}
        </div>

        <div className="field">
          <label>Observed/Inferred HCP Sentiment</label>
          <div className="sentiment-options">
            {SENTIMENTS.map((s) => (
              <label className="sentiment-option" key={s.value} style={{ color: s.color }}>
                <input
                  type="radio"
                  name="sentiment"
                  checked={form.sentiment === s.value}
                  readOnly
                  style={{ accentColor: s.color }}
                />
                {s.icon} {s.value}
              </label>
            ))}
          </div>
        </div>

        <div className="field">
          <label htmlFor="outcomes">Outcomes</label>
          <textarea
            id="outcomes"
            placeholder="Key outcomes or agreements…"
            value={form.outcomes || ''}
            readOnly
          />
        </div>

        <div className="field">
          <label>Follow-up Actions</label>
          <textarea
            placeholder="Enter next steps or tasks…"
            value={(form.follow_up_actions || []).join('\n')}
            readOnly
          />
        </div>
      </div>

      {suggestedFollowups?.length > 0 && (
        <div className="suggested-followups-inline">
          <p className="suggested-label">AI Suggested Follow-ups:</p>
          <ul>
            {suggestedFollowups.map((s, i) => (
              <li key={i}>+ {s}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
