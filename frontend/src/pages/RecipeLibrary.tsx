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

            {/* Scraper Section */}
            <div className="glass-card mb-8" style={{ padding: '1.5rem', border: '1px solid var(--accent-secondary)' }}>
                <h3 style={{ marginBottom: '1rem', color: 'var(--text-secondary)' }}>Importer depuis le web</h3>
                <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
                    Saisissez l'URL d'une recette (ex: Marmiton, CuisineAZ) pour pré-remplir l'éditeur automatiquement grâce à l'IA.
                </p>
                <div className="flex gap-4">
                    <input
                        type="url"
                        className="input-field"
                        placeholder="https://www.marmiton.org/..."
                        style={{ flex: 1 }}
                        value={scrapeUrl}
                        onChange={e => setScrapeUrl(e.target.value)}
                    />
                    <button
                        className="btn btn-primary"
                        onClick={handleScrape}
                        disabled={scraping || !scrapeUrl}
                    >
                        {scraping ? 'Analyse...' : 'Importer'}
                    </button>
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
