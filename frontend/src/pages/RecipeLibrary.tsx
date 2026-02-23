import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import apiClient from '../api/client';

interface Recipe {
    id: number;
    name: string;
    type: string;
    energy_density: number;
    satiety_index: number;
}

const RecipeLibrary: React.FC = () => {
    const [recipes, setRecipes] = useState<Recipe[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const location = useLocation();

    // Scraper state
    const [scrapeUrl, setScrapeUrl] = useState('');
    const [scraping, setScraping] = useState(false);

    useEffect(() => {
        setLoading(true);
        apiClient.get('/recipes/')
            .then(res => {
                setRecipes(res.data);
            })
            .catch(err => console.error("Could not fetch recipes", err))
            .finally(() => setLoading(false));
    }, [location.key]); // Re-fetch every time we navigate to this page

    const handleScrape = async () => {
        if (!scrapeUrl) return;
        setScraping(true);
        try {
            // 1. Démarrer la tâche d'extraction en asynchrone
            const initRes = await apiClient.post(`/recipes/import?url=${encodeURIComponent(scrapeUrl)}`);
            const taskId = initRes.data.task_id;

            if (!taskId) {
                throw new Error("Impossible d'initialiser l'extraction");
            }

            // 2. Polling du statut
            const pollInterval = setInterval(async () => {
                try {
                    const statusRes = await apiClient.get(`/recipes/import/status/${taskId}`);
                    const statusInfo = statusRes.data;

                    if (statusInfo.status === 'completed') {
                        clearInterval(pollInterval);
                        sessionStorage.setItem('scrapedRecipe', JSON.stringify(statusInfo.data));
                        window.location.href = '/recipes/new?fromScraper=true';
                    } else if (statusInfo.status === 'failed') {
                        clearInterval(pollInterval);
                        setScraping(false);
                        alert(`Échec de l'extraction: ${statusInfo.error}`);
                    }
                    // Si 'pending', on continue au prochain cycle
                } catch (err) {
                    clearInterval(pollInterval);
                    setScraping(false);
                    console.error("Erreur lors du suivi du statut", err);
                    alert("Erreur de communication avec le serveur.");
                }
            }, 2000); // Poll toutes les 2 secondes

        } catch (error) {
            console.error(error);
            setScraping(false);
            alert("Erreur lors de l'initialisation de l'extraction.");
        }
    };

    return (
        <div className="animate-fade-in">
            <div className="flex justify-between items-center mb-6">
                <h2 style={{ color: 'var(--accent-primary)' }}>Bibliothèque de Recettes</h2>
                <Link to="/recipes/new" className="btn btn-secondary">+ Nouvelle Recette</Link>
            </div>

            {/* Search bar */}
            <div className="mb-6">
                <input
                    type="text"
                    className="input-field"
                    placeholder="🔍 Rechercher une recette..."
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    style={{ width: '100%', maxWidth: '400px' }}
                />
            </div>

            {/* Scraper Section (Redesigned) */}
            <div className="glass-card mb-8">
                <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--border-color)' }}>
                    <h3 style={{ margin: 0, fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{ color: 'var(--accent-primary)' }}>🔗</span> Import & Smart Mapping
                    </h3>
                </div>
                <div style={{ padding: '2rem' }}>
                    <div className="flex flex-col gap-2 mb-4">
                        <label className="input-label" htmlFor="recipeUrl">Recipe Source URL</label>
                        <div className="flex gap-4">
                            <input
                                id="recipeUrl"
                                type="url"
                                className="input-field"
                                placeholder="Paste URL from Marmiton, CuisineAZ, etc..."
                                style={{ flex: 1, padding: '1rem', fontSize: '1rem' }}
                                value={scrapeUrl}
                                onChange={e => setScrapeUrl(e.target.value)}
                            />
                            <button
                                className="btn btn-primary"
                                style={{ padding: '0 2rem', fontWeight: 600 }}
                                onClick={handleScrape}
                                disabled={scraping || !scrapeUrl}
                            >
                                {scraping ? 'Analyzing...' : 'Analyze URL'}
                            </button>
                        </div>
                        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                            Our AI will automatically extract ingredients and map them to our internal nutrition database.
                        </p>
                    </div>
                </div>
            </div>

            {loading ? (
                <div className="text-center">Chargement des recettes...</div>
            ) : (
                <div className="week-grid">
                    {recipes
                        .filter(r => !searchQuery || r.name.toLowerCase().includes(searchQuery.toLowerCase()))
                        .map(recipe => (
                            <Link
                                to={`/recipes/${recipe.id}`}
                                key={recipe.id}
                                className="glass-card"
                                style={{ padding: '1.5rem', display: 'block', textDecoration: 'none', color: 'inherit' }}
                            >
                                <h3 style={{ marginBottom: '0.5rem' }}>{recipe.name}</h3>
                                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '1rem' }}>
                                    Type: {recipe.type}
                                </p>

                                <div className="flex justify-between mt-auto pt-4" style={{ borderTop: '1px solid var(--border-glass)' }}>
                                    <div style={{ textAlign: 'center' }}>
                                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Indice Satiété</span>
                                        <strong style={{ color: 'var(--accent-primary)' }}>{recipe.satiety_index ?? 'N/A'}</strong>
                                    </div>
                                    <div style={{ textAlign: 'center' }}>
                                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Densité (DE)</span>
                                        <strong style={{ color: 'var(--accent-secondary)' }}>{recipe.energy_density ?? 'N/A'}</strong>
                                    </div>
                                </div>
                            </Link>
                        ))}
                </div>
            )}

            {!loading && recipes.length === 0 && (
                <p className="text-center mt-8">Aucune recette trouvée.</p>
            )}
        </div>
    );
};

export default RecipeLibrary;
