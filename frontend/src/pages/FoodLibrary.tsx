import React, { useEffect, useState } from 'react';
import apiClient from '../api/client';

interface Food {
    id: number;
    name: string;
    energy_kcal: number;
    proteins_g: number;
    fat_g: number;
    carbohydrates_g: number;
    density?: number;
    portion_weight_g?: number;
    is_draft?: boolean;
}

interface FoodPortion {
    id: number;
    name: string;
    weight_g: number;
    is_default: boolean;
}

const FoodLibrary: React.FC = () => {
    const [foods, setFoods] = useState<Food[]>([]);
    const [loading, setLoading] = useState(true);
    const [totalCount, setTotalCount] = useState(0);
    const [currentPage, setCurrentPage] = useState(1);
    const PAGE_SIZE = 50;

    // List State
    type SortKey = keyof Food;
    type SortDirection = 'asc' | 'desc';

    const [searchQuery, setSearchQuery] = useState('');
    const [debouncedSearch, setDebouncedSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState<'all' | 'valid' | 'draft'>('all');
    const [portionsFilter, setPortionsFilter] = useState<'all' | 'with' | 'without'>('all');
    const [sortKey, setSortKey] = useState<SortKey>('name');
    const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
    const [selectedFoodIds, setSelectedFoodIds] = useState<number[]>([]);

    // Merge Modal State
    const [showMergeModal, setShowMergeModal] = useState(false);
    const [mergeTargetId, setMergeTargetId] = useState<number | ''>('');

    // Form State
    const [showAddForm, setShowAddForm] = useState(false);
    const [newName, setNewName] = useState('');
    const [newKcal, setNewKcal] = useState<number | ''>('');
    const [newProt, setNewProt] = useState<number | ''>('');
    const [newFat, setNewFat] = useState<number | ''>('');
    const [newCarb, setNewCarb] = useState<number | ''>('');
    const [newDensity, setNewDensity] = useState<number | ''>(1.0);
    const [newPortionWeight, setNewPortionWeight] = useState<number | ''>(100.0);
    const [newIsDraft, setNewIsDraft] = useState<boolean>(false);
    const [submitting, setSubmitting] = useState(false);
    const [editingFoodId, setEditingFoodId] = useState<number | null>(null);

    // Portions state
    const [portions, setPortions] = useState<FoodPortion[]>([]);
    const [newPortionName, setNewPortionName] = useState('');
    const [portionWeightInput, setPortionWeightInput] = useState<number | ''>('');
    const [newPortionIsDefault, setNewPortionIsDefault] = useState(false);
    const [portionSubmitting, setPortionSubmitting] = useState(false);

    const resetForm = () => {
        setNewName(''); setNewKcal(''); setNewProt(''); setNewFat(''); setNewCarb('');
        setNewDensity(1.0); setNewPortionWeight(100.0); setNewIsDraft(false);
        setEditingFoodId(null);
        setShowAddForm(false);
        // Reset portions fields
        setPortions([]); setNewPortionName(''); setPortionWeightInput(''); setNewPortionIsDefault(false);
    };

    const handleEditClick = (food: Food) => {
        setNewName(food.name);
        setNewKcal(food.energy_kcal);
        setNewProt(food.proteins_g);
        setNewFat(food.fat_g);
        setNewCarb(food.carbohydrates_g);
        setNewDensity(food.density ?? 1.0);
        setNewPortionWeight(food.portion_weight_g ?? 100.0);
        setNewIsDraft(food.is_draft || false);
        setEditingFoodId(food.id);
        setShowAddForm(true);
        // Load portions for this food
        apiClient.get(`/foods/${food.id}/portions`)
            .then(res => setPortions(res.data || []))
            .catch(() => setPortions([]));
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    // Debounce search
    useEffect(() => {
        const t = setTimeout(() => { setDebouncedSearch(searchQuery); setCurrentPage(1); }, 300);
        return () => clearTimeout(t);
    }, [searchQuery]);

    const fetchFoods = (page = currentPage, q = debouncedSearch) => {
        setLoading(true);
        const skip = (page - 1) * PAGE_SIZE;
        const params: Record<string, string | number> = { skip, limit: PAGE_SIZE };
        if (q) params['search'] = q;
        if (statusFilter !== 'all') params['is_draft'] = statusFilter === 'draft' ? 'true' : 'false';
        if (portionsFilter !== 'all') params['has_portions'] = portionsFilter === 'with' ? 'true' : 'false';
        apiClient.get('/foods/', { params })
            .then(res => {
                setFoods(res.data);
                // total from header if present, otherwise estimate
                const total = res.headers['x-total-count'];
                setTotalCount(total ? parseInt(total) : (res.data.length < PAGE_SIZE ? skip + res.data.length : skip + PAGE_SIZE + 1));
            })
            .catch(err => console.error('Could not fetch foods', err))
            .finally(() => setLoading(false));
    };

    useEffect(() => { fetchFoods(currentPage, debouncedSearch); }, [currentPage, debouncedSearch, statusFilter, portionsFilter]);

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
                fiber_g: 0.0,
                water_g: 0.0,
                density: newDensity !== '' ? Number(newDensity) : 1.0,
                portion_weight_g: newPortionWeight !== '' ? Number(newPortionWeight) : 100.0,
                is_draft: newIsDraft
            };

            if (editingFoodId) {
                await apiClient.put(`/foods/${editingFoodId}`, payload);
            } else {
                await apiClient.post('/foods/', payload);
            }

            resetForm();
            fetchFoods();
        } catch (err) {
            console.error(err);
            alert('Erreur lors de l\'enregistrement de l\'aliment.');
        } finally {
            setSubmitting(false);
        }
    };

    const handleDeleteFood = async (foodId: number) => {
        if (!window.confirm("Êtes-vous sûr de vouloir supprimer cet aliment ? Cette action est définitive.")) return;

        try {
            await apiClient.delete(`/foods/${foodId}`);
            fetchFoods();
            setSelectedFoodIds(prev => prev.filter(id => id !== foodId));
        } catch (err) {
            console.error("Erreur lors de la suppression:", err);
            alert('Impossible de supprimer cet aliment. Il est peut-être lié à une recette.');
        }
    };

    const handleBatchDelete = async () => {
        if (selectedFoodIds.length === 0) return;
        if (!window.confirm(`Êtes-vous sûr de vouloir supprimer ${selectedFoodIds.length} aliments ?`)) return;

        try {
            await apiClient.post('/foods/batch-delete', selectedFoodIds);
            fetchFoods();
            setSelectedFoodIds([]);
        } catch (err) {
            console.error("Erreur batch delete:", err);
            alert('Erreur lors de la suppression par lot. Certains aliments sont peut-être liés à des recettes.');
        }
    };

    const handleOpenMergeModal = () => {
        if (selectedFoodIds.length < 2) return;
        setMergeTargetId(''); // Reset
        setShowMergeModal(true);
    };

    const handleConfirmMerge = async () => {
        if (!mergeTargetId) return;

        const targetId = Number(mergeTargetId);
        const sourceIds = selectedFoodIds.filter(id => id !== targetId);

        if (sourceIds.length === 0) {
            alert('Veuillez sélectionner au moins un aliment supplémentaire pour la fusion.');
            return;
        }

        try {
            await apiClient.post('/foods/merge', {
                target_id: targetId,
                source_ids: sourceIds
            });
            alert('Aliments fusionnés avec succès ! Les recettes liées ont été mises à jour.');
            setShowMergeModal(false);
            setSelectedFoodIds([]);
            fetchFoods();
        } catch (err) {
            console.error("Erreur lors de la fusion:", err);
            alert('Erreur lors de la fusion. Veuillez réessayer.');
        }
    };

    const handleToggleSelect = (id: number) => {
        setSelectedFoodIds(prev =>
            prev.includes(id) ? prev.filter(foodId => foodId !== id) : [...prev, id]
        );
    };


    // Sort the current page client-side (search and status are server-side)
    const sortedFoods = [...foods].sort((a, b) => {
        let valA: any = a[sortKey];
        let valB: any = b[sortKey];

        if (sortKey === 'is_draft') {
            valA = valA === true ? 1 : 0;
            valB = valB === true ? 1 : 0;
        } else if (typeof valA === 'string' && typeof valB === 'string') {
            valA = valA.toLowerCase();
            valB = valB.toLowerCase();
        }

        if (valA === undefined) valA = 0;
        if (valB === undefined) valB = 0;

        if (valA < valB) return sortDirection === 'asc' ? -1 : 1;
        if (valA > valB) return sortDirection === 'asc' ? 1 : -1;
        return 0;
    });

    const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.checked) {
            setSelectedFoodIds(sortedFoods.map(f => f.id));
        } else {
            setSelectedFoodIds([]);
        }
    };

    const handleSort = (key: SortKey) => {
        if (sortKey === key) {
            setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
        } else {
            setSortKey(key);
            setSortDirection('asc');
        }
    };

    const SortIcon = ({ columnKey }: { columnKey: SortKey }) => {
        if (sortKey !== columnKey) return <span style={{ opacity: 0.3, marginLeft: '4px', fontSize: '0.8rem' }}>↕</span>;
        return <span style={{ marginLeft: '4px', fontSize: '0.8rem', color: 'var(--accent-primary)' }}>{sortDirection === 'asc' ? '▲' : '▼'}</span>;
    };

    const totalPages = Math.ceil(totalCount / PAGE_SIZE);

    return (
        <div className="animate-fade-in">
            <div className="flex justify-between items-center mb-6">
                <h2 style={{ color: 'var(--accent-primary)' }}>Base de données Aliments</h2>
                <div className="flex gap-2">
                    {selectedFoodIds.length > 1 && (
                        <button className="btn" style={{ padding: '0.5rem 1rem', backgroundColor: 'var(--accent-primary)', color: 'white', border: 'none' }} onClick={handleOpenMergeModal}>
                            🔗 Fusionner ({selectedFoodIds.length})
                        </button>
                    )}
                    {selectedFoodIds.length > 0 && (
                        <button className="btn" style={{ padding: '0.5rem 1rem', backgroundColor: 'var(--accent-danger)', color: 'white', border: 'none' }} onClick={handleBatchDelete}>
                            🗑 Supprimer ({selectedFoodIds.length})
                        </button>
                    )}
                    <button className="btn btn-secondary" onClick={() => showAddForm ? resetForm() : setShowAddForm(true)}>
                        {showAddForm ? 'Annuler' : '+ Nouvel Aliment'}
                    </button>
                </div>
            </div>

            {/* Barre de Filtre */}
            <div className="mb-6 flex gap-4" style={{ flexWrap: 'wrap' }}>
                <input
                    type="text"
                    className="input-field"
                    placeholder="🔍 Rechercher un aliment..."
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    style={{ flex: '1 1 300px' }}
                />
                <select
                    className="input-field"
                    value={statusFilter}
                    onChange={e => setStatusFilter(e.target.value as any)}
                    style={{ flex: '0 0 190px' }}
                >
                    <option value="all">Tous les statuts</option>
                    <option value="valid">✅ Valides</option>
                    <option value="draft">⚠️ Brouillons</option>
                </select>
                <select
                    className="input-field"
                    value={portionsFilter}
                    onChange={e => { setPortionsFilter(e.target.value as any); setCurrentPage(1); }}
                    style={{ flex: '0 0 210px' }}
                >
                    <option value="all">Toutes les portions</option>
                    <option value="with">⚖ Avec portions prédéfinies</option>
                    <option value="without">❌ Sans portions</option>
                </select>
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
                        <div className="input-group" style={{ flex: '1 1 20%' }}>
                            <label className="input-label" title="Poids en g pour 1ml (ex: 1.0 = eau, 0.6 = farine, 0.9 = huile)">Densité (g/ml)</label>
                            <input type="number" step="0.01" className="input-field" value={newDensity} onChange={e => setNewDensity(e.target.value === '' ? '' : Number(e.target.value))} required />
                        </div>
                        <div className="input-group" style={{ flex: '1 1 20%' }}>
                            <label className="input-label" title="Poids moyen d'une pièce standard (ex: œuf=50g)">Poids Portion (g)</label>
                            <input type="number" step="0.1" className="input-field" value={newPortionWeight} onChange={e => setNewPortionWeight(e.target.value === '' ? '' : Number(e.target.value))} required />
                        </div>
                    </div>

                    <div className="flex items-center gap-3 mt-4 mb-2">
                        <input
                            type="checkbox"
                            id="isDraftToggle"
                            checked={newIsDraft}
                            onChange={e => setNewIsDraft(e.target.checked)}
                            style={{ width: '18px', height: '18px', accentColor: '#eab308' }}
                        />
                        <label htmlFor="isDraftToggle" style={{ color: 'var(--text-secondary)', cursor: 'pointer', userSelect: 'none' }}>
                            Conserver en tant que <strong>Brouillon</strong> (Incomplet)
                        </label>
                    </div>

                    <button type="submit" className="btn btn-primary mt-4" disabled={submitting}>
                        {submitting ? 'Enregistrement...' : 'Enregistrer'}
                    </button>

                    {/* ── Portions (uniquement en mode édition) ──────────────────── */}
                    {editingFoodId && (
                        <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--border-glass)', paddingTop: '1rem' }}>
                            <h4 style={{ color: 'var(--accent-primary)', marginBottom: '0.75rem' }}>⚖ Portions nommées</h4>

                            {portions.length === 0 && (
                                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '0.75rem' }}>Aucune portion définie.</p>
                            )}
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginBottom: '1rem' }}>
                                {portions.map(p => (
                                    <div key={p.id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.4rem 0.6rem', background: 'rgba(255,255,255,0.04)', borderRadius: '6px' }}>
                                        <span style={{ flex: 1, fontSize: '0.9rem' }}>
                                            {p.is_default && <span title="Portion par défaut" style={{ color: 'var(--accent-primary)', marginRight: '0.3rem' }}>★</span>}
                                            {p.name}
                                        </span>
                                        <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', minWidth: '55px', textAlign: 'right' }}>{p.weight_g}g</span>
                                        <button
                                            type="button"
                                            title={p.is_default ? 'Déjà par défaut' : 'Mettre par défaut'}
                                            style={{ padding: '0.2rem 0.4rem', fontSize: '0.75rem', background: p.is_default ? 'rgba(99,102,241,0.2)' : 'transparent', border: '1px solid var(--border-glass)', borderRadius: '4px', color: p.is_default ? 'var(--accent-primary)' : 'var(--text-muted)', cursor: 'pointer' }}
                                            onClick={async () => {
                                                await apiClient.put(`/foods/${editingFoodId}/portions/${p.id}`, { name: p.name, weight_g: p.weight_g, is_default: true });
                                                const res = await apiClient.get(`/foods/${editingFoodId}/portions`);
                                                setPortions(res.data);
                                            }}
                                        >★</button>
                                        <button
                                            type="button"
                                            title="Supprimer"
                                            style={{ padding: '0.2rem 0.4rem', fontSize: '0.75rem', background: 'transparent', border: '1px solid var(--border-glass)', borderRadius: '4px', color: 'var(--accent-danger)', cursor: 'pointer' }}
                                            onClick={async () => {
                                                if (!window.confirm(`Supprimer "${p.name}" ?`)) return;
                                                await apiClient.delete(`/foods/${editingFoodId}/portions/${p.id}`);
                                                setPortions(prev => prev.filter(x => x.id !== p.id));
                                            }}
                                        >✕</button>
                                    </div>
                                ))}
                            </div>

                            {/* Ajout d'une nouvelle portion */}
                            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
                                <div style={{ flex: '1 1 160px' }}>
                                    <label className="input-label">Nom de la portion</label>
                                    <input
                                        className="input-field"
                                        value={newPortionName}
                                        onChange={e => setNewPortionName(e.target.value)}
                                        placeholder='ex: "1 moyen", "1 brin"'
                                        style={{ padding: '0.5rem', fontSize: '0.85rem' }}
                                    />
                                </div>
                                <div style={{ flex: '0 0 90px' }}>
                                    <label className="input-label">Poids (g)</label>
                                    <input
                                        type="number"
                                        className="input-field"
                                        value={portionWeightInput}
                                        onChange={e => setPortionWeightInput(e.target.value === '' ? '' : Number(e.target.value))}
                                        placeholder="g"
                                        style={{ padding: '0.5rem', fontSize: '0.85rem' }}
                                    />
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', paddingBottom: '0.1rem' }}>
                                    <input type="checkbox" id="newPortDefault" checked={newPortionIsDefault} onChange={e => setNewPortionIsDefault(e.target.checked)} />
                                    <label htmlFor="newPortDefault" style={{ fontSize: '0.8rem', color: 'var(--text-muted)', cursor: 'pointer' }}>Défaut</label>
                                </div>
                                <button
                                    type="button"
                                    className="btn btn-secondary"
                                    style={{ padding: '0.5rem 1rem', fontSize: '0.85rem', alignSelf: 'flex-end' }}
                                    disabled={!newPortionName || portionWeightInput === '' || portionSubmitting}
                                    onClick={async () => {
                                        if (!newPortionName || portionWeightInput === '') return;
                                        setPortionSubmitting(true);
                                        try {
                                            await apiClient.post(`/foods/${editingFoodId}/portions`, {
                                                name: newPortionName,
                                                weight_g: portionWeightInput,
                                                is_default: newPortionIsDefault
                                            });
                                            const res = await apiClient.get(`/foods/${editingFoodId}/portions`);
                                            setPortions(res.data);
                                            setNewPortionName(''); setPortionWeightInput(''); setNewPortionIsDefault(false);
                                        } finally {
                                            setPortionSubmitting(false);
                                        }
                                    }}
                                >
                                    {portionSubmitting ? '...' : '+ Ajouter'}
                                </button>
                            </div>
                        </div>
                    )}
                </form>
            )}

            {loading ? (
                <div className="text-center">Chargement des aliments...</div>
            ) : (
                <div className="glass-card overflow-x-auto">
                    <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                        <thead>
                            <tr style={{ borderBottom: '1px solid var(--border-color)', backgroundColor: 'rgba(0,0,0,0.05)' }}>
                                <th style={{ padding: '1rem' }}>
                                    <input
                                        type="checkbox"
                                        checked={sortedFoods.length > 0 && selectedFoodIds.length === sortedFoods.length}
                                        onChange={handleSelectAll}
                                    />
                                </th>
                                <th style={{ padding: '1rem', cursor: 'pointer', userSelect: 'none' }} onClick={() => handleSort('is_draft')}>
                                    Statut <SortIcon columnKey="is_draft" />
                                </th>
                                <th style={{ padding: '1rem', cursor: 'pointer', userSelect: 'none' }} onClick={() => handleSort('name')}>
                                    Nom <SortIcon columnKey="name" />
                                </th>
                                <th style={{ padding: '1rem', cursor: 'pointer', userSelect: 'none' }} onClick={() => handleSort('energy_kcal')}>
                                    Kcal (100g) <SortIcon columnKey="energy_kcal" />
                                </th>
                                <th style={{ padding: '1rem', cursor: 'pointer', userSelect: 'none' }} onClick={() => handleSort('proteins_g')}>
                                    Protéines (100g) <SortIcon columnKey="proteins_g" />
                                </th>
                                <th style={{ padding: '1rem', cursor: 'pointer', userSelect: 'none' }} onClick={() => handleSort('fat_g')}>
                                    Lipides (100g) <SortIcon columnKey="fat_g" />
                                </th>
                                <th style={{ padding: '1rem', cursor: 'pointer', userSelect: 'none' }} onClick={() => handleSort('carbohydrates_g')}>
                                    Glucides (100g) <SortIcon columnKey="carbohydrates_g" />
                                </th>
                                <th style={{ padding: '1rem', textAlign: 'right' }}>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {sortedFoods.map(food => (
                                <tr key={food.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                                    <td style={{ padding: '1rem' }}>
                                        <input
                                            type="checkbox"
                                            checked={selectedFoodIds.includes(food.id)}
                                            onChange={() => handleToggleSelect(food.id)}
                                        />
                                    </td>
                                    <td style={{ padding: '1rem' }}>
                                        {food.is_draft ? (
                                            <span style={{ backgroundColor: '#eab308', color: '#fff', padding: '2px 8px', borderRadius: '12px', fontSize: '0.7rem', fontWeight: 'bold' }}>
                                                Brouillon
                                            </span>
                                        ) : (
                                            <span style={{ backgroundColor: '#22c55e', color: '#fff', padding: '2px 8px', borderRadius: '12px', fontSize: '0.7rem', fontWeight: 'bold' }}>
                                                Valide
                                            </span>
                                        )}
                                    </td>
                                    <td style={{ padding: '1rem', fontWeight: 500, color: 'var(--text-primary)' }}>{food.name}</td>
                                    <td style={{ padding: '1rem', color: 'var(--accent-secondary)', fontWeight: 600 }}>{food.energy_kcal}</td>
                                    <td style={{ padding: '1rem' }}>{food.proteins_g}g</td>
                                    <td style={{ padding: '1rem' }}>{food.fat_g}g</td>
                                    <td style={{ padding: '1rem' }}>{food.carbohydrates_g}g</td>
                                    <td style={{ padding: '1rem', textAlign: 'right' }}>
                                        <div className="flex gap-2 justify-end">
                                            <button className="btn btn-secondary" style={{ padding: '0.3rem 0.6rem', fontSize: '0.8rem' }} onClick={() => handleEditClick(food)}>
                                                Éditer
                                            </button>
                                            <button className="btn" style={{ padding: '0.3rem 0.6rem', fontSize: '0.8rem', backgroundColor: 'transparent', color: 'var(--accent-danger)', border: '1px solid var(--accent-danger)' }} onClick={() => handleDeleteFood(food.id)}>
                                                🗑
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    {!loading && foods.length === 0 && (
                        <p className="text-center mt-8 mb-8" style={{ color: 'var(--text-muted)' }}>Aucun aliment trouvé selon vos critères.</p>
                    )}
                    {/* Pagination */}
                    {totalPages > 1 && (
                        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '1rem', padding: '1rem', borderTop: '1px solid var(--border-color)' }}>
                            <button className="btn btn-secondary" style={{ padding: '0.4rem 0.8rem' }} onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1}>
                                ← Précédent
                            </button>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                                Page {currentPage} / {totalPages} &nbsp;({totalCount} aliments)
                            </span>
                            <button className="btn btn-secondary" style={{ padding: '0.4rem 0.8rem' }} onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages}>
                                Suivant →
                            </button>
                        </div>
                    )}
                </div>
            )}

            {/* Modal de Fusion */}
            {showMergeModal && (
                <div style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
                    <div className="glass-card" style={{ padding: '2rem', maxWidth: '500px', width: '90%' }}>
                        <h3 style={{ marginBottom: '1rem', color: 'var(--accent-primary)' }}>🔗 Fusion d'aliments</h3>
                        <p style={{ marginBottom: '1rem', color: 'var(--text-secondary)' }}>
                            Vous avez sélectionné <strong>{selectedFoodIds.length} aliments</strong>. <br /><br />
                            Lequel de ces aliments souhaitez-vous conserver comme référence principale ? Tous les autres brouillons sélectionnés seront <strong>supprimés</strong>, et les recettes qui y étaient liées seront mises à jour pour pointer vers ce grand gagnant.
                        </p>

                        <div className="mb-6">
                            <label className="input-label">Aliment à conserver :</label>
                            <select
                                className="input-field"
                                style={{ width: '100%' }}
                                value={mergeTargetId}
                                onChange={e => setMergeTargetId(e.target.value ? Number(e.target.value) : '')}
                            >
                                <option value="" disabled>-- Choisir l'aliment cible --</option>
                                {foods.filter(f => selectedFoodIds.includes(f.id)).map(f => (
                                    <option key={f.id} value={f.id}>
                                        {f.name} {f.is_draft ? '(Brouillon)' : '(Valide)'}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div className="flex justify-end gap-2">
                            <button className="btn btn-secondary" onClick={() => setShowMergeModal(false)}>Annuler</button>
                            <button className="btn btn-primary" onClick={handleConfirmMerge} disabled={!mergeTargetId}>Confirmer la fusion</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default FoodLibrary;
