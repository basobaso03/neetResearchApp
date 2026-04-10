/**
 * Initialization Hook - monitors backend startup
 */

import { useEffect, useRef } from 'react';
import { api } from '../services/api';
import { useResearchStore } from '../store/researchStore';
import { normalizeError } from '../utils/errorHandling';

export function useInitialization() {
    const wsRef = useRef<WebSocket | null>(null);
    const { setInitStatus, setBackendReady, initStatus, addToast } = useResearchStore();

    useEffect(() => {
        // First, try to get current status via HTTP
        api.getInitStatus()
            .then((status) => {
                setInitStatus(status);
                if (status.ready) {
                    setBackendReady(true);
                    return;
                }

                // If not ready, connect via WebSocket for updates
                connectWebSocket();
            })
            .catch(() => {
                // Backend not available, try WebSocket
                setInitStatus({
                    status: 'connecting',
                    progress: 0,
                    message: 'Connecting to backend...',
                    ready: false,
                });
                connectWebSocket();
            });

        function connectWebSocket() {
            try {
                const ws = api.createInitWebSocket();
                wsRef.current = ws;

                ws.onmessage = (event) => {
                    try {
                        const status = JSON.parse(event.data);
                        setInitStatus(status);
                        if (status.ready) {
                            setBackendReady(true);
                            ws.close();
                        }
                    } catch (err) {
                        const normalized = normalizeError(err, 'Failed to parse backend initialization status');
                        addToast('error', normalized.message, normalized.details);
                        console.error('Failed to parse init status:', err);
                    }
                };

                ws.onerror = () => {
                    // Retry after delay
                    setTimeout(connectWebSocket, 2000);
                };

                ws.onclose = () => {
                    wsRef.current = null;
                };
            } catch {
                // Retry after delay
                setTimeout(connectWebSocket, 2000);
            }
        }

        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
        };
    }, [setInitStatus, setBackendReady, addToast]);

    return initStatus;
}
