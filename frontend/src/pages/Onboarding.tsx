import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/client';

const Onboarding: React.FC = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState({
        email: '',
        age: 30,
        weight_kg: 70.0,
        height_cm: 175.0,
        gender: 'female',
        activity_level: 'sedentary',
        objective: 'maintenance',
        daily_meals_count: 3
    });

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: name === 'age' || name === 'daily_meals_count' ? parseInt(value)
                : name === 'weight_kg' || name === 'height_cm' ? parseFloat(value)
                    : value
        }));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            // Create user
            const userRes = await apiClient.post('/users/', formData);
            const userId = userRes.data.id;

            // Store user id in local storage
            localStorage.setItem('user_id', userId.toString());

            // Redirect to Dashboard
            navigate('/dashboard');
        } catch (error) {
            console.error("Error creating profile:", error);
            alert("Erreur lors de la création du profil. L'email existe-t-il déjà ?");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="glass-card" style={{ maxWidth: '600px', margin: '0 auto', padding: '2rem' }}>
            <h2 style={{ textAlign: 'center', marginBottom: '0.5rem', color: 'var(--accent-primary)' }}>Votre Profil Métabolique</h2>
            <p style={{ textAlign: 'center', marginBottom: '2rem', color: 'var(--text-secondary)' }}>
                Renseignez vos informations pour que notre IA calcule précisément vos besoins.
            </p>

            <form onSubmit={handleSubmit}>
                <div className="input-group">
                    <label className="input-label">Email (Identifiant)</label>
                    <input className="input-field" type="email" name="email" value={formData.email} onChange={handleChange} required placeholder="test@demo.com" />
                </div>

                <div className="flex gap-4">
                    <div className="input-group" style={{ flex: 1 }}>
                        <label className="input-label">Âge</label>
                        <input className="input-field" type="number" name="age" value={formData.age} onChange={handleChange} required min="18" max="100" />
                    </div>
                    <div className="input-group" style={{ flex: 1 }}>
                        <label className="input-label">Sexe</label>
                        <select className="input-field" name="gender" value={formData.gender} onChange={handleChange}>
                            <option value="male">Homme</option>
                            <option value="female">Femme</option>
                        </select>
                    </div>
                </div>

                <div className="flex gap-4">
                    <div className="input-group" style={{ flex: 1 }}>
                        <label className="input-label">Poids (kg)</label>
                        <input className="input-field" type="number" name="weight_kg" value={formData.weight_kg} onChange={handleChange} required step="0.1" />
                    </div>
                    <div className="input-group" style={{ flex: 1 }}>
                        <label className="input-label">Taille (cm)</label>
                        <input className="input-field" type="number" name="height_cm" value={formData.height_cm} onChange={handleChange} required step="0.5" />
                    </div>
                </div>

                <div className="input-group">
                    <label className="input-label">Niveau d'Activité</label>
                    <select className="input-field" name="activity_level" value={formData.activity_level} onChange={handleChange}>
                        <option value="sedentary">Sédentaire (Bureau, pas de sport)</option>
                        <option value="lightly_active">Légèrement Actif (1-3x / semaine)</option>
                        <option value="moderate">Modérément Actif (3-5x / semaine)</option>
                        <option value="very_active">Très Actif (6-7x / semaine)</option>
                        <option value="extra_active">Extrêmement Actif (Sportif Pro)</option>
                    </select>
                </div>

                <div className="input-group">
                    <label className="input-label">Objectif</label>
                    <select className="input-field" name="objective" value={formData.objective} onChange={handleChange}>
                        <option value="weight_loss">Perte de Poids (-500 kcal)</option>
                        <option value="maintenance">Maintien (Équilibre)</option>
                        <option value="muscle_gain">Prise de Masse (+300 kcal)</option>
                    </select>
                </div>

                <div className="input-group" style={{ marginBottom: '2rem' }}>
                    <label className="input-label">Nombre de Repas par Jour</label>
                    <input className="input-field" type="number" name="daily_meals_count" value={formData.daily_meals_count} onChange={handleChange} required min="1" max="6" />
                </div>

                <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>
                    {loading ? 'Calcul en cours...' : 'Calculer mon besoin et Démarrer'}
                </button>
            </form>
        </div>
    );
};

export default Onboarding;
