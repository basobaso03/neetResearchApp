/**
 * API Service Layer
 * Handles all HTTP requests to the backend
 */

const runtimeHost = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) || `http://${runtimeHost}:8000/api`;
const WS_BASE = (import.meta.env.VITE_WS_BASE as string | undefined) || `ws://${runtimeHost}:8000/ws`;

export interface ResearchStartRequest {
    topic: string;
    source_type: 'web' | 'database' | 'both';
    collection_name?: string;
}

export interface ResearchStartResponse {
    session_id: string;
    topic: string;
    status: string;
    message: string;
    created_at: string;
}

export interface PhaseProgress {
    phase: string;
    status: string;
    progress: number;
    notes: string[];
}

export interface ResearchStatusResponse {
    session_id: string;
    topic: string;
    status: string;
    overall_progress: number;
    phases: PhaseProgress[];
    sources_found: number;
    estimated_time_remaining?: number;
    final_report?: string;
    error_message?: string;
    created_at: string;
    updated_at: string;
}

export interface SessionResponse {
    session_id: string;
    topic: string;
    status: string;
    progress: number;
    sources_found: number;
    created_at: string;
    updated_at: string;
    source_type: 'web' | 'database' | 'both';
    is_web_research: boolean;
    error_message?: string;
    has_report: boolean;
}

export interface InitStatus {
    status: string;
    progress: number;
    message: string;
    ready: boolean;
}

export class ApiError extends Error {
    status: number;
    detail: unknown;
    endpoint: string;

    constructor(message: string, status: number, detail: unknown, endpoint: string) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.detail = detail;
        this.endpoint = endpoint;
    }
}

class ApiService {
    private async request<T>(
        endpoint: string,
        options: RequestInit = {}
    ): Promise<T> {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
        });

        if (!response.ok) {
            const errorBody = await response.json().catch(() => ({ detail: 'Unknown error' }));
            const detail = errorBody?.detail ?? errorBody;
            const message = typeof detail === 'string' ? detail : `HTTP ${response.status}`;
            throw new ApiError(message, response.status, detail, endpoint);
        }

        return response.json();
    }

    // Health check
    async healthCheck(): Promise<{ status: string; initialization: InitStatus }> {
        return this.request('/health');
    }

    // Get initialization status
    async getInitStatus(): Promise<InitStatus> {
        return this.request('/init-status');
    }

    // Research endpoints
    async startResearch(data: ResearchStartRequest): Promise<ResearchStartResponse> {
        return this.request('/research/start', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async getResearchStatus(sessionId: string): Promise<ResearchStatusResponse> {
        return this.request(`/research/${sessionId}/status`);
    }

    async cancelResearch(sessionId: string): Promise<{ session_id: string; status: string; message: string }> {
        return this.request(`/research/${sessionId}/cancel`, {
            method: 'POST',
        });
    }

    // Session endpoints
    async getSessions(): Promise<{ sessions: SessionResponse[]; total: number }> {
        return this.request('/sessions');
    }

    async getSession(sessionId: string): Promise<SessionResponse> {
        return this.request(`/sessions/${sessionId}`);
    }

    async resumeSession(sessionId: string): Promise<{ session_id: string; status: string; message: string }> {
        return this.request(`/sessions/${sessionId}/resume`, {
            method: 'POST',
        });
    }

    async deleteSession(sessionId: string): Promise<{ message: string }> {
        return this.request(`/sessions/${sessionId}`, {
            method: 'DELETE',
        });
    }

    // Export endpoints
    getExportUrl(sessionId: string, format: 'md' | 'pdf' = 'md'): string {
        return `${API_BASE}/export/${sessionId}?format=${format}`;
    }

    async getReportContent(sessionId: string): Promise<{ session_id: string; topic: string; content: string; created_at: string }> {
        return this.request(`/export/${sessionId}/content`);
    }

    // WebSocket connections
    createResearchWebSocket(sessionId: string): WebSocket {
        return new WebSocket(`${WS_BASE}/research/${sessionId}`);
    }

    createInitWebSocket(): WebSocket {
        return new WebSocket(`${WS_BASE}/init`);
    }
}

export const api = new ApiService();
export default api;
