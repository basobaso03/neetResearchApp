/**
 * Shared frontend error normalization.
 * Produces a user-friendly message with optional technical details.
 */

export interface AppErrorInfo {
    title: string;
    message: string;
    details?: string;
}

const RETRY_IN_SECONDS_REGEX = /retry in\s+([0-9]+(?:\.[0-9]+)?)s/i;
const RETRY_DELAY_SECONDS_REGEX = /retrydelay['\"]?\s*[:=]\s*['\"]?([0-9]+)s/i;

function toErrorString(value: unknown): string {
    if (typeof value === 'string') {
        return value;
    }

    if (value instanceof Error) {
        return value.message || value.name;
    }

    try {
        return JSON.stringify(value, null, 2);
    } catch {
        return String(value);
    }
}

function parseRetrySeconds(text: string): number | null {
    const retryInMatch = text.match(RETRY_IN_SECONDS_REGEX);
    if (retryInMatch?.[1]) {
        return Math.max(1, Math.ceil(Number(retryInMatch[1])));
    }

    const retryDelayMatch = text.match(RETRY_DELAY_SECONDS_REGEX);
    if (retryDelayMatch?.[1]) {
        return Math.max(1, Number(retryDelayMatch[1]));
    }

    return null;
}

export function normalizeError(error: unknown, fallbackMessage = 'Something went wrong'): AppErrorInfo {
    const details = toErrorString(error).trim();
    const lower = details.toLowerCase();

    if (!details) {
        return {
            title: 'Request Failed',
            message: fallbackMessage,
        };
    }

    if (lower.includes('resource_exhausted') || lower.includes('quota exceeded') || lower.includes('http 429')) {
        const retrySeconds = parseRetrySeconds(details);
        const retryHint = retrySeconds ? ` Please retry in about ${retrySeconds}s.` : '';

        return {
            title: 'Rate Limit Reached',
            message: `AI provider quota is currently exhausted.${retryHint}`,
            details,
        };
    }

    if (lower.includes('session not found') || lower.includes('http 404')) {
        return {
            title: 'Session Not Found',
            message: 'This session is no longer available. Start a new session or open an existing one.',
            details,
        };
    }

    if (lower.includes('failed to fetch') || lower.includes('networkerror') || lower.includes('network error')) {
        return {
            title: 'Connection Problem',
            message: 'Could not reach the backend service. Please confirm the server is running.',
            details,
        };
    }

    return {
        title: 'Request Failed',
        message: fallbackMessage,
        details,
    };
}
