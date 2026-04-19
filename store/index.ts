import { create } from 'zustand'
import { User, PantryItem, Recipe, ScannedIngredient, TasteProfile, CookHistoryItem } from '../types'
import { getPantry } from '../lib/supabase'
import AsyncStorage from '@react-native-async-storage/async-storage'
import { Platform } from 'react-native'

export interface UserPrefs {
  dietary: string
  spice: string
  cuisines: string[]
  servings: number
}

const storage = {
  get: async (key: string) => {
    if (Platform.OS === 'web') { try { return localStorage.getItem(key) } catch { return null } }
    return AsyncStorage.getItem(key)
  },
  set: async (key: string, value: string) => {
    if (Platform.OS === 'web') { try { localStorage.setItem(key, value) } catch {} ; return }
    return AsyncStorage.setItem(key, value)
  },
}

const DEFAULT_PREFS: UserPrefs = { dietary: 'All', spice: 'Medium', cuisines: ['all'], servings: 2 }

const defaultTasteProfile: TasteProfile = {
  favoriteDishes: [], preferredCuisines: [], avoidedIngredients: [],
  totalCooked: 0, lastCookedAt: null,
  tasteInsight: 'Cook your first dish to unlock your taste profile!',
}

interface AppState {
  user: User | null
  setUser: (u: User | null) => void
  pantry: PantryItem[]
  setPantry: (items: PantryItem[]) => void
  addPantryItem: (item: PantryItem) => void
  removePantryItem: (id: string) => void
  fetchPantry: (userId: string) => Promise<void>
  savePantryLocal: () => Promise<void>
  loadPantryLocal: () => Promise<void>
  scanned: ScannedIngredient[]
  setScanned: (items: ScannedIngredient[]) => void
  recipes: Recipe[]
  setRecipes: (r: Recipe[]) => void
  activeRecipe: Recipe | null
  setActiveRecipe: (r: Recipe | null) => void
  cookStep: number
  setCookStep: (n: number) => void
  cookHistory: CookHistoryItem[]
  addCookHistory: (item: CookHistoryItem) => void
  loadCookHistory: () => Promise<void>
  tasteProfile: TasteProfile
  updateTasteProfile: (recipe: Recipe) => Promise<void>
  loadTasteProfile: () => Promise<void>
  userPrefs: UserPrefs
  setUserPrefs: (prefs: Partial<UserPrefs>) => Promise<void>
  loadUserPrefs: () => Promise<void>
  loading: boolean
  setLoading: (v: boolean) => void
  error: string | null
  setError: (m: string | null) => void
}

export const useStore = create<AppState>((set, get) => ({
  user: null,
  setUser: (user) => set({ user }),

  pantry: [],
  setPantry: (items) => set({ pantry: items }),
  addPantryItem: async (item) => {
    const pantry = [...get().pantry, item]
    set({ pantry })
    await storage.set('pantry_local', JSON.stringify(pantry))
  },
  removePantryItem: async (id) => {
    const pantry = get().pantry.filter(i => i.id !== id)
    set({ pantry })
    await storage.set('pantry_local', JSON.stringify(pantry))
  },
  fetchPantry: async (userId) => {
    try { const items = await getPantry(userId); set({ pantry: items }) } catch (e) { console.error(e) }
  },
  savePantryLocal: async () => {
    await storage.set('pantry_local', JSON.stringify(get().pantry))
  },
  loadPantryLocal: async () => {
    try {
      const raw = await storage.get('pantry_local')
      if (raw) { const items = JSON.parse(raw); if (items.length > 0) set({ pantry: items }) }
    } catch {}
  },

  scanned: [],
  setScanned: (items) => set({ scanned: items }),
  recipes: [],
  setRecipes: (recipes) => set({ recipes }),
  activeRecipe: null,
  setActiveRecipe: (r) => set({ activeRecipe: r }),
  cookStep: 0,
  setCookStep: (n) => set({ cookStep: n }),

  cookHistory: [],
  addCookHistory: async (item) => {
    const history = [...get().cookHistory, item]
    set({ cookHistory: history })
    await storage.set('cookHistory', JSON.stringify(history))
  },
  loadCookHistory: async () => {
    try { const raw = await storage.get('cookHistory'); if (raw) set({ cookHistory: JSON.parse(raw) }) } catch {}
  },

  tasteProfile: defaultTasteProfile,
  updateTasteProfile: async (recipe) => {
    const current = get().tasteProfile
    const dishes = [...new Set([...current.favoriteDishes, recipe.name])].slice(-20)
    const cuisines = [...new Set([...current.preferredCuisines, recipe.cuisine])].slice(-10)
    const updated: TasteProfile = { ...current, favoriteDishes: dishes, preferredCuisines: cuisines, totalCooked: current.totalCooked + 1, lastCookedAt: new Date().toISOString() }
    set({ tasteProfile: updated })
    await storage.set('tasteProfile', JSON.stringify(updated))
  },
  loadTasteProfile: async () => {
    try { const raw = await storage.get('tasteProfile'); if (raw) set({ tasteProfile: JSON.parse(raw) }) } catch {}
  },

  userPrefs: DEFAULT_PREFS,
  setUserPrefs: async (prefs) => {
    const updated = { ...get().userPrefs, ...prefs }
    set({ userPrefs: updated })
    await storage.set('userPrefs', JSON.stringify(updated))
  },
  loadUserPrefs: async () => {
    try { const raw = await storage.get('userPrefs'); if (raw) set({ userPrefs: JSON.parse(raw) }) } catch {}
  },

  loading: false,
  setLoading: (v) => set({ loading: v }),
  error: null,
  setError: (m) => set({ error: m }),
}))
