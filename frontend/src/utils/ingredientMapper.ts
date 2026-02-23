export interface FoodOption {
    id: number;
    name: string;
}

export interface MappedIngredient {
    status: 'matched' | 'unresolved';
    food_id?: number;
    food_name?: string;
    suggested_name?: string;
    quantity_g: number;
    raw_quantity: number | null;
    raw_unit: string | null;
}

export interface ScrapedIngredient {
    raw: string;
    quantity: number | null;
    unit: string | null;
    product: string;
}

export async function mapScrapedIngredients(scrapedIngredients: ScrapedIngredient[], dbFoods: FoodOption[]): Promise<MappedIngredient[]> {
    const mapped: MappedIngredient[] = [];

    // Helper to normalize string for comparison
    const normalize = (str: string) =>
        str.toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "") // Enlever les accents
            .replace(/[^a-z0-9\s]/g, " ")    // Remplacer ponctuation par des espaces
            .trim()
            .replace(/\s+/g, " ")
            .split(" ")
            .map(w => w.replace(/[sx]$/, "")) // Basic French plural stripping
            .join(" ");

    for (const scraped of scrapedIngredients) {
        let matchedFood: FoodOption | null = null;

        // Priorité 1 : Mettre au format correct la quantité
        // Si l'unité est kg ou l, on convertit en g/ml (multiplié par 1000)
        let quantity = scraped.quantity !== null && !isNaN(scraped.quantity) ? scraped.quantity : 100;
        if (scraped.unit === 'kg' || scraped.unit === 'l' || scraped.unit === 'litre' || scraped.unit === 'litres' || scraped.unit === 'kilogramme' || scraped.unit === 'kilogrammes') {
            quantity *= 1000;
        } else if (scraped.unit === 'cl' || scraped.unit === 'centilitre' || scraped.unit === 'centilitres') {
            quantity *= 10;
        } else if (scraped.unit?.includes('cuill') || scraped.unit?.includes('c.a.s') || scraped.unit?.includes('cas')) {
            quantity *= 15; // Approximation : 15g par cuillère à soupe
        } else if (scraped.unit?.includes('c.a.c') || scraped.unit?.includes('cac')) {
            quantity *= 5; // Approximation 5g par cuillère à café
        }

        const normalizedProduct = normalize(scraped.product);
        const productWords = normalizedProduct.split(" ").filter(w => w.length > 0);

        for (const dbFood of dbFoods) {
            const normalizedFoodName = normalize(dbFood.name);

            if (normalizedProduct === normalizedFoodName) {
                matchedFood = dbFood;
                break;
            }

            const foodNameWords = normalizedFoodName.split(" ").filter(w => w.length > 0);

            const dbContainsProduct = productWords.length > 0 && productWords.every(w => foodNameWords.includes(w));
            const productContainsDb = foodNameWords.length > 0 && foodNameWords.every(w => productWords.includes(w));

            if (dbContainsProduct || productContainsDb) {
                // Ignore dirty draft foods containing numbers (like "4 cuilleres") if they are only substring matches
                if (/[0-9]/.test(normalizedFoodName) && productContainsDb && !/[0-9]/.test(normalizedProduct)) {
                    continue;
                }
                matchedFood = dbFood;
                break; // Take the first valid match
            }
        }

        if (matchedFood) {
            mapped.push({
                status: 'matched',
                food_id: matchedFood.id,
                food_name: matchedFood.name,
                quantity_g: quantity,
                raw_quantity: scraped.quantity !== undefined ? scraped.quantity : null,
                raw_unit: scraped.unit !== undefined ? scraped.unit : null
            });
        } else {
            let newName = scraped.product.trim();
            if (!newName) newName = "Ingrédient Inconnu";

            if (newName.length > 50) newName = newName.substring(0, 47) + "...";

            mapped.push({
                status: 'unresolved',
                suggested_name: newName.charAt(0).toUpperCase() + newName.slice(1),
                quantity_g: quantity,
                raw_quantity: scraped.quantity !== undefined ? scraped.quantity : null,
                raw_unit: scraped.unit !== undefined ? scraped.unit : null
            });
        }
    }

    return mapped;
}
