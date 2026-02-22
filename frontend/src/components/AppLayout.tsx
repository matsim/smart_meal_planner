import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';

const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const location = useLocation();
    const navigate = useNavigate();
    const currentPath = location.pathname;

    const navItems = [
        { path: '/dashboard', label: 'Dashboard', icon: '📊' },
        { path: '/recipes', label: 'Recipes', icon: '📖' },
        // Placeholder for future routes
        { path: '#', label: 'Meal Planner', icon: '📅' },
        { path: '#', label: 'Shopping List', icon: '🛒' },
    ];

    const handleLogout = () => {
        localStorage.removeItem('user_id');
        navigate('/onboarding');
    };

    return (
        <div className="app-container">
            {/* Sidebar */}
            <aside className="app-sidebar flex flex-col justify-between" style={{ padding: '2rem 1rem' }}>
                <div>
                    {/* Branding */}
                    <div className="flex items-center gap-2 mb-8 px-4">
                        <div style={{ width: '32px', height: '32px', borderRadius: '50%', backgroundColor: 'var(--accent-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 'bold' }}>
                            N
                        </div>
                        <div>
                            <h2 style={{ fontSize: '1.25rem', margin: 0 }}>NutriPlan</h2>
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>PRO EDITION</span>
                        </div>
                    </div>

                    {/* Navigation */}
                    <nav className="flex flex-col gap-2">
                        {navItems.map(item => {
                            const isActive = currentPath.startsWith(item.path) && item.path !== '#';
                            return (
                                <Link
                                    key={item.label}
                                    to={item.path}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.75rem',
                                        padding: '0.75rem 1rem',
                                        borderRadius: 'var(--radius-md)',
                                        color: isActive ? 'var(--accent-primary-hover)' : 'var(--text-secondary)',
                                        backgroundColor: isActive ? 'var(--accent-primary-light)' : 'transparent',
                                        fontWeight: isActive ? 600 : 500,
                                        transition: 'all var(--transition-fast)'
                                    }}
                                >
                                    <span style={{ fontSize: '1.2rem' }}>{item.icon}</span>
                                    {item.label}
                                </Link>
                            );
                        })}
                    </nav>
                </div>

                {/* Bottom Profile Section */}
                <div style={{ padding: '1rem', borderTop: '1px solid var(--border-color)' }}>
                    <div className="flex justify-between items-center">
                        <div className="flex items-center gap-2">
                            <div style={{ width: '36px', height: '36px', borderRadius: '50%', backgroundColor: '#e2e8f0', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                                👤
                            </div>
                            <div style={{ lineHeight: '1.2' }}>
                                <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>My Profile</div>
                                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Standard Plan</div>
                            </div>
                        </div>
                        <button
                            onClick={handleLogout}
                            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '1.2rem' }}
                            title="Se déconnecter"
                        >
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                                <polyline points="16 17 21 12 16 7"></polyline>
                                <line x1="21" y1="12" x2="9" y2="12"></line>
                            </svg>
                        </button>
                    </div>
                </div>
            </aside>

            {/* Main Content Area */}
            <main className="app-main">
                {children}
            </main>
        </div>
    );
};

export default AppLayout;
