import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiClient from '../api/client';

interface Ingredient {
    id: number;
    food_id: number;
    food_name?: string; // We'll need the backend or a join to get this cleanly, or just format
    quantity_g: number;
}

interface RecipeDetail {
    id: number;
    name: string;
    description: string;
    type: string;
    instructions: string;
    preparation_time_minutes: number;
    energy_density: number;
    satiety_index: number;
    internal_nutrition_score: number;
    ingredients: Ingredient[];
}

const RecipeDetailView: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const [recipe, setRecipe] = useState<RecipeDetail | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        apiClient.get(`/recipes/${id}`)
            .then(res => setRecipe(res.data))
            .catch(err => console.error("Error fetching recipe details", err))
            .finally(() => setLoading(false));
    }, [id]);

    if (loading) return <div className="text-center mt-8">Chargement de la recette...</div>;
    if (!recipe) return <div className="text-center mt-8 text-danger">Recette introuvable.</div>;

    return (
        <div className="animate-fade-in glass-card" style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
            <button className="btn btn-secondary mb-6" onClick={() => navigate('/recipes')}>
                ← Retour à la bibliothèque
            </button>

            <h1 style={{ color: 'var(--accent-primary)', marginBottom: '0.5rem' }}>{recipe.name}</h1>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>{recipe.description}</p>

            <div className="flex gap-4 mb-6" style={{ flexWrap: 'wrap' }}>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: 'var(--radius-md)', flex: 1, minWidth: '150px' }}>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Temps de Prép.</span>
                    <div style={{ fontSize: '1.2rem', fontWeight: 600 }}>{recipe.preparation_time_minutes} min</div>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: 'var(--radius-md)', flex: 1, minWidth: '150px' }}>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Indice de Satiété</span>
                    <div style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--accent-primary)' }}>{recipe.satiety_index ?? 'N/A'}</div>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: 'var(--radius-md)', flex: 1, minWidth: '150px' }}>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Densité Énergétique</span>
                    <div style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--accent-secondary)' }}>{recipe.energy_density ?? 'N/A'}</div>
                </div>
            </div>

            <div style={{ marginBottom: '2rem' }}>
                <h3 style={{ borderBottom: '1px solid var(--border-glass)', paddingBottom: '0.5rem', marginBottom: '1rem' }}>Ingrédients</h3>
                {recipe.ingredients && recipe.ingredients.length > 0 ? (
                    <ul style={{ listStyleType: 'none', padding: 0 }}>
                        {recipe.ingredients.map(ing => (
                            <li key={ing.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.75rem 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                <span>{ing.food_name || `Aliment # ${ing.food_id}`}</span>
                                <strong style={{ color: 'var(--text-secondary)' }}>{ing.quantity_g} g</strong>
                            </li>
                        ))}
                    </ul>
                ) : (
                    <p style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>Aucun ingrédient renseigné pour cette recette.</p>
                )}
            </div>

            {recipe.instructions && (
                <div>
                    <h3 style={{ borderBottom: '1px solid var(--border-glass)', paddingBottom: '0.5rem', marginBottom: '1rem' }}>Instructions</h3>
                    <div style={{ whiteSpace: 'pre-line', color: 'var(--text-secondary)', lineHeight: '1.8' }}>
                        {recipe.instructions}
                    </div>
                </div>
            )}

            <div className="mt-8 text-center">
                <button className="btn btn-secondary text-muted" onClick={() => alert('Édition en cours de développement...')}>
                    Modifier la recette
                </button>
            </div>
        </div>
    );
};

export default RecipeDetailView;
