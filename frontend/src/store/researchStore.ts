/**
 * Research Store - Zustand state management
 */

import { create } from 'zustand';
import { api } from '../services/api';
import type { ResearchStatusResponse, SessionResponse, InitStatus } from '../services/api';
import { normalizeError } from '../utils/errorHandling';

export type ResearchPhase = 'initializing' | 'scoping' | 'researching' | 'analyzing' | 'generating' | 'completed' | 'failed' | 'cancelled';

interface Toast {
    id: string;
    type: 'success' | 'error' | 'warning' | 'info';
    message: string;
    details?: string;
}

interface ResearchState {
    // Initialization
    initStatus: InitStatus | null;
    isBackendReady: boolean;

    // Current research
    currentSessionId: string | null;
    currentStatus: ResearchStatusResponse | null;
    isLoading: boolean;
    error: string | null;

    // Sessions
    sessions: SessionResponse[];

    // Toasts
    toasts: Toast[];

    // Actions
    setInitStatus: (status: InitStatus) => void;
    setBackendReady: (ready: boolean) => void;

    startResearch: (topic: string, sourceType: 'web' | 'database' | 'both', collectionName?: string) => Promise<string>;
    setCurrentStatus: (status: ResearchStatusResponse) => void;
    cancelResearch: (sessionId?: string) => Promise<void>;

    fetchSessions: () => Promise<void>;
    resumeSession: (sessionId: string) => Promise<void>;
    deleteSession: (sessionId: string) => Promise<void>;

    addToast: (type: Toast['type'], message: string, details?: string) => void;
    addErrorToast: (error: unknown, fallbackMessage: string) => void;
    removeToast: (id: string) => void;

    setError: (error: string | null) => void;
    reset: () => void;
}

export const useResearchStore = create<ResearchState>((set, get) => ({
    // Initial state
    initStatus: null,
    isBackendReady: false,
    currentSessionId: null,
    currentStatus: null,
    isLoading: false,
    error: null,
    sessions: [],
    toasts: [],

    // Actions
    setInitStatus: (status) => set({ initStatus: status }),
    setBackendReady: (ready) => set({ isBackendReady: ready }),

    startResearch: async (topic, sourceType, collectionName) => {
        set({ isLoading: true, error: null });
        try {
            const response = await api.startResearch({
                topic,
                source_type: sourceType,
                collection_name: collectionName,
            });
            set({
                currentSessionId: response.session_id,
                isLoading: false
            });
            get().addToast('success', 'Research started!');
            return response.session_id;
        } catch (err) {
            const normalized = normalizeError(err, 'Failed to start research');
            set({ error: normalized.message, isLoading: false });
            get().addToast('error', normalized.message, normalized.details);
            throw err;
        }
    },

    setCurrentStatus: (status) => set({ currentStatus: status }),

    cancelResearch: async (sessionId) => {
        const targetSessionId = sessionId || get().currentSessionId;
        if (!targetSessionId) return;

        try {
            await api.cancelResearch(targetSessionId);
            set({ currentSessionId: null, currentStatus: null });
            get().addToast('info', 'Research cancelled');
        } catch (err) {
            const normalized = normalizeError(err, 'Failed to cancel research');
            get().addToast('error', normalized.message, normalized.details);
        }
    },

    fetchSessions: async () => {
        try {
            const response = await api.getSessions();
            set({ sessions: response.sessions });
        } catch (err) {
            const normalized = normalizeError(err, 'Failed to fetch sessions');
            get().addToast('error', normalized.message, normalized.details);
            console.error('Failed to fetch sessions:', err);
        }
    },

    resumeSession: async (sessionId) => {
        set({ isLoading: true });
        try {
            await api.resumeSession(sessionId);
            set({ currentSessionId: sessionId, isLoading: false });
            get().addToast('success', 'Session resumed');
        } catch (err) {
            const normalized = normalizeError(err, 'Failed to resume session');
            set({ isLoading: false });
            get().addToast('error', normalized.message, normalized.details);
        }
    },

    deleteSession: async (sessionId) => {
        try {
            await api.deleteSession(sessionId);
            set(state => ({
                sessions: state.sessions.filter(s => s.session_id !== sessionId)
            }));
            get().addToast('success', 'Session deleted');
        } catch (err) {
            const normalized = normalizeError(err, 'Failed to delete session');
            get().addToast('error', normalized.message, normalized.details);
        }
    },

    addToast: (type, message, details) => {
        const id = Date.now().toString();
        set(state => ({
            toasts: [...state.toasts, { id, type, message, details }]
        }));
        // Auto-remove after 5 seconds
        setTimeout(() => get().removeToast(id), 5000);
    },

    addErrorToast: (error, fallbackMessage) => {
        const normalized = normalizeError(error, fallbackMessage);
        get().addToast('error', normalized.message, normalized.details);
    },

    removeToast: (id) => {
        set(state => ({
            toasts: state.toasts.filter(t => t.id !== id)
        }));
    },

    setError: (error) => set({ error }),

    reset: () => set({
        currentSessionId: null,
        currentStatus: null,
        isLoading: false,
        error: null,
    }),
}));
