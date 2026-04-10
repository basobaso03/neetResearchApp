/**
 * WebSocket Hook for real-time research updates
 */

import { useEffect, useRef, useCallback } from 'react';
import { api } from '../services/api';
import { useResearchStore } from '../store/researchStore';
import { normalizeError } from '../utils/errorHandling';

interface WebSocketMessage {
    type: 'phase_update' | 'note' | 'completed' | 'error';
    phase?: string;
    progress?: number;
    message?: string;
    content?: string;
    notes?: string[];
    report?: string;
}

export function useWebSocket(sessionId: string | null) {
    const wsRef = useRef<WebSocket | null>(null);
    const connectRef = useRef<(() => void) | null>(null);
    const shouldReconnectRef = useRef(true);
    const intentionalCloseRef = useRef(false);
    const sessionMissingRef = useRef(false);
    const reconnectTimerRef = useRef<number | null>(null);
    const pollTimerRef = useRef<number | null>(null);
    const reconnectAttemptsRef = useRef(0);
    const { setCurrentStatus, addToast } = useResearchStore();

    const clearReconnectTimer = useCallback(() => {
        if (reconnectTimerRef.current !== null) {
            window.clearTimeout(reconnectTimerRef.current);
            reconnectTimerRef.current = null;
        }
    }, []);

    const clearPollTimer = useCallback(() => {
        if (pollTimerRef.current !== null) {
            window.clearInterval(pollTimerRef.current);
            pollTimerRef.current = null;
        }
    }, []);

    const isSessionNotFoundError = useCallback((err: unknown) => {
        const msg = normalizeError(err, 'Request failed').details?.toLowerCase() || '';
        return msg.includes('session not found') || msg.includes('http 404');
    }, []);

    const handleMissingSession = useCallback(() => {
        if (sessionMissingRef.current) return;
        sessionMissingRef.current = true;
        shouldReconnectRef.current = false;
        clearReconnectTimer();
        clearPollTimer();
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
        addToast('warning', 'Session not found. It may have expired after backend restart.');
    }, [addToast, clearReconnectTimer, clearPollTimer]);

    const startPollingFallback = useCallback(() => {
        if (!sessionId || pollTimerRef.current !== null) return;
        pollTimerRef.current = window.setInterval(() => {
            api.getResearchStatus(sessionId)
                .then(setCurrentStatus)
                .catch((err) => {
                    if (isSessionNotFoundError(err)) {
                        handleMissingSession();
                    }
                    // Keep fallback quiet for transient outages; reconnect/poll handles recovery.
                });
        }, 4000);
    }, [sessionId, setCurrentStatus, isSessionNotFoundError, handleMissingSession]);

    const stopPollingFallback = useCallback(() => {
        clearPollTimer();
    }, [clearPollTimer]);

    const scheduleReconnect = useCallback(() => {
        if (!sessionId) return;
        clearReconnectTimer();

        const attempt = reconnectAttemptsRef.current;
        const delay = Math.min(1000 * (attempt + 1), 5000);
        reconnectTimerRef.current = window.setTimeout(() => {
            reconnectAttemptsRef.current += 1;
            connectRef.current?.();
        }, delay);
    }, [sessionId, clearReconnectTimer]);

    const connect = useCallback(() => {
        if (!sessionId) return;

        intentionalCloseRef.current = false;
        const ws = api.createResearchWebSocket(sessionId);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log('WebSocket connected');
            reconnectAttemptsRef.current = 0;
            stopPollingFallback();
        };

        ws.onmessage = (event) => {
            try {
                const data: WebSocketMessage = JSON.parse(event.data);

                switch (data.type) {
                    case 'phase_update':
                        // Fetch full status from API to get complete state
                        api.getResearchStatus(sessionId)
                            .then(setCurrentStatus)
                            .catch((err) => {
                                if (isSessionNotFoundError(err)) {
                                    handleMissingSession();
                                }
                            });
                        break;

                    case 'note':
                        console.log('New note:', data.content || data.message);
                        api.getResearchStatus(sessionId)
                            .then(setCurrentStatus)
                            .catch((err) => {
                                if (isSessionNotFoundError(err)) {
                                    handleMissingSession();
                                }
                            });
                        break;

                    case 'completed':
                        addToast('success', 'Research completed!');
                        api.getResearchStatus(sessionId)
                            .then(setCurrentStatus)
                            .catch((err) => {
                                if (isSessionNotFoundError(err)) {
                                    handleMissingSession();
                                }
                            });
                        break;

                    case 'error':
                        addToast('error', data.message || 'An error occurred', data.message);
                        api.getResearchStatus(sessionId)
                            .then(setCurrentStatus)
                            .catch((err) => {
                                if (isSessionNotFoundError(err)) {
                                    handleMissingSession();
                                }
                            });
                        break;
                }
            } catch (err) {
                const normalized = normalizeError(err, 'Failed to parse WebSocket message');
                addToast('error', normalized.message, normalized.details);
                console.error('Failed to parse WebSocket message:', err);
            }
        };

        ws.onerror = (error) => {
            if (intentionalCloseRef.current) {
                return;
            }
            console.error('WebSocket error:', error);
            startPollingFallback();
        };

        ws.onclose = () => {
            if (intentionalCloseRef.current) {
                return;
            }
            console.log('WebSocket closed');
            startPollingFallback();
            if (shouldReconnectRef.current) {
                scheduleReconnect();
            }
        };

        return ws;
    }, [sessionId, setCurrentStatus, addToast, scheduleReconnect, startPollingFallback, stopPollingFallback, isSessionNotFoundError, handleMissingSession]);

    useEffect(() => {
        connectRef.current = connect;
    }, [connect]);

    const disconnect = useCallback(() => {
        shouldReconnectRef.current = false;
        intentionalCloseRef.current = true;
        clearReconnectTimer();
        clearPollTimer();
        if (wsRef.current) {
            wsRef.current.onopen = null;
            wsRef.current.onmessage = null;
            wsRef.current.onerror = null;
            wsRef.current.onclose = null;
            wsRef.current.close();
            wsRef.current = null;
        }
    }, [clearReconnectTimer, clearPollTimer]);

    useEffect(() => {
        shouldReconnectRef.current = true;
        sessionMissingRef.current = false;
        reconnectAttemptsRef.current = 0;
        connect();
        return () => disconnect();
    }, [connect, disconnect]);

    return { disconnect };
}
