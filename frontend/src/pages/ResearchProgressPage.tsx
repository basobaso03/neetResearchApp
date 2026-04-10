/**
 * Research Progress Page - Shows real-time progress
 */

import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, XCircle, FileText } from 'lucide-react';
import { useResearchStore } from '../store/researchStore';
import { useWebSocket } from '../hooks/useWebSocket';
import { api } from '../services/api';
import { ProgressTracker } from '../components/research/ProgressTracker';
import { LiveNotes } from '../components/research/LiveNotes';
import { normalizeError } from '../utils/errorHandling';
import './ResearchProgressPage.css';

export function ResearchProgressPage() {
    const { sessionId } = useParams<{ sessionId: string }>();
    const navigate = useNavigate();
    const { currentStatus, setCurrentStatus, cancelResearch, addToast } = useResearchStore();
    const [sessionNotFound, setSessionNotFound] = useState(false);

    // Connect to WebSocket for real-time updates
    useWebSocket(sessionNotFound ? null : (sessionId || null));

    // Fetch initial status
    useEffect(() => {
        let isCancelled = false;

        if (sessionId) {
            api.getResearchStatus(sessionId)
                .then((status) => {
                    if (isCancelled) return;
                    setSessionNotFound(false);
                    setCurrentStatus(status);
                })
                .catch((err) => {
                    if (isCancelled) return;
                    const normalized = normalizeError(err, 'Failed to load research status');
                    const message = normalized.details?.toLowerCase() || normalized.message.toLowerCase();
                    const missing = message.includes('session not found') || message.includes('http 404');
                    if (missing) {
                        setSessionNotFound(true);
                        addToast('warning', 'Session not found. Start a new research session.');
                        navigate('/sessions', { replace: true });
                        return;
                    }
                    addToast('error', normalized.message, normalized.details);
                    console.error(err);
                });
        }

        return () => {
            isCancelled = true;
        };
    }, [sessionId, setCurrentStatus, addToast, navigate]);

    // Redirect to report when completed
    useEffect(() => {
        if (currentStatus?.status === 'completed') {
            // Wait a moment to show completion state
            const timer = setTimeout(() => {
                navigate(`/report/${sessionId}`);
            }, 2000);
            return () => clearTimeout(timer);
        }
    }, [currentStatus?.status, sessionId, navigate]);

    const handleCancel = async () => {
        if (confirm('Are you sure you want to cancel this research?')) {
            await cancelResearch(sessionId || undefined);
            navigate('/');
        }
    };

    if (sessionNotFound) {
        return (
            <div className="progress-page">
                <div className="loading-state">
                    <p>Session not found. Redirecting...</p>
                </div>
            </div>
        );
    }

    if (!currentStatus) {
        return (
            <div className="progress-page">
                <div className="loading-state">
                    <div className="spinner spinner-lg" />
                    <p>Loading research status...</p>
                </div>
            </div>
        );
    }

    const isCompleted = currentStatus.status === 'completed';
    const isFailed = currentStatus.status === 'failed';
    const isCancelled = currentStatus.status === 'cancelled';
    const isFinished = isCompleted || isFailed || isCancelled;
    const normalizedStatusError = currentStatus.error_message
        ? normalizeError(currentStatus.error_message, 'Research failed during processing')
        : null;

    return (
        <div className="progress-page animate-fadeIn">
            <div className="progress-header">
                <button className="btn btn-ghost" onClick={() => navigate('/')}>
                    <ArrowLeft size={18} />
                    Back
                </button>

                {!isFinished && (
                    <button className="btn btn-danger btn-sm" onClick={handleCancel}>
                        <XCircle size={16} />
                        Cancel
                    </button>
                )}
            </div>

            <div className="progress-content">
                <div className="progress-main card">
                    <div className="progress-title-section">
                        <h1 className="progress-title">
                            {isCompleted ? '✅ Research Complete!' :
                                isFailed ? '❌ Research Failed' :
                                    isCancelled ? '⏸️ Research Cancelled' :
                                        '🔬 Research in Progress'}
                        </h1>
                        <p className="progress-topic">"{currentStatus.topic}"</p>
                    </div>

                    {/* Progress Tracker */}
                    <ProgressTracker
                        phases={currentStatus.phases}
                        overallProgress={currentStatus.overall_progress}
                    />

                    {/* Stats */}
                    <div className="progress-stats">
                        <div className="stat">
                            <span className="stat-label">Sources Found</span>
                            <span className="stat-value">{currentStatus.sources_found}</span>
                        </div>
                        {currentStatus.estimated_time_remaining && (
                            <div className="stat">
                                <span className="stat-label">Est. Time Remaining</span>
                                <span className="stat-value">
                                    {Math.ceil(currentStatus.estimated_time_remaining / 60)} min
                                </span>
                            </div>
                        )}
                    </div>

                    {/* Error Message */}
                    {normalizedStatusError && (
                        <div className="error-box">
                            <strong>{normalizedStatusError.title}:</strong> {normalizedStatusError.message}
                            {normalizedStatusError.details && (
                                <details className="error-details">
                                    <summary>More details</summary>
                                    <pre>{normalizedStatusError.details}</pre>
                                </details>
                            )}
                        </div>
                    )}

                    {/* Actions */}
                    {isCompleted && (
                        <Link to={`/report/${sessionId}`} className="btn btn-primary btn-lg view-report-btn">
                            <FileText size={20} />
                            View Report
                        </Link>
                    )}
                </div>

                {/* Live Notes */}
                <div className="notes-section card">
                    <h3 className="notes-title">📝 Live Research Notes</h3>
                    <LiveNotes phases={currentStatus.phases} />
                </div>
            </div>
        </div>
    );
}
