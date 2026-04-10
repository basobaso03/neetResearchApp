/**
 * New Research Page - Start a new research session
 */

import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Search, Globe, Database, Zap, ArrowLeft } from 'lucide-react';
import { useResearchStore } from '../store/researchStore';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import './NewResearchPage.css';

type SourceType = 'web' | 'database' | 'both';

export function NewResearchPage() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const initialSource = (searchParams.get('source') as SourceType) || 'web';

    const [topic, setTopic] = useState('');
    const [sourceType, setSourceType] = useState<SourceType>(initialSource);
    const [collectionName, setCollectionName] = useState('');

    const { startResearch, isLoading, error } = useResearchStore();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!topic.trim()) return;

        try {
            const sessionId = await startResearch(
                topic.trim(),
                sourceType,
                sourceType !== 'web' ? collectionName : undefined
            );
            navigate(`/progress/${sessionId}`);
        } catch {
            // Error is handled by the store
        }
    };

    return (
        <div className="new-research-page animate-fadeIn">
            <button className="back-btn btn btn-ghost" onClick={() => navigate(-1)}>
                <ArrowLeft size={18} />
                Back
            </button>

            <div className="new-research-card card">
                <div className="card-header">
                    <h1 className="card-title">
                        <Search size={28} /> New Research
                    </h1>
                </div>

                <p className="page-desc">
                    Enter your research topic below. Our AI will analyze it, gather sources, and generate a comprehensive report.
                </p>

                <form onSubmit={handleSubmit} className="research-form">
                    {/* Topic Input */}
                    <div className="form-group">
                        <label className="label" htmlFor="topic">
                            Research Topic *
                        </label>
                        <textarea
                            id="topic"
                            className="input textarea"
                            placeholder="What would you like to research? Be as specific as possible for better results..."
                            value={topic}
                            onChange={(e) => setTopic(e.target.value)}
                            rows={4}
                            required
                            disabled={isLoading}
                        />
                    </div>

                    {/* Source Selection */}
                    <div className="form-group">
                        <label className="label">Research Source</label>
                        <div className="source-options">
                            <button
                                type="button"
                                className={`source-option ${sourceType === 'web' ? 'active' : ''}`}
                                onClick={() => setSourceType('web')}
                                disabled={isLoading}
                            >
                                <Globe size={24} />
                                <span className="source-title">Web Search</span>
                                <span className="source-desc">Search the internet</span>
                            </button>

                            <button
                                type="button"
                                className={`source-option ${sourceType === 'database' ? 'active' : ''}`}
                                onClick={() => setSourceType('database')}
                                disabled={isLoading}
                            >
                                <Database size={24} />
                                <span className="source-title">Database</span>
                                <span className="source-desc">Your documents</span>
                            </button>

                            <button
                                type="button"
                                className={`source-option ${sourceType === 'both' ? 'active' : ''}`}
                                onClick={() => setSourceType('both')}
                                disabled={isLoading}
                            >
                                <div className="source-icon-group">
                                    <Globe size={18} />
                                    <Database size={18} />
                                </div>
                                <span className="source-title">Hybrid</span>
                                <span className="source-desc">Web + documents</span>
                            </button>
                        </div>
                    </div>

                    {/* Collection Name (for database source) */}
                    {sourceType === 'database' && (
                        <div className="form-group animate-slideUp">
                            <label className="label" htmlFor="collection">
                                Collection Name
                            </label>
                            <input
                                id="collection"
                                type="text"
                                className="input"
                                placeholder="Enter collection name..."
                                value={collectionName}
                                onChange={(e) => setCollectionName(e.target.value)}
                                disabled={isLoading}
                            />
                        </div>
                    )}

                    {/* Error Message */}
                    {error && (
                        <div className="error-message">
                            <span>❌</span> {error}
                        </div>
                    )}

                    {/* Submit Button */}
                    <button
                        type="submit"
                        className="btn btn-primary btn-lg submit-btn"
                        disabled={isLoading || !topic.trim()}
                    >
                        {isLoading ? (
                            <>
                                <LoadingSpinner size="sm" />
                                Starting Research...
                            </>
                        ) : (
                            <>
                                <Zap size={20} />
                                Start Research
                            </>
                        )}
                    </button>
                </form>
            </div>
        </div>
    );
}
