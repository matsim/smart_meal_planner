import React, { useState, useEffect } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import apiClient from '../api/client';
import { mapScrapedIngredients } from '../utils/ingredientMapper';

interface IngredientInput {
    food_id: number;
    food_name: string;
    quantity_g: number;
}

interface FoodOption {
    id: number;
    name: string;
    is_draft?: boolean;
}

const RecipeEditor: React.FC = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const { id } = useParams<{ id: string }>();
    const isEditing = Boolean(id);

    const [loading, setLoading] = useState(false);
    const [foods, setFoods] = useState<FoodOption[]>([]);

    // Form state
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [recipeType, setRecipeType] = useState('complete');
    const [ingredients, setIngredients] = useState<IngredientInput[]>([]);

    // Ingredient picker state
    const [selectedFoodId, setSelectedFoodId] = useState<number | ''>('');
    const [selectedQty, setSelectedQty] = useState<number | ''>('');

    useEffect(() => {
        const loadInitialData = async () => {
            // 1. Fetch foods for dropdown
            let loadedFoods: FoodOption[] = [];
            try {
                const res = await apiClient.get('/foods/?limit=1000');
                loadedFoods = res.data;
                setFoods(loadedFoods);
            } catch (err) {
                console.error("Error fetching foods:", err);
            }

            // 2. Intercept Scraped data
            const searchParams = new URLSearchParams(location.search);
            if (searchParams.get('fromScraper') === 'true') {
                const raw = sessionStorage.getItem('scrapedRecipe');
                if (raw) {
                    try {
                        const parsed = JSON.parse(raw);
                        setName(parsed.title || parsed.name || '');

                        const descParts = [];
                        if (parsed.description) descParts.push(parsed.description);

                        if (parsed.ingredients && Array.isArray(parsed.ingredients)) {
                            descParts.push("--- Ingrédients extraits ---");
                            descParts.push(parsed.ingredients.join('\n'));
                            descParts.push("----------------------------");

                            // Map ingredients string to valid DB foods
                            const mapped = await mapScrapedIngredients(parsed.ingredients, loadedFoods);
                            setIngredients(mapped);
                        }

                        if (parsed.instructions) {
                            descParts.push("--- Instructions ---");
                            descParts.push(parsed.instructions);
                        }

                        setDescription(descParts.join('\n\n'));
                    } catch (e) {
                        console.error("Could not parse scraped recipe", e);
                    }
                    sessionStorage.removeItem('scrapedRecipe');
                }
            }

            // 3. If edit mode, fetch existing recipe
            if (isEditing) {
                try {
                    const res = await apiClient.get(`/recipes/${id}`);
                    const r = res.data;
                    setName(r.name);
                    setDescription(r.description || '');
                    setRecipeType(r.type || 'complete');

                    if (r.ingredients) {
                        setIngredients(r.ingredients.map((ing: any) => ({
                            food_id: ing.food_id || 0,
                            food_name: ing.food ? ing.food.name : `Food #${ing.food_id}`,
                            quantity_g: ing.quantity_g
                        })));
                    }
                } catch (err) {
                    console.error("Could not fetch recipe for edit:", err);
                }
            }
        };

        loadInitialData();
    }, [id, isEditing, location.search]);

    const addIngredient = () => {
        if (!selectedFoodId || !selectedQty) return;
        const food = foods.find(f => f.id === Number(selectedFoodId));
        if (!food) return;

        setIngredients(prev => [
            ...prev,
            { food_id: food.id, food_name: food.name, quantity_g: Number(selectedQty) }
        ]);
        setSelectedFoodId('');
        setSelectedQty('');
    };

    const removeIngredient = (index: number) => {
        setIngredients(prev => prev.filter((_, i) => i !== index));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);

        const payload = {
            name,
            description,
            type: recipeType,
            visibility: 'global',
            ingredients_food: ingredients.map(ing => ({
                food_id: ing.food_id,
                quantity_g: ing.quantity_g,
                state: 'raw'
            }))
        };

        try {
            if (isEditing) {
                // Backend MVP ne supporte pas PUT /recipes/ sans l'implémenter, mais on essaie.
                await apiClient.put(`/recipes/${id}`, payload);
                alert("Recette mise à jour !");
                navigate(`/recipes/${id}`);
            } else {
                const res = await apiClient.post('/recipes/', payload);
                alert("Recette créée !");
                navigate(`/recipes/${res.data.id}`);
            }
        } catch (error) {
            console.error(error);
            alert("Erreur lors de la sauvegarde.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="animate-fade-in glass-card" style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
            <button className="btn btn-secondary mb-6" onClick={() => navigate(-1)}>
                ← Retour
            </button>

            <h2 style={{ color: 'var(--accent-primary)', marginBottom: '1.5rem' }}>
                {isEditing ? 'Modifier la recette' : 'Créer une nouvelle recette'}
            </h2>

            <form onSubmit={handleSubmit}>
                <div className="input-group">
                    <label className="input-label">Nom du plat</label>
                    <input className="input-field" value={name} onChange={e => setName(e.target.value)} required placeholder="Ex: Poulet Basquaise" />
                </div>

                <div className="input-group">
                    <label className="input-label">Type de repas</label>
                    <select className="input-field" value={recipeType} onChange={e => setRecipeType(e.target.value)}>
                        <option value="complete">Plat Complet</option>
                        <option value="simple">Assemblage Simple</option>
                        <option value="mixed">Mixte</option>
                    </select>
                </div>

                <div className="input-group">
                    <label className="input-label">Description (optionnelle)</label>
                    <textarea
                        className="input-field"
                        value={description}
                        onChange={e => setDescription(e.target.value)}
                        placeholder="Un délicieux plat équilibré..."
                        rows={6}
                        style={{ fontFamily: 'inherit', resize: 'vertical' }}
                    />
                </div>

                {/* Ingredients section */}
                <div className="glass-card mt-6 mb-6" style={{ padding: '1.5rem', border: '1px solid var(--border-glass)' }}>
                    <h3 style={{ marginBottom: '1rem', color: 'var(--text-secondary)' }}>Composition (Ingrédients)</h3>

                    <ul style={{ listStyleType: 'none', padding: 0, marginBottom: '1rem' }}>
                        {ingredients.map((ing, idx) => (
                            <li key={idx} className="flex justify-between items-center" style={{ padding: '0.5rem', background: 'rgba(0,0,0,0.2)', marginBottom: '0.5rem', borderRadius: 'var(--radius-sm)' }}>
                                <span>{ing.food_name} <strong style={{ color: 'var(--text-secondary)' }}>({ing.quantity_g} g)</strong></span>
                                <button type="button" onClick={() => removeIngredient(idx)} style={{ color: 'var(--accent-danger)', background: 'transparent', border: 'none', cursor: 'pointer' }}>✖ Retirer</button>
                            </li>
                        ))}
                        {ingredients.length === 0 && <li style={{ color: 'var(--text-muted)' }}>Aucun ingrédient ajouté.</li>}
                    </ul>

                    <div className="flex gap-2">
                        <select
                            className="input-field"
                            style={{ flex: 3 }}
                            value={selectedFoodId}
                            onChange={e => setSelectedFoodId(Number(e.target.value))}
                        >
                            <option value="">-- Choisir un aliment --</option>
                            {foods.map(f => (
                                <option key={f.id} value={f.id}>{f.name} {f.is_draft ? '(Brouillon - À enrichir)' : ''}</option>
                            ))}
                        </select>
                        <input
                            className="input-field"
                            type="number"
                            placeholder="Grammes"
                            style={{ flex: 1 }}
                            value={selectedQty}
                            onChange={e => setSelectedQty(e.target.value === '' ? '' : Number(e.target.value))}
                            min="1"
                        />
                        <button type="button" className="btn btn-secondary" onClick={addIngredient}>Ajouter</button>
                    </div>
                </div>

                <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '1rem' }} disabled={loading}>
                    {loading ? 'Sauvegarde en cours...' : (isEditing ? 'Mettre à jour la recette' : 'Enregistrer la recette')}
                </button>
            </form>
        </div>
    );
};

export default RecipeEditor;
