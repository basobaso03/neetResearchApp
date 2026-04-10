/**
 * Main Layout Component
 */

import { Outlet } from 'react-router-dom';
import { Navbar } from './Navbar';
import { ToastContainer } from '../ui/Toast';
import { LoadingScreen } from '../ui/LoadingSpinner';
import { useInitialization } from '../../hooks/useInitialization';
import { useResearchStore } from '../../store/researchStore';
import './Layout.css';

export function Layout() {
    const initStatus = useInitialization();
    const { isBackendReady } = useResearchStore();

    // Show loading screen while backend initializes
    if (!isBackendReady) {
        return (
            <LoadingScreen
                progress={initStatus?.progress ?? 0}
                message={initStatus?.message ?? 'Starting up...'}
            />
        );
    }

    return (
        <div className="layout">
            <Navbar />
            <main className="main-content">
                <div className="container">
                    <Outlet />
                </div>
            </main>
            <ToastContainer />
        </div>
    );
}
