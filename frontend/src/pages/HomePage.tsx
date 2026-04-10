/**
 * Home Page Component
 */

import { Link } from 'react-router-dom';
import { Search, Zap, Globe, Database } from 'lucide-react';
import { useResearchStore } from '../store/researchStore';
import { useEffect } from 'react';
import './HomePage.css';

export function HomePage() {
    const { sessions, fetchSessions } = useResearchStore();

    useEffect(() => {
        fetchSessions();
    }, [fetchSessions]);

    const recentSessions = sessions.slice(0, 3);
    const completedCount = sessions.filter(s => s.status === 'completed').length;
    const totalSources = sessions.reduce((sum, s) => sum + s.sources_found, 0);

    const getSourceLabel = (sourceType: 'web' | 'database' | 'both', isWebResearch: boolean) => {
        if (sourceType === 'both') return 'Hybrid';
        return isWebResearch ? 'Web' : 'Database';
    };

    return (
        <div className="home-page animate-fadeIn">
            <div className="home-hero">
                <h1 className="home-title">
                    Welcome to <span>NeetResearch</span> 👋
                </h1>
                <p className="home-subtitle">
                    AI-powered research assistant for comprehensive, accurate research with citations
                </p>
            </div>

            {/* Quick Start Section */}
            <section className="home-section">
                <div className="quick-start-card card">
                    <div className="card-header">
                        <h2 className="card-title">
                            <Search size={24} /> Start New Research
                        </h2>
                    </div>

                    <p className="quick-start-desc">
                        Enter a topic and let our AI research it thoroughly, gathering sources and generating a comprehensive report.
                    </p>

                    <div className="quick-start-options">
                        <Link to="/new?source=web" className="option-card">
                            <Globe size={32} className="option-icon" />
                            <span className="option-title">Web Research</span>
                            <span className="option-desc">Search the internet for sources</span>
                        </Link>

                        <Link to="/new?source=database" className="option-card">
                            <Database size={32} className="option-icon" />
                            <span className="option-title">Database Research</span>
                            <span className="option-desc">Use your document library</span>
                        </Link>

                        <Link to="/new?source=both" className="option-card">
                            <div className="option-icon-group">
                                <Globe size={24} className="option-icon" />
                                <Database size={24} className="option-icon" />
                            </div>
                            <span className="option-title">Hybrid Research</span>
                            <span className="option-desc">Use web and your documents</span>
                        </Link>
                    </div>

                    <Link to="/new" className="btn btn-primary btn-lg start-btn">
                        <Zap size={20} />
                        Start Research
                    </Link>
                </div>
            </section>

            {/* Stats and Recent Sessions */}
            <div className="home-grid">
                {/* Statistics */}
                <section className="stats-section">
                    <h3 className="section-title">📊 Your Stats</h3>
                    <div className="stats-grid">
                        <div className="stat-card card">
                            <span className="stat-value">{sessions.length}</span>
                            <span className="stat-label">Total Researches</span>
                        </div>
                        <div className="stat-card card">
                            <span className="stat-value">{completedCount}</span>
                            <span className="stat-label">Completed</span>
                        </div>
                        <div className="stat-card card">
                            <span className="stat-value">{totalSources}</span>
                            <span className="stat-label">Sources Found</span>
                        </div>
                    </div>
                </section>

                {/* Recent Sessions */}
                <section className="recent-section">
                    <div className="section-header">
                        <h3 className="section-title">📋 Recent Sessions</h3>
                        <Link to="/sessions" className="btn btn-ghost btn-sm">
                            View All
                        </Link>
                    </div>

                    {recentSessions.length > 0 ? (
                        <div className="recent-list">
                            {recentSessions.map((session) => (
                                <Link
                                    key={session.session_id}
                                    to={session.has_report ? `/report/${session.session_id}` : `/progress/${session.session_id}`}
                                    className="recent-item card"
                                >
                                    <div className="recent-item-header">
                                        <span className={`status-badge ${session.status}`}>
                                            {session.status === 'completed' && '✅'}
                                            {session.status === 'failed' && '❌'}
                                            {session.status === 'cancelled' && '⏸️'}
                                            {!['completed', 'failed', 'cancelled'].includes(session.status) && '🔄'}
                                        </span>
                                        <span className="recent-topic">{session.topic.slice(0, 50)}...</span>
                                    </div>
                                    <div className="recent-meta">
                                        <span>{getSourceLabel(session.source_type, session.is_web_research)}</span>
                                        <span>{session.sources_found} sources</span>
                                        <span>{session.progress}%</span>
                                    </div>
                                </Link>
                            ))}
                        </div>
                    ) : (
                        <div className="empty-state card">
                            <p>No research sessions yet. Start your first one!</p>
                        </div>
                    )}
                </section>
            </div>
        </div>
    );
}
