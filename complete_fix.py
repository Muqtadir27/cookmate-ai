import os, base64

root = os.getcwd()

def w(path, content):
    full = os.path.join(root, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  ✓ {path}")

print("\n=== CookMate — Complete Fix ===\n")

# ─── STORE — add userPrefs, pantry persistence ───────────────
w("store/index.ts", '''\
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
''')


# ─── ROOT LAYOUT — load all persisted data on boot ──────────
w("app/_layout.tsx", '''\
import { useEffect } from 'react'
import { Stack } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { GestureHandlerRootView } from 'react-native-gesture-handler'
import { SafeAreaProvider } from 'react-native-safe-area-context'
import { View, StyleSheet } from 'react-native'
import { Colors } from '../constants/theme'
import { supabase, getCurrentUser } from '../lib/supabase'
import { useStore } from '../store'

export default function RootLayout() {
  const { setUser, fetchPantry, loadTasteProfile, loadCookHistory, loadUserPrefs, loadPantryLocal } = useStore()

  useEffect(() => {
    // Load all local data immediately
    loadTasteProfile()
    loadCookHistory()
    loadUserPrefs()
    loadPantryLocal()

    // Then check for logged-in user
    supabase.auth.getSession().then(({ data }) => {
      if (data.session?.user) {
        getCurrentUser().then(u => { if (u) { setUser(u); fetchPantry(u.id) } })
      }
    })
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === 'SIGNED_IN' && session) {
        const u = await getCurrentUser()
        if (u) { setUser(u); fetchPantry(u.id) }
      }
      if (event === 'SIGNED_OUT') setUser(null)
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
            <Stack.Screen name="auth" options={{ presentation: 'modal' }} />
            <Stack.Screen name="cook/[id]" options={{ presentation: 'fullScreenModal', animation: 'slide_from_bottom' }} />
          </Stack>
        </View>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  )
}
const styles = StyleSheet.create({ root: { flex: 1, backgroundColor: Colors.bg } })
''')


# ─── RECIPES SCREEN — servings picker modal before generate ──
w("app/(tabs)/recipes.tsx", '''\
import { useState } from 'react'
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, TextInput, Modal, ActivityIndicator, Alert, Dimensions, Platform } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { router } from 'expo-router'
import { Colors, S, R } from '../../constants/theme'
import { useStore } from '../../store'
import { generateRecipes } from '../../lib/gemini'
import { Recipe } from '../../types'

const { width } = Dimensions.get('window')
const isWeb = Platform.OS === 'web'
const CARD_W = isWeb ? 220 : (width - S.base * 2 - 12) / 2

const FILTERS = [
  { id:'all', l:'All', e:'⭐' }, { id:'indian', l:'Indian', e:'🇮🇳' },
  { id:'asian', l:'Asian', e:'🍜' }, { id:'west', l:'Western', e:'🍝' },
  { id:'quick', l:'Quick', e:'⚡' }, { id:'veg', l:'Veg', e:'🥗' },
]

const SAMPLE: Recipe[] = [
  { id:'s1', name:'Butter Chicken', emoji:'🍛', cuisine:'Punjabi', dietary:'Non-Veg', description:'Creamy tomato curry', match_score:92, missing_ingredients:[], ingredients:[], steps:[], nutrition:{calories:520,protein_g:32,carbs_g:18,fat_g:28,fiber_g:3}, time_minutes:40, servings:2, difficulty:'Medium', tips:[], generated_at:'' },
  { id:'s2', name:'Masala Dosa', emoji:'🫓', cuisine:'South Indian', dietary:'Vegetarian', description:'Crispy rice crepe', match_score:88, missing_ingredients:[], ingredients:[], steps:[], nutrition:{calories:280,protein_g:8,carbs_g:52,fat_g:6,fiber_g:4}, time_minutes:30, servings:2, difficulty:'Medium', tips:[], generated_at:'' },
  { id:'s3', name:'Biryani', emoji:'🍚', cuisine:'Mughlai', dietary:'Non-Veg', description:'Layered spiced rice', match_score:85, missing_ingredients:[], ingredients:[], steps:[], nutrition:{calories:620,protein_g:28,carbs_g:82,fat_g:18,fiber_g:5}, time_minutes:60, servings:2, difficulty:'Hard', tips:[], generated_at:'' },
  { id:'s4', name:'Pad Thai', emoji:'🍜', cuisine:'Thai', dietary:'Vegetarian', description:'Stir-fried noodles', match_score:78, missing_ingredients:[], ingredients:[], steps:[], nutrition:{calories:420,protein_g:14,carbs_g:68,fat_g:12,fiber_g:3}, time_minutes:25, servings:2, difficulty:'Easy', tips:[], generated_at:'' },
  { id:'s5', name:'Shakshuka', emoji:'🍳', cuisine:'Middle Eastern', dietary:'Vegetarian', description:'Eggs in tomato sauce', match_score:95, missing_ingredients:[], ingredients:[], steps:[], nutrition:{calories:310,protein_g:18,carbs_g:22,fat_g:16,fiber_g:6}, time_minutes:20, servings:2, difficulty:'Easy', tips:[], generated_at:'' },
  { id:'s6', name:'Pav Bhaji', emoji:'🥖', cuisine:'Mumbai Street', dietary:'Vegetarian', description:'Spiced veggie mash', match_score:90, missing_ingredients:[], ingredients:[], steps:[], nutrition:{calories:380,protein_g:10,carbs_g:62,fat_g:12,fiber_g:8}, time_minutes:35, servings:2, difficulty:'Easy', tips:[], generated_at:'' },
]

const TAG_COLORS: Record<string,string> = {
  'Punjabi':'#FF5722','South Indian':'#00E5A0','Mughlai':'#B794F4',
  'Thai':'#76E4F7','Middle Eastern':'#F6E05E','Mumbai Street':'#F687B3',
}

export default function RecipesScreen() {
  const insets = useSafeAreaInsets()
  const { recipes, setRecipes, setActiveRecipe, setCookStep, pantry, loading, setLoading, tasteProfile, userPrefs } = useStore()
  const [active, setActive] = useState('all')
  const [search, setSearch] = useState('')
  const [showServings, setShowServings] = useState(false)
  const [servings, setServings] = useState(userPrefs.servings ?? 2)

  const display = recipes.length > 0 ? recipes : SAMPLE
  const filtered = display.filter(r => {
    const matchSearch = !search || r.name.toLowerCase().includes(search.toLowerCase())
    const matchFilter = active === 'all' ||
      (active === 'veg' && r.dietary.toLowerCase().includes('veg')) ||
      (active === 'quick' && r.time_minutes <= 25) ||
      (active === 'indian' && ['Punjabi','South Indian','Mughlai','Mumbai Street'].includes(r.cuisine)) ||
      (active === 'asian' && ['Thai','Japanese','Chinese','Korean'].includes(r.cuisine)) ||
      (active === 'west' && ['Italian','French','American','Continental'].includes(r.cuisine))
    return matchSearch && matchFilter
  })

  function openRecipe(r: Recipe) {
    setActiveRecipe(r)
    setCookStep(0)
    router.push(`/cook/${r.id}`)
  }

  async function doGenerate(srv: number) {
    setShowServings(false)
    if (pantry.length === 0) {
      Alert.alert('Empty pantry', 'Add ingredients first', [{ text:'Go Scan', onPress:() => router.push('/(tabs)/scan') }])
      return
    }
    setLoading(true)
    try {
      const r = await generateRecipes(
        pantry,
        { cuisines: userPrefs.cuisines, dietary: userPrefs.dietary, spice: userPrefs.spice, servings: srv },
        tasteProfile
      )
      setRecipes(r)
    } catch (e: any) {
      Alert.alert('Generation Failed', e.message ?? 'Check your API key and internet connection')
    } finally { setLoading(false) }
  }

  const tagColor = (r: Recipe) => TAG_COLORS[r.cuisine] ?? Colors.accent

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom:100 }}>

        <View style={styles.header}>
          <Text style={styles.title}>AI Recipes</Text>
          <TouchableOpacity style={[styles.genBtn, loading && { opacity:0.6 }]}
            onPress={() => setShowServings(true)} disabled={loading} activeOpacity={0.88}>
            {loading ? <ActivityIndicator size="small" color={Colors.purple} /> : <Text style={{ fontSize:16 }}>✨</Text>}
            <Text style={styles.genText}>{loading ? 'Generating...' : 'Generate'}</Text>
          </TouchableOpacity>
        </View>

        <View style={[styles.px, { marginBottom: S.base }]}>
          <View style={styles.searchBox}>
            <Text style={{ fontSize:16, marginRight:8 }}>🔍</Text>
            <TextInput style={styles.searchInput} placeholder="Search recipes..." placeholderTextColor={Colors.text3} value={search} onChangeText={setSearch} />
            {search.length > 0 && <TouchableOpacity onPress={() => setSearch('')}><Text style={{ color: Colors.text3, fontSize:20 }}>×</Text></TouchableOpacity>}
          </View>
        </View>

        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingHorizontal: S.base, gap:8, marginBottom: S.lg }}>
          {FILTERS.map(f => (
            <TouchableOpacity key={f.id} style={[styles.pill, active===f.id && styles.pillOn]} onPress={() => setActive(f.id)}>
              <Text style={{ fontSize:14 }}>{f.e}</Text>
              <Text style={[styles.pillLabel, active===f.id && styles.pillLabelOn]}>{f.l}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {recipes.length > 0 && (
          <View style={[styles.px, { marginBottom: S.base }]}>
            <View style={styles.aiNote}>
              <Text style={{ fontSize:16 }}>✨</Text>
              <Text style={styles.aiNoteText}>Generated from your {pantry.length} pantry items · Personalised for {userPrefs.servings} people</Text>
            </View>
          </View>
        )}

        <View style={[styles.px, isWeb ? { flexDirection:'row', flexWrap:'wrap', gap:12 } : styles.grid]}>
          {filtered.map(r => (
            <TouchableOpacity key={r.id} style={[styles.card, isWeb && { width: CARD_W }]}
              onPress={() => openRecipe(r)} activeOpacity={0.85}>
              <View style={[styles.cardTop, { backgroundColor: tagColor(r)+'18' }]}>
                <Text style={{ fontSize:52 }}>{r.emoji}</Text>
                <View style={[styles.tag, { backgroundColor: tagColor(r)+'25', borderColor: tagColor(r)+'60' }]}>
                  <Text style={[styles.tagText, { color: tagColor(r) }]}>{r.cuisine}</Text>
                </View>
                {r.match_score > 0 && (
                  <View style={styles.matchPill}>
                    <Text style={styles.matchText}>✓ {r.match_score > 1 ? r.match_score : Math.round(r.match_score * 100)}%</Text>
                  </View>
                )}
              </View>
              <View style={styles.cardBody}>
                <Text style={styles.cardName} numberOfLines={1}>{r.name}</Text>
                <Text style={styles.cardDesc} numberOfLines={1}>{r.description}</Text>
                <View style={styles.cardMeta}>
                  <View style={styles.metaPill}><Text style={styles.metaText}>⏱ {r.time_minutes}m</Text></View>
                  <View style={styles.metaPill}><Text style={styles.metaText}>{r.difficulty}</Text></View>
                  <View style={styles.metaPill}><Text style={[styles.metaText, { color: Colors.yellow }]}>★ {(r.match_score > 1 ? r.match_score : r.match_score * 100 / 20).toFixed(1)}</Text></View>
                </View>
              </View>
            </TouchableOpacity>
          ))}
        </View>

        {filtered.length === 0 && !loading && (
          <View style={styles.empty}>
            <Text style={{ fontSize:48 }}>🍽️</Text>
            <Text style={styles.emptyTitle}>No recipes found</Text>
            <Text style={styles.emptySub}>Try a different filter or generate new recipes</Text>
            <TouchableOpacity style={styles.emptyBtn} onPress={() => setShowServings(true)}>
              <Text style={styles.emptyBtnText}>✨ Generate Now</Text>
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>

      {/* Servings Picker Modal */}
      <Modal visible={showServings} transparent animationType="slide" onRequestClose={() => setShowServings(false)}>
        <TouchableOpacity style={styles.overlay} activeOpacity={1} onPress={() => setShowServings(false)} />
        <View style={styles.modal}>
          <Text style={styles.modalTitle}>How many people?</Text>
          <Text style={styles.modalSub}>Ingredient quantities will be adjusted automatically</Text>
          <View style={styles.servingsRow}>
            {[1,2,3,4,6,8].map(n => (
              <TouchableOpacity key={n} style={[styles.servingBtn, servings===n && styles.servingBtnOn]}
                onPress={() => setServings(n)}>
                <Text style={[styles.servingNum, servings===n && styles.servingNumOn]}>{n}</Text>
                <Text style={[styles.servingLabel, servings===n && styles.servingLabelOn]}>
                  {n === 1 ? 'Just me' : n === 2 ? 'Couple' : n <= 4 ? 'Family' : 'Party'}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
          <View style={styles.prefsRow}>
            <View style={styles.prefBadge}><Text style={styles.prefText}>🍽️ {userPrefs.dietary}</Text></View>
            <View style={styles.prefBadge}><Text style={styles.prefText}>🌶️ {userPrefs.spice}</Text></View>
            <TouchableOpacity style={[styles.prefBadge, { borderColor: Colors.accent+'60' }]} onPress={() => { setShowServings(false); router.push('/(tabs)/profile') }}>
              <Text style={[styles.prefText, { color: Colors.accent }]}>Edit prefs →</Text>
            </TouchableOpacity>
          </View>
          <TouchableOpacity style={styles.generateBtn} onPress={() => doGenerate(servings)} activeOpacity={0.88}>
            <Text style={styles.generateBtnText}>✨ Generate for {servings} {servings === 1 ? 'person' : 'people'}</Text>
          </TouchableOpacity>
        </View>
      </Modal>
    </View>
  )
}

const styles = StyleSheet.create({
  root:           { flex:1, backgroundColor: Colors.bg },
  px:             { paddingHorizontal: S.base },
  header:         { flexDirection:'row', justifyContent:'space-between', alignItems:'center', paddingHorizontal: S.base, paddingTop: S.lg, paddingBottom: S.xl },
  title:          { fontSize:32, fontWeight:'800', color: Colors.text },
  genBtn:         { flexDirection:'row', alignItems:'center', gap:6, backgroundColor: Colors.purpleDim, borderWidth:1, borderColor: Colors.purple+'55', borderRadius: R.full, paddingHorizontal:16, paddingVertical:9 },
  genText:        { fontSize:13, fontWeight:'700', color: Colors.purple },
  searchBox:      { flexDirection:'row', alignItems:'center', backgroundColor: Colors.surface, borderWidth:1, borderColor: Colors.border2, borderRadius: R.lg, paddingHorizontal: S.base, paddingVertical:12 },
  searchInput:    { flex:1, fontSize:15, color: Colors.text },
  pill:           { flexDirection:'row', alignItems:'center', gap:5, paddingHorizontal:14, paddingVertical:8, borderRadius: R.full, backgroundColor: Colors.surface, borderWidth:1, borderColor: Colors.border2 },
  pillOn:         { backgroundColor: Colors.accentGlow, borderColor:'rgba(255,87,34,0.45)' },
  pillLabel:      { fontSize:13, fontWeight:'600', color: Colors.text2 },
  pillLabelOn:    { color: Colors.accent },
  aiNote:         { flexDirection:'row', alignItems:'center', gap:8, backgroundColor: Colors.purpleDim, borderRadius: R.lg, padding: S.md },
  aiNoteText:     { flex:1, fontSize:12, color: Colors.purple, fontWeight:'600' },
  grid:           { flexDirection:'row', flexWrap:'wrap', gap:12 },
  card:           { width: (width - S.base * 2 - 12) / 2, backgroundColor: Colors.bg3, borderRadius: R.xl, borderWidth:1, borderColor: Colors.border2, overflow:'hidden' },
  cardTop:        { height:130, alignItems:'center', justifyContent:'center', position:'relative' },
  tag:            { position:'absolute', top:8, right:8, borderWidth:1, borderRadius: R.full, paddingHorizontal:8, paddingVertical:3 },
  tagText:        { fontSize:10, fontWeight:'700' },
  matchPill:      { position:'absolute', bottom:8, left:8, backgroundColor: Colors.green+'22', borderRadius: R.full, paddingHorizontal:8, paddingVertical:3 },
  matchText:      { fontSize:11, fontWeight:'700', color: Colors.green },
  cardBody:       { padding:12 },
  cardName:       { fontSize:14, fontWeight:'800', color: Colors.text, marginBottom:3 },
  cardDesc:       { fontSize:11, color: Colors.text2, marginBottom:8 },
  cardMeta:       { flexDirection:'row', gap:5, flexWrap:'wrap' },
  metaPill:       { backgroundColor: Colors.surface2, borderRadius: R.full, paddingHorizontal:7, paddingVertical:3 },
  metaText:       { fontSize:10, fontWeight:'600', color: Colors.text2 },
  empty:          { alignItems:'center', paddingVertical: 60, gap: S.md },
  emptyTitle:     { fontSize:20, fontWeight:'800', color: Colors.text },
  emptySub:       { fontSize:14, color: Colors.text2 },
  emptyBtn:       { backgroundColor: Colors.accent, borderRadius: R.full, paddingHorizontal:24, paddingVertical:12, marginTop: S.sm },
  emptyBtnText:   { color:'#fff', fontWeight:'800', fontSize:15 },
  overlay:        { flex:1, backgroundColor:'rgba(0,0,0,0.6)' },
  modal:          { backgroundColor: Colors.bg2, borderTopLeftRadius:28, borderTopRightRadius:28, padding: S.xl, paddingBottom:40, gap: S.base },
  modalTitle:     { fontSize:24, fontWeight:'800', color: Colors.text, textAlign:'center' },
  modalSub:       { fontSize:13, color: Colors.text2, textAlign:'center', marginTop:-4 },
  servingsRow:    { flexDirection:'row', flexWrap:'wrap', gap:10, justifyContent:'center', marginVertical: S.sm },
  servingBtn:     { width:90, backgroundColor: Colors.bg3, borderWidth:1.5, borderColor: Colors.border2, borderRadius: R.lg, padding:12, alignItems:'center', gap:3 },
  servingBtnOn:   { borderColor: Colors.accent, backgroundColor: Colors.accentGlow },
  servingNum:     { fontSize:26, fontWeight:'800', color: Colors.text2 },
  servingNumOn:   { color: Colors.accent },
  servingLabel:   { fontSize:10, color: Colors.text3, fontWeight:'600' },
  servingLabelOn: { color: Colors.accent },
  prefsRow:       { flexDirection:'row', gap:8, flexWrap:'wrap' },
  prefBadge:      { backgroundColor: Colors.surface, borderWidth:1, borderColor: Colors.border2, borderRadius: R.full, paddingHorizontal:12, paddingVertical:6 },
  prefText:       { fontSize:12, fontWeight:'600', color: Colors.text2 },
  generateBtn:    { backgroundColor: Colors.accent, borderRadius: R.xl, paddingVertical:18, alignItems:'center', marginTop: S.sm },
  generateBtnText:{ fontSize:17, fontWeight:'800', color:'#fff' },
})
''')


# ─── PROFILE — working settings with modals ─────────────────
w("app/(tabs)/profile.tsx", '''\
import { useState } from 'react'
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, Switch, Alert, Modal, Share, Linking } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { router } from 'expo-router'
import { Colors, S, R } from '../../constants/theme'
import { useStore } from '../../store'
import { supabase } from '../../lib/supabase'

const DIETARY_OPTIONS = ['All', 'Vegetarian', 'Vegan', 'Non-Veg', 'Gluten-Free', 'Keto']
const SPICE_OPTIONS = ['Mild', 'Medium', 'Hot', 'Extra Hot']
const CUISINE_OPTIONS = ['all', 'indian', 'south-indian', 'asian', 'continental', 'middle-eastern', 'american']
const CUISINE_LABELS: Record<string,string> = { all:'All', indian:'Indian', 'south-indian':'South Indian', asian:'Asian', continental:'Continental', 'middle-eastern':'Middle Eastern', american:'American' }

export default function ProfileScreen() {
  const insets = useSafeAreaInsets()
  const { user, setUser, pantry, cookHistory, tasteProfile, userPrefs, setUserPrefs } = useStore()
  const [notifs, setNotifs] = useState(true)
  const [showDietary, setShowDietary] = useState(false)
  const [showSpice, setShowSpice] = useState(false)
  const [showCuisines, setShowCuisines] = useState(false)

  async function handleSignOut() {
    Alert.alert('Sign Out', 'Are you sure?', [
      { text:'Cancel', style:'cancel' },
      { text:'Sign Out', style:'destructive', onPress: async () => {
        await supabase.auth.signOut(); setUser(null)
      }},
    ])
  }

  async function handleShare() {
    try {
      await Share.share({ message: 'Check out CookMate AI — scan ingredients and get instant AI recipes! Download now.' })
    } catch {}
  }

  function handlePrivacy() {
    Linking.openURL('https://cookmate-ai.vercel.app/privacy')
  }

  function toggleCuisine(id: string) {
    let current = [...userPrefs.cuisines]
    if (id === 'all') { setUserPrefs({ cuisines: ['all'] }); return }
    current = current.filter(c => c !== 'all')
    if (current.includes(id)) {
      current = current.filter(c => c !== id)
      if (current.length === 0) current = ['all']
    } else {
      current.push(id)
    }
    setUserPrefs({ cuisines: current })
  }

  const cuisineDisplay = userPrefs.cuisines.includes('all') ? 'All' : userPrefs.cuisines.map(c => CUISINE_LABELS[c] ?? c).join(', ')

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom:100 }}>

        {/* Avatar */}
        <View style={styles.hero}>
          <View style={styles.ring}>
            <View style={styles.avatarBox}>
              <Text style={{ fontSize:44 }}>👨‍🍳</Text>
            </View>
          </View>
          <Text style={styles.name}>{user?.name ?? 'Welcome, Chef!'}</Text>
          <Text style={styles.email}>{user?.email ?? 'Sign in to save your data'}</Text>
          <View style={styles.statsRow}>
            {[
              { v: String(pantry.length), l:'PANTRY', c: Colors.green },
              { v: String(tasteProfile.totalCooked), l:'COOKED', c: Colors.accent },
              { v: String(tasteProfile.preferredCuisines.length || userPrefs.cuisines.length), l:'CUISINES', c: Colors.purple },
            ].map((s,i,a) => (
              <View key={s.l} style={{ alignItems:'center', flex:1, borderRightWidth: i<a.length-1 ? 1 : 0, borderColor: Colors.border2 }}>
                <Text style={[styles.statVal, { color: s.c }]}>{s.v}</Text>
                <Text style={styles.statLabel}>{s.l}</Text>
              </View>
            ))}
          </View>
        </View>

        {/* Taste Insight */}
        {tasteProfile.totalCooked > 0 && (
          <View style={[styles.px, { marginBottom: S.lg }]}>
            <View style={styles.insightCard}>
              <Text style={{ fontSize:20 }}>🧠</Text>
              <View style={{ flex:1 }}>
                <Text style={styles.insightTitle}>Your Taste Profile</Text>
                <Text style={styles.insightText}>{tasteProfile.tasteInsight}</Text>
                {tasteProfile.favoriteDishes.length > 0 && (
                  <Text style={styles.insightSub}>Loves: {tasteProfile.favoriteDishes.slice(0,3).join(' · ')}</Text>
                )}
              </View>
            </View>
          </View>
        )}

        {/* Cook History */}
        {cookHistory.length > 0 && (
          <View style={[styles.px, { marginBottom: S.lg }]}>
            <Text style={styles.sectionLabel}>Recent Cooks</Text>
            <View style={styles.card}>
              {cookHistory.slice(-5).reverse().map((h, i, a) => (
                <View key={h.id} style={[styles.row, i<a.length-1 && styles.rowBorder]}>
                  <Text style={{ fontSize:24, marginRight:12 }}>{h.recipeEmoji}</Text>
                  <View style={{ flex:1 }}>
                    <Text style={styles.rowLabel}>{h.recipeName}</Text>
                    <Text style={{ fontSize:11, color: Colors.text2 }}>{h.cuisine} · {new Date(h.cookedAt).toLocaleDateString()}</Text>
                  </View>
                  <View style={styles.doneBadge}><Text style={styles.doneText}>✓</Text></View>
                </View>
              ))}
            </View>
          </View>
        )}

        {/* Pro Banner */}
        <View style={[styles.px, { marginBottom: S.lg }]}>
          <TouchableOpacity style={styles.proBanner} activeOpacity={0.88}
            onPress={() => Alert.alert('CookMate Pro', 'Coming soon! Get unlimited scans, meal planning, and advanced nutrition tracking.')}>
            <View style={styles.proLeft}>
              <View style={styles.proIconBox}><Text style={{ fontSize:22 }}>⚡</Text></View>
              <View>
                <Text style={styles.proTitle}>Upgrade to Pro</Text>
                <Text style={styles.proSub}>Unlimited scans · Meal plans · Nutrition</Text>
              </View>
            </View>
            <View style={styles.priceBox}>
              <Text style={styles.priceVal}>₹299</Text>
              <Text style={styles.pricePer}>/mo</Text>
            </View>
          </TouchableOpacity>
        </View>

        {/* Preferences */}
        <View style={[styles.px, { marginBottom: S.lg }]}>
          <Text style={styles.sectionLabel}>Preferences</Text>
          <View style={styles.card}>
            <TouchableOpacity style={[styles.row, styles.rowBorder]} onPress={() => setShowDietary(true)}>
              <View style={[styles.iconBox, { backgroundColor: Colors.green+'18' }]}><Text style={{ fontSize:18 }}>🍽️</Text></View>
              <Text style={styles.rowLabel}>Dietary</Text>
              <Text style={[styles.rowVal, { color: Colors.green }]}>{userPrefs.dietary}</Text>
              <Text style={styles.chevron}>›</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[styles.row, styles.rowBorder]} onPress={() => setShowSpice(true)}>
              <View style={[styles.iconBox, { backgroundColor: Colors.accent+'18' }]}><Text style={{ fontSize:18 }}>🌶️</Text></View>
              <Text style={styles.rowLabel}>Spice Level</Text>
              <Text style={[styles.rowVal, { color: Colors.accent }]}>{userPrefs.spice}</Text>
              <Text style={styles.chevron}>›</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[styles.row, styles.rowBorder]} onPress={() => setShowCuisines(true)}>
              <View style={[styles.iconBox, { backgroundColor: Colors.cyan+'18' }]}><Text style={{ fontSize:18 }}>🌍</Text></View>
              <Text style={styles.rowLabel}>Cuisines</Text>
              <Text style={[styles.rowVal, { color: Colors.cyan }]} numberOfLines={1}>{cuisineDisplay}</Text>
              <Text style={styles.chevron}>›</Text>
            </TouchableOpacity>
            <View style={styles.row}>
              <View style={[styles.iconBox, { backgroundColor: Colors.yellow+'18' }]}><Text style={{ fontSize:18 }}>🔔</Text></View>
              <Text style={styles.rowLabel}>Notifications</Text>
              <Switch value={notifs} onValueChange={setNotifs} trackColor={{ false: Colors.surface2, true: Colors.accent }} thumbColor="#fff" />
            </View>
          </View>
        </View>

        {/* Auth */}
        <View style={[styles.px, { marginBottom: S.lg }]}>
          {user ? (
            <TouchableOpacity style={styles.signOutBtn} onPress={handleSignOut}>
              <Text style={styles.signOutText}>Sign Out</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity style={styles.signInBtn} onPress={() => router.push('/auth')} activeOpacity={0.88}>
              <Text style={{ fontSize:20 }}>🔑</Text>
              <Text style={styles.signInText}>Sign In / Create Account</Text>
            </TouchableOpacity>
          )}
        </View>

        {/* About */}
        <View style={[styles.px, { marginBottom: S.lg }]}>
          <Text style={styles.sectionLabel}>About</Text>
          <View style={styles.card}>
            <TouchableOpacity style={[styles.row, styles.rowBorder]}
              onPress={() => Linking.openURL('https://play.google.com/store')}>
              <Text style={{ fontSize:20, marginRight:14 }}>⭐</Text>
              <Text style={styles.rowLabel}>Rate CookMate</Text>
              <Text style={styles.chevron}>›</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[styles.row, styles.rowBorder]} onPress={handleShare}>
              <Text style={{ fontSize:20, marginRight:14 }}>📤</Text>
              <Text style={styles.rowLabel}>Share App</Text>
              <Text style={styles.chevron}>›</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[styles.row, styles.rowBorder]} onPress={handlePrivacy}>
              <Text style={{ fontSize:20, marginRight:14 }}>🔒</Text>
              <Text style={styles.rowLabel}>Privacy Policy</Text>
              <Text style={styles.chevron}>›</Text>
            </TouchableOpacity>
            <View style={styles.row}>
              <Text style={{ fontSize:20, marginRight:14 }}>ℹ️</Text>
              <Text style={styles.rowLabel}>Version</Text>
              <Text style={[styles.rowVal, { color: Colors.text3 }]}>1.0.0</Text>
            </View>
          </View>
        </View>
      </ScrollView>

      {/* Dietary Modal */}
      <Modal visible={showDietary} transparent animationType="slide" onRequestClose={() => setShowDietary(false)}>
        <TouchableOpacity style={styles.overlay} activeOpacity={1} onPress={() => setShowDietary(false)} />
        <View style={styles.modal}>
          <Text style={styles.modalTitle}>Dietary Preference</Text>
          {DIETARY_OPTIONS.map(opt => (
            <TouchableOpacity key={opt} style={[styles.optRow, userPrefs.dietary===opt && styles.optRowOn]}
              onPress={() => { setUserPrefs({ dietary: opt }); setShowDietary(false) }}>
              <Text style={[styles.optText, userPrefs.dietary===opt && styles.optTextOn]}>{opt}</Text>
              {userPrefs.dietary===opt && <Text style={{ color: Colors.accent, fontSize:18 }}>✓</Text>}
            </TouchableOpacity>
          ))}
        </View>
      </Modal>

      {/* Spice Modal */}
      <Modal visible={showSpice} transparent animationType="slide" onRequestClose={() => setShowSpice(false)}>
        <TouchableOpacity style={styles.overlay} activeOpacity={1} onPress={() => setShowSpice(false)} />
        <View style={styles.modal}>
          <Text style={styles.modalTitle}>Spice Level</Text>
          {SPICE_OPTIONS.map(opt => (
            <TouchableOpacity key={opt} style={[styles.optRow, userPrefs.spice===opt && styles.optRowOn]}
              onPress={() => { setUserPrefs({ spice: opt }); setShowSpice(false) }}>
              <Text style={[styles.optText, userPrefs.spice===opt && styles.optTextOn]}>{opt}</Text>
              {userPrefs.spice===opt && <Text style={{ color: Colors.accent, fontSize:18 }}>✓</Text>}
            </TouchableOpacity>
          ))}
        </View>
      </Modal>

      {/* Cuisines Modal */}
      <Modal visible={showCuisines} transparent animationType="slide" onRequestClose={() => setShowCuisines(false)}>
        <TouchableOpacity style={styles.overlay} activeOpacity={1} onPress={() => setShowCuisines(false)} />
        <View style={styles.modal}>
          <Text style={styles.modalTitle}>Preferred Cuisines</Text>
          <Text style={styles.modalSub}>Select one or more</Text>
          {CUISINE_OPTIONS.map(id => {
            const on = userPrefs.cuisines.includes(id)
            return (
              <TouchableOpacity key={id} style={[styles.optRow, on && styles.optRowOn]} onPress={() => toggleCuisine(id)}>
                <Text style={[styles.optText, on && styles.optTextOn]}>{CUISINE_LABELS[id]}</Text>
                {on && <Text style={{ color: Colors.accent, fontSize:18 }}>✓</Text>}
              </TouchableOpacity>
            )
          })}
          <TouchableOpacity style={styles.doneBtn} onPress={() => setShowCuisines(false)}>
            <Text style={styles.doneBtnText}>Done</Text>
          </TouchableOpacity>
        </View>
      </Modal>
    </View>
  )
}

const styles = StyleSheet.create({
  root:        { flex:1, backgroundColor: Colors.bg },
  px:          { paddingHorizontal: S.base },
  hero:        { alignItems:'center', paddingTop: S.xl, paddingBottom: S.xl, paddingHorizontal: S.base },
  ring:        { width:100, height:100, borderRadius:50, borderWidth:2.5, borderColor: Colors.accent, alignItems:'center', justifyContent:'center', marginBottom: S.md },
  avatarBox:   { width:88, height:88, borderRadius:44, backgroundColor: Colors.surface, alignItems:'center', justifyContent:'center' },
  name:        { fontSize:24, fontWeight:'800', color: Colors.text, marginBottom:4 },
  email:       { fontSize:13, color: Colors.text2, marginBottom: S.xl },
  statsRow:    { flexDirection:'row', width:'100%', backgroundColor: Colors.bg3, borderWidth:1, borderColor: Colors.border2, borderRadius: R.xl, paddingVertical: S.base },
  statVal:     { fontSize:26, fontWeight:'800' },
  statLabel:   { fontSize:9, fontWeight:'700', color: Colors.text3, letterSpacing:1, marginTop:2 },
  insightCard: { flexDirection:'row', alignItems:'center', gap:12, backgroundColor: Colors.purpleDim, borderWidth:1, borderColor: Colors.purple+'44', borderRadius: R.xl, padding: S.base },
  insightTitle:{ fontSize:13, fontWeight:'700', color: Colors.purple, marginBottom:3 },
  insightText: { fontSize:13, color: Colors.text, lineHeight:18 },
  insightSub:  { fontSize:11, color: Colors.text2, marginTop:4 },
  proBanner:   { flexDirection:'row', alignItems:'center', backgroundColor: Colors.bg3, borderWidth:1.5, borderColor: Colors.purple+'55', borderRadius: R.xl, padding: S.base },
  proLeft:     { flexDirection:'row', alignItems:'center', gap:12, flex:1 },
  proIconBox:  { width:44, height:44, borderRadius: R.md, backgroundColor: Colors.purpleDim, alignItems:'center', justifyContent:'center' },
  proTitle:    { fontSize:16, fontWeight:'800', color: Colors.text },
  proSub:      { fontSize:11, color: Colors.text2, marginTop:2 },
  priceBox:    { flexDirection:'row', alignItems:'flex-end', gap:1 },
  priceVal:    { fontSize:22, fontWeight:'800', color: Colors.purple },
  pricePer:    { fontSize:11, color: Colors.text2, marginBottom:3 },
  sectionLabel:{ fontSize:11, fontWeight:'700', letterSpacing:1.2, textTransform:'uppercase', color: Colors.text3, marginBottom: S.md },
  card:        { backgroundColor: Colors.bg3, borderWidth:1, borderColor: Colors.border2, borderRadius: R.xl, overflow:'hidden' },
  row:         { flexDirection:'row', alignItems:'center', paddingHorizontal: S.base, paddingVertical:14 },
  rowBorder:   { borderBottomWidth:1, borderBottomColor: Colors.border },
  iconBox:     { width:38, height:38, borderRadius: R.sm, alignItems:'center', justifyContent:'center', marginRight:12 },
  rowLabel:    { flex:1, fontSize:15, fontWeight:'600', color: Colors.text },
  rowVal:      { fontSize:13, fontWeight:'700', maxWidth:120 },
  chevron:     { color: Colors.text3, fontSize:20, marginLeft:6 },
  doneBadge:   { width:28, height:28, borderRadius:14, backgroundColor: Colors.greenDim, alignItems:'center', justifyContent:'center' },
  doneText:    { color: Colors.green, fontWeight:'800', fontSize:14 },
  signInBtn:   { flexDirection:'row', alignItems:'center', justifyContent:'center', gap:12, backgroundColor: Colors.accent, borderRadius: R.xl, paddingVertical:18 },
  signInText:  { fontSize:17, fontWeight:'800', color:'#fff' },
  signOutBtn:  { alignItems:'center', backgroundColor: Colors.redDim, borderWidth:1, borderColor: Colors.red+'44', borderRadius: R.xl, paddingVertical:16 },
  signOutText: { fontSize:16, fontWeight:'700', color: Colors.red },
  overlay:     { flex:1, backgroundColor:'rgba(0,0,0,0.6)' },
  modal:       { backgroundColor: Colors.bg2, borderTopLeftRadius:28, borderTopRightRadius:28, padding: S.xl, paddingBottom:40, gap: S.sm },
  modalTitle:  { fontSize:22, fontWeight:'800', color: Colors.text, marginBottom:4 },
  modalSub:    { fontSize:13, color: Colors.text2, marginBottom: S.sm },
  optRow:      { flexDirection:'row', alignItems:'center', justifyContent:'space-between', paddingVertical:14, paddingHorizontal: S.base, borderRadius: R.lg },
  optRowOn:    { backgroundColor: Colors.accentGlow },
  optText:     { fontSize:16, color: Colors.text2, fontWeight:'600' },
  optTextOn:   { color: Colors.accent, fontWeight:'800' },
  doneBtn:     { backgroundColor: Colors.accent, borderRadius: R.xl, paddingVertical:14, alignItems:'center', marginTop: S.sm },
  doneBtnText: { color:'#fff', fontWeight:'800', fontSize:16 },
})
''')


print("\n✅ All files written!")
print("\nRun these now:")
print("  npx expo start --clear")
print("  Press w for browser, or scan QR for phone")
print("\nWhat's fixed:")
print("  ✓ Servings picker before every generate (1/2/3/4/6/8 people)")
print("  ✓ Dietary preference — tappable modal, saves instantly")
print("  ✓ Spice Level — tappable modal, saves instantly")
print("  ✓ Cuisines — multi-select modal, saves instantly")
print("  ✓ All prefs persist across app restarts (AsyncStorage)")
print("  ✓ Pantry persists across restarts")
print("  ✓ Share App — native share sheet")
print("  ✓ Privacy Policy — opens browser")
print("  ✓ Rate CookMate — opens app store")
print("  ✓ Upgrade to Pro — shows coming soon alert")
print("  ✓ Cuisines count in profile reflects real preferences")
