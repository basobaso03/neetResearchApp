/**
 * Loading Spinner Component
 */

import './LoadingSpinner.css';

interface LoadingSpinnerProps {
    size?: 'sm' | 'md' | 'lg';
    message?: string;
}

export function LoadingSpinner({ size = 'md', message }: LoadingSpinnerProps) {
    const sizeClass = size === 'sm' ? 'spinner-sm' : size === 'lg' ? 'spinner-lg' : '';

    return (
        <div className="loading-spinner-container">
            <div className={`spinner ${sizeClass}`} />
            {message && <p className="loading-message">{message}</p>}
        </div>
    );
}

/**
 * Full Page Loading Screen with progress
 */
interface LoadingScreenProps {
    progress?: number;
    message?: string;
}

export function LoadingScreen({ progress, message }: LoadingScreenProps) {
    return (
        <div className="loading-screen">
            <div className="loading-screen-content">
                <div className="loading-logo">🔬</div>
                <h1 className="loading-title">
                    <span>Neet</span>Research
                </h1>

                {progress !== undefined && (
                    <div className="loading-progress">
                        <div className="progress-bar">
                            <div
                                className="progress-bar-fill"
                                style={{ width: `${progress}%` }}
                            />
                        </div>
                        <span className="progress-text">{progress}%</span>
                    </div>
                )}

                {message && (
                    <p className="loading-screen-message">{message}</p>
                )}

                <LoadingSpinner size="lg" />
            </div>
        </div>
    );
}
