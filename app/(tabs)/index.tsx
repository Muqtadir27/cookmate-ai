import { useState, useEffect } from 'react'
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, Dimensions, Platform, ActivityIndicator } from 'react-native'
import { router } from 'expo-router'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { Colors, S, R } from '../../constants/theme'
import { useStore } from '../../store'
import { generateRecipes } from '../../lib/gemini'

const { width } = Dimensions.get('window')
const isWeb = Platform.OS === 'web'
const CARD_W = isWeb ? 200 : (width - S.base * 2 - 12) / 2

const CUISINES = [
  { l:'All', e:'⭐', id:'all' }, { l:'Indian', e:'🇮🇳', id:'indian' },
  { l:'Asian', e:'🍜', id:'asian' }, { l:'Quick', e:'⚡', id:'quick' },
  { l:'Veg', e:'🥗', id:'veg' }, { l:'Street', e:'🛺', id:'street' },
]

export default function HomeScreen() {
  const insets = useSafeAreaInsets()
  const { user, pantry, recipes, setRecipes, setActiveRecipe, setLoading, loading, tasteProfile } = useStore()
  const [activeCuisine, setActiveCuisine] = useState('all')
  const h = new Date().getHours()
  const greeting = h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening'

  const displayRecipes = recipes.length > 0 ? recipes : []

  async function handleGenerate() {
    if (pantry.length === 0) { router.push('/scan'); return }
    setLoading(true)
    try {
      const r = await generateRecipes(
        pantry,
        { cuisines: [activeCuisine], dietary: user?.dietary_preference ?? 'all', spice: user?.spice_level ?? 'medium', servings: 2 },
        tasteProfile
      )
      setRecipes(r)
      router.push('/recipes')
    } catch (e: any) {
      console.error(e)
    } finally { setLoading(false) }
  }

  function openRecipe(r: any) {
    setActiveRecipe(r)
    router.push(`/cook/${r.id}`)
  }

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: 100 }}>

        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>{greeting} 👋</Text>
            <Text style={styles.title}>What shall we</Text>
            <Text style={styles.title}>cook <Text style={styles.accent}>today?</Text></Text>
          </View>
          <TouchableOpacity style={styles.avatar} onPress={() => router.push('/profile')}>
            <Text style={{ fontSize: 22 }}>👨‍🍳</Text>
          </TouchableOpacity>
        </View>

        {/* Scan CTA */}
        <View style={styles.px}>
          <TouchableOpacity style={styles.scanCard} onPress={() => router.push('/scan')} activeOpacity={0.88}>
            <View style={styles.scanLeft}>
              <View style={styles.scanIcon}><Text style={{ fontSize: 28 }}>📸</Text></View>
              <View>
                <Text style={styles.scanTitle}>Scan Ingredients</Text>
                <Text style={styles.scanSub}>AI detects & generates recipes instantly</Text>
              </View>
            </View>
            <View style={styles.scanArrow}><Text style={{ color:'#fff', fontSize:18, fontWeight:'800' }}>→</Text></View>
          </TouchableOpacity>
        </View>

        {/* Stats */}
        <View style={[styles.px, { flexDirection:'row', gap:10, marginBottom: S.lg }]}>
          {[
            { v: String(pantry.length || 0), label:'In Pantry',  color: Colors.green,  emoji:'🧺', onPress: () => router.push('/pantry') },
            { v: String(recipes.length || 0),label:'Recipes',    color: Colors.purple, emoji:'📖', onPress: () => router.push('/recipes') },
            { v: String(tasteProfile.totalCooked), label:'Cooked', color: Colors.cyan, emoji:'🍳', onPress: () => router.push('/profile') },
          ].map(s => (
            <TouchableOpacity key={s.label} style={[styles.statCard, { flex:1 }]} onPress={s.onPress}>
              <Text style={{ fontSize:18 }}>{s.emoji}</Text>
              <Text style={[styles.statVal, { color:s.color }]}>{s.v}</Text>
              <Text style={styles.statLabel}>{s.label}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Cuisine Pills */}
        <View style={{ marginBottom: S.lg }}>
          <Text style={[styles.section, { marginHorizontal: S.base }]}>Cuisines</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingHorizontal: S.base, gap:8 }}>
            {CUISINES.map(c => (
              <TouchableOpacity key={c.id} style={[styles.pill, activeCuisine===c.id && styles.pillOn]} onPress={() => setActiveCuisine(c.id)}>
                <Text style={{ fontSize:14 }}>{c.e}</Text>
                <Text style={[styles.pillLabel, activeCuisine===c.id && styles.pillLabelOn]}>{c.l}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>

        {/* Recipes or Generate CTA */}
        <View style={styles.px}>
          <View style={styles.rowBetween}>
            <Text style={styles.section}>
              {displayRecipes.length > 0 ? 'Your AI Recipes' : 'Ready to Cook'}
            </Text>
            <TouchableOpacity onPress={() => router.push('/recipes')}>
              <Text style={styles.seeAll}>See all →</Text>
            </TouchableOpacity>
          </View>

          {displayRecipes.length > 0 ? (
            <ScrollView horizontal={isWeb} showsHorizontalScrollIndicator={false}>
              <View style={isWeb ? { flexDirection:'row', gap:12 } : styles.grid}>
                {displayRecipes.slice(0,4).map(r => (
                  <TouchableOpacity key={r.id} style={[styles.recipeCard, isWeb && { width: CARD_W }]}
                    onPress={() => openRecipe(r)} activeOpacity={0.85}>
                    <View style={[styles.recipeImg, { backgroundColor: Colors.accent+'22' }]}>
                      <Text style={{ fontSize:44 }}>{r.emoji}</Text>
                      <View style={[styles.matchBadge, { backgroundColor: Colors.green+'22' }]}>
                        <Text style={[styles.matchText, { color: Colors.green }]}>✓ {r.match_score > 1 ? r.match_score : Math.round(r.match_score * 100)}%</Text>
                      </View>
                    </View>
                    <View style={styles.recipeBody}>
                      <Text style={styles.recipeName} numberOfLines={1}>{r.name}</Text>
                      <View style={{ flexDirection:'row', gap:6, marginTop:4 }}>
                        <View style={styles.timeBadge}><Text style={styles.timeText}>⏱ {r.time_minutes}m</Text></View>
                        <View style={styles.timeBadge}><Text style={styles.timeText}>{r.difficulty}</Text></View>
                      </View>
                    </View>
                    <View style={[styles.accentBar, { backgroundColor: Colors.accent }]} />
                  </TouchableOpacity>
                ))}
              </View>
            </ScrollView>
          ) : (
            <TouchableOpacity style={styles.generateCta} onPress={handleGenerate} activeOpacity={0.88} disabled={loading}>
              {loading ? <ActivityIndicator color="#fff" /> : <Text style={{ fontSize:28 }}>✨</Text>}
              <View>
                <Text style={styles.generateTitle}>{loading ? 'Generating recipes...' : 'Generate AI Recipes'}</Text>
                <Text style={styles.generateSub}>
                  {pantry.length > 0 ? `Using ${pantry.length} pantry items` : 'Scan ingredients first'}
                </Text>
              </View>
            </TouchableOpacity>
          )}
        </View>

        {/* Taste Profile Insight */}
        {tasteProfile.totalCooked > 0 && (
          <View style={[styles.px, { marginTop: S.lg }]}>
            <View style={styles.insightCard}>
              <Text style={{ fontSize:20 }}>🧠</Text>
              <View style={{ flex:1 }}>
                <Text style={styles.insightTitle}>Your Taste Profile</Text>
                <Text style={styles.insightText}>{tasteProfile.tasteInsight}</Text>
                <Text style={styles.insightSub}>{tasteProfile.totalCooked} dishes cooked · {tasteProfile.preferredCuisines.slice(0,2).join(', ') || 'all cuisines'}</Text>
              </View>
            </View>
          </View>
        )}

      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  root:          { flex:1, backgroundColor: Colors.bg },
  px:            { paddingHorizontal: S.base, marginBottom: S.base },
  header:        { flexDirection:'row', justifyContent:'space-between', alignItems:'flex-start', paddingHorizontal: S.base, paddingTop: S.lg, paddingBottom: S.xl },
  greeting:      { fontSize:13, fontWeight:'500', color: Colors.text2, marginBottom:4 },
  title:         { fontSize:34, fontWeight:'800', color: Colors.text, letterSpacing:-0.8, lineHeight:40 },
  accent:        { color: Colors.accent },
  avatar:        { width:46, height:46, borderRadius:R.full, backgroundColor: Colors.surface, borderWidth:1.5, borderColor: Colors.border2, alignItems:'center', justifyContent:'center' },
  scanCard:      { flexDirection:'row', alignItems:'center', justifyContent:'space-between', backgroundColor: Colors.accent, borderRadius: R.xl, padding: S.base, marginBottom: S.base },
  scanLeft:      { flexDirection:'row', alignItems:'center', gap:12, flex:1 },
  scanIcon:      { width:52, height:52, backgroundColor:'rgba(255,255,255,0.2)', borderRadius: R.md, alignItems:'center', justifyContent:'center' },
  scanTitle:     { fontSize:16, fontWeight:'800', color:'#fff', marginBottom:2 },
  scanSub:       { fontSize:11, color:'rgba(255,255,255,0.75)' },
  scanArrow:     { width:36, height:36, borderRadius:R.full, backgroundColor:'rgba(255,255,255,0.25)', alignItems:'center', justifyContent:'center' },
  statCard:      { backgroundColor: Colors.bg3, borderWidth:1, borderColor: Colors.border2, borderRadius: R.lg, padding: S.md, alignItems:'center', gap:4 },
  statVal:       { fontSize:22, fontWeight:'800' },
  statLabel:     { fontSize:10, color: Colors.text2, fontWeight:'600' },
  rowBetween:    { flexDirection:'row', justifyContent:'space-between', alignItems:'center', marginBottom: S.md },
  section:       { fontSize:11, fontWeight:'700', letterSpacing:1.2, textTransform:'uppercase', color: Colors.text3, marginBottom: S.md },
  seeAll:        { fontSize:13, fontWeight:'600', color: Colors.accent },
  pill:          { flexDirection:'row', alignItems:'center', gap:5, paddingHorizontal:14, paddingVertical:8, borderRadius: R.full, backgroundColor: Colors.surface, borderWidth:1, borderColor: Colors.border2 },
  pillOn:        { backgroundColor: Colors.accentGlow, borderColor:'rgba(255,87,34,0.45)' },
  pillLabel:     { fontSize:13, fontWeight:'600', color: Colors.text2 },
  pillLabelOn:   { color: Colors.accent },
  grid:          { flexDirection:'row', flexWrap:'wrap', gap:12 },
  recipeCard:    { width: CARD_W, backgroundColor: Colors.bg3, borderWidth:1, borderColor: Colors.border2, borderRadius: R.xl, overflow:'hidden' },
  recipeImg:     { height:120, alignItems:'center', justifyContent:'center', position:'relative' },
  matchBadge:    { position:'absolute', bottom:6, right:6, borderRadius:R.full, paddingHorizontal:8, paddingVertical:3 },
  matchText:     { fontSize:10, fontWeight:'700' },
  recipeBody:    { padding:12 },
  recipeName:    { fontSize:14, fontWeight:'700', color: Colors.text },
  timeBadge:     { backgroundColor: Colors.surface2, borderRadius: R.full, paddingHorizontal:8, paddingVertical:3 },
  timeText:      { fontSize:10, fontWeight:'600', color: Colors.text2 },
  accentBar:     { height:3, position:'absolute', bottom:0, left:0, right:0 },
  generateCta:   { flexDirection:'row', alignItems:'center', gap:16, backgroundColor: Colors.bg3, borderWidth:1.5, borderColor: Colors.purple+'55', borderRadius: R.xl, padding: S.lg },
  generateTitle: { fontSize:16, fontWeight:'800', color: Colors.text },
  generateSub:   { fontSize:12, color: Colors.text2, marginTop:2 },
  insightCard:   { flexDirection:'row', alignItems:'center', gap:12, backgroundColor: Colors.purpleDim, borderWidth:1, borderColor: Colors.purple+'44', borderRadius: R.xl, padding: S.base },
  insightTitle:  { fontSize:13, fontWeight:'700', color: Colors.purple, marginBottom:3 },
  insightText:   { fontSize:13, color: Colors.text, lineHeight:18 },
  insightSub:    { fontSize:11, color: Colors.text2, marginTop:4 },
})
