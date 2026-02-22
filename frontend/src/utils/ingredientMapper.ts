import apiClient from '../api/client';

export interface FoodOption {
    id: number;
    name: string;
}

export interface MappedIngredient {
    food_id: number;
    food_name: string;
    quantity_g: number;
}

export async function mapScrapedIngredients(scrapedIngredients: string[], dbFoods: FoodOption[]): Promise<MappedIngredient[]> {
    const mapped: MappedIngredient[] = [];

    // Helper to normalize string for comparison
    const normalize = (str: string) => str.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim();

    for (const scrapedLine of scrapedIngredients) {
        let matchedFood: FoodOption | null = null;
        let quantity = 100; // Default weight

        // Basic parsing: look for digits followed by 'g'
        const qtyMatch = scrapedLine.match(/(\d+)\s*g/i);
        if (qtyMatch) {
            quantity = parseInt(qtyMatch[1], 10);
        }

        const normalizedLine = normalize(scrapedLine);

        for (const dbFood of dbFoods) {
            const normalizedFoodName = normalize(dbFood.name);
            if (normalizedLine.includes(normalizedFoodName) || normalizedFoodName.includes(normalizedLine)) {
                matchedFood = dbFood;
                break; // Take the first match
            }
        }

        if (matchedFood) {
            mapped.push({
                food_id: matchedFood.id,
                food_name: matchedFood.name,
                quantity_g: quantity
            });
        } else {
            // Création asynchrone d'un aliment brouillon si non trouvé
            // On essaie d'extraire un nom propre (en enlevant les chiffres et "de", "g")
            let newName = scrapedLine.replace(/(\d+)\s*g/i, '').replace(/\b(?:de|des|du|la|le|un|une)\b/gi, '').trim();
            if (!newName) newName = "Ingrédient Inconnu";

            // On limite la taille pour être sûr
            if (newName.length > 50) newName = newName.substring(0, 47) + "...";

            try {
                const res = await apiClient.post('/foods/', {
                    name: newName.charAt(0).toUpperCase() + newName.slice(1),
                    energy_kcal: 0,
                    proteins_g: 0,
                    carbohydrates_g: 0,
                    fat_g: 0,
                    fiber_g: 0,
                    water_g: 0,
                    is_draft: true
                });
                const newFood = res.data;
                mapped.push({
                    food_id: newFood.id,
                    food_name: newFood.name,
                    quantity_g: quantity
                });
            } catch (err) {
                console.error("Impossible de créer l'aliment brouillon:", newName, err);
            }
        }
    }

    return mapped;
}
