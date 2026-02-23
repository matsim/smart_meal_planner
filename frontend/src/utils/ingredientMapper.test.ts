import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mapScrapedIngredients } from './ingredientMapper';
import apiClient from '../api/client';

vi.mock('../api/client', () => ({
    default: {
        post: vi.fn()
    }
}));

describe('mapScrapedIngredients', () => {
    const mockDbFoods = [
        { id: 1, name: 'Poulet' },
        { id: 2, name: 'Riz basmati' },
        { id: 3, name: 'Oignon rouge' },
        { id: 4, name: 'Huile d\'olive' }
    ];

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('doit mapper un ingrédient simple avec quantité en grammes', async () => {
        const scraped = [{ raw: '200g de poulet', quantity: 200, unit: 'g', product: 'poulet' }];
        const result = await mapScrapedIngredients(scraped, mockDbFoods);

        expect(result).toHaveLength(1);
        expect(result[0].food_id).toBe(1);
        expect(result[0].quantity_g).toBe(200);
    });

    it('doit ignorer la casse et la ponctuation lors du matching', async () => {
        const scraped = [{ raw: '150 g de Riz Basmati, cuit', quantity: 150, unit: 'g', product: 'Riz Basmati, cuit' }];
        const result = await mapScrapedIngredients(scraped, mockDbFoods);

        expect(result).toHaveLength(1);
        expect(result[0].food_id).toBe(2);
        expect(result[0].quantity_g).toBe(150);
    });

    it('doit gérer les quantités implicites ou sans unité standardisée', async () => {
        const scraped = [{ raw: '1 Oignon rouge émincé', quantity: 1, unit: null, product: 'Oignon rouge émincé' }];
        const result = await mapScrapedIngredients(scraped, mockDbFoods);

        expect(result).toHaveLength(1);
        expect(result[0].food_id).toBe(3);
        expect(result[0].quantity_g).toBe(1); // La V1 extrait bien '1' comme quantité brute.
    });

    it('doit créer un ingrédient brouillon si non trouvé en base', async () => {
        (apiClient.post as any).mockResolvedValue({ data: { id: 99, name: "Une pincée de sel magique" } });

        const scraped = [
            { raw: '200g de poulet', quantity: 200, unit: 'g', product: 'poulet' },
            { raw: 'Une pincée de sel magique', quantity: null, unit: 'pincée', product: 'sel magique' }
        ];
        const result = await mapScrapedIngredients(scraped, mockDbFoods);

        expect(result).toHaveLength(2);
        expect(result[0].food_id).toBe(1);
        expect(result[1].food_id).toBe(99);

        expect(apiClient.post).toHaveBeenCalledTimes(1);
        expect(apiClient.post).toHaveBeenCalledWith('/foods/', expect.objectContaining({
            is_draft: true
        }));
    });

    it('doit gérer les cas réels avec pluriels et fractions (ex: oignons -> oignon)', async () => {
        const realisticDb = [
            { id: 10, name: 'Poulet' },
            { id: 11, name: 'Oignon' },
            { id: 12, name: 'Ail' },
            { id: 13, name: 'Sauce soja' },
            { id: 14, name: 'Riz' }
        ];

        const scraped = [
            { raw: '4 filets de poulet', quantity: 4, unit: 'filets', product: 'poulet' },
            { raw: '1 oignons', quantity: 1, unit: null, product: 'oignons' },
            { raw: 'ail au poudre', quantity: null, unit: null, product: 'ail en poudre' }
        ];

        const result = await mapScrapedIngredients(scraped, realisticDb);

        const foundIds = result.map((r: any) => r.food_id);

        expect(foundIds).toContain(10); // Poulet
        expect(foundIds).toContain(11); // Oignon (doit matcher 'oignons')
        expect(foundIds).toContain(12); // Ail
    });
});
