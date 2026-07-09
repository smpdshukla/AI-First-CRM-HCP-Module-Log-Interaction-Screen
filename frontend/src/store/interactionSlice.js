import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import {
  createInteraction,
  sendChatMessage,
  saveInteractionForm,
} from '../api/client';

const blankForm = {
  hcp_name: '',
  interaction_type: 'Meeting',
  date: '',
  time: '',
  attendees: [],
  topics_discussed: '',
  materials_shared: [],
  sentiment: null,
  outcomes: '',
  follow_up_actions: [],
};

const initialState = {
  interactionId: null,
  form: blankForm,
  suggestedFollowups: [],
  chatMessages: [], // { role: 'user' | 'assistant', content: string }
  status: 'idle', // 'idle' | 'loading' | 'error'
  error: null,
};

// merges a backend `state` object (from /new, /chat, or GET) into the form shape
function applyBackendState(form, backendState) {
  if (!backendState) return form;
  return {
    hcp_name: backendState.hcp_name ?? form.hcp_name,
    interaction_type: backendState.interaction_type ?? form.interaction_type,
    date: backendState.date ?? form.date,
    time: backendState.time ?? form.time,
    attendees: backendState.attendees ?? form.attendees,
    topics_discussed: backendState.topics_discussed ?? form.topics_discussed,
    materials_shared: backendState.materials_shared ?? form.materials_shared,
    sentiment: backendState.sentiment ?? form.sentiment,
    outcomes: backendState.outcomes ?? form.outcomes,
    follow_up_actions: backendState.follow_up_actions ?? form.follow_up_actions,
  };
}

export const startNewInteraction = createAsyncThunk(
  'interaction/startNew',
  async () => {
    const data = await createInteraction();
    return data;
  }
);

export const sendMessage = createAsyncThunk(
  'interaction/sendMessage',
  async ({ interactionId, message }) => {
    const data = await sendChatMessage(interactionId, message);
    return data;
  }
);

export const saveForm = createAsyncThunk(
  'interaction/saveForm',
  async ({ interactionId, form }) => {
    const data = await saveInteractionForm(interactionId, form);
    return data;
  }
);

const interactionSlice = createSlice({
  name: 'interaction',
  initialState,
  reducers: {
    updateField(state, action) {
      const { field, value } = action.payload;
      state.form[field] = value;
    },
    addAttendee(state, action) {
      state.form.attendees.push(action.payload);
    },
    removeAttendee(state, action) {
      state.form.attendees.splice(action.payload, 1);
    },
    addFollowUpAction(state, action) {
      state.form.follow_up_actions.push(action.payload);
    },
    removeFollowUpAction(state, action) {
      state.form.follow_up_actions.splice(action.payload, 1);
    },
    acceptSuggestedFollowup(state, action) {
      const suggestion = state.suggestedFollowups[action.payload];
      if (suggestion) {
        state.form.follow_up_actions.push(suggestion);
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // --- start new interaction ---
      .addCase(startNewInteraction.pending, (state) => {
        state.status = 'loading';
        state.error = null;
      })
      .addCase(startNewInteraction.fulfilled, (state, action) => {
        state.status = 'idle';
        state.interactionId = action.payload.interaction_id;
        state.form = applyBackendState(blankForm, action.payload.state);
        state.chatMessages = [];
        state.suggestedFollowups = [];
      })
      .addCase(startNewInteraction.rejected, (state, action) => {
        state.status = 'error';
        state.error = action.error.message;
      })

      // --- send chat message ---
      .addCase(sendMessage.pending, (state, action) => {
        state.status = 'loading';
        state.error = null;
        state.chatMessages.push({
          role: 'user',
          content: action.meta.arg.message,
        });
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.status = 'idle';
        state.form = applyBackendState(state.form, action.payload.state);
        state.suggestedFollowups =
          action.payload.state.suggested_followups ?? state.suggestedFollowups;
        state.chatMessages.push({
          role: 'assistant',
          content: action.payload.reply,
        });
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.status = 'error';
        state.error = action.error.message;
        state.chatMessages.push({
          role: 'assistant',
          content: `Something went wrong: ${action.error.message}`,
        });
      })

      // --- save form directly (no LLM) ---
      .addCase(saveForm.pending, (state) => {
        state.status = 'loading';
        state.error = null;
      })
      .addCase(saveForm.fulfilled, (state) => {
        state.status = 'idle';
      })
      .addCase(saveForm.rejected, (state, action) => {
        state.status = 'error';
        state.error = action.error.message;
      });
  },
});

export const {
  updateField,
  addAttendee,
  removeAttendee,
  addFollowUpAction,
  removeFollowUpAction,
  acceptSuggestedFollowup,
} = interactionSlice.actions;

export default interactionSlice.reducer;
