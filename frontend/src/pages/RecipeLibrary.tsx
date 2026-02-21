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

    useEffect(() => {
        apiClient.get('/recipes/')
            .then(res => {
                setRecipes(res.data);
            })
            .catch(err => console.error("Could not fetch recipes", err))
            .finally(() => setLoading(false));
    }, []);

    return (
        <div className="animate-fade-in">
            <div className="flex justify-between items-center mb-6">
                <h2 style={{ color: 'var(--accent-primary)' }}>Bibliothèque de Recettes</h2>
                <Link to="/recipes/new" className="btn btn-secondary">+ Nouvelle Recette</Link>
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
