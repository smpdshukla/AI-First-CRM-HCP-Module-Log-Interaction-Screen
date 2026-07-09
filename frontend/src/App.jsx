import { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { startNewInteraction } from './store/interactionSlice';
import LogInteractionScreen from './components/LogInteractionScreen';

export default function App() {
  const dispatch = useDispatch();
  const interactionId = useSelector((s) => s.interaction.interactionId);

  useEffect(() => {
    if (!interactionId) {
      dispatch(startNewInteraction());
    }
  }, [interactionId, dispatch]);

  return <LogInteractionScreen />;
}
