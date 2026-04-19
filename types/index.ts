export interface User {
  id: string
  email: string
  name: string
  cuisine_preference: string[]
  dietary_preference: string
  spice_level: string
}

export interface PantryItem {
  id: string
  user_id: string
  name: string
  emoji: string
  quantity: string
  unit: string
  category: string
  confidence?: number
  is_low?: boolean
  added_at: string
}

export interface ScannedIngredient {
  name: string
  emoji: string
  quantity: string
  unit: string
  category: string
  confidence: number
}

export interface RecipeIngredient {
  name: string
  emoji: string
  quantity: string
  unit: string
  have: boolean
}

export interface CookStep {
  number: number
  title: string
  instruction: string
  tip?: string
  timer_seconds?: number
  ingredients_used: string[]
}

export interface NutritionInfo {
  calories: number
  protein_g: number
  carbs_g: number
  fat_g: number
  fiber_g: number
}

export interface Recipe {
  id: string
  name: string
  emoji: string
  cuisine: string
  dietary: string
  description: string
  match_score: number
  missing_ingredients: string[]
  ingredients: RecipeIngredient[]
  steps: CookStep[]
  nutrition: NutritionInfo
  time_minutes: number
  servings: number
  difficulty: 'Easy' | 'Medium' | 'Hard'
  tips: string[]
  generated_at: string
}

export interface TasteProfile {
  favoriteDishes: string[]
  preferredCuisines: string[]
  avoidedIngredients: string[]
  totalCooked: number
  lastCookedAt: string | null
  tasteInsight: string
}

export interface CookHistoryItem {
  id: string
  recipeName: string
  recipeEmoji: string
  cuisine: string
  cookedAt: string
  rating?: number
}
