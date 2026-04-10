/**
 * Live Notes Component - Shows research notes in real-time
 */

import './LiveNotes.css';

interface PhaseProgress {
    phase: string;
    status: string;
    progress: number;
    notes?: string[];
}

interface LiveNotesProps {
    phases: PhaseProgress[];
}

export function LiveNotes({ phases }: LiveNotesProps) {
    // Collect all notes from all phases
    const allNotes = phases.flatMap(phase =>
        (phase.notes || []).map(note => ({
            phase: phase.phase,
            note
        }))
    );

    if (allNotes.length === 0) {
        return (
            <div className="live-notes empty">
                <p className="empty-text">Notes will appear here as research progresses...</p>
            </div>
        );
    }

    return (
        <div className="live-notes">
            <ul className="notes-list">
                {allNotes.map((item, index) => (
                    <li key={index} className="note-item animate-slideUp">
                        <span className="note-bullet">•</span>
                        <span className="note-text">{item.note}</span>
                    </li>
                ))}
            </ul>
        </div>
    );
}
