import os, json

root = os.getcwd()

def w(path, content):
    full = os.path.join(root, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  ✓ {path}")

print("\n=== CookMate AI — Full Functional Build ===\n")

# ─────────────────────────────────────────────────────────────
# 1. ENHANCED GEMINI LIB — better prompts, taste profile, subs
# ─────────────────────────────────────────────────────────────
w("lib/gemini.ts", '''import { ScannedIngredient, Recipe, PantryItem, TasteProfile } from \'../types\'

const API_KEY = process.env.EXPO_PUBLIC_GEMINI_API_KEY!
const BASE = \'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent\'

async function ask(parts: object[], maxTokens = 4000): Promise<string> {
  const res = await fetch(`${BASE}?key=${API_KEY}`, {
    method: \'POST\',
    headers: { \'Content-Type\': \'application/json\' },
    body: JSON.stringify({
      contents: [{ parts }],
      generationConfig: { temperature: 0.7, maxOutputTokens: maxTokens },
    }),
  })
  if (!res.ok) {
    const errText = await res.text()
    throw new Error(`Gemini ${res.status}: ${errText}`)
  }
  const d = await res.json()
  return d.candidates?.[0]?.content?.parts?.[0]?.text ?? \'\'
}

function parseJSON<T>(raw: string): T | null {
  try {
    const clean = raw.replace(/```json|```/g, \'\').trim()
    // find first [ or { 
    const arrStart = clean.indexOf(\'[\')
    const objStart = clean.indexOf(\'{\')
    let jsonStr = clean
    if (arrStart !== -1 && (objStart === -1 || arrStart < objStart)) {
      jsonStr = clean.slice(arrStart, clean.lastIndexOf(\']\') + 1)
    } else if (objStart !== -1) {
      jsonStr = clean.slice(objStart, clean.lastIndexOf(\'}\') + 1)
    }
    return JSON.parse(jsonStr)
  } catch {
    return null
  }
}

// ── 1. SCAN INGREDIENTS FROM PHOTO ─────────────────────────
export async function scanIngredients(base64: string, mime = \'image/jpeg\'): Promise<ScannedIngredient[]> {
  const prompt = `You are an expert ingredient recognition AI for a cooking app.
Analyze this image and identify ALL visible food ingredients.

Return ONLY a valid JSON array with no markdown, no explanation:
[{"name":"Tomatoes","emoji":"🍅","quantity":"3","unit":"pcs","category":"vegetables","confidence":97}]

Rules:
- Categories: proteins | vegetables | grains | spices | dairy | oils | condiments | other
- confidence: 0-100 (how sure you are)
- quantity: estimate visible amount as a number string
- unit: pcs | kg | g | L | ml | cups | tbsp | tsp
- Include partial/blurry items with lower confidence
- Use common names, not scientific names
- Be generous — include everything edible you can see`

  const text = await ask([
    { text: prompt },
    { inline_data: { mime_type: mime, data: base64 } },
  ])
  return parseJSON<ScannedIngredient[]>(text) ?? []
}

// ── 2. GENERATE PERSONALISED RECIPES ───────────────────────
export async function generateRecipes(
  pantry: PantryItem[],
  prefs: { cuisines: string[]; dietary: string; spice: string; servings: number },
  tasteProfile?: TasteProfile | null
): Promise<Recipe[]> {
  const ingredients = pantry.map(i => `${i.emoji} ${i.name} (${i.quantity} ${i.unit})`).join(\'\\n\')
  const cuisines = prefs.cuisines.includes(\'all\')
    ? \'Indian, South Indian, Southeast Asian, Continental, Middle Eastern\'
    : prefs.cuisines.join(\', \')

  const tasteCtx = tasteProfile ? `
USER TASTE PROFILE (learned from past cooks):
- Favourite dishes: ${tasteProfile.favoriteDishes.slice(0, 5).join(\', \') || \'none yet\'}
- Avoided ingredients: ${tasteProfile.avoidedIngredients.join(\', \') || \'none\'}
- Preferred cuisines: ${tasteProfile.preferredCuisines.join(\', \') || \'all\'}
- Total recipes cooked: ${tasteProfile.totalCooked}
Prioritise dishes similar to favourites, avoid avoided ingredients.` : \'\'

  const prompt = `You are a world-class chef AI with deep knowledge of global cuisines.

PANTRY INGREDIENTS:
${ingredients}

USER PREFERENCES:
- Cuisines: ${cuisines}
- Dietary: ${prefs.dietary}
- Spice level: ${prefs.spice}
- Servings: ${prefs.servings}
${tasteCtx}

Generate EXACTLY 5 recipes. Rules:
1. Maximise ingredient match from pantry
2. Use EXACT authentic dish names (not "Indian Curry" but "Dal Makhani")
3. Every step must be detailed and actionable
4. Include realistic timers for cooking steps
5. Calculate accurate nutrition per serving

Return ONLY a valid JSON array:
[{
  "id":"r1",
  "name":"Chole Bhature",
  "emoji":"🫘",
  "cuisine":"Punjabi",
  "dietary":"Vegetarian",
  "description":"Fluffy fried bread with spiced chickpea curry — a North Indian classic",
  "match_score":94,
  "missing_ingredients":["baking soda"],
  "ingredients":[{"name":"Chickpeas","emoji":"🫘","quantity":"2","unit":"cups","have":true}],
  "steps":[{
    "number":1,
    "title":"Soak chickpeas overnight",
    "instruction":"Rinse 2 cups chickpeas thoroughly. Soak in 6 cups water for 8 hours or overnight. They will double in size.",
    "tip":"Add a pinch of baking soda to soften faster.",
    "timer_seconds":0,
    "ingredients_used":["Chickpeas"]
  }],
  "nutrition":{"calories":520,"protein_g":18,"carbs_g":72,"fat_g":16,"fiber_g":12},
  "time_minutes":45,
  "servings":2,
  "difficulty":"Medium",
  "tips":["Soak chickpeas overnight for best results","The bhatura dough needs 2h rest"],
  "generated_at":"${new Date().toISOString()}"
}]
Sort by match_score descending. Be culturally accurate and specific.`

  const text = await ask([{ text: prompt }], 5000)
  const recipes = parseJSON<Recipe[]>(text)
  if (!recipes || recipes.length === 0) {
    throw new Error(\'AI returned no recipes. Check your Gemini API key.\')
  }
  return recipes
}

// ── 3. COOK MODE AI Q&A ─────────────────────────────────────
export async function askCookingQuestion(
  question: string,
  ctx: { recipeName: string; step: number; totalSteps: number; instruction: string; allIngredients: string[] }
): Promise<string> {
  const prompt = `You are a sous-chef AI assistant in a cooking app.
Dish: "${ctx.recipeName}" | Step ${ctx.step}/${ctx.totalSteps}
Current instruction: "${ctx.instruction}"
All ingredients in this recipe: ${ctx.allIngredients.join(\', \')}

User asks: "${question}"

Answer in 2-3 sentences maximum. Be specific, practical, and direct.
No filler like "Great question!" or "Of course!".`
  return await ask([{ text: prompt }], 300)
}

// ── 4. SMART INGREDIENT SUBSTITUTION ───────────────────────
export async function getSubstitute(
  missing: string,
  recipe: string,
  available: string[]
): Promise<{ substitute: string; ratio: string; note: string }> {
  const prompt = `You are a culinary expert.
Making "${recipe}" but missing: ${missing}
Available in pantry: ${available.join(\', \')}

Find the best substitute from available items, or suggest a common household item.
Return ONLY valid JSON (no markdown):
{"substitute":"Greek yogurt","ratio":"1:1","note":"Adds slight tang, works perfectly in curries"}`
  const text = await ask([{ text: prompt }], 200)
  return parseJSON<{ substitute: string; ratio: string; note: string }>(text) ?? 
    { substitute: \'No substitute found\', ratio: \'-\', note: \'This ingredient may be essential\' }
}

// ── 5. GENERATE TASTE PROFILE INSIGHTS ─────────────────────
export async function generateTasteInsight(profile: TasteProfile): Promise<string> {
  if (profile.totalCooked < 2) return \'Cook more dishes to unlock your personalised taste profile!\'
  const prompt = `Based on this cooking history, write ONE fun sentence about this person\'s taste preferences:
Favourite dishes: ${profile.favoriteDishes.join(\', \')}
Preferred cuisines: ${profile.preferredCuisines.join(\', \')}
Total cooked: ${profile.totalCooked}

Write exactly 1 sentence, max 15 words, fun and personalised. No quotes.`
  return await ask([{ text: prompt }], 100)
}
''')


# ─────────────────────────────────────────────────────────────
# 2. ENHANCED TYPES — adds TasteProfile, CookHistoryItem
# ─────────────────────────────────────────────────────────────
w("types/index.ts", '''export interface User {
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
  difficulty: \'Easy\' | \'Medium\' | \'Hard\'
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
''')


# ─────────────────────────────────────────────────────────────
# 3. ENHANCED STORE — adds taste profile, cook history, persist
# ─────────────────────────────────────────────────────────────
w("store/index.ts", '''import { create } from \'zustand\'
import { User, PantryItem, Recipe, ScannedIngredient, TasteProfile, CookHistoryItem } from \'../types\'
import { getPantry } from \'../lib/supabase\'
import AsyncStorage from \'@react-native-async-storage/async-storage\'
import { Platform } from \'react-native\'

const storage = {
  get: async (key: string) => {
    if (Platform.OS === \'web\') {
      try { return localStorage.getItem(key) } catch { return null }
    }
    return AsyncStorage.getItem(key)
  },
  set: async (key: string, value: string) => {
    if (Platform.OS === \'web\') {
      try { localStorage.setItem(key, value) } catch {}
      return
    }
    return AsyncStorage.setItem(key, value)
  },
}

interface AppState {
  user: User | null
  setUser: (u: User | null) => void

  pantry: PantryItem[]
  setPantry: (items: PantryItem[]) => void
  addPantryItem: (item: PantryItem) => void
  removePantryItem: (id: string) => void
  fetchPantry: (userId: string) => Promise<void>

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

  loading: boolean
  setLoading: (v: boolean) => void
  error: string | null
  setError: (m: string | null) => void
}

const defaultTasteProfile: TasteProfile = {
  favoriteDishes: [],
  preferredCuisines: [],
  avoidedIngredients: [],
  totalCooked: 0,
  lastCookedAt: null,
  tasteInsight: \'Cook your first dish to unlock your taste profile!\',
}

export const useStore = create<AppState>((set, get) => ({
  user: null,
  setUser: (user) => set({ user }),

  pantry: [],
  setPantry: (items) => set({ pantry: items }),
  addPantryItem: (item) => set(s => ({ pantry: [...s.pantry, item] })),
  removePantryItem: (id) => set(s => ({ pantry: s.pantry.filter(i => i.id !== id) })),
  fetchPantry: async (userId) => {
    try {
      const items = await getPantry(userId)
      set({ pantry: items })
    } catch (e) { console.error(e) }
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
    await storage.set(\'cookHistory\', JSON.stringify(history))
  },
  loadCookHistory: async () => {
    try {
      const raw = await storage.get(\'cookHistory\')
      if (raw) set({ cookHistory: JSON.parse(raw) })
    } catch {}
  },

  tasteProfile: defaultTasteProfile,
  updateTasteProfile: async (recipe) => {
    const current = get().tasteProfile
    const dishes = [...new Set([...current.favoriteDishes, recipe.name])].slice(-20)
    const cuisines = [...new Set([...current.preferredCuisines, recipe.cuisine])].slice(-10)
    const updated: TasteProfile = {
      ...current,
      favoriteDishes: dishes,
      preferredCuisines: cuisines,
      totalCooked: current.totalCooked + 1,
      lastCookedAt: new Date().toISOString(),
    }
    set({ tasteProfile: updated })
    await storage.set(\'tasteProfile\', JSON.stringify(updated))
  },
  loadTasteProfile: async () => {
    try {
      const raw = await storage.get(\'tasteProfile\')
      if (raw) set({ tasteProfile: JSON.parse(raw) })
    } catch {}
  },

  loading: false,
  setLoading: (v) => set({ loading: v }),
  error: null,
  setError: (m) => set({ error: m }),
}))
''')


# ─────────────────────────────────────────────────────────────
# 4. ENHANCED SUPABASE LIB
# ─────────────────────────────────────────────────────────────
w("lib/supabase.ts", '''import { createClient } from \'@supabase/supabase-js\'
import AsyncStorage from \'@react-native-async-storage/async-storage\'
import { Platform } from \'react-native\'
import { PantryItem, ScannedIngredient } from \'../types\'

export const supabase = createClient(
  process.env.EXPO_PUBLIC_SUPABASE_URL!,
  process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY!,
  {
    auth: {
      storage: Platform.OS === \'web\' ? undefined : AsyncStorage,
      autoRefreshToken: true,
      persistSession: Platform.OS !== \'web\',
      detectSessionInUrl: Platform.OS === \'web\',
    },
  }
)

export async function signUp(email: string, password: string, name: string) {
  const { data, error } = await supabase.auth.signUp({
    email, password,
    options: { data: { name } },
  })
  if (error) throw error
  if (data.user) {
    await supabase.from(\'profiles\').upsert({
      id: data.user.id, name, email,
      cuisine_preference: [\'indian\', \'south-indian\'],
      dietary_preference: \'all\',
      spice_level: \'Medium\',
    })
  }
  return data
}

export async function signIn(email: string, password: string) {
  const { data, error } = await supabase.auth.signInWithPassword({ email, password })
  if (error) throw error
  return data
}

export async function signOut() { await supabase.auth.signOut() }

export async function getCurrentUser() {
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return null
  const { data } = await supabase.from(\'profiles\').select(\'*\').eq(\'id\', user.id).single()
  return data
}

export async function getPantry(userId: string): Promise<PantryItem[]> {
  const { data, error } = await supabase
    .from(\'pantry\').select(\'*\').eq(\'user_id\', userId).order(\'category\')
  if (error) throw error
  return data ?? []
}

export async function addPantryItems(items: ScannedIngredient[], userId: string) {
  const rows = items.map(i => ({
    user_id: userId, name: i.name, emoji: i.emoji,
    quantity: i.quantity, unit: i.unit, category: i.category,
    confidence: i.confidence, added_at: new Date().toISOString(),
  }))
  const { error } = await supabase.from(\'pantry\').upsert(rows, { onConflict: \'user_id,name\' })
  if (error) throw error
}

export async function addManualItem(item: Omit<PantryItem, \'id\' | \'added_at\'>) {
  const { data, error } = await supabase
    .from(\'pantry\').insert({ ...item, added_at: new Date().toISOString() }).select().single()
  if (error) throw error
  return data
}

export async function deletePantryItem(id: string) {
  const { error } = await supabase.from(\'pantry\').delete().eq(\'id\', id)
  if (error) throw error
}

export async function saveCookHistory(userId: string, recipeName: string, emoji: string, cuisine: string) {
  await supabase.from(\'cook_history\').insert({
    user_id: userId, recipe_name: recipeName, emoji, cuisine,
    completed: true, cooked_at: new Date().toISOString(),
  })
}

export async function getStats(userId: string) {
  const { data } = await supabase
    .from(\'cook_history\').select(\'id\').eq(\'user_id\', userId).eq(\'completed\', true)
  return { recipes_cooked: data?.length ?? 0 }
}
''')


# ─────────────────────────────────────────────────────────────
# 5. ROOT LAYOUT — loads taste profile + history on boot
# ─────────────────────────────────────────────────────────────
w("app/_layout.tsx", '''import { useEffect } from \'react\'
import { Stack } from \'expo-router\'
import { StatusBar } from \'expo-status-bar\'
import { GestureHandlerRootView } from \'react-native-gesture-handler\'
import { SafeAreaProvider } from \'react-native-safe-area-context\'
import { View, StyleSheet } from \'react-native\'
import { Colors } from \'../constants/theme\'
import { supabase, getCurrentUser } from \'../lib/supabase\'
import { useStore } from \'../store\'

export default function RootLayout() {
  const { setUser, fetchPantry, loadTasteProfile, loadCookHistory } = useStore()

  useEffect(() => {
    // Load local data immediately on boot
    loadTasteProfile()
    loadCookHistory()

    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user) {
        getCurrentUser().then(u => {
          setUser(u)
          if (u) fetchPantry(u.id)
        })
      }
    })
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === \'SIGNED_IN\' && session) {
        const u = await getCurrentUser()
        setUser(u)
        if (u) fetchPantry(u.id)
      }
      if (event === \'SIGNED_OUT\') setUser(null)
    })
    return () => subscription.unsubscribe()
  }, [])

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <View style={styles.root}>
          <StatusBar style="light" />
          <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: Colors.bg } }}>
            <Stack.Screen name="(tabs)" />
            <Stack.Screen name="auth" options={{ presentation: \'modal\' }} />
            <Stack.Screen name="cook/[id]" options={{ presentation: \'fullScreenModal\', animation: \'slide_from_bottom\' }} />
          </Stack>
        </View>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: Colors.bg },
})
''')


# ─────────────────────────────────────────────────────────────
# 6. HOME SCREEN — live pantry, taste profile widget, history
# ─────────────────────────────────────────────────────────────
w("app/(tabs)/index.tsx", '''import { View, Text, ScrollView, TouchableOpacity, StyleSheet, Dimensions, Alert } from \'react-native\'
import { router } from \'expo-router\'
import { useSafeAreaInsets } from \'react-native-safe-area-context\'
import { Colors, S, R } from \'../../constants/theme\'
import { useStore } from \'../../store\'

const { width } = Dimensions.get(\'window\')
const COL = (width - 48) / 2

export default function HomeScreen() {
  const insets = useSafeAreaInsets()
  const { user, pantry, recipes, cookHistory, tasteProfile } = useStore()
  const hour = new Date().getHours()
  const greeting = hour < 12 ? \'Good morning\' : hour < 17 ? \'Good afternoon\' : \'Good evening\'
  const firstName = user?.name?.split(\' \')[0] ?? \'Chef\'

  const recentHistory = cookHistory.slice(-3).reverse()

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: 100 }}>

        {/* ── Header ── */}
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>{greeting} 👋</Text>
            <Text style={styles.title}>What shall we{\'\\n\'}cook <Text style={styles.titleAccent}>today?</Text></Text>
          </View>
          <TouchableOpacity style={styles.avatar} onPress={() => router.push(\'/(tabs)/profile\')}>
            <Text style={styles.avatarText}>{firstName[0]?.toUpperCase() ?? \'C\'}</Text>
          </TouchableOpacity>
        </View>

        {/* ── Scan CTA ── */}
        <TouchableOpacity style={styles.scanCta} onPress={() => router.push(\'/(tabs)/scan\')} activeOpacity={0.88}>
          <View style={styles.scanCtaIcon}><Text style={{ fontSize: 24 }}>📸</Text></View>
          <View style={{ flex: 1 }}>
            <Text style={styles.scanCtaTitle}>Scan Ingredients</Text>
            <Text style={styles.scanCtaSub}>AI detects & generates recipes instantly</Text>
          </View>
          <View style={styles.scanArrow}><Text style={{ color: Colors.bg, fontSize: 18, fontWeight: \'700\' }}>→</Text></View>
        </TouchableOpacity>

        {/* ── Stats Row ── */}
        <View style={styles.statsRow}>
          {[
            { icon: \'🧺\', val: pantry.length || 0, label: \'In Pantry\', color: Colors.green, onPress: () => router.push(\'/(tabs)/pantry\') },
            { icon: \'📖\', val: `${recipes.length || \'140\'  }+`, label: \'Recipes\', color: Colors.purple, onPress: () => router.push(\'/(tabs)/recipes\') },
            { icon: \'🌍\', val: 8, label: \'Cuisines\', color: Colors.cyan, onPress: () => {} },
          ].map((s, i) => (
            <TouchableOpacity key={i} style={styles.statCard} onPress={s.onPress} activeOpacity={0.8}>
              <Text style={{ fontSize: 22, marginBottom: 6 }}>{s.icon}</Text>
              <Text style={[styles.statVal, { color: s.color }]}>{s.val}</Text>
              <Text style={styles.statLabel}>{s.label}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* ── Taste Profile Widget ── */}
        {tasteProfile.totalCooked > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionLabel}>🧠 Your Taste Profile</Text>
            <View style={styles.tasteCard}>
              <Text style={styles.tasteInsight}>{tasteProfile.tasteInsight}</Text>
              <View style={styles.tasteRow}>
                <View style={styles.tasteStat}>
                  <Text style={[styles.tasteStatVal, { color: Colors.accent }]}>{tasteProfile.totalCooked}</Text>
                  <Text style={styles.tasteStatLabel}>Cooked</Text>
                </View>
                <View style={styles.tasteDivider} />
                <View style={styles.tasteStat}>
                  <Text style={[styles.tasteStatVal, { color: Colors.green }]}>{tasteProfile.preferredCuisines.length}</Text>
                  <Text style={styles.tasteStatLabel}>Cuisines</Text>
                </View>
                <View style={styles.tasteDivider} />
                <View style={styles.tasteStat}>
                  <Text style={[styles.tasteStatVal, { color: Colors.purple }]}>{tasteProfile.favoriteDishes.length}</Text>
                  <Text style={styles.tasteStatLabel}>Favorites</Text>
                </View>
              </View>
              {tasteProfile.favoriteDishes.length > 0 && (
                <View style={styles.favRow}>
                  {tasteProfile.favoriteDishes.slice(-4).map((d, i) => (
                    <View key={i} style={styles.favChip}>
                      <Text style={styles.favChipText}>{d}</Text>
                    </View>
                  ))}
                </View>
              )}
            </View>
          </View>
        )}

        {/* ── Pantry Quick View ── */}
        {pantry.length > 0 && (
          <View style={styles.section}>
            <View style={styles.rowBetween}>
              <Text style={styles.sectionLabel}>🧺 Your Pantry</Text>
              <TouchableOpacity onPress={() => router.push(\'/(tabs)/pantry\')}>
                <Text style={styles.seeAll}>View all →</Text>
              </TouchableOpacity>
            </View>
            <ScrollView horizontal showsHorizontalScrollIndicator={false}>
              {pantry.slice(0, 8).map((item, i) => (
                <View key={i} style={styles.pantryChip}>
                  <Text style={{ fontSize: 18 }}>{item.emoji}</Text>
                  <Text style={styles.pantryChipName} numberOfLines={1}>{item.name}</Text>
                </View>
              ))}
              {pantry.length > 8 && (
                <TouchableOpacity style={[styles.pantryChip, { backgroundColor: Colors.accentGlow, borderColor: Colors.accent }]} onPress={() => router.push(\'/(tabs)/recipes\')}>
                  <Text style={{ color: Colors.accent, fontWeight: \'700\', fontSize: 13 }}>+{pantry.length - 8} more</Text>
                  <Text style={{ color: Colors.accent, fontSize: 11 }}>→ Cook!</Text>
                </TouchableOpacity>
              )}
            </ScrollView>
          </View>
        )}

        {/* ── Generate CTA if pantry has items ── */}
        {pantry.length > 0 && (
          <TouchableOpacity style={styles.generateCta} onPress={() => router.push(\'/(tabs)/recipes\')} activeOpacity={0.88}>
            <Text style={styles.generateCtaIcon}>✨</Text>
            <View style={{ flex: 1 }}>
              <Text style={styles.generateCtaTitle}>Generate AI Recipes</Text>
              <Text style={styles.generateCtaSub}>{pantry.length} ingredients ready → tap to cook</Text>
            </View>
            <View style={[styles.scanArrow, { backgroundColor: Colors.purple }]}>
              <Text style={{ color: \'#fff\', fontSize: 18, fontWeight: \'700\' }}>→</Text>
            </View>
          </TouchableOpacity>
        )}

        {/* ── Recent Cook History ── */}
        {recentHistory.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionLabel}>🍳 Recently Cooked</Text>
            {recentHistory.map((item, i) => (
              <View key={i} style={styles.historyRow}>
                <View style={styles.historyEmoji}>
                  <Text style={{ fontSize: 24 }}>{item.recipeEmoji}</Text>
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.historyName}>{item.recipeName}</Text>
                  <Text style={styles.historyMeta}>{item.cuisine} · {new Date(item.cookedAt).toLocaleDateString()}</Text>
                </View>
                <View style={styles.cookedBadge}>
                  <Text style={styles.cookedBadgeText}>✓ Cooked</Text>
                </View>
              </View>
            ))}
          </View>
        )}

        {/* ── Empty State ── */}
        {pantry.length === 0 && cookHistory.length === 0 && (
          <View style={styles.emptyState}>
            <Text style={{ fontSize: 64, marginBottom: 16 }}>👨‍🍳</Text>
            <Text style={styles.emptyTitle}>Start Your Journey</Text>
            <Text style={styles.emptySub}>Scan your fridge or add ingredients to get personalized AI recipes in seconds</Text>
            <TouchableOpacity style={styles.emptyBtn} onPress={() => router.push(\'/(tabs)/scan\')}>
              <Text style={styles.emptyBtnText}>📸 Scan Ingredients</Text>
            </TouchableOpacity>
          </View>
        )}

      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  root:             { flex: 1, backgroundColor: Colors.bg },
  header:           { flexDirection: \'row\', justifyContent: \'space-between\', alignItems: \'flex-start\', paddingHorizontal: S.base, paddingTop: S.base, paddingBottom: S.md },
  greeting:         { fontSize: 13, color: Colors.text2, marginBottom: 4, fontWeight: \'500\' },
  title:            { fontSize: 30, color: Colors.text, fontWeight: \'800\', lineHeight: 36, letterSpacing: -0.5 },
  titleAccent:      { color: Colors.accent },
  avatar:           { width: 44, height: 44, borderRadius: 22, backgroundColor: Colors.accentGlow, borderWidth: 2, borderColor: Colors.accent, alignItems: \'center\', justifyContent: \'center\' },
  avatarText:       { fontSize: 18, fontWeight: \'800\', color: Colors.accent },
  scanCta:          { flexDirection: \'row\', alignItems: \'center\', gap: 14, backgroundColor: Colors.accent, borderRadius: R.lg, padding: S.base, marginHorizontal: S.base, marginBottom: S.md },
  scanCtaIcon:      { width: 48, height: 48, backgroundColor: \'rgba(0,0,0,0.2)\', borderRadius: R.sm, alignItems: \'center\', justifyContent: \'center\' },
  scanCtaTitle:     { fontSize: 16, color: \'#fff\', fontWeight: \'800\', marginBottom: 2 },
  scanCtaSub:       { fontSize: 12, color: \'rgba(255,255,255,0.8)\' },
  scanArrow:        { width: 36, height: 36, borderRadius: 18, backgroundColor: \'rgba(0,0,0,0.2)\', alignItems: \'center\', justifyContent: \'center\' },
  statsRow:         { flexDirection: \'row\', gap: 8, paddingHorizontal: S.base, marginBottom: S.md },
  statCard:         { flex: 1, backgroundColor: Colors.bg3, borderWidth: 1, borderColor: Colors.border, borderRadius: R.md, padding: 14, alignItems: \'center\' },
  statVal:          { fontSize: 22, fontWeight: \'800\', marginBottom: 2 },
  statLabel:        { fontSize: 11, color: Colors.text2, textTransform: \'uppercase\', letterSpacing: 0.5 },
  section:          { paddingHorizontal: S.base, marginBottom: S.lg },
  sectionLabel:     { fontSize: 11, fontWeight: \'700\', color: Colors.text3, textTransform: \'uppercase\', letterSpacing: 0.8, marginBottom: 10 },
  rowBetween:       { flexDirection: \'row\', justifyContent: \'space-between\', alignItems: \'center\', marginBottom: 10 },
  seeAll:           { fontSize: 13, color: Colors.accent, fontWeight: \'600\' },
  tasteCard:        { backgroundColor: Colors.bg3, borderWidth: 1, borderColor: Colors.border2, borderRadius: R.lg, padding: S.base },
  tasteInsight:     { fontSize: 14, color: Colors.text, fontWeight: \'600\', marginBottom: 14, lineHeight: 20 },
  tasteRow:         { flexDirection: \'row\', marginBottom: 12 },
  tasteStat:        { flex: 1, alignItems: \'center\' },
  tasteStatVal:     { fontSize: 22, fontWeight: \'800\' },
  tasteStatLabel:   { fontSize: 10, color: Colors.text3, textTransform: \'uppercase\', marginTop: 2 },
  tasteDivider:     { width: 1, backgroundColor: Colors.border, marginVertical: 4 },
  favRow:           { flexDirection: \'row\', flexWrap: \'wrap\', gap: 6 },
  favChip:          { backgroundColor: Colors.surface, borderRadius: R.full, paddingHorizontal: 10, paddingVertical: 4 },
  favChipText:      { fontSize: 12, color: Colors.text2, fontWeight: \'500\' },
  pantryChip:       { backgroundColor: Colors.bg3, borderWidth: 1, borderColor: Colors.border, borderRadius: R.sm, padding: 10, alignItems: \'center\', marginRight: 8, minWidth: 64, gap: 4 },
  pantryChipName:   { fontSize: 11, color: Colors.text2, fontWeight: \'600\', maxWidth: 60, textAlign: \'center\' },
  generateCta:      { flexDirection: \'row\', alignItems: \'center\', gap: 14, backgroundColor: Colors.purpleDim, borderWidth: 1, borderColor: Colors.purple + \'40\', borderRadius: R.lg, padding: S.base, marginHorizontal: S.base, marginBottom: S.md },
  generateCtaIcon:  { fontSize: 28 },
  generateCtaTitle: { fontSize: 16, color: Colors.text, fontWeight: \'800\', marginBottom: 2 },
  generateCtaSub:   { fontSize: 12, color: Colors.text2 },
  historyRow:       { flexDirection: \'row\', alignItems: \'center\', gap: 12, backgroundColor: Colors.bg3, borderWidth: 1, borderColor: Colors.border, borderRadius: R.md, padding: 12, marginBottom: 8 },
  historyEmoji:     { width: 44, height: 44, backgroundColor: Colors.surface, borderRadius: R.sm, alignItems: \'center\', justifyContent: \'center\' },
  historyName:      { fontSize: 14, color: Colors.text, fontWeight: \'700\', marginBottom: 2 },
  historyMeta:      { fontSize: 12, color: Colors.text2 },
  cookedBadge:      { backgroundColor: Colors.greenDim, borderRadius: R.full, paddingHorizontal: 10, paddingVertical: 4 },
  cookedBadgeText:  { fontSize: 11, color: Colors.green, fontWeight: \'700\' },
  emptyState:       { alignItems: \'center\', paddingTop: 40, paddingHorizontal: 40 },
  emptyTitle:       { fontSize: 26, color: Colors.text, fontWeight: \'800\', marginBottom: 10 },
  emptySub:         { fontSize: 14, color: Colors.text2, textAlign: \'center\', lineHeight: 22, marginBottom: 28 },
  emptyBtn:         { backgroundColor: Colors.accent, borderRadius: R.sm, paddingHorizontal: 28, paddingVertical: 14 },
  emptyBtnText:     { fontSize: 15, color: \'#fff\', fontWeight: \'700\' },
})
''')


# ─────────────────────────────────────────────────────────────
# 7. SCAN SCREEN — fully functional with image picker for web
# ─────────────────────────────────────────────────────────────
w("app/(tabs)/scan.tsx", '''import { useState, useRef } from \'react\'
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, Alert, TextInput, Platform } from \'react-native\'
import * as ImagePicker from \'expo-image-picker\'
import { router } from \'expo-router\'
import { useSafeAreaInsets } from \'react-native-safe-area-context\'
import { Colors, S, R } from \'../../constants/theme\'
import { scanIngredients } from \'../../lib/gemini\'
import { addPantryItems } from \'../../lib/supabase\'
import { useStore } from \'../../store\'
import { ScannedIngredient } from \'../../types\'

const QUICK_ADD = [
  { name: \'Tomatoes\', emoji: \'🍅\', category: \'vegetables\' },
  { name: \'Onions\', emoji: \'🧅\', category: \'vegetables\' },
  { name: \'Dal\', emoji: \'🫘\', category: \'proteins\' },
  { name: \'Rice\', emoji: \'🍚\', category: \'grains\' },
  { name: \'Eggs\', emoji: \'🥚\', category: \'proteins\' },
  { name: \'Garlic\', emoji: \'🧄\', category: \'spices\' },
  { name: \'Milk\', emoji: \'🥛\', category: \'dairy\' },
  { name: \'Butter\', emoji: \'🧈\', category: \'dairy\' },
  { name: \'Spices\', emoji: \'🌶️\', category: \'spices\' },
  { name: \'Spinach\', emoji: \'🥬\', category: \'vegetables\' },
  { name: \'Chilli\', emoji: \'🫑\', category: \'spices\' },
  { name: \'Cheese\', emoji: \'🧀\', category: \'dairy\' },
]

export default function ScanScreen() {
  const insets = useSafeAreaInsets()
  const { user, setScanned, fetchPantry, addPantryItem } = useStore()
  const [mode, setMode] = useState<\'camera\' | \'manual\'>(\'camera\')
  const [scanning, setScanning] = useState(false)
  const [detected, setDetected] = useState<ScannedIngredient[]>([])
  const [saving, setSaving] = useState(false)
  const [manualInput, setManualInput] = useState(\'\')
  const [selected, setSelected] = useState<Set<number>>(new Set())

  async function handleGallery() {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      base64: true, quality: 0.8,
      allowsEditing: true,
    })
    if (!result.canceled && result.assets[0].base64) {
      setScanning(true)
      setDetected([])
      try {
        const results = await scanIngredients(result.assets[0].base64)
        if (results.length === 0) {
          Alert.alert(\'No ingredients found\', \'Try a clearer photo with better lighting.\')
        } else {
          setDetected(results)
          setScanned(results)
          setSelected(new Set(results.map((_, i) => i)))
        }
      } catch (e: any) {
        Alert.alert(\'Scan failed\', e.message || \'Could not process image. Check your Gemini API key.\')
      } finally { setScanning(false) }
    }
  }

  async function handleQuickAdd(item: typeof QUICK_ADD[0]) {
    const ingredient: ScannedIngredient = {
      name: item.name, emoji: item.emoji,
      quantity: \'1\', unit: \'pcs\',
      category: item.category, confidence: 100,
    }
    setDetected(prev => {
      const exists = prev.find(p => p.name === item.name)
      if (exists) return prev
      const updated = [...prev, ingredient]
      setSelected(new Set(updated.map((_, i) => i)))
      return updated
    })
  }

  async function handleAddManual() {
    if (!manualInput.trim()) return
    const parts = manualInput.trim().split(\' \')
    const name = parts.join(\' \')
    const ingredient: ScannedIngredient = {
      name, emoji: \'🥘\', quantity: \'1\', unit: \'pcs\',
      category: \'other\', confidence: 100,
    }
    setDetected(prev => {
      const updated = [...prev, ingredient]
      setSelected(new Set(updated.map((_, i) => i)))
      return updated
    })
    setManualInput(\'\')
  }

  function toggleSelect(i: number) {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(i)) next.delete(i)
      else next.add(i)
      return next
    })
  }

  async function handleAddToPantry() {
    const toAdd = detected.filter((_, i) => selected.has(i))
    if (toAdd.length === 0) { Alert.alert(\'Select items\', \'Tap ingredients to select before adding.\'); return }

    setSaving(true)
    try {
      if (user) {
        await addPantryItems(toAdd, user.id)
        await fetchPantry(user.id)
      } else {
        // offline mode — add to local store
        toAdd.forEach(item => {
          addPantryItem({
            id: Date.now().toString() + Math.random(),
            user_id: \'local\',
            name: item.name, emoji: item.emoji,
            quantity: item.quantity, unit: item.unit,
            category: item.category, confidence: item.confidence,
            added_at: new Date().toISOString(),
          })
        })
      }
      Alert.alert(
        \'✅ Added!\',
        `${toAdd.length} ingredient${toAdd.length > 1 ? \'s\' : \'\'} added to your pantry.`,
        [
          { text: \'Generate Recipes ✨\', onPress: () => router.push(\'/(tabs)/recipes\') },
          { text: \'Keep Adding\', style: \'cancel\', onPress: () => { setDetected([]); setSelected(new Set()) } },
        ]
      )
    } catch (e: any) {
      Alert.alert(\'Error\', e.message || \'Could not save to pantry.\')
    } finally { setSaving(false) }
  }

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>Scan & Detect</Text>
          <Text style={styles.sub}>Add ingredients → get AI recipes</Text>
        </View>
      </View>

      {/* Mode Toggle */}
      <View style={styles.modeToggle}>
        <TouchableOpacity
          style={[styles.modeBtn, mode === \'camera\' && styles.modeBtnActive]}
          onPress={() => setMode(\'camera\')}
        >
          <Text style={[styles.modeBtnText, mode === \'camera\' && styles.modeBtnTextActive]}>📸 Camera Scan</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.modeBtn, mode === \'manual\' && styles.modeBtnActive]}
          onPress={() => setMode(\'manual\')}
        >
          <Text style={[styles.modeBtnText, mode === \'manual\' && styles.modeBtnTextActive]}>✏️ Type Manually</Text>
        </TouchableOpacity>
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: 140 }}>
        {mode === \'camera\' ? (
          <>
            {/* Camera Zone */}
            <View style={styles.cameraZone}>
              <View style={styles.corner} />
              <View style={[styles.corner, { top: 14, right: 14, left: undefined }]} />
              <View style={[styles.corner, { bottom: 14, left: 14, top: undefined }]} />
              <View style={[styles.corner, { bottom: 14, right: 14, top: undefined, left: undefined }]} />

              {scanning ? (
                <View style={styles.scanningState}>
                  <Text style={{ fontSize: 48, marginBottom: 12 }}>🤖</Text>
                  <Text style={styles.scanningText}>Analyzing image...</Text>
                  <Text style={styles.scanningSubtext}>Gemini Vision is detecting ingredients</Text>
                </View>
              ) : detected.length === 0 ? (
                <View style={styles.placeholderState}>
                  <Text style={{ fontSize: 56, marginBottom: 12, opacity: 0.5 }}>📷</Text>
                  <Text style={styles.placeholderTitle}>Point & Detect</Text>
                  <Text style={styles.placeholderSub}>AI identifies ingredients automatically</Text>
                  <TouchableOpacity style={styles.openCameraBtn} onPress={handleGallery}>
                    <Text style={styles.openCameraBtnText}>Open Camera</Text>
                  </TouchableOpacity>
                </View>
              ) : (
                <View style={styles.detectedState}>
                  <Text style={styles.detectedCount}>🎯 {detected.length} ingredients detected</Text>
                  <Text style={styles.detectedHint}>Tap to deselect, then add to pantry</Text>
                </View>
              )}
            </View>

            {/* Camera Controls */}
            {!scanning && (
              <View style={styles.controls}>
                <TouchableOpacity style={styles.galleryBtn} onPress={handleGallery}>
                  <Text style={{ fontSize: 22 }}>🖼️</Text>
                  <Text style={styles.galleryBtnText}>Pick Photo</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.shutterBtn} onPress={handleGallery}>
                  <Text style={{ fontSize: 30 }}>📸</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.galleryBtn} onPress={() => { setDetected([]); setSelected(new Set()) }}>
                  <Text style={{ fontSize: 22 }}>🔄</Text>
                  <Text style={styles.galleryBtnText}>Reset</Text>
                </TouchableOpacity>
              </View>
            )}
          </>
        ) : (
          /* Manual Input Mode */
          <View style={styles.manualZone}>
            <View style={styles.manualInput}>
              <TextInput
                style={styles.textInput}
                placeholder="Type ingredient name..."
                placeholderTextColor={Colors.text3}
                value={manualInput}
                onChangeText={setManualInput}
                onSubmitEditing={handleAddManual}
                returnKeyType="done"
              />
              <TouchableOpacity style={styles.addManualBtn} onPress={handleAddManual}>
                <Text style={{ color: \'#fff\', fontWeight: \'700\' }}>Add</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}

        {/* Quick Add Grid */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>⚡ Quick Add</Text>
          <View style={styles.quickGrid}>
            {QUICK_ADD.map((item, i) => {
              const alreadyAdded = detected.some(d => d.name === item.name)
              return (
                <TouchableOpacity
                  key={i}
                  style={[styles.quickItem, alreadyAdded && styles.quickItemAdded]}
                  onPress={() => handleQuickAdd(item)}
                  activeOpacity={0.7}
                >
                  <Text style={{ fontSize: 24 }}>{item.emoji}</Text>
                  <Text style={[styles.quickItemName, alreadyAdded && { color: Colors.green }]}>{item.name}</Text>
                  {alreadyAdded && <View style={styles.addedDot} />}
                </TouchableOpacity>
              )
            })}
          </View>
        </View>

        {/* Detected Results */}
        {detected.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionLabel}>🤖 Detected — tap to toggle selection</Text>
            <View style={styles.detectedGrid}>
              {detected.map((item, i) => (
                <TouchableOpacity
                  key={i}
                  style={[styles.detectedItem, !selected.has(i) && styles.detectedItemUnselected]}
                  onPress={() => toggleSelect(i)}
                  activeOpacity={0.8}
                >
                  <View style={styles.detectedItemTop}>
                    <Text style={{ fontSize: 22 }}>{item.emoji}</Text>
                    {selected.has(i) && <View style={styles.selectedCheck}><Text style={{ fontSize: 10, color: \'#fff\' }}>✓</Text></View>}
                  </View>
                  <Text style={styles.detectedItemName} numberOfLines={1}>{item.name}</Text>
                  <Text style={styles.detectedItemQty}>{item.quantity} {item.unit}</Text>
                  <Text style={[styles.confBadge, { color: item.confidence > 80 ? Colors.green : Colors.yellow }]}>{item.confidence}%</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        )}
      </ScrollView>

      {/* Sticky Add Button */}
      {detected.length > 0 && (
        <View style={[styles.stickyBar, { paddingBottom: insets.bottom + 8 }]}>
          <TouchableOpacity
            style={[styles.addBtn, saving && { opacity: 0.6 }]}
            onPress={handleAddToPantry}
            disabled={saving}
            activeOpacity={0.88}
          >
            <Text style={styles.addBtnText}>
              {saving ? \'Saving...\' : `Add ${selected.size} to Pantry → Find Recipes ✨`}
            </Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  )
}

const CORNER_SIZE = 22
const CORNER_W = 3
const styles = StyleSheet.create({
  root:                 { flex: 1, backgroundColor: Colors.bg },
  header:               { paddingHorizontal: S.base, paddingTop: S.sm, paddingBottom: 4 },
  title:                { fontSize: 24, color: Colors.text, fontWeight: \'800\' },
  sub:                  { fontSize: 13, color: Colors.text2 },
  modeToggle:           { flexDirection: \'row\', marginHorizontal: S.base, marginBottom: S.md, backgroundColor: Colors.surface, borderRadius: R.md, padding: 4 },
  modeBtn:              { flex: 1, paddingVertical: 10, alignItems: \'center\', borderRadius: R.sm },
  modeBtnActive:        { backgroundColor: Colors.accent },
  modeBtnText:          { fontSize: 13, color: Colors.text2, fontWeight: \'600\' },
  modeBtnTextActive:    { color: \'#fff\', fontWeight: \'800\' },
  cameraZone:           { marginHorizontal: S.base, height: 260, backgroundColor: Colors.bg3, borderRadius: R.lg, borderWidth: 1, borderColor: Colors.border, marginBottom: S.sm, position: \'relative\', alignItems: \'center\', justifyContent: \'center\' },
  corner:               { position: \'absolute\', top: 14, left: 14, width: CORNER_SIZE, height: CORNER_SIZE, borderTopWidth: CORNER_W, borderLeftWidth: CORNER_W, borderColor: Colors.accent, borderRadius: 3 },
  scanningState:        { alignItems: \'center\' },
  scanningText:         { fontSize: 16, color: Colors.accent, fontWeight: \'700\', marginBottom: 6 },
  scanningSubtext:      { fontSize: 12, color: Colors.text2 },
  placeholderState:     { alignItems: \'center\' },
  placeholderTitle:     { fontSize: 18, color: Colors.text, fontWeight: \'700\', marginBottom: 6 },
  placeholderSub:       { fontSize: 13, color: Colors.text2, marginBottom: 20 },
  openCameraBtn:        { backgroundColor: Colors.accent, borderRadius: R.full, paddingHorizontal: 28, paddingVertical: 12 },
  openCameraBtnText:    { color: \'#fff\', fontWeight: \'800\', fontSize: 15 },
  detectedState:        { alignItems: \'center\' },
  detectedCount:        { fontSize: 18, color: Colors.green, fontWeight: \'800\', marginBottom: 6 },
  detectedHint:         { fontSize: 12, color: Colors.text2 },
  controls:             { flexDirection: \'row\', alignItems: \'center\', justifyContent: \'center\', gap: 32, paddingVertical: 12, marginBottom: S.sm },
  galleryBtn:           { alignItems: \'center\', gap: 4 },
  galleryBtnText:       { fontSize: 11, color: Colors.text2, fontWeight: \'600\' },
  shutterBtn:           { width: 72, height: 72, borderRadius: 36, backgroundColor: Colors.accent, alignItems: \'center\', justifyContent: \'center\', shadowColor: Colors.accent, shadowOffset: { width: 0, height: 0 }, shadowOpacity: 0.5, shadowRadius: 16, elevation: 10 },
  manualZone:           { marginHorizontal: S.base, marginBottom: S.md },
  manualInput:          { flexDirection: \'row\', gap: 10, backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border, borderRadius: R.sm, padding: 4 },
  textInput:            { flex: 1, paddingHorizontal: 12, paddingVertical: 10, color: Colors.text, fontSize: 15 },
  addManualBtn:         { backgroundColor: Colors.accent, borderRadius: R.xs, paddingHorizontal: 16, paddingVertical: 10 },
  section:              { paddingHorizontal: S.base, marginBottom: S.lg },
  sectionLabel:         { fontSize: 11, fontWeight: \'700\', color: Colors.text3, textTransform: \'uppercase\', letterSpacing: 0.8, marginBottom: 10 },
  quickGrid:            { flexDirection: \'row\', flexWrap: \'wrap\', gap: 8 },
  quickItem:            { backgroundColor: Colors.bg3, borderWidth: 1, borderColor: Colors.border, borderRadius: R.sm, padding: 10, alignItems: \'center\', width: \'22%\', position: \'relative\' },
  quickItemAdded:       { borderColor: Colors.green, backgroundColor: Colors.greenDim },
  quickItemName:        { fontSize: 10, color: Colors.text2, marginTop: 4, textAlign: \'center\' },
  addedDot:             { position: \'absolute\', top: 6, right: 6, width: 8, height: 8, borderRadius: 4, backgroundColor: Colors.green },
  detectedGrid:         { flexDirection: \'row\', flexWrap: \'wrap\', gap: 8 },
  detectedItem:         { width: \'22%\', backgroundColor: Colors.surface, borderWidth: 1.5, borderColor: Colors.green, borderRadius: R.sm, padding: 10, alignItems: \'center\', position: \'relative\' },
  detectedItemUnselected:{ borderColor: Colors.border, opacity: 0.5 },
  detectedItemTop:      { position: \'relative\', marginBottom: 4 },
  selectedCheck:        { position: \'absolute\', top: -4, right: -10, width: 16, height: 16, backgroundColor: Colors.green, borderRadius: 8, alignItems: \'center\', justifyContent: \'center\' },
  detectedItemName:     { fontSize: 11, color: Colors.text, fontWeight: \'700\', textAlign: \'center\' },
  detectedItemQty:      { fontSize: 10, color: Colors.text2 },
  confBadge:            { fontSize: 10, fontWeight: \'700\', marginTop: 2 },
  stickyBar:            { position: \'absolute\', bottom: 62, left: 0, right: 0, paddingHorizontal: S.base, paddingTop: 10, backgroundColor: Colors.bg + \'F0\' },
  addBtn:               { backgroundColor: Colors.accent, borderRadius: R.sm, paddingVertical: 16, alignItems: \'center\' },
  addBtnText:           { fontSize: 15, color: \'#fff\', fontWeight: \'800\' },
})
''')


# ─────────────────────────────────────────────────────────────
# 8. RECIPES SCREEN — real AI generation + substitution
# ─────────────────────────────────────────────────────────────
w("app/(tabs)/recipes.tsx", '''import { useState } from \'react\'
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, Alert, TextInput } from \'react-native\'
import { router } from \'expo-router\'
import { useSafeAreaInsets } from \'react-native-safe-area-context\'
import { Colors, S, R } from \'../../constants/theme\'
import { generateRecipes, getSubstitute } from \'../../lib/gemini\'
import { useStore } from \'../../store\'
import { Recipe } from \'../../types\'

const FILTERS = [\'All\', \'🇮🇳 Indian\', \'🍜 Asian\', \'🍝 Continental\', \'⚡ Quick\', \'🥗 Veg\', \'🥩 Non-Veg\']

export default function RecipesScreen() {
  const insets = useSafeAreaInsets()
  const { pantry, recipes, setRecipes, setActiveRecipe, user, tasteProfile, loading, setLoading, setCookStep } = useStore()
  const [activeFilter, setActiveFilter] = useState(\'All\')
  const [search, setSearch] = useState(\'\')
  const [genError, setGenError] = useState<string | null>(null)
  const [subLoading, setSubLoading] = useState<string | null>(null)
  const [subResults, setSubResults] = useState<Record<string, { substitute: string; ratio: string; note: string }>>({})

  async function handleGenerate() {
    if (pantry.length === 0) {
      Alert.alert(\'Empty Pantry\', \'Scan or add ingredients first! Go to the Scan tab.\',
        [{ text: \'Go Scan 📸\', onPress: () => router.push(\'/(tabs)/scan\') }, { text: \'Cancel\' }])
      return
    }
    setLoading(true)
    setGenError(null)
    try {
      const result = await generateRecipes(
        pantry,
        {
          cuisines: user?.cuisine_preference ?? [\'all\'],
          dietary: user?.dietary_preference ?? \'all\',
          spice: user?.spice_level ?? \'Medium\',
          servings: 2,
        },
        tasteProfile.totalCooked > 0 ? tasteProfile : null
      )
      setRecipes(result)
    } catch (e: any) {
      const msg = e.message || \'Could not generate recipes.\'
      setGenError(msg)
      Alert.alert(\'Generation Failed\', msg)
    } finally { setLoading(false) }
  }

  async function handleSubstitute(missing: string, recipeName: string) {
    const key = `${recipeName}-${missing}`
    setSubLoading(key)
    try {
      const result = await getSubstitute(missing, recipeName, pantry.map(p => p.name))
      setSubResults(prev => ({ ...prev, [key]: result }))
    } catch { }
    finally { setSubLoading(null) }
  }

  function openRecipe(recipe: Recipe) {
    setActiveRecipe(recipe)
    setCookStep(0)
    router.push(`/cook/${recipe.id}`)
  }

  const filteredRecipes = recipes.filter(r => {
    if (search && !r.name.toLowerCase().includes(search.toLowerCase())) return false
    if (activeFilter === \'All\') return true
    if (activeFilter.includes(\'Indian\')) return r.cuisine.toLowerCase().includes(\'indian\')
    if (activeFilter.includes(\'Asian\')) return [\'asian\', \'chinese\', \'thai\', \'japanese\', \'korean\'].some(c => r.cuisine.toLowerCase().includes(c))
    if (activeFilter.includes(\'Quick\')) return r.time_minutes <= 20
    if (activeFilter.includes(\'Veg\') && !activeFilter.includes(\'Non\')) return r.dietary.toLowerCase().includes(\'veg\')
    if (activeFilter.includes(\'Non-Veg\')) return !r.dietary.toLowerCase().includes(\'veg\')
    return true
  })

  const diffColor = (d: string) => d === \'Easy\' ? Colors.green : d === \'Medium\' ? Colors.yellow : Colors.red

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>AI Recipes</Text>
        <TouchableOpacity style={styles.genBtn} onPress={handleGenerate} disabled={loading}>
          <Text style={styles.genBtnText}>{loading ? \'Cooking...\' : \'✨ Generate\'}</Text>
        </TouchableOpacity>
      </View>

      {/* Search */}
      <View style={styles.searchBar}>
        <Text style={{ fontSize: 16, color: Colors.text3 }}>🔍</Text>
        <TextInput
          style={styles.searchInput}
          placeholder="Search recipes..."
          placeholderTextColor={Colors.text3}
          value={search}
          onChangeText={setSearch}
        />
        {search.length > 0 && (
          <TouchableOpacity onPress={() => setSearch(\'\')}><Text style={{ color: Colors.text3 }}>✕</Text></TouchableOpacity>
        )}
      </View>

      {/* Filters */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.filtersRow} contentContainerStyle={{ paddingHorizontal: S.base, gap: 8 }}>
        {FILTERS.map(f => (
          <TouchableOpacity key={f} style={[styles.filter, activeFilter === f && styles.filterActive]} onPress={() => setActiveFilter(f)}>
            <Text style={[styles.filterText, activeFilter === f && styles.filterTextActive]}>{f}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ padding: S.base, paddingBottom: 100 }}>

        {/* AI Generation Banner */}
        {recipes.length > 0 && (
          <View style={styles.banner}>
            <Text style={{ fontSize: 24 }}>✨</Text>
            <View style={{ flex: 1 }}>
              <Text style={styles.bannerCount}>{recipes.length} personalised recipes</Text>
              <Text style={styles.bannerSub}>
                {tasteProfile.totalCooked > 0 ? `Tailored to your taste profile (${tasteProfile.totalCooked} dishes cooked)` : `Generated from your ${pantry.length} pantry items`}
              </Text>
            </View>
          </View>
        )}

        {/* Empty State */}
        {recipes.length === 0 && !loading && (
          <View style={styles.empty}>
            <Text style={{ fontSize: 72, marginBottom: 16 }}>🤖</Text>
            <Text style={styles.emptyTitle}>No recipes yet</Text>
            <Text style={styles.emptySub}>
              {pantry.length === 0
                ? \'Add ingredients to your pantry first, then generate personalised AI recipes\'
                : `You have ${pantry.length} ingredients ready. Tap Generate to create recipes!`}
            </Text>
            {genError && <View style={styles.errorBox}><Text style={styles.errorText}>⚠️ {genError}</Text></View>}
            {pantry.length === 0 ? (
              <TouchableOpacity style={styles.emptyBtn} onPress={() => router.push(\'/(tabs)/scan\')}>
                <Text style={styles.emptyBtnText}>📸 Scan Ingredients</Text>
              </TouchableOpacity>
            ) : (
              <TouchableOpacity style={styles.emptyBtn} onPress={handleGenerate} disabled={loading}>
                <Text style={styles.emptyBtnText}>✨ Generate Recipes ({pantry.length} ingredients)</Text>
              </TouchableOpacity>
            )}
          </View>
        )}

        {/* Loading State */}
        {loading && (
          <View style={styles.loadingWrap}>
            <Text style={{ fontSize: 48, marginBottom: 16 }}>🤖</Text>
            <Text style={styles.loadingText}>Generating personalised recipes...</Text>
            <Text style={styles.loadingSub}>Analysing {pantry.length} ingredients</Text>
            {tasteProfile.totalCooked > 0 && (
              <Text style={styles.loadingProfile}>Using your taste profile ({tasteProfile.totalCooked} dishes cooked)</Text>
            )}
          </View>
        )}

        {/* Recipe Cards */}
        {filteredRecipes.map((recipe, i) => {
          const allIngredientNames = pantry.map(p => p.name)
          return (
            <View key={recipe.id} style={styles.card}>
              {/* Card Header */}
              <TouchableOpacity style={styles.cardTop} onPress={() => openRecipe(recipe)} activeOpacity={0.85}>
                <View style={styles.cardEmoji}>
                  <Text style={{ fontSize: 36 }}>{recipe.emoji}</Text>
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.cardName}>{recipe.name}</Text>
                  <Text style={styles.cardCuisine}>{recipe.cuisine} · {recipe.dietary}</Text>
                  <View style={styles.matchBarWrap}>
                    <View style={[styles.matchFill, { width: `${recipe.match_score}%` }]} />
                  </View>
                  <Text style={styles.matchLabel}>{recipe.match_score}% match</Text>
                </View>
              </TouchableOpacity>

              {/* Description */}
              <Text style={styles.cardDesc}>{recipe.description}</Text>

              {/* Badges */}
              <View style={styles.badges}>
                <View style={[styles.badge, { backgroundColor: recipe.match_score >= 90 ? Colors.greenDim : Colors.yellowDim }]}>
                  <Text style={[styles.badgeText, { color: recipe.match_score >= 90 ? Colors.green : Colors.yellow }]}>
                    {recipe.missing_ingredients.length === 0 ? \'✓ All ingredients\' : `Missing ${recipe.missing_ingredients.length}`}
                  </Text>
                </View>
                <View style={styles.badge}><Text style={styles.badgeText}>⏱ {recipe.time_minutes}m</Text></View>
                <View style={styles.badge}><Text style={[styles.badgeText, { color: diffColor(recipe.difficulty) }]}>{recipe.difficulty}</Text></View>
                <View style={styles.badge}><Text style={styles.badgeText}>{recipe.nutrition.calories} kcal</Text></View>
              </View>

              {/* Missing ingredients with substitution */}
              {recipe.missing_ingredients.length > 0 && (
                <View style={styles.missingBox}>
                  <Text style={styles.missingTitle}>Missing ingredients:</Text>
                  {recipe.missing_ingredients.map((m, j) => {
                    const key = `${recipe.name}-${m}`
                    const sub = subResults[key]
                    return (
                      <View key={j}>
                        <View style={styles.missingRow}>
                          <Text style={styles.missingItem}>• {m}</Text>
                          <TouchableOpacity
                            style={styles.subBtn}
                            onPress={() => handleSubstitute(m, recipe.name)}
                            disabled={subLoading === key}
                          >
                            <Text style={styles.subBtnText}>{subLoading === key ? \'...\'  : \'Find sub\'}</Text>
                          </TouchableOpacity>
                        </View>
                        {sub && (
                          <View style={styles.subResult}>
                            <Text style={styles.subResultText}>
                              💡 Use <Text style={{ color: Colors.green, fontWeight: \'700\' }}>{sub.substitute}</Text> ({sub.ratio}) — {sub.note}
                            </Text>
                          </View>
                        )}
                      </View>
                    )
                  })}
                </View>
              )}

              {/* Nutrition Row */}
              <View style={styles.nutritionRow}>
                {[
                  { val: recipe.nutrition.calories, label: \'Cal\', color: Colors.accent },
                  { val: `${recipe.nutrition.protein_g}g`, label: \'Protein\', color: Colors.green },
                  { val: `${recipe.nutrition.carbs_g}g`, label: \'Carbs\', color: Colors.yellow },
                  { val: `${recipe.nutrition.fat_g}g`, label: \'Fat\', color: Colors.purple },
                ].map((n, j) => (
                  <View key={j} style={styles.nutritionItem}>
                    <Text style={[styles.nutritionVal, { color: n.color }]}>{n.val}</Text>
                    <Text style={styles.nutritionLabel}>{n.label}</Text>
                  </View>
                ))}
              </View>

              {/* Cook Button */}
              <TouchableOpacity style={styles.cookBtn} onPress={() => openRecipe(recipe)} activeOpacity={0.88}>
                <Text style={styles.cookBtnText}>🍳 Start Cooking — {recipe.steps.length} steps</Text>
              </TouchableOpacity>
            </View>
          )
        })}
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  root:           { flex: 1, backgroundColor: Colors.bg },
  header:         { flexDirection: \'row\', justifyContent: \'space-between\', alignItems: \'center\', paddingHorizontal: S.base, paddingVertical: 12 },
  title:          { fontSize: 28, color: Colors.text, fontWeight: \'800\' },
  genBtn:         { backgroundColor: Colors.purple, borderRadius: R.full, paddingHorizontal: 18, paddingVertical: 10 },
  genBtnText:     { color: \'#fff\', fontWeight: \'800\', fontSize: 14 },
  searchBar:      { flexDirection: \'row\', alignItems: \'center\', gap: 10, backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border, borderRadius: R.sm, marginHorizontal: S.base, marginBottom: 10, paddingHorizontal: 14, paddingVertical: 10 },
  searchInput:    { flex: 1, color: Colors.text, fontSize: 14 },
  filtersRow:     { marginBottom: 10, maxHeight: 44 },
  filter:         { paddingHorizontal: 14, paddingVertical: 8, borderRadius: R.full, backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border },
  filterActive:   { backgroundColor: Colors.accentGlow, borderColor: Colors.accent + \'60\' },
  filterText:     { fontSize: 13, color: Colors.text2, fontWeight: \'600\' },
  filterTextActive:{ color: Colors.accent, fontWeight: \'800\' },
  banner:         { flexDirection: \'row\', alignItems: \'center\', gap: 12, backgroundColor: Colors.greenDim, borderWidth: 1, borderColor: Colors.green + \'30\', borderRadius: R.lg, padding: S.base, marginBottom: 14 },
  bannerCount:    { fontSize: 18, color: Colors.green, fontWeight: \'800\' },
  bannerSub:      { fontSize: 12, color: Colors.text2 },
  empty:          { alignItems: \'center\', paddingTop: 60, paddingHorizontal: 32 },
  emptyTitle:     { fontSize: 24, color: Colors.text, fontWeight: \'800\', marginBottom: 10 },
  emptySub:       { fontSize: 14, color: Colors.text2, textAlign: \'center\', lineHeight: 22, marginBottom: 24 },
  errorBox:       { backgroundColor: Colors.redDim, borderRadius: R.sm, padding: 12, marginBottom: 20, width: \'100%\' },
  errorText:      { color: Colors.red, fontSize: 13, lineHeight: 18 },
  emptyBtn:       { backgroundColor: Colors.accent, borderRadius: R.sm, paddingHorizontal: 24, paddingVertical: 14, width: \'100%\', alignItems: \'center\' },
  emptyBtnText:   { color: \'#fff\', fontWeight: \'800\', fontSize: 15 },
  loadingWrap:    { alignItems: \'center\', paddingTop: 60 },
  loadingText:    { fontSize: 18, color: Colors.text, fontWeight: \'700\', marginBottom: 8, textAlign: \'center\' },
  loadingSub:     { fontSize: 14, color: Colors.text2, marginBottom: 6 },
  loadingProfile: { fontSize: 13, color: Colors.purple, fontStyle: \'italic\' },
  card:           { backgroundColor: Colors.bg3, borderWidth: 1, borderColor: Colors.border, borderRadius: R.lg, padding: S.base, marginBottom: 14 },
  cardTop:        { flexDirection: \'row\', gap: 12, marginBottom: 10 },
  cardEmoji:      { width: 64, height: 64, backgroundColor: Colors.surface, borderRadius: R.sm, alignItems: \'center\', justifyContent: \'center\' },
  cardName:       { fontSize: 17, color: Colors.text, fontWeight: \'800\', marginBottom: 3 },
  cardCuisine:    { fontSize: 12, color: Colors.text2, marginBottom: 8 },
  matchBarWrap:   { height: 4, backgroundColor: Colors.surface2, borderRadius: 2, overflow: \'hidden\', marginBottom: 4 },
  matchFill:      { height: \'100%\', backgroundColor: Colors.green, borderRadius: 2 },
  matchLabel:     { fontSize: 11, color: Colors.green, fontWeight: \'700\' },
  cardDesc:       { fontSize: 13, color: Colors.text2, lineHeight: 20, marginBottom: 10 },
  badges:         { flexDirection: \'row\', flexWrap: \'wrap\', gap: 6, marginBottom: 10 },
  badge:          { backgroundColor: Colors.surface, borderRadius: R.full, paddingHorizontal: 10, paddingVertical: 4 },
  badgeText:      { fontSize: 11, color: Colors.text2, fontWeight: \'600\' },
  missingBox:     { backgroundColor: Colors.redDim, borderRadius: R.sm, padding: 12, marginBottom: 10 },
  missingTitle:   { fontSize: 12, color: Colors.red, fontWeight: \'700\', marginBottom: 8, textTransform: \'uppercase\', letterSpacing: 0.5 },
  missingRow:     { flexDirection: \'row\', justifyContent: \'space-between\', alignItems: \'center\', marginBottom: 4 },
  missingItem:    { fontSize: 13, color: Colors.text2 },
  subBtn:         { backgroundColor: Colors.surface, borderRadius: R.full, paddingHorizontal: 10, paddingVertical: 4 },
  subBtnText:     { fontSize: 11, color: Colors.accent, fontWeight: \'700\' },
  subResult:      { backgroundColor: Colors.greenDim, borderRadius: R.xs, padding: 8, marginBottom: 6 },
  subResultText:  { fontSize: 12, color: Colors.text2, lineHeight: 18 },
  nutritionRow:   { flexDirection: \'row\', borderTopWidth: 1, borderTopColor: Colors.border, paddingTop: 10, marginBottom: 12 },
  nutritionItem:  { flex: 1, alignItems: \'center\' },
  nutritionVal:   { fontSize: 16, fontWeight: \'800\', marginBottom: 2 },
  nutritionLabel: { fontSize: 10, color: Colors.text3, textTransform: \'uppercase\' },
  cookBtn:        { backgroundColor: Colors.accent, borderRadius: R.sm, paddingVertical: 14, alignItems: \'center\' },
  cookBtnText:    { fontSize: 15, color: \'#fff\', fontWeight: \'800\' },
})
''')


# ─────────────────────────────────────────────────────────────
# 9. COOK MODE — full step-by-step, timer, AI Q&A, taste profile update
# ─────────────────────────────────────────────────────────────
w("app/cook/[id].tsx", '''import { useState, useEffect, useRef } from \'react\'
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, Alert, TextInput, Platform } from \'react-native\'
import { router } from \'expo-router\'
import { useSafeAreaInsets } from \'react-native-safe-area-context\'
import { Colors, S, R } from \'../../constants/theme\'
import { askCookingQuestion } from \'../../lib/gemini\'
import { saveCookHistory } from \'../../lib/supabase\'
import { useStore } from \'../../store\'

export default function CookScreen() {
  const insets = useSafeAreaInsets()
  const { activeRecipe, cookStep, setCookStep, user, addCookHistory, updateTasteProfile } = useStore()
  const [timerVal, setTimerVal] = useState(0)
  const [timerRunning, setTimerRunning] = useState(false)
  const [timerMax, setTimerMax] = useState(0)
  const [question, setQuestion] = useState(\'\')
  const [aiAnswer, setAiAnswer] = useState(\'\')
  const [aiLoading, setAiLoading] = useState(false)
  const [showQA, setShowQA] = useState(false)
  const intervalRef = useRef<any>(null)

  const recipe = activeRecipe
  if (!recipe) return (
    <View style={[styles.root, { alignItems: \'center\', justifyContent: \'center\' }]}>
      <Text style={{ color: Colors.text2, fontSize: 16 }}>No recipe selected</Text>
      <TouchableOpacity style={styles.backBtn2} onPress={() => router.back()}>
        <Text style={{ color: Colors.accent, fontWeight: \'700\', marginTop: 16 }}>← Go back</Text>
      </TouchableOpacity>
    </View>
  )

  const step = recipe.steps[cookStep]
  const progress = ((cookStep + 1) / recipe.steps.length) * 100
  const allIngredients = recipe.ingredients.map(i => i.name)

  useEffect(() => {
    if (step?.timer_seconds) {
      setTimerVal(step.timer_seconds)
      setTimerMax(step.timer_seconds)
      setTimerRunning(false)
      clearInterval(intervalRef.current)
    }
    setAiAnswer(\'\')
    setQuestion(\'\')
  }, [cookStep])

  useEffect(() => {
    if (timerRunning && timerVal > 0) {
      intervalRef.current = setInterval(() => {
        setTimerVal(v => {
          if (v <= 1) {
            clearInterval(intervalRef.current)
            setTimerRunning(false)
            Alert.alert(\'⏰ Timer Done!\', \'Ready for the next step!\')
            return 0
          }
          return v - 1
        })
      }, 1000)
    }
    return () => clearInterval(intervalRef.current)
  }, [timerRunning])

  async function handleAskAI() {
    if (!question.trim()) return
    setAiLoading(true)
    try {
      const answer = await askCookingQuestion(question, {
        recipeName: recipe.name,
        step: cookStep + 1,
        totalSteps: recipe.steps.length,
        instruction: step.instruction,
        allIngredients,
      })
      setAiAnswer(answer)
    } catch (e: any) {
      setAiAnswer(\'Could not get an answer. Check your API key.\')
    } finally { setAiLoading(false) }
  }

  function nextStep() {
    if (cookStep < recipe.steps.length - 1) {
      setCookStep(cookStep + 1)
    } else {
      handleComplete()
    }
  }

  async function handleComplete() {
    const historyItem = {
      id: Date.now().toString(),
      recipeName: recipe.name,
      recipeEmoji: recipe.emoji,
      cuisine: recipe.cuisine,
      cookedAt: new Date().toISOString(),
    }
    addCookHistory(historyItem)
    updateTasteProfile(recipe)
    if (user) {
      try { await saveCookHistory(user.id, recipe.name, recipe.emoji, recipe.cuisine) } catch {}
    }
    Alert.alert(
      `🎉 ${recipe.name} is ready!`,
      \'Great job! This has been saved to your cook history and your taste profile has been updated.\',
      [{ text: \'Back to Recipes\', onPress: () => { router.push(\'/(tabs)/recipes\') } }]
    )
  }

  const timerFmt = () => {
    const m = Math.floor(timerVal / 60)
    const s = timerVal % 60
    return `${m}:${s < 10 ? \'0\' : \'\'}${s}`
  }

  const timerPct = timerMax > 0 ? timerVal / timerMax : 0

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backBtn} onPress={() => { clearInterval(intervalRef.current); router.back() }}>
          <Text style={{ fontSize: 20, color: Colors.text }}>←</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle} numberOfLines={1}>{recipe.name}</Text>
        <TouchableOpacity style={styles.qaToggle} onPress={() => setShowQA(!showQA)}>
          <Text style={{ fontSize: 18 }}>🤖</Text>
        </TouchableOpacity>
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: 40 }}>

        {/* Recipe Hero */}
        <View style={styles.hero}>
          <Text style={{ fontSize: 56, marginBottom: 8 }}>{recipe.emoji}</Text>
          <Text style={styles.heroName}>{recipe.name}</Text>
          <View style={styles.heroMeta}>
            <Text style={styles.heroMetaItem}>⏱ {recipe.time_minutes} min</Text>
            <Text style={styles.heroMetaItem}>🍽️ {recipe.servings} servings</Text>
            <Text style={styles.heroMetaItem}>📊 {recipe.difficulty}</Text>
          </View>
        </View>

        {/* Progress */}
        <View style={styles.progressCard}>
          <View style={styles.dots}>
            {recipe.steps.map((_, i) => (
              <TouchableOpacity
                key={i}
                onPress={() => setCookStep(i)}
                style={[
                  styles.dot,
                  i < cookStep && styles.dotDone,
                  i === cookStep && styles.dotActive,
                ]}
              />
            ))}
          </View>
          <View style={styles.progressBar}>
            <View style={[styles.progressFill, { width: `${progress}%` }]} />
          </View>
          <View style={styles.progressLabels}>
            <Text style={styles.progressText}>Step {cookStep + 1} of {recipe.steps.length}</Text>
            <Text style={styles.progressText}>{Math.round(progress)}% done</Text>
          </View>
        </View>

        {/* Current Step */}
        <View style={styles.stepCard}>
          <View style={styles.stepNumRow}>
            <Text style={styles.stepNum}>STEP {String(step.number).padStart(2, \'0\')}</Text>
            {step.ingredients_used.length > 0 && (
              <View style={styles.stepIngBadge}>
                <Text style={styles.stepIngText}>{step.ingredients_used.slice(0, 2).join(\', \')}{step.ingredients_used.length > 2 ? \'...\' : \'\'}</Text>
              </View>
            )}
          </View>
          <Text style={styles.stepTitle}>{step.title}</Text>
          <Text style={styles.stepInstruction}>{step.instruction}</Text>
          {step.tip && (
            <View style={styles.tipBox}>
              <Text style={styles.tipText}>💡 Chef\'s tip: {step.tip}</Text>
            </View>
          )}
        </View>

        {/* Timer */}
        {step.timer_seconds != null && step.timer_seconds > 0 && (
          <View style={styles.timerCard}>
            <View style={styles.timerRingWrap}>
              <View style={styles.timerRing}>
                <View style={[styles.timerArc, { opacity: timerPct }]} />
              </View>
              <Text style={styles.timerDisplay}>{timerFmt()}</Text>
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.timerLabel}>Timer</Text>
              <Text style={styles.timerSub}>
                {(step.timer_seconds ?? 0) >= 60 ? `${Math.floor((step.timer_seconds ?? 0) / 60)} min` : `${step.timer_seconds} sec`}
              </Text>
              <TouchableOpacity
                style={styles.timerBtn}
                onPress={() => {
                  if (timerVal === 0) setTimerVal(step.timer_seconds!)
                  setTimerRunning(r => !r)
                }}
              >
                <Text style={styles.timerBtnText}>
                  {timerRunning ? \'⏸ Pause\' : timerVal === 0 ? \'↺ Restart\' : \'▶ Start\'}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        )}

        {/* Navigation */}
        <View style={styles.navRow}>
          {cookStep > 0 && (
            <TouchableOpacity style={styles.prevBtn} onPress={() => setCookStep(cookStep - 1)}>
              <Text style={styles.prevBtnText}>← Prev</Text>
            </TouchableOpacity>
          )}
          <TouchableOpacity
            style={[styles.nextBtn, cookStep === 0 && { flex: 1 }]}
            onPress={nextStep}
            activeOpacity={0.88}
          >
            <Text style={styles.nextBtnText}>
              {cookStep === recipe.steps.length - 1 ? \'🎉 Complete!\' : \'Next Step →\'}
            </Text>
          </TouchableOpacity>
        </View>

        {/* AI Q&A Panel */}
        {showQA && (
          <View style={styles.qaPanel}>
            <Text style={styles.qaTitle}>🤖 Ask AI Chef</Text>
            <Text style={styles.qaSub}>Ask anything about this step or the dish</Text>
            <View style={styles.qaInputRow}>
              <TextInput
                style={styles.qaInput}
                placeholder="e.g. How long should I fry the onions?"
                placeholderTextColor={Colors.text3}
                value={question}
                onChangeText={setQuestion}
                multiline
              />
            </View>
            <TouchableOpacity
              style={[styles.qaBtn, aiLoading && { opacity: 0.6 }]}
              onPress={handleAskAI}
              disabled={aiLoading}
            >
              <Text style={styles.qaBtnText}>{aiLoading ? \'Thinking...\' : \'Ask Chef AI 🤖\'}</Text>
            </TouchableOpacity>
            {aiAnswer.length > 0 && (
              <View style={styles.qaAnswer}>
                <Text style={styles.qaAnswerLabel}>Chef AI says:</Text>
                <Text style={styles.qaAnswerText}>{aiAnswer}</Text>
              </View>
            )}
          </View>
        )}

        {/* Ingredients checklist */}
        <View style={styles.ingredientsCard}>
          <Text style={styles.ingredientsTitle}>📋 Ingredients</Text>
          {recipe.ingredients.map((ing, i) => (
            <View key={i} style={styles.ingRow}>
              <Text style={{ fontSize: 18 }}>{ing.emoji}</Text>
              <Text style={styles.ingName}>{ing.name}</Text>
              <Text style={styles.ingQty}>{ing.quantity} {ing.unit}</Text>
              <View style={[styles.haveTag, { backgroundColor: ing.have ? Colors.greenDim : Colors.redDim }]}>
                <Text style={{ fontSize: 10, color: ing.have ? Colors.green : Colors.red, fontWeight: \'700\' }}>
                  {ing.have ? \'✓ Have\' : \'✗ Missing\'}
                </Text>
              </View>
            </View>
          ))}
        </View>

        {/* Tips */}
        {recipe.tips.length > 0 && (
          <View style={styles.tipsCard}>
            <Text style={styles.tipsTitle}>💡 Pro Tips</Text>
            {recipe.tips.map((tip, i) => (
              <Text key={i} style={styles.tipItem}>• {tip}</Text>
            ))}
          </View>
        )}

      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  root:             { flex: 1, backgroundColor: Colors.bg },
  header:           { flexDirection: \'row\', alignItems: \'center\', paddingHorizontal: S.base, paddingVertical: 12 },
  backBtn:          { width: 40, height: 40, borderRadius: 20, backgroundColor: Colors.surface, alignItems: \'center\', justifyContent: \'center\' },
  backBtn2:         { alignSelf: \'center\' },
  headerTitle:      { flex: 1, fontSize: 18, color: Colors.text, fontWeight: \'700\', textAlign: \'center\', marginHorizontal: 12 },
  qaToggle:         { width: 40, height: 40, borderRadius: 20, backgroundColor: Colors.purpleDim, borderWidth: 1, borderColor: Colors.purple + \'40\', alignItems: \'center\', justifyContent: \'center\' },
  hero:             { alignItems: \'center\', paddingVertical: S.lg },
  heroName:         { fontSize: 22, color: Colors.text, fontWeight: \'800\', marginBottom: 10 },
  heroMeta:         { flexDirection: \'row\', gap: 16 },
  heroMetaItem:     { fontSize: 13, color: Colors.text2 },
  progressCard:     { marginHorizontal: S.base, backgroundColor: Colors.bg3, borderWidth: 1, borderColor: Colors.border, borderRadius: R.md, padding: S.base, marginBottom: S.base },
  dots:             { flexDirection: \'row\', justifyContent: \'center\', gap: 6, marginBottom: 10, flexWrap: \'wrap\' },
  dot:              { width: 8, height: 8, borderRadius: 4, backgroundColor: Colors.surface2 },
  dotDone:          { backgroundColor: Colors.green },
  dotActive:        { width: 24, borderRadius: 4, backgroundColor: Colors.accent },
  progressBar:      { height: 3, backgroundColor: Colors.surface2, borderRadius: 2, overflow: \'hidden\', marginBottom: 8 },
  progressFill:     { height: \'100%\', backgroundColor: Colors.accent, borderRadius: 2 },
  progressLabels:   { flexDirection: \'row\', justifyContent: \'space-between\' },
  progressText:     { fontSize: 11, color: Colors.text3 },
  stepCard:         { marginHorizontal: S.base, backgroundColor: Colors.bg3, borderWidth: 1, borderColor: Colors.border, borderRadius: R.lg, padding: S.lg, marginBottom: S.base },
  stepNumRow:       { flexDirection: \'row\', alignItems: \'center\', gap: 10, marginBottom: 8 },
  stepNum:          { fontSize: 11, color: Colors.accent, fontWeight: \'800\', letterSpacing: 1 },
  stepIngBadge:     { backgroundColor: Colors.surface, borderRadius: R.full, paddingHorizontal: 10, paddingVertical: 3 },
  stepIngText:      { fontSize: 11, color: Colors.text2 },
  stepTitle:        { fontSize: 20, color: Colors.text, fontWeight: \'800\', marginBottom: 12 },
  stepInstruction:  { fontSize: 15, color: Colors.text, lineHeight: 26, marginBottom: 14 },
  tipBox:           { backgroundColor: Colors.yellowDim, borderRadius: R.sm, padding: 12, borderWidth: 1, borderColor: Colors.yellow + \'30\' },
  tipText:          { fontSize: 13, color: Colors.yellow, lineHeight: 20 },
  timerCard:        { flexDirection: \'row\', alignItems: \'center\', gap: 20, marginHorizontal: S.base, backgroundColor: Colors.bg3, borderWidth: 1, borderColor: Colors.border, borderRadius: R.lg, padding: S.lg, marginBottom: S.base },
  timerRingWrap:    { width: 90, height: 90, position: \'relative\', alignItems: \'center\', justifyContent: \'center\' },
  timerRing:        { width: 90, height: 90, borderRadius: 45, borderWidth: 6, borderColor: Colors.surface2, position: \'absolute\' },
  timerArc:         { width: 90, height: 90, borderRadius: 45, borderWidth: 6, borderColor: Colors.accent, position: \'absolute\' },
  timerDisplay:     { fontSize: 22, color: Colors.text, fontWeight: \'800\' },
  timerLabel:       { fontSize: 16, color: Colors.text, fontWeight: \'700\', marginBottom: 3 },
  timerSub:         { fontSize: 12, color: Colors.text2, marginBottom: 12 },
  timerBtn:         { backgroundColor: Colors.accent, borderRadius: R.xs, paddingHorizontal: 18, paddingVertical: 9, alignSelf: \'flex-start\' },
  timerBtnText:     { color: \'#fff\', fontWeight: \'800\', fontSize: 13 },
  navRow:           { flexDirection: \'row\', gap: 10, marginHorizontal: S.base, marginBottom: S.base },
  prevBtn:          { backgroundColor: Colors.surface, borderRadius: R.sm, paddingVertical: 14, paddingHorizontal: 20, borderWidth: 1, borderColor: Colors.border },
  prevBtnText:      { color: Colors.text2, fontWeight: \'700\', fontSize: 14 },
  nextBtn:          { flex: 1, backgroundColor: Colors.accent, borderRadius: R.sm, paddingVertical: 14, alignItems: \'center\' },
  nextBtnText:      { color: \'#fff\', fontWeight: \'800\', fontSize: 15 },
  qaPanel:          { marginHorizontal: S.base, backgroundColor: Colors.purpleDim, borderWidth: 1, borderColor: Colors.purple + \'30\', borderRadius: R.lg, padding: S.base, marginBottom: S.base },
  qaTitle:          { fontSize: 16, color: Colors.text, fontWeight: \'800\', marginBottom: 4 },
  qaSub:            { fontSize: 12, color: Colors.text2, marginBottom: 14 },
  qaInputRow:       { marginBottom: 10 },
  qaInput:          { backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border, borderRadius: R.sm, paddingHorizontal: 14, paddingVertical: 12, color: Colors.text, fontSize: 14, minHeight: 60 },
  qaBtn:            { backgroundColor: Colors.purple, borderRadius: R.sm, paddingVertical: 12, alignItems: \'center\', marginBottom: 12 },
  qaBtnText:        { color: \'#fff\', fontWeight: \'800\', fontSize: 14 },
  qaAnswer:         { backgroundColor: Colors.surface, borderRadius: R.sm, padding: 14 },
  qaAnswerLabel:    { fontSize: 11, color: Colors.purple, fontWeight: \'800\', textTransform: \'uppercase\', letterSpacing: 0.6, marginBottom: 6 },
  qaAnswerText:     { fontSize: 14, color: Colors.text, lineHeight: 22 },
  ingredientsCard:  { marginHorizontal: S.base, backgroundColor: Colors.bg3, borderWidth: 1, borderColor: Colors.border, borderRadius: R.lg, padding: S.base, marginBottom: S.base },
  ingredientsTitle: { fontSize: 14, color: Colors.text, fontWeight: \'800\', marginBottom: 12, textTransform: \'uppercase\', letterSpacing: 0.5 },
  ingRow:           { flexDirection: \'row\', alignItems: \'center\', gap: 10, marginBottom: 10 },
  ingName:          { flex: 1, fontSize: 14, color: Colors.text, fontWeight: \'600\' },
  ingQty:           { fontSize: 12, color: Colors.text2 },
  haveTag:          { borderRadius: R.full, paddingHorizontal: 8, paddingVertical: 3 },
  tipsCard:         { marginHorizontal: S.base, backgroundColor: Colors.yellowDim, borderWidth: 1, borderColor: Colors.yellow + \'30\', borderRadius: R.lg, padding: S.base, marginBottom: S.base },
  tipsTitle:        { fontSize: 14, color: Colors.yellow, fontWeight: \'800\', marginBottom: 10 },
  tipItem:          { fontSize: 13, color: Colors.text2, lineHeight: 22, marginBottom: 4 },
})
''')


# ─────────────────────────────────────────────────────────────
# 10. PANTRY SCREEN — functional with manual add + delete
# ─────────────────────────────────────────────────────────────
w("app/(tabs)/pantry.tsx", '''import { useState } from \'react\'
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, TextInput, Alert, Modal } from \'react-native\'
import { useSafeAreaInsets } from \'react-native-safe-area-context\'
import { router } from \'expo-router\'
import { Colors, S, R } from \'../../constants/theme\'
import { deletePantryItem, addManualItem } from \'../../lib/supabase\'
import { useStore } from \'../../store\'
import { PantryItem } from \'../../types\'

const CATS = [\'All\', \'proteins\', \'vegetables\', \'grains\', \'spices\', \'dairy\', \'oils\']
const CAT_LABELS: Record<string, string> = {
  proteins: \'🥩 Proteins\', vegetables: \'🥦 Vegetables\',
  grains: \'🌾 Grains\', spices: \'🧂 Spices\',
  dairy: \'🥛 Dairy\', oils: \'🫚 Oils\', condiments: \'🥫 Condiments\', other: \'📦 Other\'
}
const CAT_COLORS: Record<string, string> = {
  proteins: \'#FF6B35\', vegetables: \'#00E5A0\', grains: \'#FCD34D\',
  spices: \'#F472B6\', dairy: \'#60A5FA\', oils: \'#A78BFA\', other: \'#9490B8\'
}

export default function PantryScreen() {
  const insets = useSafeAreaInsets()
  const { pantry, removePantryItem, addPantryItem, user, fetchPantry } = useStore()
  const [search, setSearch] = useState(\'\')
  const [activeCat, setActiveCat] = useState(\'All\')
  const [showAdd, setShowAdd] = useState(false)
  const [newItem, setNewItem] = useState({ name: \'\', emoji: \'🥘\', quantity: \'1\', unit: \'pcs\', category: \'other\' })

  const filtered = pantry.filter(item => {
    const matchSearch = item.name.toLowerCase().includes(search.toLowerCase())
    const matchCat = activeCat === \'All\' || item.category === activeCat
    return matchSearch && matchCat
  })

  const grouped = filtered.reduce((acc, item) => {
    const key = item.category || \'other\'
    if (!acc[key]) acc[key] = []
    acc[key].push(item)
    return acc
  }, {} as Record<string, PantryItem[]>)

  async function handleDelete(item: PantryItem) {
    Alert.alert(\'Remove Item\', `Remove ${item.emoji} ${item.name} from pantry?`, [
      { text: \'Cancel\', style: \'cancel\' },
      {
        text: \'Remove\', style: \'destructive\',
        onPress: async () => {
          if (user && item.id !== \'local\') {
            try { await deletePantryItem(item.id) } catch {}
          }
          removePantryItem(item.id)
        }
      }
    ])
  }

  async function handleAddItem() {
    if (!newItem.name.trim()) { Alert.alert(\'Enter a name\'); return }
    const item: PantryItem = {
      id: Date.now().toString() + Math.random(),
      user_id: user?.id ?? \'local\',
      name: newItem.name.trim(),
      emoji: newItem.emoji,
      quantity: newItem.quantity,
      unit: newItem.unit,
      category: newItem.category,
      added_at: new Date().toISOString(),
    }
    if (user) {
      try {
        const saved = await addManualItem({ user_id: user.id, name: item.name, emoji: item.emoji, quantity: item.quantity, unit: item.unit, category: item.category })
        addPantryItem(saved)
      } catch { addPantryItem(item) }
    } else {
      addPantryItem(item)
    }
    setNewItem({ name: \'\', emoji: \'🥘\', quantity: \'1\', unit: \'pcs\', category: \'other\' })
    setShowAdd(false)
  }

  const lowStock = pantry.filter(i => i.is_low).length

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>My Pantry</Text>
          <Text style={styles.sub}>{pantry.length} ingredients tracked</Text>
        </View>
        <TouchableOpacity style={styles.addBtn} onPress={() => setShowAdd(true)}>
          <Text style={{ color: \'#fff\', fontSize: 22, fontWeight: \'800\' }}>+</Text>
        </TouchableOpacity>
      </View>

      {/* Stats */}
      <View style={styles.statsRow}>
        {[
          { icon: \'📦\', val: pantry.length, label: \'Total\', color: Colors.green },
          { icon: \'⚠️\', val: lowStock, label: \'Low Stock\', color: Colors.yellow },
          { icon: \'📅\', val: 1, label: \'Expiring\', color: Colors.red },
        ].map((s, i) => (
          <View key={i} style={styles.statCard}>
            <Text style={{ fontSize: 22, marginBottom: 4 }}>{s.icon}</Text>
            <Text style={[styles.statVal, { color: s.color }]}>{s.val}</Text>
            <Text style={styles.statLabel}>{s.label}</Text>
          </View>
        ))}
      </View>

      {/* Search */}
      <View style={styles.searchBar}>
        <Text style={{ fontSize: 16, color: Colors.text3 }}>🔍</Text>
        <TextInput
          style={styles.searchInput}
          placeholder="Search ingredients..."
          placeholderTextColor={Colors.text3}
          value={search}
          onChangeText={setSearch}
        />
        {search.length > 0 && (
          <TouchableOpacity onPress={() => setSearch(\'\')}><Text style={{ color: Colors.text3 }}>✕</Text></TouchableOpacity>
        )}
      </View>

      {/* Category Filter */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.catRow} contentContainerStyle={{ paddingHorizontal: S.base, gap: 8 }}>
        {CATS.map(c => (
          <TouchableOpacity key={c} style={[styles.catPill, activeCat === c && styles.catPillActive]} onPress={() => setActiveCat(c)}>
            <Text style={[styles.catText, activeCat === c && styles.catTextActive]}>
              {c === \'All\' ? \'All\' : (CAT_LABELS[c] ?? c)}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: 100 }}>
        {pantry.length === 0 ? (
          <View style={styles.empty}>
            <Text style={{ fontSize: 72, marginBottom: 16 }}>🧺</Text>
            <Text style={styles.emptyTitle}>Pantry is empty</Text>
            <Text style={styles.emptySub}>Scan your ingredients or tap + to add manually</Text>
            <TouchableOpacity style={styles.scanBtn} onPress={() => router.push(\'/(tabs)/scan\')}>
              <Text style={styles.scanBtnText}>📸 Scan Ingredients</Text>
            </TouchableOpacity>
          </View>
        ) : (
          Object.entries(grouped).map(([cat, items]) => (
            <View key={cat} style={styles.section}>
              <View style={styles.sectionHeader}>
                <View style={[styles.catDot, { backgroundColor: CAT_COLORS[cat] ?? Colors.text3 }]} />
                <Text style={styles.sectionTitle}>{CAT_LABELS[cat] ?? cat}</Text>
                <View style={styles.countBadge}><Text style={styles.countText}>{items.length}</Text></View>
              </View>
              {items.map(item => (
                <TouchableOpacity
                  key={item.id}
                  style={styles.itemRow}
                  onLongPress={() => handleDelete(item)}
                  activeOpacity={0.8}
                >
                  <View style={styles.itemEmoji}>
                    <Text style={{ fontSize: 22 }}>{item.emoji}</Text>
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.itemName}>{item.name}</Text>
                    <Text style={styles.itemCat}>{item.category}</Text>
                  </View>
                  <View style={[styles.qtyBadge, { backgroundColor: (CAT_COLORS[item.category] ?? Colors.accent) + \'20\' }]}>
                    <Text style={[styles.qtyText, { color: CAT_COLORS[item.category] ?? Colors.accent }]}>
                      {item.quantity} {item.unit}
                    </Text>
                  </View>
                  <TouchableOpacity style={styles.menuBtn} onPress={() => handleDelete(item)}>
                    <Text style={{ color: Colors.text3, fontSize: 18 }}>···</Text>
                  </TouchableOpacity>
                </TouchableOpacity>
              ))}
            </View>
          ))
        )}
      </ScrollView>

      {pantry.length > 0 && (
        <View style={styles.hintBar}>
          <Text style={styles.hintText}>💡 Long-press or tap ··· to remove items</Text>
        </View>
      )}

      {/* Add Item Modal */}
      <Modal visible={showAdd} transparent animationType="slide" onRequestClose={() => setShowAdd(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modal}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Add Ingredient</Text>
              <TouchableOpacity onPress={() => setShowAdd(false)}>
                <Text style={{ color: Colors.text2, fontSize: 18 }}>✕</Text>
              </TouchableOpacity>
            </View>
            <TextInput style={styles.modalInput} placeholder="Ingredient name" placeholderTextColor={Colors.text3} value={newItem.name} onChangeText={v => setNewItem(p => ({ ...p, name: v }))} />
            <View style={styles.modalRow}>
              <TextInput style={[styles.modalInput, { flex: 1 }]} placeholder="Qty" placeholderTextColor={Colors.text3} value={newItem.quantity} onChangeText={v => setNewItem(p => ({ ...p, quantity: v }))} keyboardType="numeric" />
              <TextInput style={[styles.modalInput, { flex: 1 }]} placeholder="Unit (pcs/kg/g)" placeholderTextColor={Colors.text3} value={newItem.unit} onChangeText={v => setNewItem(p => ({ ...p, unit: v }))} />
            </View>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 16 }}>
              {Object.keys(CAT_LABELS).map(c => (
                <TouchableOpacity key={c} style={[styles.catChip, newItem.category === c && { backgroundColor: Colors.accent + \'30\', borderColor: Colors.accent }]} onPress={() => setNewItem(p => ({ ...p, category: c }))}>
                  <Text style={{ fontSize: 12, color: newItem.category === c ? Colors.accent : Colors.text2, fontWeight: \'600\' }}>{CAT_LABELS[c]}</Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
            <TouchableOpacity style={styles.modalSaveBtn} onPress={handleAddItem}>
              <Text style={styles.modalSaveBtnText}>Add to Pantry ✓</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  )
}

const styles = StyleSheet.create({
  root:           { flex: 1, backgroundColor: Colors.bg },
  header:         { flexDirection: \'row\', justifyContent: \'space-between\', alignItems: \'center\', paddingHorizontal: S.base, paddingTop: S.base, paddingBottom: 10 },
  title:          { fontSize: 28, color: Colors.text, fontWeight: \'800\' },
  sub:            { fontSize: 13, color: Colors.text2 },
  addBtn:         { width: 44, height: 44, borderRadius: 22, backgroundColor: Colors.accent, alignItems: \'center\', justifyContent: \'center\' },
  statsRow:       { flexDirection: \'row\', gap: 8, paddingHorizontal: S.base, marginBottom: 12 },
  statCard:       { flex: 1, backgroundColor: Colors.bg3, borderWidth: 1, borderColor: Colors.border, borderRadius: R.md, padding: 12, alignItems: \'center\' },
  statVal:        { fontSize: 22, fontWeight: \'800\' },
  statLabel:      { fontSize: 10, color: Colors.text3, textTransform: \'uppercase\', letterSpacing: 0.4 },
  searchBar:      { flexDirection: \'row\', alignItems: \'center\', gap: 10, backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border, borderRadius: R.sm, marginHorizontal: S.base, marginBottom: 10, paddingHorizontal: 14, paddingVertical: 10 },
  searchInput:    { flex: 1, color: Colors.text, fontSize: 14 },
  catRow:         { marginBottom: 12, maxHeight: 44 },
  catPill:        { paddingHorizontal: 14, paddingVertical: 8, borderRadius: R.full, backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border },
  catPillActive:  { backgroundColor: Colors.accentGlow, borderColor: Colors.accent + \'50\' },
  catText:        { fontSize: 12, color: Colors.text2, fontWeight: \'600\' },
  catTextActive:  { color: Colors.accent, fontWeight: \'800\' },
  empty:          { alignItems: \'center\', paddingTop: 60, paddingHorizontal: 40 },
  emptyTitle:     { fontSize: 24, color: Colors.text, fontWeight: \'800\', marginBottom: 10 },
  emptySub:       { fontSize: 14, color: Colors.text2, textAlign: \'center\', lineHeight: 22, marginBottom: 24 },
  scanBtn:        { backgroundColor: Colors.accent, borderRadius: R.sm, paddingHorizontal: 24, paddingVertical: 12 },
  scanBtnText:    { color: \'#fff\', fontWeight: \'800\', fontSize: 14 },
  section:        { paddingHorizontal: S.base, marginBottom: S.lg },
  sectionHeader:  { flexDirection: \'row\', alignItems: \'center\', gap: 8, marginBottom: 10 },
  catDot:         { width: 10, height: 10, borderRadius: 5 },
  sectionTitle:   { flex: 1, fontSize: 13, color: Colors.text3, fontWeight: \'700\', textTransform: \'uppercase\', letterSpacing: 0.6 },
  countBadge:     { backgroundColor: Colors.surface, borderRadius: R.full, paddingHorizontal: 8, paddingVertical: 2 },
  countText:      { fontSize: 11, color: Colors.text2, fontWeight: \'700\' },
  itemRow:        { flexDirection: \'row\', alignItems: \'center\', gap: 12, backgroundColor: Colors.bg3, borderWidth: 1, borderColor: Colors.border, borderRadius: R.sm, padding: 12, marginBottom: 6 },
  itemEmoji:      { width: 44, height: 44, backgroundColor: Colors.surface, borderRadius: R.xs, alignItems: \'center\', justifyContent: \'center\' },
  itemName:       { fontSize: 15, color: Colors.text, fontWeight: \'700\', marginBottom: 2 },
  itemCat:        { fontSize: 11, color: Colors.text3, textTransform: \'capitalize\' },
  qtyBadge:       { borderRadius: R.full, paddingHorizontal: 10, paddingVertical: 4 },
  qtyText:        { fontSize: 12, fontWeight: \'700\' },
  menuBtn:        { paddingHorizontal: 8 },
  hintBar:        { position: \'absolute\', bottom: 72, left: 0, right: 0, alignItems: \'center\' },
  hintText:       { fontSize: 12, color: Colors.text3 },
  modalOverlay:   { flex: 1, backgroundColor: \'rgba(0,0,0,0.7)\', justifyContent: \'flex-end\' },
  modal:          { backgroundColor: Colors.bg2, borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: S.xl, paddingBottom: 40 },
  modalHeader:    { flexDirection: \'row\', justifyContent: \'space-between\', alignItems: \'center\', marginBottom: 20 },
  modalTitle:     { fontSize: 20, color: Colors.text, fontWeight: \'800\' },
  modalInput:     { backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border, borderRadius: R.sm, paddingHorizontal: 14, paddingVertical: 12, color: Colors.text, fontSize: 15, marginBottom: 10 },
  modalRow:       { flexDirection: \'row\', gap: 10 },
  catChip:        { backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border, borderRadius: R.full, paddingHorizontal: 12, paddingVertical: 6, marginRight: 8 },
  modalSaveBtn:   { backgroundColor: Colors.accent, borderRadius: R.sm, paddingVertical: 14, alignItems: \'center\', marginTop: 6 },
  modalSaveBtnText:{ color: \'#fff\', fontWeight: \'800\', fontSize: 16 },
})
''')


# ─────────────────────────────────────────────────────────────
# 11. PROFILE — taste profile, cook history, settings
# ─────────────────────────────────────────────────────────────
w("app/(tabs)/profile.tsx", '''import { View, Text, ScrollView, TouchableOpacity, StyleSheet, Alert } from \'react-native\'
import { useSafeAreaInsets } from \'react-native-safe-area-context\'
import { router } from \'expo-router\'
import { Colors, S, R } from \'../../constants/theme\'
import { signOut } from \'../../lib/supabase\'
import { useStore } from \'../../store\'

export default function ProfileScreen() {
  const insets = useSafeAreaInsets()
  const { user, setUser, pantry, cookHistory, tasteProfile } = useStore()
  const initials = user?.name?.split(\' \').map((n: string) => n[0]).join(\'\').toUpperCase().slice(0, 2) ?? \'👤\'
  const recentHistory = cookHistory.slice(-5).reverse()

  async function handleSignOut() {
    Alert.alert(\'Sign Out\', \'Are you sure?\', [
      { text: \'Cancel\', style: \'cancel\' },
      { text: \'Sign Out\', style: \'destructive\', onPress: async () => { await signOut(); setUser(null) } }
    ])
  }

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: 100 }}>

        {/* Hero */}
        <View style={styles.hero}>
          <View style={styles.avatarRing}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>{initials}</Text>
            </View>
          </View>
          <Text style={styles.name}>{user?.name ?? \'Welcome, Chef!\'}</Text>
          <Text style={styles.email}>{user?.email ?? \'Sign in to save your data across devices\'}</Text>

          {/* Stats */}
          <View style={styles.statsRow}>
            {[
              { val: pantry.length, label: \'PANTRY\', color: Colors.green },
              { val: tasteProfile.totalCooked, label: \'COOKED\', color: Colors.accent },
              { val: tasteProfile.preferredCuisines.length || 4, label: \'CUISINES\', color: Colors.purple },
            ].map((s, i) => (
              <View key={i} style={styles.stat}>
                <Text style={[styles.statVal, { color: s.color }]}>{s.val}</Text>
                <Text style={styles.statLabel}>{s.label}</Text>
              </View>
            ))}
          </View>
        </View>

        {/* Taste Profile Card */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>🧠 Taste Profile</Text>
          <View style={styles.tasteCard}>
            <Text style={styles.tasteInsight}>{tasteProfile.tasteInsight}</Text>
            {tasteProfile.favoriteDishes.length > 0 ? (
              <>
                <Text style={styles.tasteSectionTitle}>Favourites</Text>
                <View style={styles.chipRow}>
                  {tasteProfile.favoriteDishes.slice(-6).map((d, i) => (
                    <View key={i} style={styles.chip}><Text style={styles.chipText}>{d}</Text></View>
                  ))}
                </View>
                <Text style={styles.tasteSectionTitle}>Cuisines</Text>
                <View style={styles.chipRow}>
                  {tasteProfile.preferredCuisines.slice(-5).map((c, i) => (
                    <View key={i} style={[styles.chip, { backgroundColor: Colors.purpleDim }]}><Text style={[styles.chipText, { color: Colors.purple }]}>{c}</Text></View>
                  ))}
                </View>
              </>
            ) : (
              <TouchableOpacity style={styles.buildProfileBtn} onPress={() => router.push(\'/(tabs)/scan\')}>
                <Text style={styles.buildProfileBtnText}>Cook dishes to build your taste profile →</Text>
              </TouchableOpacity>
            )}
          </View>
        </View>

        {/* Cook History */}
        {recentHistory.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionLabel}>🍳 Cook History</Text>
            {recentHistory.map((item, i) => (
              <View key={i} style={styles.historyRow}>
                <View style={styles.historyEmoji}>
                  <Text style={{ fontSize: 22 }}>{item.recipeEmoji}</Text>
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.historyName}>{item.recipeName}</Text>
                  <Text style={styles.historyMeta}>{item.cuisine} · {new Date(item.cookedAt).toLocaleDateString()}</Text>
                </View>
                <View style={styles.doneBadge}><Text style={styles.doneText}>✓</Text></View>
              </View>
            ))}
          </View>
        )}

        {/* Pro Banner */}
        <TouchableOpacity style={styles.proBanner} activeOpacity={0.85}>
          <Text style={{ fontSize: 28 }}>⚡</Text>
          <View style={{ flex: 1 }}>
            <Text style={styles.proTitle}>Upgrade to Pro</Text>
            <Text style={styles.proSub}>Unlimited scans · Meal plans · Advanced nutrition</Text>
          </View>
          <View>
            <Text style={styles.proPrice}>₹299</Text>
            <Text style={styles.proPer}>/month</Text>
          </View>
        </TouchableOpacity>

        {/* Settings */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>⚙️ Preferences</Text>
          <View style={styles.settingsCard}>
            {[
              { icon: \'🍽️\', label: \'Dietary\', val: user?.dietary_preference ?? \'All\' },
              { icon: \'🌶️\', label: \'Spice Level\', val: user?.spice_level ?? \'Medium\' },
              { icon: \'🌍\', label: \'Cuisines\', val: user?.cuisine_preference?.join(\', \') ?? \'Indian, Asian\' },
              { icon: \'🔔\', label: \'Notifications\', val: \'On\' },
            ].map((item, i) => (
              <TouchableOpacity key={i} style={[styles.settingRow, i > 0 && styles.settingBorder]}>
                <View style={styles.settingIcon}><Text style={{ fontSize: 18 }}>{item.icon}</Text></View>
                <Text style={styles.settingLabel}>{item.label}</Text>
                <Text style={styles.settingVal}>{item.val}</Text>
                <Text style={{ color: Colors.text3 }}>›</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Auth Button */}
        {!user ? (
          <TouchableOpacity style={styles.signInBtn} onPress={() => router.push(\'/auth\')}>
            <Text style={styles.signInText}>🔑 Sign In / Create Account</Text>
          </TouchableOpacity>
        ) : (
          <TouchableOpacity style={styles.signOutBtn} onPress={handleSignOut}>
            <Text style={styles.signOutText}>Sign Out</Text>
          </TouchableOpacity>
        )}

      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  root:             { flex: 1, backgroundColor: Colors.bg },
  hero:             { alignItems: \'center\', padding: S.xl, paddingBottom: S.lg, borderBottomWidth: 1, borderBottomColor: Colors.border },
  avatarRing:       { width: 96, height: 96, borderRadius: 48, borderWidth: 3, borderColor: Colors.accent, alignItems: \'center\', justifyContent: \'center\', marginBottom: 14 },
  avatar:           { width: 84, height: 84, borderRadius: 42, backgroundColor: Colors.accentGlow, alignItems: \'center\', justifyContent: \'center\' },
  avatarText:       { fontSize: 30, fontWeight: \'800\', color: Colors.accent },
  name:             { fontSize: 24, color: Colors.text, fontWeight: \'800\', marginBottom: 4 },
  email:            { fontSize: 13, color: Colors.text2, marginBottom: 20 },
  statsRow:         { flexDirection: \'row\', gap: 1, backgroundColor: Colors.border, borderRadius: R.lg, overflow: \'hidden\', width: \'100%\' },
  stat:             { flex: 1, backgroundColor: Colors.bg3, padding: 14, alignItems: \'center\' },
  statVal:          { fontSize: 24, fontWeight: \'800\' },
  statLabel:        { fontSize: 10, color: Colors.text3, textTransform: \'uppercase\', letterSpacing: 0.5, marginTop: 2 },
  section:          { paddingHorizontal: S.base, marginTop: S.lg },
  sectionLabel:     { fontSize: 11, fontWeight: \'700\', color: Colors.text3, textTransform: \'uppercase\', letterSpacing: 0.8, marginBottom: 10 },
  tasteCard:        { backgroundColor: Colors.bg3, borderWidth: 1, borderColor: Colors.border, borderRadius: R.lg, padding: S.base },
  tasteInsight:     { fontSize: 14, color: Colors.text, fontStyle: \'italic\', marginBottom: 14, lineHeight: 22 },
  tasteSectionTitle:{ fontSize: 11, color: Colors.text3, fontWeight: \'700\', textTransform: \'uppercase\', letterSpacing: 0.5, marginBottom: 8, marginTop: 6 },
  chipRow:          { flexDirection: \'row\', flexWrap: \'wrap\', gap: 6, marginBottom: 8 },
  chip:             { backgroundColor: Colors.surface, borderRadius: R.full, paddingHorizontal: 10, paddingVertical: 4 },
  chipText:         { fontSize: 12, color: Colors.text2, fontWeight: \'600\' },
  buildProfileBtn:  { backgroundColor: Colors.accentGlow, borderRadius: R.sm, paddingVertical: 12, alignItems: \'center\', borderWidth: 1, borderColor: Colors.accent + \'30\' },
  buildProfileBtnText:{ color: Colors.accent, fontWeight: \'700\', fontSize: 13 },
  historyRow:       { flexDirection: \'row\', alignItems: \'center\', gap: 12, backgroundColor: Colors.bg3, borderWidth: 1, borderColor: Colors.border, borderRadius: R.sm, padding: 12, marginBottom: 6 },
  historyEmoji:     { width: 40, height: 40, backgroundColor: Colors.surface, borderRadius: R.xs, alignItems: \'center\', justifyContent: \'center\' },
  historyName:      { fontSize: 14, color: Colors.text, fontWeight: \'700\', marginBottom: 2 },
  historyMeta:      { fontSize: 11, color: Colors.text2 },
  doneBadge:        { width: 28, height: 28, borderRadius: 14, backgroundColor: Colors.greenDim, alignItems: \'center\', justifyContent: \'center\' },
  doneText:         { color: Colors.green, fontWeight: \'800\' },
  proBanner:        { flexDirection: \'row\', alignItems: \'center\', gap: 12, marginHorizontal: S.base, marginTop: S.lg, backgroundColor: Colors.purpleDim, borderWidth: 1, borderColor: Colors.purple + \'40\', borderRadius: R.lg, padding: S.base },
  proTitle:         { fontSize: 16, color: Colors.text, fontWeight: \'800\', marginBottom: 2 },
  proSub:           { fontSize: 12, color: Colors.text2 },
  proPrice:         { fontSize: 20, color: Colors.purple, fontWeight: \'800\', textAlign: \'right\' },
  proPer:           { fontSize: 11, color: Colors.text3, textAlign: \'right\' },
  settingsCard:     { backgroundColor: Colors.bg3, borderWidth: 1, borderColor: Colors.border, borderRadius: R.lg, overflow: \'hidden\' },
  settingRow:       { flexDirection: \'row\', alignItems: \'center\', gap: 12, padding: S.base },
  settingBorder:    { borderTopWidth: 1, borderTopColor: Colors.border },
  settingIcon:      { width: 36, height: 36, borderRadius: R.xs, backgroundColor: Colors.surface, alignItems: \'center\', justifyContent: \'center\' },
  settingLabel:     { flex: 1, fontSize: 15, color: Colors.text, fontWeight: \'600\' },
  settingVal:       { fontSize: 13, color: Colors.text2, marginRight: 6 },
  signInBtn:        { margin: S.base, marginTop: S.xl, backgroundColor: Colors.accent, borderRadius: R.sm, padding: 16, alignItems: \'center\' },
  signInText:       { color: \'#fff\', fontWeight: \'800\', fontSize: 15 },
  signOutBtn:       { margin: S.base, marginTop: S.xl, backgroundColor: Colors.redDim, borderRadius: R.sm, padding: 16, alignItems: \'center\', borderWidth: 1, borderColor: Colors.red + \'40\' },
  signOutText:      { color: Colors.red, fontWeight: \'800\', fontSize: 15 },
})
''')


# ─────────────────────────────────────────────────────────────
# 12. TAB LAYOUT + THEME (keep existing good design)
# ─────────────────────────────────────────────────────────────
w("app/(tabs)/_layout.tsx", '''import { Tabs } from \'expo-router\'
import { View, Text, StyleSheet, Platform } from \'react-native\'
import { useSafeAreaInsets } from \'react-native-safe-area-context\'
import { Colors } from \'../../constants/theme\'

function TabIcon({ emoji, label, focused }: { emoji: string; label: string; focused: boolean }) {
  return (
    <View style={[styles.icon, focused && styles.iconActive]}>
      <Text style={[styles.emoji, focused && styles.emojiActive]}>{emoji}</Text>
      <Text style={[styles.label, focused && styles.labelActive]}>{label}</Text>
      {focused && <View style={styles.activeDot} />}
    </View>
  )
}

export default function TabLayout() {
  const insets = useSafeAreaInsets()
  return (
    <Tabs screenOptions={{
      headerShown: false,
      tabBarShowLabel: false,
      tabBarStyle: {
        position: \'absolute\',
        bottom: 0, left: 0, right: 0,
        height: 62 + insets.bottom,
        backgroundColor: Platform.OS === \'android\' ? Colors.bg2 : \'rgba(10,10,22,0.97)\',
        borderTopWidth: 1,
        borderTopColor: Colors.border,
        elevation: 0,
      },
    }}>
      <Tabs.Screen name="index" options={{ tabBarIcon: ({ focused }) => <TabIcon emoji="🏠" label="Home" focused={focused} /> }} />
      <Tabs.Screen name="scan" options={{ tabBarIcon: ({ focused }) => <TabIcon emoji="📸" label="Scan" focused={focused} /> }} />
      <Tabs.Screen name="recipes" options={{ tabBarIcon: ({ focused }) => <TabIcon emoji="🍽️" label="Recipes" focused={focused} /> }} />
      <Tabs.Screen name="pantry" options={{ tabBarIcon: ({ focused }) => <TabIcon emoji="🧺" label="Pantry" focused={focused} /> }} />
      <Tabs.Screen name="profile" options={{ tabBarIcon: ({ focused }) => <TabIcon emoji="👤" label="Profile" focused={focused} /> }} />
    </Tabs>
  )
}

const styles = StyleSheet.create({
  icon:       { alignItems: \'center\', paddingTop: 8, gap: 2, opacity: 0.45, position: \'relative\' },
  iconActive: { opacity: 1 },
  emoji:      { fontSize: 22 },
  emojiActive:{ fontSize: 24 },
  label:      { fontSize: 10, color: Colors.text3, letterSpacing: 0.3, fontWeight: \'600\' },
  labelActive:{ color: Colors.accent, fontWeight: \'800\' },
  activeDot:  { position: \'absolute\', bottom: -6, width: 4, height: 4, borderRadius: 2, backgroundColor: Colors.accent },
})
''')

# ─────────────────────────────────────────────────────────────
# 13. THEME — updated with all needed colors
# ─────────────────────────────────────────────────────────────
w("constants/theme.ts", '''export const Colors = {
  bg:          \'#08080F\',
  bg2:         \'#0F0F1A\',
  bg3:         \'#151525\',
  surface:     \'#1C1C2E\',
  surface2:    \'#242438\',
  border:      \'rgba(255,255,255,0.08)\',
  border2:     \'rgba(255,255,255,0.15)\',
  text:        \'#F2F0FF\',
  text2:       \'#9490B8\',
  text3:       \'#5A5678\',
  accent:      \'#FF6B35\',
  accent2:     \'#FF8C5A\',
  accentGlow:  \'rgba(255,107,53,0.18)\',
  green:       \'#00E5A0\',
  greenDim:    \'rgba(0,229,160,0.14)\',
  purple:      \'#A78BFA\',
  purpleDim:   \'rgba(167,139,250,0.15)\',
  pink:        \'#F472B6\',
  pinkDim:     \'rgba(244,114,182,0.14)\',
  yellow:      \'#FCD34D\',
  yellowDim:   \'rgba(252,211,77,0.12)\',
  blue:        \'#60A5FA\',
  blueDim:     \'rgba(96,165,250,0.13)\',
  red:         \'#FF4F6B\',
  redDim:      \'rgba(255,79,107,0.13)\',
  cyan:        \'#22D3EE\',
  cyanDim:     \'rgba(34,211,238,0.13)\',
} as const

export const S = {
  xs: 4, sm: 8, md: 12, base: 16, lg: 20, xl: 24,
} as const

export const R = {
  xs: 6, sm: 10, md: 14, lg: 18, xl: 24, full: 999,
} as const
''')

print("\n✅ All files written!\n")
print("Now run these commands:")
print("  npx expo start --clear")
print("  Press w for web browser")
print("")
print("What works now:")
print("  ✓ Home — live pantry, taste profile, cook history")
print("  ✓ Scan — image pick + AI detection + quick add + manual add")
print("  ✓ Recipes — real AI generation + ingredient substitution")  
print("  ✓ Cook Mode — step-by-step + timer + AI Q&A + taste profile update")
print("  ✓ Pantry — add/delete items + modal form")
print("  ✓ Profile — taste profile + cook history display")

