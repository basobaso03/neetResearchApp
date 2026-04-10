/**
 * Navbar Component
 */

import { Link, useLocation } from 'react-router-dom';
import { Home, History, Search } from 'lucide-react';
import './Navbar.css';

export function Navbar() {
    const location = useLocation();

    const isActive = (path: string) => location.pathname === path;

    return (
        <nav className="navbar">
            <div className="navbar-content">
                <Link to="/" className="navbar-brand">
                    <span className="navbar-logo">🔬</span>
                    <span>NeetResearch</span>
                </Link>

                <div className="navbar-links">
                    <Link
                        to="/"
                        className={`navbar-link ${isActive('/') ? 'active' : ''}`}
                    >
                        <Home size={18} />
                        <span>Home</span>
                    </Link>

                    <Link
                        to="/new"
                        className={`navbar-link ${isActive('/new') ? 'active' : ''}`}
                    >
                        <Search size={18} />
                        <span>New Research</span>
                    </Link>

                    <Link
                        to="/sessions"
                        className={`navbar-link ${isActive('/sessions') ? 'active' : ''}`}
                    >
                        <History size={18} />
                        <span>Sessions</span>
                    </Link>
                </div>
            </div>
        </nav>
    );
}
