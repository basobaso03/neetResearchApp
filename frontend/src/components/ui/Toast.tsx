/**
 * Toast Component - Notification display
 */

import { X } from 'lucide-react';
import { useResearchStore } from '../../store/researchStore';
import './Toast.css';

export function ToastContainer() {
    const { toasts, removeToast } = useResearchStore();

    if (toasts.length === 0) return null;

    return (
        <div className="toast-container">
            {toasts.map((toast) => (
                <div key={toast.id} className={`toast ${toast.type}`}>
                    <span className="toast-icon">
                        {toast.type === 'success' && '✅'}
                        {toast.type === 'error' && '❌'}
                        {toast.type === 'warning' && '⚠️'}
                        {toast.type === 'info' && 'ℹ️'}
                    </span>
                    <div className="toast-content">
                        <span className="toast-message">{toast.message}</span>
                        {toast.details && (
                            <details className="toast-details">
                                <summary>More details</summary>
                                <pre>{toast.details}</pre>
                            </details>
                        )}
                    </div>
                    <button
                        className="toast-close"
                        onClick={() => removeToast(toast.id)}
                        aria-label="Close"
                    >
                        <X size={16} />
                    </button>
                </div>
            ))}
        </div>
    );
}
