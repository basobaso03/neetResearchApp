/**
 * Progress Tracker Component - Visual phase progress display
 */

import { Check, Loader, Circle, AlertCircle } from 'lucide-react';
import './ProgressTracker.css';

interface PhaseProgress {
    phase: string;
    status: string;
    progress: number;
    notes?: string[];
}

interface ProgressTrackerProps {
    phases: PhaseProgress[];
    overallProgress: number;
}

const phaseLabels: Record<string, { label: string; icon: string }> = {
    scoping: { label: 'Scoping', icon: '🎯' },
    researching: { label: 'Researching', icon: '🔬' },
    analyzing: { label: 'Analyzing', icon: '📊' },
    generating: { label: 'Generating', icon: '📝' },
};

export function ProgressTracker({ phases, overallProgress }: ProgressTrackerProps) {
    return (
        <div className="progress-tracker">
            {/* Overall Progress Bar */}
            <div className="overall-progress">
                <div className="progress-bar">
                    <div
                        className={`progress-bar-fill ${overallProgress === 100 ? 'success' : ''}`}
                        style={{ width: `${overallProgress}%` }}
                    />
                </div>
                <span className="progress-percent">{overallProgress}%</span>
            </div>

            {/* Phase Steps */}
            <div className="phase-steps">
                {phases.map((phase, index) => {
                    const phaseInfo = phaseLabels[phase.phase] || { label: phase.phase, icon: '📌' };
                    const isCompleted = phase.status === 'completed';
                    const isActive = phase.status === 'active';
                    const isError = phase.status === 'error';

                    return (
                        <div
                            key={phase.phase}
                            className={`phase-step ${isCompleted ? 'completed' : ''} ${isActive ? 'active' : ''} ${isError ? 'error' : ''}`}
                        >
                            {/* Connector Line */}
                            {index > 0 && (
                                <div className={`phase-connector ${isCompleted || isActive ? 'filled' : ''}`} />
                            )}

                            {/* Icon */}
                            <div className="phase-icon">
                                {isCompleted ? (
                                    <Check size={20} />
                                ) : isActive ? (
                                    <Loader size={20} className="spinning" />
                                ) : isError ? (
                                    <AlertCircle size={20} />
                                ) : (
                                    <Circle size={20} />
                                )}
                            </div>

                            {/* Label */}
                            <div className="phase-info">
                                <span className="phase-emoji">{phaseInfo.icon}</span>
                                <span className="phase-label">{phaseInfo.label}</span>
                                {isActive && (
                                    <span className="phase-progress">{phase.progress}%</span>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
