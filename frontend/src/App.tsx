import { Routes, Route, Link } from 'react-router-dom';
import Onboarding from './pages/Onboarding';
import Dashboard from './pages/Dashboard';

function App() {
  return (
    <div className="app-layout">
      <nav className="glass-card" style={{ padding: '1rem', marginBottom: '2rem', borderRadius: '0 0 var(--radius-lg) var(--radius-lg)', borderTop: 'none' }}>
        <div className="container flex justify-between items-center">
          <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'var(--accent-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 'bold', fontFamily: 'var(--font-heading)' }}>S</div>
            <span style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'var(--font-heading)' }}>SmartMeal Planner</span>
          </Link>
          <div className="flex gap-4">
            <Link to="/" className="btn btn-secondary">Accueil</Link>
            <Link to="/onboarding" className="btn btn-primary">Mon Profil</Link>
          </div>
        </div>
      </nav>

      <main className="container animate-fade-in">
        <Routes>
          <Route path="/" element={
            <div className="text-center" style={{ marginTop: '10vh' }}>
              <h1 style={{ fontSize: '3rem', marginBottom: '1rem' }}>Des repas optimisés par <span style={{ color: 'var(--accent-primary)' }}>l'IA</span></h1>
              <p style={{ fontSize: '1.2rem', color: 'var(--text-secondary)', maxWidth: '600px', margin: '0 auto 2rem' }}>
                Atteignez vos objectifs de poids sans jamais avoir faim grâce à notre algorithme de Satiété et de Programmation Linéaire.
              </p>
              <Link to="/onboarding" className="btn btn-primary" style={{ fontSize: '1.1rem', padding: '0.8rem 2rem' }}>
                Démarrer
              </Link>
            </div>
          } />
          <Route path="/onboarding" element={<Onboarding />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
