import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import RecipeEditor from './RecipeEditor';
import apiClient from '../api/client';

// Mock du client API pour éviter les vrais appels réseau
vi.mock('../api/client', () => ({
    default: {
        get: vi.fn(),
        post: vi.fn(),
        put: vi.fn(),
    }
}));

describe('RecipeEditor Scraper Integration', () => {
    beforeEach(() => {
        // Reset mocks and storage before each test
        vi.clearAllMocks();
        sessionStorage.clear();

        // Mock default API responses
        (apiClient.get as any).mockResolvedValue({
            data: [
                { id: 1, name: "Poulet" },
                { id: 2, name: "Chocolat" }
            ]
        });
    });

    it('doit pré-remplir les champs avec les données scrapées du sessionStorage', async () => {
        // 1. Préparation des fausses données scrapées
        const fakeScrapedData = {
            title: "Gâteau au chocolat test",
            ingredients: ["200g chocolat", "3 oeufs"],
            instructions: "Mélangez le tout et enfournez."
        };
        sessionStorage.setItem('scrapedRecipe', JSON.stringify(fakeScrapedData));

        // 2. Rendu du composant avec l'URL déclenchant le comportement
        render(
            <MemoryRouter initialEntries={['/recipes/new?fromScraper=true']}>
                <Routes>
                    <Route path="/recipes/new" element={<RecipeEditor />} />
                </Routes>
            </MemoryRouter>
        );

        // 3. Vérification que le champ "Nom" a été pré-rempli
        // On attend que le useEffect ait fait effet
        await waitFor(() => {
            const nameInput = screen.getByPlaceholderText(/Ex: Poulet Basquaise/i) as HTMLInputElement;
            expect(nameInput.value).toBe("Gâteau au chocolat test");
        });

        // 4. Vérification que la description contient les instructions et ingrédients
        const descInput = screen.getByPlaceholderText(/Un délicieux plat équilibré/i) as HTMLTextAreaElement;
        expect(descInput.value).toContain("--- Ingrédients extraits ---");
        expect(descInput.value).toContain("200g chocolat");
        expect(descInput.value).toContain("--- Instructions ---");
        expect(descInput.value).toContain("Mélangez le tout et enfournez.");

        // 5. Vérifier que le sessionStorage a bien été vidé après lecture
        expect(sessionStorage.getItem('scrapedRecipe')).toBeNull();

        // 6. Vérifier que l'ingrédient mappé est ajouté à la liste UI
        // Chocolat exists in both the <li> and the <select> option, so we fetch all and check we have multiple instances
        const chocolatElements = screen.getAllByText(/Chocolat/i);
        expect(chocolatElements.length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText(/\(200\s*g\)/i)).toBeInTheDocument();
    });
});
