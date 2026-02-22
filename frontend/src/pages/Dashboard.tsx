import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import apiClient from '../api/client';

interface MetabolicProfile {
    bmr: number;
    tdee: number;
    target_kcal: number;
    protein_g: number;
    fat_g: number;
    carbs_g: number;
}

interface RecipeData {
    id: number;
    name: string;
    type: string;
}

interface MealData {
    id: number;
    type: string;
    recipe?: RecipeData;
}

interface PlanData {
    id: number;
    target_kcal: number;
    achieved_kcal: number;
    start_date: string;
    end_date: string;
    days: Record<string, MealData[]>;
}

interface ShoppingItem {
    food_id: number;
    food_name: string;
    total_quantity_g: number;
}

interface ShoppingData {
    plan_id: number;
    items: ShoppingItem[];
}

const Dashboard: React.FC = () => {
    const navigate = useNavigate();
    const userId = localStorage.getItem('user_id');

    const [profile, setProfile] = useState<MetabolicProfile | null>(null);
    const [generating, setGenerating] = useState(false);

    const [planId, setPlanId] = useState<number | null>(null);
    const [planData, setPlanData] = useState<PlanData | null>(null);
    const [shoppingList, setShoppingList] = useState<ShoppingData | null>(null);
    const [errorMsg, setErrorMsg] = useState<string | null>(null);

    useEffect(() => {
        if (!userId) {
            navigate('/onboarding');
            return;
        }

        // Fetch User Profile
        apiClient.get(`/users/${userId}/metabolic-profile`)
            .then(res => setProfile(res.data))
            .catch(err => console.error("Could not fetch profile", err));

        // Autoload latest plan if exists
        apiClient.get(`/planner/users/${userId}/latest`)
            .then(res => {
                setPlanId(res.data.id);
                setPlanData(res.data);
            })
            .catch(err => {
                if (err.response?.status !== 404) {
                    console.error("Could not fetch latest plan", err);
                }
            });

    }, [userId, navigate]);

    const fetchPlanDetails = async (id: number) => {
        try {
            const res = await apiClient.get(`/planner/${id}`);
            setPlanData(res.data);
        } catch (err) {
            console.error(err);
        }
    };

    const generatePlan = async () => {
        setGenerating(true);
        setErrorMsg(null);
        setPlanData(null);
        setShoppingList(null);

        try {
            const start_date = new Date().toISOString().split('T')[0];
            const res = await apiClient.post(`/planner/generate`, {
                user_id: parseInt(userId!, 10),
                start_date: start_date
            });
            setPlanId(res.data.plan_id);
            await fetchPlanDetails(res.data.plan_id);
        } catch (error: any) {
            console.error(error);
            const detail = error.response?.data?.detail;
            setErrorMsg(typeof detail === 'string' ? detail : JSON.stringify(detail) || "Erreur de génération.");
        } finally {
            setGenerating(false);
        }
    };

    const fetchShoppingList = async () => {
        if (!planId) return;
        try {
            const res = await apiClient.get(`/planner/${planId}/shopping-list`);
            setShoppingList(res.data);
        } catch (err) {
            console.error(err);
        }
    };

    // Option: Meal Substitution
    const [selectedMeal, setSelectedMeal] = useState<MealData | null>(null);
    const [alternatives, setAlternatives] = useState<any[]>([]);
    const [loadingAlts, setLoadingAlts] = useState(false);

    const handleOpenSwap = async (meal: MealData) => {
        setSelectedMeal(meal);
        setLoadingAlts(true);
        try {
            const res = await apiClient.get(`/planner/meals/${meal.id}/alternatives`);
            setAlternatives(res.data);
        } catch (err) {
            console.error("Could not fetch alternatives", err);
        } finally {
            setLoadingAlts(false);
        }
    };

    const handleSwapMeal = async (newRecipeId: number) => {
        if (!selectedMeal || !planId) return;
        try {
            await apiClient.put(`/planner/meals/${selectedMeal.id}`, { recipe_id: newRecipeId });
            // Refresh plan after swapping
            await fetchPlanDetails(planId);
            setSelectedMeal(null);
            setAlternatives([]);
            alert("Repas modifié avec succès !");
        } catch (err) {
            console.error("Error swapping meal", err);
            alert("Erreur lors du changement de repas.");
        }
    };

    if (!profile) return <div className="text-center mt-8">Chargement de votre profil...</div>;

    return (
        <div className="animate-fade-in">
            {/* Profil Métabolique */}
            <div className="glass-card mb-4" style={{ padding: '2rem' }}>
                <h2 style={{ color: 'var(--accent-primary)', marginBottom: '1rem' }}>Tableau de Bord</h2>

                <div className="flex gap-4" style={{ flexWrap: 'wrap' }}>
                    <div className="glass-card text-center" style={{ flex: '1', padding: '1.5rem', minWidth: '200px' }}>
                        <h3 style={{ color: 'var(--text-secondary)' }}>Maintien (TDEE)</h3>
                        <p style={{ fontSize: '2rem', fontWeight: 'bold' }}>{profile.tdee} <span style={{ fontSize: '1rem' }}>kcal</span></p>
                    </div>
                    <div className="glass-card text-center" style={{ flex: '1', padding: '1.5rem', minWidth: '200px', border: '1px solid var(--accent-primary)' }}>
                        <h3 style={{ color: 'var(--accent-primary-hover)' }}>Cible Quotidienne</h3>
                        <p style={{ fontSize: '2rem', fontWeight: 'bold' }}>{profile.target_kcal} <span style={{ fontSize: '1rem' }}>kcal</span></p>
                    </div>
                </div>

                <div className="flex justify-between items-center mt-4" style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: 'var(--radius-md)' }}>
                    <div className="text-center" style={{ flex: 1 }}><span style={{ color: 'var(--text-muted)' }}>Protéines:</span> <b>{profile.protein_g}g</b></div>
                    <div className="text-center" style={{ flex: 1, borderLeft: '1px solid var(--border-glass)', borderRight: '1px solid var(--border-glass)' }}><span style={{ color: 'var(--text-muted)' }}>Lipides:</span> <b>{profile.fat_g}g</b></div>
                    <div className="text-center" style={{ flex: 1 }}><span style={{ color: 'var(--text-muted)' }}>Glucides:</span> <b>{profile.carbs_g}g</b></div>
                </div>
            </div>

            <div className="text-center mt-8 mb-8">
                <button
                    className="btn btn-primary"
                    style={{ fontSize: '1.2rem', padding: '1rem 3rem' }}
                    onClick={generatePlan}
                    disabled={generating}
                >
                    {generating ? 'Génération en cours (Algorithme PuLP)...' : 'Générer ma semaine aux macros !'}
                </button>
            </div>

            {errorMsg && (
                <div className="glass-card animate-fade-in text-center" style={{ padding: '2rem', border: '1px solid var(--accent-warning)' }}>
                    <h3 style={{ color: 'var(--accent-warning)' }}>{errorMsg}</h3>
                </div>
            )}

            {/* Grille Hebdomadaire Redesigned */}
            {planData && (
                <div className="mt-8 animate-fade-in">
                    {/* Header: Dates & Actions */}
                    <div className="flex justify-between items-center mb-6">
                        <div>
                            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, margin: 0 }}>Plan Actuel</h2>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                                Du {new Date(planData.start_date).toLocaleDateString()} au {new Date(planData.end_date).toLocaleDateString()}
                            </span>
                        </div>
                        <div className="flex gap-4">
                            <button className="btn btn-secondary" onClick={fetchShoppingList}>
                                <span style={{ marginRight: '0.5rem' }}>🛒</span> Grocery List
                            </button>
                            <button className="btn btn-primary" onClick={generatePlan} disabled={generating}>
                                <span style={{ marginRight: '0.5rem' }}>🔄</span> {generating ? 'Generating...' : 'Regenerate Week'}
                            </button>
                        </div>
                    </div>

                    {/* Weekly Calendar Header (Days) */}
                    <div className="flex justify-between mb-8" style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem' }}>
                        {Object.keys(planData.days).map((dateStr, i) => {
                            const dateObj = new Date(dateStr);
                            const dayName = dateObj.toLocaleDateString('en-US', { weekday: 'short' }).toUpperCase();
                            const dayNum = dateObj.getDate();
                            return (
                                <div key={dateStr} className="text-center" style={{ flex: 1, borderTop: i === 0 ? '3px solid var(--accent-primary)' : '3px solid transparent', paddingTop: '0.5rem' }}>
                                    <div style={{ fontSize: '0.8rem', color: i === 0 ? 'var(--accent-primary)' : 'var(--text-secondary)', fontWeight: 600 }}>{dayName}</div>
                                    <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{dayNum}</div>
                                </div>
                            );
                        })}
                    </div>

                    {/* Meal Rows */}
                    {['breakfast', 'lunch', 'dinner', 'snack'].map(mealType => {
                        // Check if at least one day has this meal type
                        const hasThisMealType = Object.values(planData.days).some(meals =>
                            meals.some(m => m.type === mealType)
                        );

                        if (!hasThisMealType) return null;

                        return (
                            <div key={mealType} className="mb-8">
                                <h3 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '1rem' }}>
                                    {mealType}
                                </h3>
                                <div className="flex gap-4" style={{ overflowX: 'auto', paddingBottom: '0.5rem' }}>
                                    {Object.entries(planData.days).map(([date, meals]) => {
                                        const meal = meals.find(m => m.type === mealType);

                                        if (!meal) {
                                            return (
                                                <div key={date} className="glass-card flex items-center justify-center" style={{ flex: '0 0 calc(100% / 7 - 1rem)', minWidth: '160px', height: '180px', borderStyle: 'dashed' }}>
                                                    <span style={{ color: 'var(--text-muted)' }}>-</span>
                                                </div>
                                            );
                                        }

                                        return (
                                            <div key={meal.id} className="glass-card" style={{ flex: '0 0 calc(100% / 7 - 1rem)', minWidth: '160px', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                                                {/* Placeholder Image */}
                                                <div style={{ height: '100px', backgroundColor: '#e2e8f0', position: 'relative' }}>
                                                    <div style={{ position: 'absolute', bottom: '8px', left: '8px', background: 'rgba(0,0,0,0.6)', color: 'white', fontSize: '0.7rem', padding: '0.2rem 0.4rem', borderRadius: '4px', fontWeight: 600 }}>
                                                        ~ {meal.recipe ? 450 : 0} kcal
                                                    </div>
                                                </div>

                                                <div style={{ padding: '0.75rem', flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                                                    <Link to={meal.recipe ? `/recipes/${meal.recipe.id}` : '#'} style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.2, marginBottom: '0.5rem' }}>
                                                        {meal.recipe ? meal.recipe.name : 'Libre'}
                                                    </Link>

                                                    <button onClick={() => handleOpenSwap(meal)} style={{ alignSelf: 'flex-start', background: 'transparent', border: 'none', color: 'var(--accent-secondary)', fontSize: '0.8rem', cursor: 'pointer', padding: 0, fontWeight: 500 }}>
                                                        Swap Meal ⇄
                                                    </button>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Modal de changement de recette */}
            {selectedMeal && (
                <div style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
                    <div className="glass-card animate-fade-in" style={{ padding: '2rem', maxWidth: '500px', width: '100%' }}>
                        <div className="flex justify-between items-center mb-4">
                            <h3 style={{ color: 'var(--accent-primary)' }}>Alternatives pour ce repas</h3>
                            <button onClick={() => setSelectedMeal(null)} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', fontSize: '1.5rem', cursor: 'pointer' }}>×</button>
                        </div>

                        {loadingAlts ? (
                            <div className="text-center">Recherche d'alternatives aux macros similaires...</div>
                        ) : (
                            <div className="flex flex-col gap-3">
                                {alternatives.length === 0 ? (
                                    <p>Aucune alternative trouvée dans la même gamme de calories.</p>
                                ) : (
                                    alternatives.map((alt, idx) => (
                                        <div key={idx} className="flex justify-between items-center" style={{ padding: '0.8rem', background: 'rgba(255,255,255,0.05)', borderRadius: 'var(--radius-sm)' }}>
                                            <div>
                                                <div style={{ fontWeight: 'bold' }}>{alt.recipe_name}</div>
                                                <div style={{ fontSize: '0.8rem', color: 'var(--accent-secondary)' }}>Match Macro: {alt.match_score}%</div>
                                            </div>
                                            <button className="btn btn-primary" style={{ padding: '0.4rem 0.8rem' }} onClick={() => handleSwapMeal(alt.recipe_id)}>
                                                Choisir
                                            </button>
                                        </div>
                                    ))
                                )}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Liste de Courses */}
            {shoppingList && (
                <div className="mt-8 mb-8 animate-fade-in glass-card" style={{ padding: '2rem', border: '1px solid var(--accent-secondary)' }}>
                    <h2 style={{ marginBottom: '1rem', color: 'var(--accent-secondary)' }}>Liste de Courses Agrégée</h2>
                    {shoppingList.items.length === 0 ? (
                        <p>La liste de courses est vide (aucune recette n'a d'ingrédients associés en base de données pour la démo).</p>
                    ) : (
                        <ul style={{ listStyle: 'none', padding: 0 }}>
                            {shoppingList.items.map((item, i) => (
                                <li key={i} style={{ padding: '0.5rem 0', borderBottom: '1px solid var(--border-glass)', display: 'flex', justifyContent: 'space-between' }}>
                                    <span>{item.food_name}</span>
                                    <span style={{ fontWeight: 'bold' }}>{item.total_quantity_g} g</span>
                                </li>
                            ))}
                        </ul>
                    )}
                </div>
            )}
        </div>
    );
};

export default Dashboard;
