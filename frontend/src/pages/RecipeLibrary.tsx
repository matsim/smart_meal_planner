import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
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

    // Scraper state
    const [scrapeUrl, setScrapeUrl] = useState('');
    const [scraping, setScraping] = useState(false);

    useEffect(() => {
        apiClient.get('/recipes/')
            .then(res => {
                setRecipes(res.data);
            })
            .catch(err => console.error("Could not fetch recipes", err))
            .finally(() => setLoading(false));
    }, []);

    const handleScrape = async () => {
        if (!scrapeUrl) return;
        setScraping(true);
        try {
            const res = await apiClient.post(`/recipes/scrape?url=${encodeURIComponent(scrapeUrl)}`);
            if (res.data.success && res.data.data) {
                // Pass scraped data via sessionStorage since it's a simple redirection
                sessionStorage.setItem('scrapedRecipe', JSON.stringify(res.data.data));
                window.location.href = '/recipes/new?fromScraper=true';
            }
        } catch (error) {
            console.error(error);
            alert("Erreur lors de l'extraction de la recette.");
        } finally {
            setScraping(false);
        }
    };

    return (
        <div className="animate-fade-in">
            <div className="flex justify-between items-center mb-6">
                <h2 style={{ color: 'var(--accent-primary)' }}>Bibliothèque de Recettes</h2>
                <Link to="/recipes/new" className="btn btn-secondary">+ Nouvelle Recette</Link>
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
                    {recipes.map(recipe => (
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
