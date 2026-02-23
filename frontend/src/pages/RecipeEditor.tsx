import React, { useState, useEffect } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import apiClient from '../api/client';
import { mapScrapedIngredients } from '../utils/ingredientMapper';

interface IngredientInput {
    status?: 'matched' | 'unresolved' | 'to_create';
    suggested_name?: string;
    food_id?: number;
    food_name?: string;
    food_density?: number;   // g/ml — utilisé pour convertir les unités volumétriques
    quantity_g: number;
    raw_quantity?: number | null;
    raw_unit?: string | null;
    // Portions nommées disponibles pour cet aliment
    food_portions?: FoodPortion[];
    food_portion_id?: number | null;
}

interface FoodOption {
    id: number;
    name: string;
    is_draft?: boolean;
}

interface FoodPortion {
    id: number;
    name: string;
    weight_g: number;
    is_default: boolean;
}

const UNIT_OPTIONS = [
    { value: '', label: '-' },
    { value: 'g', label: 'g' },
    { value: 'kg', label: 'kg' },
    { value: 'ml', label: 'ml' },
    { value: 'cl', label: 'cl' },
    { value: 'L', label: 'L' },
    { value: 'c.à.s', label: 'c.à.s' },
    { value: 'c.à.c', label: 'c.à.c' },
    { value: 'tasse', label: 'tasse' },
    { value: 'verre', label: 'verre' },
    { value: 'bol', label: 'bol' },
    { value: 'pincée', label: 'pincée' },
    { value: 'gousse', label: 'gousse(s)' },
    { value: 'tranche', label: 'tranche(s)' },
    { value: 'filet', label: 'filet(s)' },
    { value: 'feuille', label: 'feuille(s)' },
    { value: 'brin', label: 'brin(s)' },
    { value: 'poignée', label: 'poignée(s)' },
    { value: 'boîte', label: 'boîte(s)' }
];

// Volume en ml par unité — utilisé pour convertir via densité (g = qty × ml × density)
const VOLUMETRIC_ML: Record<string, number> = {
    'c.à.s': 15,
    'c.à.c': 5,
    'tasse': 240,
    'verre': 200,
    'bol': 350,
    'cl': 10,
    'L': 1000,
};

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

    // Loading state for OFF searches
    const [isSearchingOFF, setIsSearchingOFF] = useState<Record<number, boolean>>({});
    const [offResults, setOffResults] = useState<Record<number, any[]>>({});

    // Loading state for local DB searches
    const [isSearchingLocal, setIsSearchingLocal] = useState<Record<number, boolean>>({});
    const [localResults, setLocalResults] = useState<Record<number, any[]>>({});
    const [localSearch, setLocalSearch] = useState<Record<number, string>>({});

    // Modal d'édition d'aliment
    interface FoodEditData {
        ingIdx: number;       // pour refresh l'ingrédient après
        food_id: number;
        name: string;
        energy_kcal: number;
        proteins_g: number;
        fat_g: number;
        carbohydrates_g: number;
        density: number;
        portions: FoodPortion[];
    }
    const [editingFood, setEditingFood] = useState<FoodEditData | null>(null);
    const [editFoodSaving, setEditFoodSaving] = useState(false);
    const [editFoodPortionName, setEditFoodPortionName] = useState('');
    const [editFoodPortionWeight, setEditFoodPortionWeight] = useState<number | ''>('');
    const [editFoodPortionDefault, setEditFoodPortionDefault] = useState(false);
    const [editFoodPortionSaving, setEditFoodPortionSaving] = useState(false);

    const openFoodEdit = async (ingIdx: number, food_id: number, food_name: string) => {
        try {
            const [foodRes, portRes] = await Promise.all([
                apiClient.get(`/foods/${food_id}`),
                apiClient.get(`/foods/${food_id}/portions`)
            ]);
            const f = foodRes.data;
            setEditingFood({
                ingIdx, food_id,
                name: f.name,
                energy_kcal: f.energy_kcal,
                proteins_g: f.proteins_g,
                fat_g: f.fat_g,
                carbohydrates_g: f.carbohydrates_g,
                density: f.density ?? 1.0,
                portions: portRes.data || []
            });
            setEditFoodPortionName('');
            setEditFoodPortionWeight('');
            setEditFoodPortionDefault(false);
        } catch {
            alert('Impossible de charger les données.');
        }
    };

    const saveEditFood = async () => {
        if (!editingFood) return;
        setEditFoodSaving(true);
        try {
            await apiClient.put(`/foods/${editingFood.food_id}`, {
                name: editingFood.name,
                energy_kcal: editingFood.energy_kcal,
                proteins_g: editingFood.proteins_g,
                fat_g: editingFood.fat_g,
                carbohydrates_g: editingFood.carbohydrates_g,
                density: editingFood.density,
                fiber_g: 0,
                water_g: 0,
                portion_weight_g: 100
            });
            // Refresh le nom et la densité dans la ligne d'ingrédient
            setIngredients(prev => {
                const newIngs = [...prev];
                newIngs[editingFood.ingIdx] = {
                    ...newIngs[editingFood.ingIdx],
                    food_name: editingFood.name,
                    food_density: editingFood.density
                };
                return newIngs;
            });
            setEditingFood(null);
        } finally {
            setEditFoodSaving(false);
        }
    };

    const addEditFoodPortion = async () => {
        if (!editingFood || !editFoodPortionName || editFoodPortionWeight === '') return;
        setEditFoodPortionSaving(true);
        try {
            await apiClient.post(`/foods/${editingFood.food_id}/portions`, {
                name: editFoodPortionName,
                weight_g: editFoodPortionWeight,
                is_default: editFoodPortionDefault
            });
            const res = await apiClient.get(`/foods/${editingFood.food_id}/portions`);
            setEditingFood(prev => prev ? { ...prev, portions: res.data } : null);
            // Refresh portions dans l'ingrédient concerné
            setIngredients(prev => {
                const newIngs = [...prev];
                newIngs[editingFood.ingIdx] = { ...newIngs[editingFood.ingIdx], food_portions: res.data };
                return newIngs;
            });
            setEditFoodPortionName('');
            setEditFoodPortionWeight('');
            setEditFoodPortionDefault(false);
        } finally {
            setEditFoodPortionSaving(false);
        }
    };

    const deleteEditFoodPortion = async (portionId: number) => {
        if (!editingFood) return;
        if (!window.confirm('Supprimer cette portion ?')) return;
        await apiClient.delete(`/foods/${editingFood.food_id}/portions/${portionId}`);
        const res = await apiClient.get(`/foods/${editingFood.food_id}/portions`);
        setEditingFood(prev => prev ? { ...prev, portions: res.data } : null);
        setIngredients(prev => {
            const newIngs = [...prev];
            newIngs[editingFood.ingIdx] = { ...newIngs[editingFood.ingIdx], food_portions: res.data };
            return newIngs;
        });
    };

    const setDefaultEditFoodPortion = async (p: FoodPortion) => {
        if (!editingFood) return;
        await apiClient.put(`/foods/${editingFood.food_id}/portions/${p.id}`, { name: p.name, weight_g: p.weight_g, is_default: true });
        const res = await apiClient.get(`/foods/${editingFood.food_id}/portions`);
        setEditingFood(prev => prev ? { ...prev, portions: res.data } : null);
        setIngredients(prev => {
            const newIngs = [...prev];
            newIngs[editingFood.ingIdx] = { ...newIngs[editingFood.ingIdx], food_portions: res.data };
            return newIngs;
        });
    };

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
                    // Supprimer immédiatement pour éviter le bug de double exécution (React Strict Mode + Async map)
                    sessionStorage.removeItem('scrapedRecipe');
                    try {
                        const parsed = JSON.parse(raw);
                        setName(parsed.title || parsed.name || '');

                        const descParts = [];
                        if (parsed.description) descParts.push(parsed.description);

                        if (parsed.ingredients && Array.isArray(parsed.ingredients)) {
                            descParts.push("--- Ingrédients extraits ---");
                            descParts.push(parsed.ingredients.map((i: any) => i.raw || "").join('\n'));
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
                            status: 'matched',
                            // Le schéma RecipeIngredient expose food comme objet imbriqué, pas food_id directement
                            food_id: ing.food?.id ?? ing.food_id,
                            food_name: ing.food?.name ?? `Aliment #${ing.food_id}`,
                            food_density: ing.food?.density ?? undefined,
                            food_portions: ing.food?.portions ?? undefined,
                            food_portion_id: ing.food_portion_id ?? null,
                            quantity_g: ing.quantity_g,
                            raw_quantity: ing.raw_quantity !== undefined ? ing.raw_quantity : null,
                            raw_unit: ing.raw_unit || null
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
            { status: 'matched', food_id: food.id, food_name: food.name, quantity_g: Number(selectedQty) }
        ]);
        setSelectedFoodId('');
        setSelectedQty('');
    };

    const removeIngredient = (index: number) => {
        setIngredients(prev => prev.filter((_, i) => i !== index));
    };

    const updateIngredient = (index: number, field: keyof IngredientInput | 'status', value: string | number) => {
        setIngredients(prev => {
            const newIngs = [...prev];
            const ing = { ...newIngs[index] };

            if (field === 'raw_quantity' || field === 'quantity_g') {
                const numVal = value === '' ? null : Number(value);
                (ing as any)[field] = numVal;

                if (field === 'raw_quantity') {
                    if (ing.raw_unit === 'g' || ing.raw_unit === 'ml') {
                        // g/ml : quantity_g = raw_quantity directement
                        ing.quantity_g = numVal ?? 0;
                    } else if (ing.raw_unit && VOLUMETRIC_ML[ing.raw_unit]) {
                        // Unité volumétrique : quantity_g = raw_quantity × ml × density
                        const density = ing.food_density ?? 1.0;
                        ing.quantity_g = Math.round((numVal ?? 0) * VOLUMETRIC_ML[ing.raw_unit] * density * 10) / 10;
                    } else {
                        // Proportionnel pour les pièces
                        const oldRaw = newIngs[index].raw_quantity;
                        const oldQg = newIngs[index].quantity_g ?? 0;
                        if (oldRaw && oldRaw !== 0 && numVal !== null) {
                            ing.quantity_g = Math.round((numVal / oldRaw) * oldQg * 10) / 10;
                        } else if (numVal !== null && oldQg === 0) {
                            ing.quantity_g = numVal;
                        }
                    }
                }
            } else if (field === 'raw_unit') {
                (ing as any)[field] = value;

                // Quand on passe à g/ml, synchroniser quantity_g avec raw_quantity
                if ((value === 'g' || value === 'ml') && ing.raw_quantity !== null && ing.raw_quantity !== undefined) {
                    ing.quantity_g = ing.raw_quantity;
                } else if (VOLUMETRIC_ML[value as string] && ing.raw_quantity) {
                    // Passage vers une unité volumétrique : recalculer
                    const density = ing.food_density ?? 1.0;
                    ing.quantity_g = Math.round(ing.raw_quantity * VOLUMETRIC_ML[value as string] * density * 10) / 10;
                }
            } else if (field === 'status') {
                ing.status = value as any;
            } else if (field === 'food_id') {
                const foodId = Number(value);
                const food = foods.find(f => f.id === foodId);
                if (food) {
                    ing.status = 'matched';
                    ing.food_id = food.id;
                    ing.food_name = food.name;
                }
            } else {
                (ing as any)[field] = value;
            }

            newIngs[index] = ing;
            return newIngs;
        });
    };

    const handleSearchOFF = async (idx: number, query: string) => {
        if (!query) return;

        setIsSearchingOFF(prev => ({ ...prev, [idx]: true }));
        setOffResults(prev => ({ ...prev, [idx]: [] })); // Clear previous results

        try {
            // Un timeout légèrement supérieur côté front pour couvrir les 15s du backend
            const res = await apiClient.get(`/foods/off/search?q=${encodeURIComponent(query)}`, { timeout: 20000 });
            const results = res.data;
            if (results && results.length > 0) {
                setOffResults(prev => ({ ...prev, [idx]: results }));
            } else {
                alert("Aucun résultat trouvé sur Open Food Facts pour ce terme. Vous pouvez modifier le nom manuellement.");
            }
        } catch (err: any) {
            console.error("OFF Search Error:", err);
            if (err.code === 'ECONNABORTED' || err.message.includes('timeout')) {
                alert("La recherche Open Food Facts a expiré (le serveur est trop long à répondre). Veuillez réessayer ou lier manuellement.");
            } else {
                alert("Erreur lors de la recherche sur Open Food Facts.");
            }
        } finally {
            setIsSearchingOFF(prev => ({ ...prev, [idx]: false }));
        }
    };

    const applyOFFResult = (idx: number, result: any) => {
        updateIngredient(idx, 'suggested_name', result.name);
        setOffResults(prev => ({ ...prev, [idx]: [] })); // Close the dropdown
    };

    const handleSearchLocal = async (idx: number, query: string) => {
        if (!query || query.length < 2) return;

        setIsSearchingLocal(prev => ({ ...prev, [idx]: true }));
        setLocalResults(prev => ({ ...prev, [idx]: [] }));
        try {
            const res = await apiClient.get(`/foods/search?q=${encodeURIComponent(query)}&limit=20`);
            setLocalResults(prev => ({ ...prev, [idx]: res.data || [] }));
        } catch (err) {
            console.error('Local search error:', err);
        } finally {
            setIsSearchingLocal(prev => ({ ...prev, [idx]: false }));
        }
    };

    const applyLocalResult = async (idx: number, food: any) => {
        // 1. Mise à jour immédiate du lien (statut matched)
        setIngredients(prev => {
            const newIngs = [...prev];
            const ing = { ...newIngs[idx] };
            ing.status = 'matched';
            ing.food_id = food.id;
            ing.food_name = food.name;
            newIngs[idx] = ing;
            return newIngs;
        });
        setLocalResults(prev => ({ ...prev, [idx]: [] }));
        setLocalSearch(prev => ({ ...prev, [idx]: '' }));

        // 2. Charger les portions de cet aliment
        try {
            const res = await apiClient.get(`/foods/${food.id}/portions`);
            const portions: FoodPortion[] = res.data || [];
            const defaultPortion = portions.find(p => p.is_default) ?? portions[0] ?? null;
            setIngredients(prev => {
                const newIngs = [...prev];
                const ing = { ...newIngs[idx] };
                ing.food_portions = portions;
                ing.food_density = food.density ?? 1.0;  // stocker la densité
                if (defaultPortion) {
                    ing.food_portion_id = defaultPortion.id;
                    // Auto-calculer quantity_g avec la portion par défaut
                    const rawQty = ing.raw_quantity ?? 1;
                    ing.quantity_g = Math.round(rawQty * defaultPortion.weight_g * 10) / 10;
                }
                newIngs[idx] = ing;
                return newIngs;
            });
        } catch {
            // Pas de portions disponibles — stocker quand même la densité
            setIngredients(prev => {
                const newIngs = [...prev];
                newIngs[idx] = { ...newIngs[idx], food_density: food.density ?? 1.0 };
                return newIngs;
            });
        }
    };

    const handleLocalSearchChange = (idx: number, val: string) => {
        setLocalSearch(prev => ({ ...prev, [idx]: val }));
        if (val.length >= 3) {
            handleSearchLocal(idx, val);
        } else {
            setLocalResults(prev => ({ ...prev, [idx]: [] }));
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        // 1. Ingrédients non résolus → demander confirmation ou les convertir en brouillons
        const hasUnresolved = ingredients.some(ing => ing.status === 'unresolved');
        if (hasUnresolved) {
            const proceed = window.confirm(
                "⚠️ Certains ingrédients ne sont pas encore liés à la base de données.\n\n" +
                "Ils seront enregistrés comme aliments brouillons (sans valeurs nutritionnelles).\n\n" +
                "Continuer quand même ?"
            );
            if (!proceed) return;
            // Traiter les unresolved comme to_create
            setIngredients(prev => prev.map(ing =>
                ing.status === 'unresolved' ? { ...ing, status: 'to_create' } : ing
            ));
        }

        setLoading(true);

        try {
            // 2. Créer les ingrédients brouillons — utiliser une copie locale (pas le state React qui est batché)
            const finalIngredients = ingredients.map(ing =>
                ing.status === 'unresolved' ? { ...ing, status: 'to_create' as const } : { ...ing }
            );
            for (let i = 0; i < finalIngredients.length; i++) {
                const ing = finalIngredients[i];
                if (ing.status === 'to_create' && ing.suggested_name) {
                    try {
                        const res = await apiClient.post('/foods/', {
                            name: ing.suggested_name,
                            energy_kcal: 0.0, proteins_g: 0.0, carbohydrates_g: 0.0, fat_g: 0.0, fiber_g: 0.0, water_g: 0.0,
                            density: 1.0, portion_weight_g: 100.0, is_draft: true
                        });
                        ing.food_id = res.data.id;
                        ing.food_name = res.data.name;
                        ing.status = 'matched';
                    } catch (apiErr) {
                        console.error("Erreur lors de la création asynchrone du draft", apiErr);
                        alert(`Impossible de créer l'ingrédient ${ing.suggested_name}`);
                        setLoading(false);
                        return;
                    }
                }
            }

            // 3. Préparer le payload de la recette
            const payload = {
                name,
                description,
                type: recipeType,
                visibility: 'global',
                ingredients_food: finalIngredients.map(ing => ({
                    food_id: ing.food_id!,
                    quantity_g: ing.quantity_g || 0,
                    raw_quantity: ing.raw_quantity !== undefined ? ing.raw_quantity : null,
                    raw_unit: ing.raw_unit || null,
                    food_portion_id: ing.food_portion_id ?? null,
                    state: 'raw'
                }))
            };

            if (isEditing) {
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
                            <li key={idx} className="flex justify-between items-center gap-2" style={{ padding: '0.5rem', background: 'rgba(0,0,0,0.2)', marginBottom: '0.5rem', borderRadius: 'var(--radius-sm)' }}>
                                <input
                                    type="number"
                                    className="input-field"
                                    style={{ width: '80px', padding: '0.5rem' }}
                                    value={ing.raw_quantity || ''}
                                    onChange={(e) => updateIngredient(idx, 'raw_quantity', e.target.value)}
                                    placeholder="Qté"
                                />
                                {/* Sélecteur unité OU portion — mutuellement exclusifs */}
                                {ing.food_portions && ing.food_portions.length > 0 ? (
                                    /* Mode portions : le dropdown remplace le sélecteur d'unité */
                                    <select
                                        className="input-field"
                                        style={{ width: '160px', padding: '0.5rem', fontSize: '0.85rem' }}
                                        value={ing.food_portion_id ?? ''}
                                        onChange={e => {
                                            const portionId = Number(e.target.value) || null;
                                            const portion = ing.food_portions?.find(p => p.id === portionId);
                                            setIngredients(prev => {
                                                const newIngs = [...prev];
                                                const updated = { ...newIngs[idx] };
                                                updated.food_portion_id = portionId;
                                                updated.raw_unit = null; // Pas d'unité générique en mode portions
                                                if (portion) {
                                                    const rawQty = updated.raw_quantity ?? 1;
                                                    updated.quantity_g = Math.round(rawQty * portion.weight_g * 10) / 10;
                                                }
                                                newIngs[idx] = updated;
                                                return newIngs;
                                            });
                                        }}
                                    >
                                        <option value="">-- taille --</option>
                                        {ing.food_portions.map(p => (
                                            <option key={p.id} value={p.id}>{p.name} ({p.weight_g}g)</option>
                                        ))}
                                    </select>
                                ) : (
                                    /* Mode unité générique */
                                    <select
                                        className="input-field"
                                        style={{ width: '100px', padding: '0.5rem' }}
                                        value={ing.raw_unit || ''}
                                        onChange={(e) => updateIngredient(idx, 'raw_unit', e.target.value)}
                                    >
                                        {UNIT_OPTIONS.map(u => (
                                            <option key={u.value} value={u.value}>{u.label}</option>
                                        ))}
                                        {ing.raw_unit && !UNIT_OPTIONS.some(u => u.value === ing.raw_unit) && (
                                            <option value={ing.raw_unit}>{ing.raw_unit}</option>
                                        )}
                                    </select>
                                )}
                                {ing.status === 'unresolved' ? (
                                    <>
                                        {/* Compact single-row: name + link controls */}
                                        <div style={{ flex: 1, display: 'flex', gap: '0.4rem', alignItems: 'center', minWidth: 0, overflow: 'hidden' }}>
                                            <span title="Aliment introuvable" style={{ flexShrink: 0 }}>⚠️</span>
                                            <input
                                                className="input-field"
                                                style={{ flex: '1 1 100px', padding: '0.4rem', minWidth: '80px', fontSize: '0.85rem' }}
                                                value={ing.suggested_name || ''}
                                                onChange={e => updateIngredient(idx, 'suggested_name', e.target.value)}
                                                placeholder="Nom"
                                            />
                                            <input
                                                className="input-field"
                                                style={{ flex: '1 1 110px', padding: '0.4rem', minWidth: '90px', fontSize: '0.85rem' }}
                                                value={localSearch[idx] || ''}
                                                onChange={e => handleLocalSearchChange(idx, e.target.value)}
                                                placeholder={isSearchingLocal[idx] ? '…' : 'Lier'}
                                            />
                                            <button
                                                type="button"
                                                title="Open Food Facts"
                                                style={{ flexShrink: 0, padding: '0.3rem 0.5rem', fontSize: '0.75rem', background: 'rgba(255,255,255,0.08)', border: '1px solid var(--border-glass)', borderRadius: '4px', color: 'var(--text-muted)', cursor: 'pointer', opacity: isSearchingOFF[idx] ? 0.5 : 1 }}
                                                onClick={() => handleSearchOFF(idx, ing.suggested_name || '')}
                                                disabled={isSearchingOFF[idx]}
                                            >
                                                {isSearchingOFF[idx] ? '⏳' : '🔍'}
                                            </button>
                                            <button
                                                type="button"
                                                title="Créer comme nouvel aliment brouillon"
                                                style={{ flexShrink: 0, padding: '0.3rem 0.5rem', fontSize: '0.75rem', background: 'rgba(34,197,94,0.15)', border: '1px solid #22c55e', borderRadius: '4px', color: '#22c55e', cursor: 'pointer' }}
                                                onClick={() => updateIngredient(idx, 'status', 'to_create')}
                                            >
                                                ✚
                                            </button>
                                        </div>

                                        {/* Autocomplete results — below the row, full width */}
                                        {(localResults[idx]?.length > 0 || offResults[idx]?.length > 0) && (
                                            <div style={{ gridColumn: '1 / -1', width: '100%', marginTop: '0.25rem', background: 'rgba(0,0,0,0.4)', borderRadius: '6px', padding: '0.4rem', border: '1px solid var(--border-glass)', position: 'relative', zIndex: 10 }}>
                                                {localResults[idx]?.length > 0 && (
                                                    <>
                                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.3rem' }}>Base locale</div>
                                                        {localResults[idx].map((f, fIdx) => (
                                                            <button
                                                                key={fIdx}
                                                                type="button"
                                                                onMouseDown={() => applyLocalResult(idx, f)}
                                                                style={{ display: 'flex', width: '100%', justifyContent: 'space-between', padding: '0.35rem 0.5rem', background: 'transparent', border: 'none', borderRadius: '4px', color: 'var(--text-primary)', cursor: 'pointer', fontSize: '0.85rem', textAlign: 'left' }}
                                                                onMouseOver={e => e.currentTarget.style.background = 'rgba(255,255,255,0.08)'}
                                                                onMouseOut={e => e.currentTarget.style.background = 'transparent'}
                                                            >
                                                                <span>{f.name}</span>
                                                                <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>{f.energy_kcal} kcal</span>
                                                            </button>
                                                        ))}
                                                        <button type="button" onClick={() => setLocalResults(prev => ({ ...prev, [idx]: [] }))} style={{ width: '100%', padding: '0.25rem', fontSize: '0.75rem', background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>Fermer</button>
                                                    </>
                                                )}
                                                {offResults[idx]?.length > 0 && (
                                                    <>
                                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.3rem', marginTop: localResults[idx]?.length > 0 ? '0.5rem' : 0 }}>Open Food Facts</div>
                                                        {offResults[idx].map((r, rIdx) => (
                                                            <button
                                                                key={rIdx}
                                                                type="button"
                                                                onMouseDown={() => applyOFFResult(idx, r)}
                                                                style={{ display: 'flex', width: '100%', justifyContent: 'space-between', padding: '0.35rem 0.5rem', background: 'transparent', border: 'none', borderRadius: '4px', color: 'var(--text-primary)', cursor: 'pointer', fontSize: '0.85rem', textAlign: 'left' }}
                                                                onMouseOver={e => e.currentTarget.style.background = 'rgba(255,255,255,0.08)'}
                                                                onMouseOut={e => e.currentTarget.style.background = 'transparent'}
                                                            >
                                                                <span>{r.name}</span>
                                                                <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>{r.energy_kcal} kcal</span>
                                                            </button>
                                                        ))}
                                                        <button type="button" onClick={() => setOffResults(prev => ({ ...prev, [idx]: [] }))} style={{ width: '100%', padding: '0.25rem', fontSize: '0.75rem', background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>Fermer</button>
                                                    </>
                                                )}
                                            </div>
                                        )}
                                    </>
                                ) : (
                                    <div style={{ flex: 1, display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                                        {ing.status === 'to_create' && (
                                            <span style={{ color: '#22c55e', fontWeight: 'bold', fontSize: '0.9rem' }}>✨ Créer: "{ing.suggested_name}"</span>
                                        )}
                                        {ing.status === 'matched' && (
                                            <span style={{ color: 'var(--text-secondary)', fontWeight: 'bold', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                                                ✅ {ing.food_name}
                                                <button
                                                    type="button"
                                                    title="Éditer cet aliment"
                                                    onClick={() => { if (ing.food_id !== undefined) openFoodEdit(idx, ing.food_id, ing.food_name || ''); }}
                                                    style={{ padding: '0.15rem 0.35rem', fontSize: '0.75rem', background: 'rgba(255,255,255,0.06)', border: '1px solid var(--border-glass)', borderRadius: '4px', color: 'var(--text-muted)', cursor: 'pointer' }}
                                                >✏️</button>
                                            </span>
                                        )}
                                        <input
                                            className="input-field"
                                            style={{ width: '150px', padding: '0.4rem', fontSize: '0.85rem' }}
                                            value={localSearch[idx] || ''}
                                            onChange={e => handleLocalSearchChange(idx, e.target.value)}
                                            placeholder="Modifier le lien..."
                                        />
                                        {localResults[idx] && localResults[idx].length > 0 && (
                                            <div style={{ width: '100%', marginTop: '0.3rem', background: 'rgba(255,255,255,0.05)', borderRadius: 'var(--radius-sm)', padding: '0.5rem', border: '1px solid var(--border-glass)' }}>
                                                <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                                                    {localResults[idx].map((f, fIdx) => (
                                                        <li key={fIdx}>
                                                            <button
                                                                type="button"
                                                                onMouseDown={() => applyLocalResult(idx, f)}
                                                                style={{ width: '100%', textAlign: 'left', padding: '0.5rem', background: 'rgba(0,0,0,0.3)', border: 'none', borderRadius: '4px', color: 'var(--text-primary)', cursor: 'pointer', display: 'flex', justifyContent: 'space-between' }}
                                                                onMouseOver={e => e.currentTarget.style.background = 'rgba(255,255,255,0.1)'}
                                                                onMouseOut={e => e.currentTarget.style.background = 'rgba(0,0,0,0.3)'}
                                                            >
                                                                <span>{f.name}</span>
                                                                <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{f.energy_kcal} kcal/100g</span>
                                                            </button>
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* Affichage du poids — uniquement si pertinent */}
                                {(() => {
                                    // Mode portions : poids calculé affiché en readonly
                                    if (ing.food_portions && ing.food_portions.length > 0) {
                                        return ing.food_portion_id
                                            ? <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem', flexShrink: 0 }}>= {ing.quantity_g}g</span>
                                            : null;
                                    }
                                    // g ou ml directs : quantity_g = raw_quantity, pas besoin d'afficher
                                    if (ing.raw_unit === 'g' || ing.raw_unit === 'ml') return null;
                                    // Unités volumétriques : afficher le poids calculé via densité
                                    if (ing.raw_unit && VOLUMETRIC_ML[ing.raw_unit]) {
                                        // quantity_g est déjà calculé par updateIngredient — on l'affiche simplement
                                        return ing.quantity_g > 0
                                            ? <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem', flexShrink: 0 }}>= {ing.quantity_g}g</span>
                                            : null;
                                    }
                                    // Unité de type pièce ou inconnue : saisie manuelle du poids
                                    return (
                                        <>
                                            <span style={{ color: 'var(--text-muted)', flexShrink: 0 }}>=</span>
                                            <input
                                                type="number"
                                                className="input-field"
                                                style={{ width: '80px', padding: '0.4rem', fontSize: '0.85rem' }}
                                                value={ing.quantity_g || ''}
                                                onChange={(e) => updateIngredient(idx, 'quantity_g', e.target.value)}
                                                placeholder="g"
                                            />
                                            <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', flexShrink: 0 }}>g</span>
                                        </>
                                    );
                                })()}

                                <button type="button" onClick={() => removeIngredient(idx)} style={{ color: 'var(--accent-danger)', background: 'transparent', border: 'none', cursor: 'pointer', marginLeft: '0.5rem' }}>✖</button>
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

            {/* ── Modale d'édition d'aliment ─────────────────────────────── */}
            {editingFood && (
                <div
                    onClick={e => { if (e.target === e.currentTarget) setEditingFood(null); }}
                    style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.65)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}
                >
                    <div style={{ background: 'var(--bg-card, #1e1e2e)', border: '1px solid var(--border-glass)', borderRadius: '12px', padding: '1.5rem', width: '100%', maxWidth: '560px', maxHeight: '90vh', overflowY: 'auto' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                            <div style={{ flex: 1, marginRight: '0.75rem' }}>
                                <label style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.25rem' }}>Nom de l'aliment</label>
                                <input
                                    className="input-field"
                                    style={{ width: '100%', padding: '0.4rem', fontSize: '1rem', fontWeight: 'bold', color: 'var(--accent-primary)' }}
                                    value={editingFood!.name}
                                    onChange={e => setEditingFood(prev => prev ? { ...prev, name: e.target.value } : null)}
                                />
                            </div>
                            <button type="button" onClick={() => setEditingFood(null)} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '1.2rem', flexShrink: 0 }}>✕</button>
                        </div>

                        {/* Macros */}
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.6rem', marginBottom: '0.8rem' }}>
                            {([
                                ['Calories (kcal/100g)', 'energy_kcal'],
                                ['Protéines (g)', 'proteins_g'],
                                ['Lipides (g)', 'fat_g'],
                                ['Glucides (g)', 'carbohydrates_g'],
                            ] as const).map(([label, field]) => (
                                <div key={field}>
                                    <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.2rem' }}>{label}</label>
                                    <input
                                        type="number" step="0.1" className="input-field"
                                        value={editingFood![field]}
                                        onChange={e => setEditingFood(prev => prev ? { ...prev, [field]: Number(e.target.value) } : null)}
                                        style={{ padding: '0.4rem', fontSize: '0.85rem' }}
                                    />
                                </div>
                            ))}
                            <div>
                                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.2rem' }} title="Poids en g pour 1 ml (eau=1.0, huile=0.9, farine=0.6)">Densité (g/ml)</label>
                                <input
                                    type="number" step="0.01" className="input-field"
                                    value={editingFood!.density}
                                    onChange={e => setEditingFood(prev => prev ? { ...prev, density: Number(e.target.value) } : null)}
                                    style={{ padding: '0.4rem', fontSize: '0.85rem' }}
                                />
                            </div>
                        </div>

                        <button
                            type="button" className="btn btn-primary"
                            style={{ width: '100%', marginBottom: '1.2rem', padding: '0.5rem' }}
                            disabled={editFoodSaving}
                            onClick={saveEditFood}
                        >
                            {editFoodSaving ? 'Sauvegarde...' : '💾 Sauvegarder les données'}
                        </button>

                        {/* Portions */}
                        <div style={{ borderTop: '1px solid var(--border-glass)', paddingTop: '1rem' }}>
                            <h4 style={{ color: 'var(--accent-primary)', marginBottom: '0.6rem', fontSize: '0.95rem' }}>⚖ Portions nommées</h4>

                            {editingFood!.portions.length === 0 && (
                                <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginBottom: '0.6rem' }}>Aucune portion définie.</p>
                            )}
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', marginBottom: '0.8rem' }}>
                                {editingFood!.portions.map(p => (
                                    <div key={p.id} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', padding: '0.3rem 0.5rem', background: 'rgba(255,255,255,0.04)', borderRadius: '6px' }}>
                                        <span style={{ flex: 1, fontSize: '0.88rem' }}>
                                            {p.is_default && <span style={{ color: 'var(--accent-primary)', marginRight: '0.25rem' }}>★</span>}
                                            {p.name}
                                        </span>
                                        <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem', minWidth: '50px', textAlign: 'right' }}>{p.weight_g}g</span>
                                        <button type="button" title="Mettre par défaut"
                                            style={{ padding: '0.15rem 0.35rem', fontSize: '0.72rem', background: p.is_default ? 'rgba(99,102,241,0.2)' : 'transparent', border: '1px solid var(--border-glass)', borderRadius: '4px', color: p.is_default ? 'var(--accent-primary)' : 'var(--text-muted)', cursor: 'pointer' }}
                                            onClick={() => setDefaultEditFoodPortion(p)}
                                        >★</button>
                                        <button type="button" title="Supprimer"
                                            style={{ padding: '0.15rem 0.35rem', fontSize: '0.72rem', background: 'transparent', border: '1px solid var(--border-glass)', borderRadius: '4px', color: 'var(--accent-danger)', cursor: 'pointer' }}
                                            onClick={() => deleteEditFoodPortion(p.id)}
                                        >✕</button>
                                    </div>
                                ))}
                            </div>

                            {/* Ajouter une portion */}
                            <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
                                <div style={{ flex: '1 1 140px' }}>
                                    <label style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'block' }}>Nom</label>
                                    <input className="input-field" value={editFoodPortionName} onChange={e => setEditFoodPortionName(e.target.value)}
                                        placeholder='"1 moyen", "1 brin"' style={{ padding: '0.4rem', fontSize: '0.82rem' }} />
                                </div>
                                <div style={{ flex: '0 0 80px' }}>
                                    <label style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'block' }}>Poids (g)</label>
                                    <input type="number" className="input-field" value={editFoodPortionWeight}
                                        onChange={e => setEditFoodPortionWeight(e.target.value === '' ? '' : Number(e.target.value))}
                                        style={{ padding: '0.4rem', fontSize: '0.82rem' }} />
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', paddingBottom: '0.1rem' }}>
                                    <input type="checkbox" id="epDefault" checked={editFoodPortionDefault} onChange={e => setEditFoodPortionDefault(e.target.checked)} />
                                    <label htmlFor="epDefault" style={{ fontSize: '0.75rem', color: 'var(--text-muted)', cursor: 'pointer' }}>Défaut</label>
                                </div>
                                <button type="button" className="btn btn-secondary"
                                    style={{ padding: '0.4rem 0.8rem', fontSize: '0.82rem', alignSelf: 'flex-end' }}
                                    disabled={!editFoodPortionName || editFoodPortionWeight === '' || editFoodPortionSaving}
                                    onClick={addEditFoodPortion}
                                >{editFoodPortionSaving ? '...' : '+ Ajouter'}</button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default RecipeEditor;
