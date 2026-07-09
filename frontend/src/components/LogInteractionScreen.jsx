import { useSelector } from 'react-redux';
import InteractionForm from './InteractionForm';
import ChatPanel from './ChatPanel';
import './LogInteractionScreen.css';

export default function LogInteractionScreen() {
  const status = useSelector((s) => s.interaction.status);
  const error = useSelector((s) => s.interaction.error);

  return (
    <div className="screen">
      <header className="screen-header">
        <h1>Log HCP Interaction</h1>
        {status === 'loading' && <span className="status-pill">Working…</span>}
      </header>

      {error && <div className="error-banner">Error: {error}</div>}

      <div className="screen-body">
        <InteractionForm />
        <ChatPanel />
      </div>
    </div>
  );
}
