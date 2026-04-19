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
              <Text style={styles.aiNoteText}>Generated from your {pantry.length} pantry items · Personalised for {servings} people</Text>
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
