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
        <div className="animate-fade-in pb-8">
            <div className="mb-4">
                <button className="btn btn-secondary text-sm" style={{ padding: '0.4rem 0.8rem' }} onClick={() => navigate(-1)}>
                    ← Back
                </button>
            </div>

            {/* Banner Image Placeholder */}
            <div className="w-full relative rounded-lg overflow-hidden mb-8" style={{ height: '300px', backgroundColor: '#e2e8f0' }}>
                <div className="absolute inset-0" style={{ background: 'linear-gradient(to top, rgba(0,0,0,0.8) 0%, rgba(0,0,0,0) 100%)' }}></div>
                <div className="absolute bottom-6 left-6 text-white">
                    <div className="badge mb-2" style={{ backgroundColor: 'rgba(255,255,255,0.2)', color: 'white' }}>
                        Source: Database
                    </div>
                    <h1 style={{ color: 'white', margin: 0, fontSize: '2.5rem' }}>{recipe.name}</h1>
                    <div className="flex gap-4 mt-2 text-sm opacity-90">
                        <span>⏱ {recipe.preparation_time_minutes} min Prep</span>
                        <span>🔥 {Math.round((recipe.energy_density || 1) * 400)} kcal</span>
                    </div>
                </div>
            </div>

            <div className="flex gap-8 flex-col md:flex-row">
                {/* Left Column (Servings, Ingredients, Macros) */}
                <div style={{ width: '320px', flexShrink: 0 }} className="flex flex-col gap-6">

                    {/* Ingredients Card */}
                    <div className="glass-card p-6" style={{ padding: '1.5rem' }}>
                        <div className="flex justify-between items-center mb-4">
                            <h3 style={{ margin: 0, fontSize: '1.2rem' }}>Ingredients</h3>
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{recipe.ingredients.length} items</span>
                        </div>

                        {recipe.ingredients && recipe.ingredients.length > 0 ? (
                            <ul style={{ listStyleType: 'none', padding: 0, margin: 0 }}>
                                {recipe.ingredients.map(ing => (
                                    <li key={ing.id} className="flex justify-between items-center" style={{ padding: '0.75rem 0', borderBottom: '1px solid var(--border-color)' }}>
                                        <div className="flex items-center gap-3">
                                            <input type="checkbox" style={{ width: '16px', height: '16px', accentColor: 'var(--accent-primary)' }} />
                                            <span style={{ fontSize: '0.9rem', color: 'var(--text-primary)' }}>{ing.food_name || `Aliment # ${ing.food_id}`}</span>
                                        </div>
                                        <strong style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>{ing.quantity_g}g</strong>
                                    </li>
                                ))}
                            </ul>
                        ) : (
                            <p style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontSize: '0.9rem' }}>Aucun ingrédient renseigné.</p>
                        )}

                        <button className="btn btn-secondary w-full mt-4" style={{ color: 'var(--accent-primary)', borderColor: 'var(--accent-primary-light)', backgroundColor: 'var(--accent-primary-light)' }}>
                            🛒 Add to Shopping List
                        </button>
                    </div>

                    {/* Macros Card (Placeholder values based on BD) */}
                    <div className="glass-card" style={{ padding: '1.5rem' }}>
                        <h3 style={{ margin: 0, marginBottom: '1rem', fontSize: '1rem', color: 'var(--text-secondary)' }}>MACROS PER SERVING</h3>

                        <div className="mb-3">
                            <div className="flex justify-between text-sm mb-1">
                                <span>Protein</span>
                                <strong>32g</strong>
                            </div>
                            <div style={{ width: '100%', height: '6px', backgroundColor: 'var(--border-color)', borderRadius: '3px' }}>
                                <div style={{ width: '45%', height: '100%', backgroundColor: 'var(--accent-primary)', borderRadius: '3px' }}></div>
                            </div>
                        </div>

                        <div className="mb-3">
                            <div className="flex justify-between text-sm mb-1">
                                <span>Carbs</span>
                                <strong>12g</strong>
                            </div>
                            <div style={{ width: '100%', height: '6px', backgroundColor: 'var(--border-color)', borderRadius: '3px' }}>
                                <div style={{ width: '25%', height: '100%', backgroundColor: 'var(--accent-secondary)', borderRadius: '3px' }}></div>
                            </div>
                        </div>

                        <div>
                            <div className="flex justify-between text-sm mb-1">
                                <span>Fat</span>
                                <strong>18g</strong>
                            </div>
                            <div style={{ width: '100%', height: '6px', backgroundColor: 'var(--border-color)', borderRadius: '3px' }}>
                                <div style={{ width: '35%', height: '100%', backgroundColor: 'var(--accent-warning)', borderRadius: '3px' }}></div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Right Column (Performance, Instructions) */}
                <div className="flex-1 flex flex-col gap-6">

                    {/* Performance Analysis Card */}
                    <div className="glass-card" style={{ padding: '1.5rem' }}>
                        <h3 style={{ margin: 0, marginBottom: '1.5rem', fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span style={{ color: 'var(--accent-primary)' }}>📈</span> Performance Analysis
                        </h3>

                        <div className="flex flex-col gap-4">
                            <div className="flex justify-between items-center p-3 rounded" style={{ backgroundColor: '#f8fafc' }}>
                                <div>
                                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Energy Density</div>
                                    <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{recipe.energy_density ? recipe.energy_density.toFixed(1) : '1.2'} <span style={{ fontSize: '0.8rem', fontWeight: 'normal', color: 'var(--text-muted)' }}>kcal/g</span></div>
                                </div>
                                <div className="badge">Low Density</div>
                            </div>

                            <div className="flex justify-between items-center p-3 rounded" style={{ backgroundColor: '#f8fafc' }}>
                                <div>
                                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Satiety Index</div>
                                    <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{recipe.satiety_index ? Math.round(recipe.satiety_index) : '85'}<span style={{ fontSize: '1rem', color: 'var(--text-muted)' }}>/100</span></div>
                                </div>
                                <div style={{ width: '40px', height: '40px', borderRadius: '50%', border: '4px solid var(--accent-primary)' }}></div>
                            </div>
                        </div>
                    </div>

                    {/* Instructions Card */}
                    <div className="glass-card flex-1" style={{ padding: '2rem' }}>
                        <div className="flex justify-between items-center mb-6">
                            <h2 style={{ margin: 0, fontSize: '1.5rem' }}>Instructions</h2>
                            <button className="btn btn-secondary text-sm px-3 py-1 bg-transparent border-none">👁 Kitchen View</button>
                        </div>

                        <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem', lineHeight: '1.6' }}>{recipe.description}</p>

                        <div className="flex flex-col gap-6">
                            {recipe.instructions ? (
                                recipe.instructions.split('\n').filter(line => line.trim() !== '').map((step, idx) => (
                                    <div key={idx} className="flex gap-4">
                                        <div style={{ flexShrink: 0, width: '32px', height: '32px', borderRadius: '50%', backgroundColor: 'var(--accent-primary-light)', color: 'var(--accent-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold' }}>
                                            {idx + 1}
                                        </div>
                                        <div style={{ paddingTop: '5px', lineHeight: '1.6', color: 'var(--text-primary)' }}>
                                            {step}
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <p style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>Aucune instruction détaillée fournie.</p>
                            )}
                        </div>

                        <div className="mt-8 text-center pt-8" style={{ borderTop: '1px solid var(--border-color)' }}>
                            <button className="btn btn-secondary text-muted" onClick={() => navigate(`/recipes/${recipe.id}/edit`)}>
                                ✏️ Edit Recipe
                            </button>
                        </div>
                    </div>

                </div>
            </div>
        </div>
    );
};

export default RecipeDetailView;
