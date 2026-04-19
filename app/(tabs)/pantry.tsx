import { useState } from 'react'
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, TextInput, Modal, Alert } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { Colors, S, R } from '../../constants/theme'
import { useStore } from '../../store'
import { PantryItem } from '../../types'

const CATS = [
  { id:'all',      l:'All',      e:'🗂️' }, { id:'proteins', l:'Proteins', e:'🍖' },
  { id:'veggies',  l:'Veggies',  e:'🥦' }, { id:'grains',   l:'Grains',   e:'🌾' },
  { id:'spices',   l:'Spices',   e:'🫙' }, { id:'dairy',    l:'Dairy',    e:'🥛' },
  { id:'oils',     l:'Oils',     e:'🫒' },
]

const CAT_COLORS: Record<string,string> = {
  proteins:'#FC8181', veggies:'#68D391', grains:'#76E4F7',
  spices:'#FF5722', dairy:'#F6E05E', oils:'#00E5A0', other:'#B794F4',
}

const EMOJI_MAP: Record<string,string> = {
  proteins:'🍖', veggies:'🥦', grains:'🌾', spices:'🫙', dairy:'🥛', oils:'🫒', other:'📦'
}

export default function PantryScreen() {
  const insets = useSafeAreaInsets()
  const { pantry, addPantryItem, removePantryItem, user } = useStore()
  const [active, setActive] = useState('all')
  const [search, setSearch] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState({ name:'', emoji:'🥘', quantity:'1', unit:'pcs', category:'veggies' })

  const shown = pantry.filter(i =>
    (active==='all' || i.category===active) &&
    (!search || i.name.toLowerCase().includes(search.toLowerCase()))
  )

  function handleAdd() {
    if (!form.name.trim()) { Alert.alert('Enter ingredient name'); return }
    addPantryItem({
      id: Date.now().toString(),
      user_id: user?.id ?? 'local',
      name: form.name.trim(),
      emoji: form.emoji,
      quantity: form.quantity,
      unit: form.unit,
      category: form.category,
      added_at: new Date().toISOString(),
    })
    setForm({ name:'', emoji:'🥘', quantity:'1', unit:'pcs', category:'veggies' })
    setShowModal(false)
  }

  function handleDelete(item: PantryItem) {
    Alert.alert('Remove', `Remove ${item.name} from pantry?`, [
      { text:'Cancel', style:'cancel' },
      { text:'Remove', style:'destructive', onPress:() => removePantryItem(item.id) },
    ])
  }

  const col = (cat: string) => CAT_COLORS[cat] ?? Colors.purple

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom:100 }}>

        <View style={styles.header}>
          <View>
            <Text style={styles.title}>My Pantry</Text>
            <Text style={styles.sub}>{pantry.length} ingredients tracked</Text>
          </View>
          <TouchableOpacity style={styles.addBtn} onPress={() => setShowModal(true)}>
            <Text style={{ color:'#fff', fontSize:26, fontWeight:'800', lineHeight:30 }}>+</Text>
          </TouchableOpacity>
        </View>

        {/* Stats */}
        <View style={[styles.px, { flexDirection:'row', gap:10, marginBottom: S.lg }]}>
          {[
            { l:'Total',     v: String(pantry.length), col: Colors.green,  e:'📦' },
            { l:'Low Stock', v: String(pantry.filter(i=>i.is_low).length || 0), col: Colors.yellow, e:'⚠️' },
            { l:'Categories',v: String(new Set(pantry.map(i=>i.category)).size), col: Colors.cyan, e:'🗂️' },
          ].map(s => (
            <View key={s.l} style={[styles.statCard, { flex:1 }]}>
              <Text style={{ fontSize:20 }}>{s.e}</Text>
              <Text style={[styles.statVal, { color: s.col }]}>{s.v}</Text>
              <Text style={styles.statLabel}>{s.l}</Text>
            </View>
          ))}
        </View>

        {/* Search */}
        <View style={[styles.px, { marginBottom: S.base }]}>
          <View style={styles.searchBox}>
            <Text style={{ fontSize:16, marginRight:8 }}>🔍</Text>
            <TextInput style={styles.searchInput} placeholder="Search ingredients..." placeholderTextColor={Colors.text3} value={search} onChangeText={setSearch} />
          </View>
        </View>

        {/* Category Filter */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingHorizontal: S.base, gap:8, marginBottom: S.lg }}>
          {CATS.map(c => (
            <TouchableOpacity key={c.id} style={[styles.pill, active===c.id && styles.pillOn]} onPress={() => setActive(c.id)}>
              <Text style={{ fontSize:13 }}>{c.e}</Text>
              <Text style={[styles.pillLabel, active===c.id && styles.pillLabelOn]}>{c.l}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* Items */}
        {shown.length > 0 ? (
          <View style={[styles.px, { gap:10 }]}>
            {shown.map(item => (
              <View key={item.id} style={styles.itemRow}>
                <View style={[styles.itemIcon, { backgroundColor: col(item.category)+'20' }]}>
                  <Text style={{ fontSize:28 }}>{item.emoji}</Text>
                </View>
                <View style={{ flex:1 }}>
                  <Text style={styles.itemName}>{item.name}</Text>
                  <Text style={styles.itemCat}>{item.category.charAt(0).toUpperCase()+item.category.slice(1)}</Text>
                </View>
                <View style={[styles.qtyTag, { backgroundColor: col(item.category)+'18', borderColor: col(item.category)+'55' }]}>
                  <Text style={[styles.qtyText, { color: col(item.category) }]}>{item.quantity} {item.unit}</Text>
                </View>
                <TouchableOpacity style={styles.deleteBtn} onPress={() => handleDelete(item)}>
                  <Text style={{ color: Colors.red, fontSize:18 }}>🗑️</Text>
                </TouchableOpacity>
              </View>
            ))}
          </View>
        ) : (
          <View style={styles.empty}>
            <Text style={{ fontSize:48 }}>🧺</Text>
            <Text style={styles.emptyTitle}>Pantry is empty</Text>
            <Text style={styles.emptySub}>Tap + to add ingredients or scan them</Text>
            <TouchableOpacity style={styles.emptyBtn} onPress={() => setShowModal(true)}>
              <Text style={styles.emptyBtnText}>+ Add Ingredient</Text>
            </TouchableOpacity>
          </View>
        )}

      </ScrollView>

      {/* Add Modal */}
      <Modal visible={showModal} transparent animationType="slide" onRequestClose={() => setShowModal(false)}>
        <TouchableOpacity style={styles.overlay} activeOpacity={1} onPress={() => setShowModal(false)} />
        <View style={styles.modal}>
          <Text style={styles.modalTitle}>Add Ingredient</Text>

          <TextInput style={styles.modalInput} placeholder="Name (e.g. Tomatoes)" placeholderTextColor={Colors.text3}
            value={form.name} onChangeText={v => setForm(f => ({...f, name:v}))} autoFocus />
          <TextInput style={styles.modalInput} placeholder="Emoji (e.g. 🍅)" placeholderTextColor={Colors.text3}
            value={form.emoji} onChangeText={v => setForm(f => ({...f, emoji:v}))} />

          <View style={{ flexDirection:'row', gap:10 }}>
            <TextInput style={[styles.modalInput, { flex:1 }]} placeholder="Qty" placeholderTextColor={Colors.text3}
              value={form.quantity} onChangeText={v => setForm(f => ({...f, quantity:v}))} keyboardType="numeric" />
            <TextInput style={[styles.modalInput, { flex:1 }]} placeholder="Unit (pcs/kg/g)" placeholderTextColor={Colors.text3}
              value={form.unit} onChangeText={v => setForm(f => ({...f, unit:v}))} />
          </View>

          <Text style={styles.modalLabel}>Category</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: S.base }}>
            <View style={{ flexDirection:'row', gap:8 }}>
              {CATS.filter(c=>c.id!=='all').map(c => (
                <TouchableOpacity key={c.id} style={[styles.catPill, form.category===c.id && styles.catPillOn]}
                  onPress={() => setForm(f => ({...f, category:c.id, emoji: EMOJI_MAP[c.id] ?? '📦'}))}>
                  <Text style={{ fontSize:14 }}>{c.e}</Text>
                  <Text style={[styles.catLabel, form.category===c.id && { color: Colors.accent }]}>{c.l}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </ScrollView>

          <TouchableOpacity style={styles.modalBtn} onPress={handleAdd}>
            <Text style={styles.modalBtnText}>Add to Pantry</Text>
          </TouchableOpacity>
        </View>
      </Modal>
    </View>
  )
}

const styles = StyleSheet.create({
  root:        { flex:1, backgroundColor: Colors.bg },
  px:          { paddingHorizontal: S.base },
  header:      { flexDirection:'row', justifyContent:'space-between', alignItems:'center', paddingHorizontal: S.base, paddingTop: S.lg, paddingBottom: S.xl },
  title:       { fontSize:32, fontWeight:'800', color: Colors.text },
  sub:         { fontSize:13, color: Colors.text2, marginTop:3 },
  addBtn:      { width:46, height:46, borderRadius: R.full, backgroundColor: Colors.accent, alignItems:'center', justifyContent:'center' },
  statCard:    { backgroundColor: Colors.bg3, borderWidth:1, borderColor: Colors.border2, borderRadius: R.lg, padding: S.md, alignItems:'center', gap:3 },
  statVal:     { fontSize:22, fontWeight:'800' },
  statLabel:   { fontSize:9, color: Colors.text2, fontWeight:'600', textAlign:'center' },
  searchBox:   { flexDirection:'row', alignItems:'center', backgroundColor: Colors.surface, borderWidth:1, borderColor: Colors.border2, borderRadius: R.lg, paddingHorizontal: S.base, paddingVertical:12 },
  searchInput: { flex:1, fontSize:15, color: Colors.text },
  pill:        { flexDirection:'row', alignItems:'center', gap:5, paddingHorizontal:12, paddingVertical:8, borderRadius: R.full, backgroundColor: Colors.surface, borderWidth:1, borderColor: Colors.border2 },
  pillOn:      { backgroundColor: Colors.accentGlow, borderColor:'rgba(255,87,34,0.45)' },
  pillLabel:   { fontSize:12, fontWeight:'600', color: Colors.text2 },
  pillLabelOn: { color: Colors.accent },
  itemRow:     { flexDirection:'row', alignItems:'center', gap:12, backgroundColor: Colors.bg3, borderWidth:1, borderColor: Colors.border2, borderRadius: R.xl, padding:14 },
  itemIcon:    { width:54, height:54, borderRadius: R.lg, alignItems:'center', justifyContent:'center' },
  itemName:    { fontSize:15, fontWeight:'700', color: Colors.text },
  itemCat:     { fontSize:11, color: Colors.text2, marginTop:2 },
  qtyTag:      { borderWidth:1, borderRadius: R.full, paddingHorizontal:12, paddingVertical:5 },
  qtyText:     { fontSize:12, fontWeight:'700' },
  deleteBtn:   { width:36, alignItems:'center' },
  empty:       { alignItems:'center', paddingVertical:60, gap: S.md },
  emptyTitle:  { fontSize:20, fontWeight:'800', color: Colors.text },
  emptySub:    { fontSize:14, color: Colors.text2 },
  emptyBtn:    { backgroundColor: Colors.accent, borderRadius: R.full, paddingHorizontal:24, paddingVertical:12, marginTop: S.sm },
  emptyBtnText:{ color:'#fff', fontWeight:'800', fontSize:15 },
  overlay:     { flex:1, backgroundColor:'rgba(0,0,0,0.6)' },
  modal:       { backgroundColor: Colors.bg2, borderTopLeftRadius:24, borderTopRightRadius:24, padding: S.xl, gap: S.md },
  modalTitle:  { fontSize:22, fontWeight:'800', color: Colors.text, marginBottom: S.sm },
  modalInput:  { backgroundColor: Colors.surface, borderWidth:1, borderColor: Colors.border2, borderRadius: R.lg, paddingHorizontal: S.base, paddingVertical:14, fontSize:15, color: Colors.text },
  modalLabel:  { fontSize:12, fontWeight:'700', color: Colors.text3, letterSpacing:1, textTransform:'uppercase' },
  catPill:     { flexDirection:'row', alignItems:'center', gap:5, paddingHorizontal:12, paddingVertical:8, borderRadius: R.full, backgroundColor: Colors.surface, borderWidth:1, borderColor: Colors.border2 },
  catPillOn:   { backgroundColor: Colors.accentGlow, borderColor:'rgba(255,87,34,0.45)' },
  catLabel:    { fontSize:12, fontWeight:'600', color: Colors.text2 },
  modalBtn:    { backgroundColor: Colors.accent, borderRadius: R.xl, paddingVertical:16, alignItems:'center', marginTop: S.sm },
  modalBtnText:{ color:'#fff', fontSize:16, fontWeight:'800' },
})
