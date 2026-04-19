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
