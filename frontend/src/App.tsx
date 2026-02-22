import { Routes, Route, Link } from 'react-router-dom';
import Onboarding from './pages/Onboarding';
import Dashboard from './pages/Dashboard';
import RecipeLibrary from './pages/RecipeLibrary';
import RecipeDetail from './pages/RecipeDetail';
import RecipeEditor from './pages/RecipeEditor';
import FoodLibrary from './pages/FoodLibrary';
import AppLayout from './components/AppLayout';

function App() {
  return (
    <Routes>
      {/* Routes publiques / hors layout */}
      <Route path="/" element={
        <div className="container animate-fade-in text-center" style={{ marginTop: '10vh' }}>
          <h1 style={{ fontSize: '3rem', marginBottom: '1rem' }}>Des repas optimisés par <span style={{ color: 'var(--accent-primary)' }}>l'IA</span></h1>
          <p style={{ fontSize: '1.2rem', color: 'var(--text-secondary)', maxWidth: '600px', margin: '0 auto 2rem' }}>
            Atteignez vos objectifs de poids sans jamais avoir faim grâce à notre algorithme de Satiété et de Programmation Linéaire.
          </p>
          <Link to="/onboarding" className="btn btn-primary" style={{ fontSize: '1.1rem', padding: '0.8rem 2rem' }}>
            Démarrer
          </Link>
        </div>
      } />
      <Route path="/onboarding" element={
        <div className="container animate-fade-in" style={{ padding: '2rem 0' }}>
          <Onboarding />
        </div>
      } />

      {/* Routes de l'application avec Sidebar */}
      <Route path="/*" element={
        <AppLayout>
          <div className="animate-fade-in container">
            <Routes>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/foods" element={<FoodLibrary />} />
              <Route path="/recipes" element={<RecipeLibrary />} />
              <Route path="/recipes/new" element={<RecipeEditor />} />
              <Route path="/recipes/:id" element={<RecipeDetail />} />
              <Route path="/recipes/:id/edit" element={<RecipeEditor />} />
            </Routes>
          </div>
        </AppLayout>
      } />
    </Routes>
  );
}

export default App;
