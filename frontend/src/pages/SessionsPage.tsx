/**
 * Sessions Page - List and manage research sessions
 */

import { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { History, Play, Trash2, FileText, Clock } from 'lucide-react';
import { useResearchStore } from '../store/researchStore';
import { normalizeError } from '../utils/errorHandling';
import './SessionsPage.css';

export function SessionsPage() {
    const navigate = useNavigate();
    const { sessions, fetchSessions, resumeSession, deleteSession } = useResearchStore();

    useEffect(() => {
        fetchSessions();
    }, [fetchSessions]);

    const handleResume = async (sessionId: string) => {
        await resumeSession(sessionId);
        navigate(`/progress/${sessionId}`);
    };

    const handleDelete = async (sessionId: string, topic: string) => {
        if (confirm(`Delete session "${topic.slice(0, 50)}..."?`)) {
            await deleteSession(sessionId);
        }
    };

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'completed':
                return <span className="status-badge completed">✅ Completed</span>;
            case 'failed':
                return <span className="status-badge failed">❌ Failed</span>;
            case 'cancelled':
                return <span className="status-badge cancelled">⏸️ Cancelled</span>;
            default:
                return <span className="status-badge in-progress">🔄 In Progress</span>;
        }
    };

    const getSourceBadge = (sourceType: 'web' | 'database' | 'both', isWebResearch: boolean) => {
        if (sourceType === 'both') {
            return <span className="status-badge in-progress">🌐 + 🗄️ Hybrid</span>;
        }

        return isWebResearch ?
            <span className="status-badge completed">🌐 Web</span> :
            <span className="status-badge cancelled">🗄️ Database</span>;
    };

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    return (
        <div className="sessions-page animate-fadeIn">
            <div className="page-header">
                <h1 className="page-title">
                    <History size={28} />
                    Research Sessions
                </h1>
                <Link to="/new" className="btn btn-primary">
                    New Research
                </Link>
            </div>

            {sessions.length === 0 ? (
                <div className="empty-state card">
                    <h2>No sessions yet</h2>
                    <p>Start your first research to see it here.</p>
                    <Link to="/new" className="btn btn-primary">
                        Start Research
                    </Link>
                </div>
            ) : (
                <div className="sessions-list">
                    {sessions.map((session) => (
                        <div key={session.session_id} className="session-card card">
                            <div className="session-header">
                                <div className="session-source">
                                    {getSourceBadge(session.source_type, session.is_web_research)}
                                </div>
                                {getStatusBadge(session.status)}
                            </div>

                            <h3 className="session-topic">{session.topic}</h3>

                            <div className="session-meta">
                                <span className="meta-item">
                                    <Clock size={14} />
                                    {formatDate(session.created_at)}
                                </span>
                                <span className="meta-item">
                                    {session.sources_found} sources
                                </span>
                                <span className="meta-item">
                                    {session.progress}%
                                </span>
                            </div>

                            {session.error_message && (() => {
                                const normalizedError = normalizeError(session.error_message, 'Research session failed');
                                return (
                                    <div className="session-error">
                                        <p>{normalizedError.message}</p>
                                        {normalizedError.details && (
                                            <details className="session-error-details">
                                                <summary>More details</summary>
                                                <pre>{normalizedError.details}</pre>
                                            </details>
                                        )}
                                    </div>
                                );
                            })()}

                            <div className="session-actions">
                                {session.has_report ? (
                                    <Link
                                        to={`/report/${session.session_id}`}
                                        className="btn btn-primary btn-sm"
                                    >
                                        <FileText size={16} />
                                        View Report
                                    </Link>
                                ) : session.status === 'failed' || session.status === 'cancelled' ? (
                                    <button
                                        className="btn btn-secondary btn-sm"
                                        onClick={() => handleResume(session.session_id)}
                                    >
                                        <Play size={16} />
                                        Resume
                                    </button>
                                ) : (
                                    <Link
                                        to={`/progress/${session.session_id}`}
                                        className="btn btn-secondary btn-sm"
                                    >
                                        View Progress
                                    </Link>
                                )}

                                <button
                                    className="btn btn-ghost btn-sm delete-btn"
                                    onClick={() => handleDelete(session.session_id, session.topic)}
                                >
                                    <Trash2 size={16} />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
