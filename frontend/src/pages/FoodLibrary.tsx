import React, { useEffect, useState } from 'react';
import apiClient from '../api/client';

interface Food {
    id: number;
    name: string;
    energy_kcal: number;
    proteins_g: number;
    fat_g: number;
    carbohydrates_g: number;
    is_draft?: boolean;
}

const FoodLibrary: React.FC = () => {
    const [foods, setFoods] = useState<Food[]>([]);
    const [loading, setLoading] = useState(true);

    // Create Form State
    const [showAddForm, setShowAddForm] = useState(false);
    const [newName, setNewName] = useState('');
    const [newKcal, setNewKcal] = useState<number | ''>('');
    const [newProt, setNewProt] = useState<number | ''>('');
    const [newFat, setNewFat] = useState<number | ''>('');
    const [newCarb, setNewCarb] = useState<number | ''>('');
    const [submitting, setSubmitting] = useState(false);
    const [editingFoodId, setEditingFoodId] = useState<number | null>(null);

    const resetForm = () => {
        setNewName(''); setNewKcal(''); setNewProt(''); setNewFat(''); setNewCarb('');
        setEditingFoodId(null);
        setShowAddForm(false);
    };

    const handleEditClick = (food: Food) => {
        setNewName(food.name);
        setNewKcal(food.energy_kcal);
        setNewProt(food.proteins_g);
        setNewFat(food.fat_g);
        setNewCarb(food.carbohydrates_g);
        setEditingFoodId(food.id);
        setShowAddForm(true);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    const fetchFoods = () => {
        setLoading(true);
        apiClient.get('/foods/?limit=100')
            .then(res => setFoods(res.data))
            .catch(err => console.error("Could not fetch foods", err))
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        fetchFoods();
    }, []);

    const handleSaveFood = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newName || newKcal === '' || newProt === '' || newFat === '' || newCarb === '') return;

        setSubmitting(true);
        try {
            const payload = {
                name: newName,
                energy_kcal: Number(newKcal),
                proteins_g: Number(newProt),
                fat_g: Number(newFat),
                carbohydrates_g: Number(newCarb),
                is_draft: false // Enregistrement valide donc on enlève le mode brouillon
            };

            if (editingFoodId) {
                await apiClient.put(`/foods/${editingFoodId}`, payload);
                alert('Aliment mis à jour avec succès !');
            } else {
                await apiClient.post('/foods/', payload);
                alert('Aliment ajouté avec succès !');
            }

            resetForm();
            fetchFoods(); // Refresh list
        } catch (err) {
            console.error(err);
            alert('Erreur lors de l\'enregistrement de l\'aliment.');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="animate-fade-in">
            <div className="flex justify-between items-center mb-6">
                <h2 style={{ color: 'var(--accent-primary)' }}>Base de données Aliments</h2>
                <button className="btn btn-secondary" onClick={() => showAddForm ? resetForm() : setShowAddForm(true)}>
                    {showAddForm ? 'Annuler' : '+ Nouvel Aliment'}
                </button>
            </div>

            {showAddForm && (
                <form onSubmit={handleSaveFood} className="glass-card mb-8" style={{ padding: '1.5rem', animation: 'fadeIn 0.3s ease-in' }}>
                    <h3 style={{ marginBottom: '1rem', color: 'var(--text-secondary)' }}>
                        {editingFoodId ? 'Éditer un aliment' : 'Ajouter un aliment (100g)'}
                    </h3>
                    <div className="flex gap-4" style={{ flexWrap: 'wrap' }}>
                        <div className="input-group" style={{ flex: '1 1 100%' }}>
                            <label className="input-label">Nom de l'aliment</label>
                            <input className="input-field" value={newName} onChange={e => setNewName(e.target.value)} required placeholder="Ex: Riz Basmati Cru" />
                        </div>
                        <div className="input-group" style={{ flex: '1 1 20%' }}>
                            <label className="input-label">Calories (kcal)</label>
                            <input type="number" step="0.1" className="input-field" value={newKcal} onChange={e => setNewKcal(e.target.value === '' ? '' : Number(e.target.value))} required />
                        </div>
                        <div className="input-group" style={{ flex: '1 1 20%' }}>
                            <label className="input-label">Protéines (g)</label>
                            <input type="number" step="0.1" className="input-field" value={newProt} onChange={e => setNewProt(e.target.value === '' ? '' : Number(e.target.value))} required />
                        </div>
                        <div className="input-group" style={{ flex: '1 1 20%' }}>
                            <label className="input-label">Lipides (g)</label>
                            <input type="number" step="0.1" className="input-field" value={newFat} onChange={e => setNewFat(e.target.value === '' ? '' : Number(e.target.value))} required />
                        </div>
                        <div className="input-group" style={{ flex: '1 1 20%' }}>
                            <label className="input-label">Glucides (g)</label>
                            <input type="number" step="0.1" className="input-field" value={newCarb} onChange={e => setNewCarb(e.target.value === '' ? '' : Number(e.target.value))} required />
                        </div>
                    </div>
                    <button type="submit" className="btn btn-primary mt-4" disabled={submitting}>
                        {submitting ? 'Enregistrement...' : 'Enregistrer'}
                    </button>
                </form>
            )}

            {loading ? (
                <div className="text-center">Chargement des aliments...</div>
            ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
                    {foods.map(food => (
                        <div key={food.id} className="glass-card" style={{ padding: '1rem', position: 'relative' }}>
                            {food.is_draft && (
                                <span style={{ position: 'absolute', top: '10px', right: '10px', backgroundColor: '#eab308', color: '#fff', padding: '2px 8px', borderRadius: '12px', fontSize: '0.7rem', fontWeight: 'bold' }}>
                                    À enrichir
                                </span>
                            )}
                            <h4 style={{ marginBottom: '0.5rem', color: 'var(--text-primary)', paddingRight: food.is_draft ? '70px' : '0' }}>{food.name}</h4>
                            <div className="flex justify-between" style={{ fontSize: '0.85rem' }}>
                                <span style={{ color: 'var(--accent-secondary)' }}><b>{food.energy_kcal}</b> kcal</span>
                                <span style={{ color: 'var(--text-muted)' }}>P: {food.proteins_g}g</span>
                                <span style={{ color: 'var(--text-muted)' }}>L: {food.fat_g}g</span>
                                <span style={{ color: 'var(--text-muted)' }}>G: {food.carbohydrates_g}g</span>
                            </div>
                            <button className="btn btn-secondary mt-4" style={{ width: '100%', fontSize: '0.8rem', padding: '0.4rem' }} onClick={() => handleEditClick(food)}>
                                {food.is_draft ? 'Enrichir les valeurs' : 'Éditer'}
                            </button>
                        </div>
                    ))}
                </div>
            )}

            {!loading && foods.length === 0 && (
                <p className="text-center mt-8">Aucun aliment trouvé.</p>
            )}
        </div>
    );
};

export default FoodLibrary;
