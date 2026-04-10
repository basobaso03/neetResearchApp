/**
 * Report View Page - Display completed research report
 */

import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Download, Copy, Check, Calendar, FileText } from 'lucide-react';
import { api } from '../services/api';
import ReactMarkdown from 'react-markdown';
import { normalizeError } from '../utils/errorHandling';
import './ReportViewPage.css';

interface ReportData {
    session_id: string;
    topic: string;
    content: string;
    created_at: string;
}

export function ReportViewPage() {
    const { sessionId } = useParams<{ sessionId: string }>();
    const navigate = useNavigate();
    const [report, setReport] = useState<ReportData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<{ message: string; details?: string } | null>(null);
    const [copied, setCopied] = useState(false);
    const [showExportMenu, setShowExportMenu] = useState(false);

    useEffect(() => {
        if (sessionId) {
            api.getReportContent(sessionId)
                .then(setReport)
                .catch(err => {
                    const normalized = normalizeError(err, 'Failed to load report');
                    setError({ message: normalized.message, details: normalized.details });
                })
                .finally(() => setLoading(false));
        }
    }, [sessionId]);

    const handleCopy = async () => {
        if (report) {
            await navigator.clipboard.writeText(report.content);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    const handleExport = (format: 'md' | 'pdf') => {
        if (sessionId) {
            window.open(api.getExportUrl(sessionId, format), '_blank');
        }
        setShowExportMenu(false);
    };

    if (loading) {
        return (
            <div className="report-page">
                <div className="loading-state">
                    <div className="spinner spinner-lg" />
                    <p>Loading report...</p>
                </div>
            </div>
        );
    }

    if (error || !report) {
        return (
            <div className="report-page">
                <div className="error-state card">
                    <h2>❌ Failed to load report</h2>
                    <p>{error?.message || 'Report not found'}</p>
                    {error?.details && (
                        <details className="error-details">
                            <summary>More details</summary>
                            <pre>{error.details}</pre>
                        </details>
                    )}
                    <Link to="/" className="btn btn-primary">Go Home</Link>
                </div>
            </div>
        );
    }

    const createdDate = new Date(report.created_at).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });

    return (
        <div className="report-page animate-fadeIn">
            <div className="report-header">
                <button className="btn btn-ghost" onClick={() => navigate(-1)}>
                    <ArrowLeft size={18} />
                    Back
                </button>

                <div className="report-actions">
                    <button className="btn btn-secondary" onClick={handleCopy}>
                        {copied ? <Check size={18} /> : <Copy size={18} />}
                        {copied ? 'Copied!' : 'Copy'}
                    </button>

                    <div className="export-dropdown">
                        <button
                            className="btn btn-primary"
                            onClick={() => setShowExportMenu(!showExportMenu)}
                        >
                            <Download size={18} />
                            Export
                        </button>

                        {showExportMenu && (
                            <div className="export-menu card">
                                <button onClick={() => handleExport('md')} className="export-option">
                                    <FileText size={18} />
                                    Markdown (.md)
                                </button>
                                <button onClick={() => handleExport('pdf')} className="export-option">
                                    <FileText size={18} />
                                    PDF (.pdf)
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            <article className="report-content card">
                <header className="report-meta">
                    <h1 className="report-title">{report.topic}</h1>
                    <div className="report-info">
                        <span className="info-item">
                            <Calendar size={16} />
                            {createdDate}
                        </span>
                    </div>
                </header>

                <div className="markdown-content">
                    <ReactMarkdown>{report.content}</ReactMarkdown>
                </div>
            </article>
        </div>
    );
}
