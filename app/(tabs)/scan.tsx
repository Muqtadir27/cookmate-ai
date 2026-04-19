import { useState } from 'react'
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, TextInput,
  Dimensions, Platform, ActivityIndicator, Alert, Modal } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { router } from 'expo-router'
import * as ImagePicker from 'expo-image-picker'
import { Colors, S, R } from '../../constants/theme'
import { useStore } from '../../store'
import { scanIngredientsGroq } from '../../lib/gemini'

const { width } = Dimensions.get('window')
const isWeb = Platform.OS === 'web'
const COLS = isWeb ? 6 : 4
const GAP = 10
const CARD = (width - S.base * 2 - GAP * (COLS - 1)) / COLS

const QUICK = [
  { e:'🍅', n:'Tomatoes', cat:'veggies' }, { e:'🧅', n:'Onion', cat:'veggies' },
  { e:'🫘', n:'Dal', cat:'proteins' },     { e:'🍚', n:'Rice', cat:'grains' },
  { e:'🥚', n:'Eggs', cat:'proteins' },    { e:'🧄', n:'Garlic', cat:'spices' },
  { e:'🥛', n:'Milk', cat:'dairy' },       { e:'🧈', n:'Butter', cat:'dairy' },
  { e:'🫙', n:'Spices', cat:'spices' },    { e:'🥬', n:'Spinach', cat:'veggies' },
  { e:'🌶️', n:'Chilli', cat:'spices' },    { e:'🧀', n:'Cheese', cat:'dairy' },
]

interface ScannedItem { name: string; emoji: string; qty: string; unit: string }

export default function ScanScreen() {
  const insets = useSafeAreaInsets()
  const { pantry, addPantryItem, user } = useStore()
  const [mode, setMode] = useState<'camera'|'manual'>('camera')
  const [items, setItems] = useState<ScannedItem[]>([])
  const [input, setInput] = useState('')
  const [scanning, setScanning] = useState(false)
  const [showQtyEditor, setShowQtyEditor] = useState(false)
  const [editingItem, setEditingItem] = useState<ScannedItem | null>(null)
  const [editQty, setEditQty] = useState('1')
  const [editUnit, setEditUnit] = useState('pcs')

  const hasItem = (n: string) => items.some(i => i.name === n)

  function addItem(name: string, emoji: string = '🥘', qty = '1', unit = 'pcs') {
    if (!hasItem(name)) setItems(p => [...p, { name, emoji, qty, unit }])
  }

  function removeItem(name: string) { setItems(p => p.filter(i => i.name !== name)) }

  function openEdit(item: ScannedItem) {
    setEditingItem(item)
    setEditQty(item.qty)
    setEditUnit(item.unit)
    setShowQtyEditor(true)
  }

  function saveEdit() {
    if (!editingItem) return
    setItems(p => p.map(i => i.name === editingItem.name ? { ...i, qty: editQty, unit: editUnit } : i))
    setShowQtyEditor(false)
  }

  async function pickAndScan() {
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        base64: true, quality: 0.7,
      })
      if (result.canceled || !result.assets[0]) return
      const asset = result.assets[0]
      if (!asset.base64) { Alert.alert('Error', 'Could not read image'); return }
      setScanning(true)
      const detected = await scanIngredientsGroq(asset.base64, asset.mimeType ?? 'image/jpeg')
      if (detected.length === 0) {
        Alert.alert('No ingredients found', 'Try a clearer photo')
      } else {
        // Show quantity editor for each detected item
        const newItems: ScannedItem[] = detected.map(d => ({
          name: d.name,
          emoji: d.emoji ?? '🥘',
          qty: d.quantity ?? '1',
          unit: d.unit ?? 'pcs',
        }))
        // Add all detected items and open the quantity review sheet
        setItems(prev => {
          const existing = prev.map(i => i.name)
          const toAdd = newItems.filter(n => !existing.includes(n.name))
          return [...prev, ...toAdd]
        })
        Alert.alert(
          'Detected! 🎯',
          `Found ${detected.length} ingredients: ${detected.map(d => d.name).join(', ')}\n\nTap any item below to edit its quantity.`,
        )
      }
    } catch (e: any) {
      Alert.alert('Scan failed', e.message ?? 'Could not process image')
    } finally { setScanning(false) }
  }

  function handleAddToPantry() {
    if (items.length === 0) { Alert.alert('Add ingredients first'); return }
    items.forEach(item => {
      const q = QUICK.find(q => q.n === item.name)
      addPantryItem({
        id: Date.now().toString() + Math.random(),
        user_id: user?.id ?? 'local',
        name: item.name,
        emoji: item.emoji,
        quantity: item.qty,
        unit: item.unit,
        category: q?.cat ?? 'other',
        added_at: new Date().toISOString(),
      })
    })
    Alert.alert(
      '✅ Added to Pantry!',
      `${items.length} ingredients saved. Now generate recipes!`,
      [
        { text: 'Go to Pantry ✨', onPress: () => router.push('/(tabs)/pantry') },
        { text: 'Add More', style: 'cancel', onPress: () => setItems([]) },
      ]
    )
  }

  const UNITS = ['pcs', 'kg', 'g', 'L', 'ml', 'cups', 'tbsp', 'tsp', 'bunch']

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: 140 }}>

        <View style={styles.header}>
          <Text style={styles.title}>Scan & Detect</Text>
          <Text style={styles.sub}>Add ingredients → get AI recipes instantly</Text>
        </View>

        <View style={[styles.px, { marginBottom: S.base }]}>
          <View style={styles.toggle}>
            {(['camera', 'manual'] as const).map(m => (
              <TouchableOpacity key={m} style={[styles.toggleBtn, mode === m && styles.toggleOn]} onPress={() => setMode(m)}>
                <Text style={{ fontSize: 16 }}>{m === 'camera' ? '📸' : '✏️'}</Text>
                <Text style={[styles.toggleLabel, mode === m && styles.toggleLabelOn]}>
                  {m === 'camera' ? 'Camera Scan' : 'Type Manually'}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {mode === 'camera' ? (
          <View style={styles.px}>
            <View style={styles.camBox}>
              {[styles.tl, styles.tr, styles.bl, styles.br].map((s, i) => <View key={i} style={s} />)}
              <View style={styles.camInner}>
                {scanning ? (
                  <>
                    <ActivityIndicator size="large" color={Colors.accent} />
                    <Text style={[styles.camTitle, { marginTop: S.base }]}>Analyzing...</Text>
                    <Text style={styles.camSub}>AI is detecting ingredients</Text>
                  </>
                ) : (
                  <>
                    <Text style={{ fontSize: 56 }}>📸</Text>
                    <Text style={styles.camTitle}>Point & Detect</Text>
                    <Text style={styles.camSub}>AI identifies all ingredients automatically</Text>
                    <TouchableOpacity style={styles.camBtn} onPress={pickAndScan} activeOpacity={0.88}>
                      <Text style={styles.camBtnText}>Pick Photo to Scan</Text>
                    </TouchableOpacity>
                  </>
                )}
              </View>
            </View>
          </View>
        ) : (
          <View style={styles.px}>
            <View style={styles.inputRow}>
              <TextInput style={styles.input} placeholder="Type ingredient name..."
                placeholderTextColor={Colors.text3} value={input} onChangeText={setInput}
                onSubmitEditing={() => { if (input.trim()) { addItem(input.trim()); setInput('') } }} />
              <TouchableOpacity style={styles.addBtn}
                onPress={() => { if (input.trim()) { addItem(input.trim()); setInput('') } }}>
                <Text style={{ color: '#fff', fontSize: 24, fontWeight: '800' }}>+</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}

        {/* Added items with quantity editing */}
        {items.length > 0 && (
          <View style={[styles.px, { marginTop: S.base }]}>
            <Text style={styles.sectionLabel}>Added · {items.length} — tap to edit quantity</Text>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
              {items.map(item => (
                <View key={item.name} style={styles.chip}>
                  <TouchableOpacity onPress={() => openEdit(item)} style={styles.chipInner}>
                    <Text style={styles.chipText}>{item.name}</Text>
                    <View style={styles.qtyBubble}>
                      <Text style={styles.qtyBubbleText}>{item.qty} {item.unit}</Text>
                    </View>
                  </TouchableOpacity>
                  <TouchableOpacity onPress={() => removeItem(item.name)} style={styles.chipRemove}>
                    <Text style={{ color: Colors.red, fontWeight: '800', fontSize: 14 }}>×</Text>
                  </TouchableOpacity>
                </View>
              ))}
            </View>
          </View>
        )}

        {/* Quick Add Grid */}
        <View style={[styles.px, { marginTop: S.lg }]}>
          <Text style={styles.sectionLabel}>Quick Add</Text>
          <View style={styles.grid}>
            {QUICK.map(s => (
              <TouchableOpacity key={s.n} style={[styles.sugCard, hasItem(s.n) && styles.sugCardOn]}
                onPress={() => hasItem(s.n) ? openEdit(items.find(i => i.name === s.n)!) : addItem(s.n, s.e)}
                activeOpacity={0.8}>
                <Text style={{ fontSize: 26 }}>{s.e}</Text>
                <Text style={[styles.sugName, hasItem(s.n) && { color: Colors.green }]}>{s.n}</Text>
                {hasItem(s.n) && (
                  <View style={styles.checkBadge}>
                    <Text style={{ color: Colors.green, fontSize: 10, fontWeight: '800' }}>✓</Text>
                  </View>
                )}
              </TouchableOpacity>
            ))}
          </View>
        </View>

      </ScrollView>

      {/* Sticky Add to Pantry button */}
      {items.length > 0 && (
        <View style={[styles.stickyBar, { paddingBottom: insets.bottom + 8 }]}>
          <TouchableOpacity style={styles.pantryBtn} onPress={handleAddToPantry} activeOpacity={0.88}>
            <Text style={{ fontSize: 20 }}>🧺</Text>
            <Text style={styles.pantryBtnText}>Add {items.length} to Pantry → Go to Pantry</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Quantity Editor Modal */}
      <Modal visible={showQtyEditor} transparent animationType="slide" onRequestClose={() => setShowQtyEditor(false)}>
        <TouchableOpacity style={styles.overlay} activeOpacity={1} onPress={() => setShowQtyEditor(false)} />
        <View style={styles.modal}>
          <Text style={styles.modalTitle}>How much {editingItem?.name}?</Text>
          <Text style={styles.modalSub}>Edit the quantity you have at home</Text>

          <View style={styles.qtyRow}>
            <TouchableOpacity style={styles.qtyMinus}
              onPress={() => setEditQty(q => String(Math.max(0.5, parseFloat(q || '1') - 1)))}>
              <Text style={{ fontSize: 24, color: Colors.text, fontWeight: '800' }}>−</Text>
            </TouchableOpacity>
            <TextInput
              style={styles.qtyInput}
              value={editQty}
              onChangeText={setEditQty}
              keyboardType="decimal-pad"
            />
            <TouchableOpacity style={styles.qtyPlus}
              onPress={() => setEditQty(q => String(parseFloat(q || '1') + 1))}>
              <Text style={{ fontSize: 24, color: '#fff', fontWeight: '800' }}>+</Text>
            </TouchableOpacity>
          </View>

          <Text style={[styles.sectionLabel, { marginBottom: 10 }]}>Unit</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: S.base }}>
            <View style={{ flexDirection: 'row', gap: 8 }}>
              {UNITS.map(u => (
                <TouchableOpacity key={u} style={[styles.unitPill, editUnit === u && styles.unitPillOn]}
                  onPress={() => setEditUnit(u)}>
                  <Text style={[styles.unitText, editUnit === u && styles.unitTextOn]}>{u}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </ScrollView>

          <TouchableOpacity style={styles.saveBtn} onPress={saveEdit}>
            <Text style={styles.saveBtnText}>Save — {editQty} {editUnit}</Text>
          </TouchableOpacity>
        </View>
      </Modal>
    </View>
  )
}

const styles = StyleSheet.create({
  root:          { flex: 1, backgroundColor: Colors.bg },
  px:            { paddingHorizontal: S.base },
  header:        { paddingHorizontal: S.base, paddingTop: S.lg, paddingBottom: S.xl },
  title:         { fontSize: 32, fontWeight: '800', color: Colors.text },
  sub:           { fontSize: 14, color: Colors.text2, marginTop: 4 },
  toggle:        { flexDirection: 'row', backgroundColor: Colors.surface, borderRadius: R.lg, padding: 4, gap: 4 },
  toggleBtn:     { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingVertical: 12, borderRadius: R.md },
  toggleOn:      { backgroundColor: Colors.accent },
  toggleLabel:   { fontSize: 14, fontWeight: '700', color: Colors.text2 },
  toggleLabelOn: { color: '#fff' },
  camBox:        { backgroundColor: Colors.bg3, borderWidth: 1.5, borderColor: Colors.border2, borderRadius: R.xl, minHeight: 280, position: 'relative', overflow: 'hidden', marginBottom: S.base },
  camInner:      { flex: 1, alignItems: 'center', justifyContent: 'center', padding: S.xl, gap: S.md, minHeight: 280 },
  tl:            { position: 'absolute', top: 16, left: 16, width: 32, height: 32, borderTopWidth: 3, borderLeftWidth: 3, borderColor: Colors.accent, borderRadius: 4 },
  tr:            { position: 'absolute', top: 16, right: 16, width: 32, height: 32, borderTopWidth: 3, borderRightWidth: 3, borderColor: Colors.accent, borderRadius: 4 },
  bl:            { position: 'absolute', bottom: 16, left: 16, width: 32, height: 32, borderBottomWidth: 3, borderLeftWidth: 3, borderColor: Colors.accent, borderRadius: 4 },
  br:            { position: 'absolute', bottom: 16, right: 16, width: 32, height: 32, borderBottomWidth: 3, borderRightWidth: 3, borderColor: Colors.accent, borderRadius: 4 },
  camTitle:      { fontSize: 20, fontWeight: '800', color: Colors.text },
  camSub:        { fontSize: 13, color: Colors.text2, textAlign: 'center', lineHeight: 20 },
  camBtn:        { backgroundColor: Colors.accent, borderRadius: R.full, paddingHorizontal: 32, paddingVertical: 14, marginTop: S.sm },
  camBtnText:    { color: '#fff', fontSize: 15, fontWeight: '800' },
  inputRow:      { flexDirection: 'row', gap: 10 },
  input:         { flex: 1, backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border2, borderRadius: R.lg, paddingHorizontal: S.base, paddingVertical: 14, fontSize: 15, color: Colors.text },
  addBtn:        { width: 52, height: 52, backgroundColor: Colors.accent, borderRadius: R.lg, alignItems: 'center', justifyContent: 'center' },
  sectionLabel:  { fontSize: 11, fontWeight: '700', letterSpacing: 1.2, textTransform: 'uppercase', color: Colors.text3, marginBottom: S.md },
  chip:          { flexDirection: 'row', alignItems: 'center', backgroundColor: Colors.greenDim, borderWidth: 1, borderColor: Colors.green + '55', borderRadius: R.full },
  chipInner:     { flexDirection: 'row', alignItems: 'center', gap: 6, paddingVertical: 7, paddingLeft: 12, paddingRight: 4 },
  chipText:      { fontSize: 13, fontWeight: '700', color: Colors.green },
  qtyBubble:     { backgroundColor: Colors.green + '33', borderRadius: R.full, paddingHorizontal: 7, paddingVertical: 2 },
  qtyBubbleText: { fontSize: 11, fontWeight: '700', color: Colors.green },
  chipRemove:    { paddingHorizontal: 10, paddingVertical: 7 },
  grid:          { flexDirection: 'row', flexWrap: 'wrap', gap: GAP },
  sugCard:       { width: CARD, backgroundColor: Colors.bg3, borderWidth: 1, borderColor: Colors.border2, borderRadius: R.lg, padding: 10, alignItems: 'center', gap: 4, position: 'relative' },
  sugCardOn:     { borderColor: Colors.green, backgroundColor: Colors.greenDim },
  sugName:       { fontSize: 10, fontWeight: '600', color: Colors.text2, textAlign: 'center' },
  checkBadge:    { position: 'absolute', top: 6, right: 6, width: 16, height: 16, borderRadius: 8, backgroundColor: Colors.green + '33', alignItems: 'center', justifyContent: 'center' },
  stickyBar:     { position: 'absolute', bottom: 0, left: 0, right: 0, paddingHorizontal: S.base, paddingTop: 10, backgroundColor: Colors.bg + 'F5' },
  pantryBtn:     { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10, backgroundColor: Colors.accent, borderRadius: R.xl, paddingVertical: 16 },
  pantryBtnText: { fontSize: 15, fontWeight: '800', color: '#fff' },
  overlay:       { flex: 1, backgroundColor: 'rgba(0,0,0,0.65)' },
  modal:         { backgroundColor: Colors.bg2, borderTopLeftRadius: 28, borderTopRightRadius: 28, padding: S.xl, paddingBottom: 48, gap: S.sm },
  modalTitle:    { fontSize: 22, fontWeight: '800', color: Colors.text },
  modalSub:      { fontSize: 13, color: Colors.text2, marginBottom: S.sm },
  qtyRow:        { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: S.base },
  qtyMinus:      { width: 52, height: 52, borderRadius: 26, backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border2, alignItems: 'center', justifyContent: 'center' },
  qtyInput:      { flex: 1, textAlign: 'center', fontSize: 32, fontWeight: '800', color: Colors.text, backgroundColor: Colors.surface, borderRadius: R.lg, paddingVertical: 12 },
  qtyPlus:       { width: 52, height: 52, borderRadius: 26, backgroundColor: Colors.accent, alignItems: 'center', justifyContent: 'center' },
  unitPill:      { paddingHorizontal: 14, paddingVertical: 8, borderRadius: R.full, backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border2 },
  unitPillOn:    { backgroundColor: Colors.accentGlow, borderColor: Colors.accent + '60' },
  unitText:      { fontSize: 13, fontWeight: '600', color: Colors.text2 },
  unitTextOn:    { color: Colors.accent, fontWeight: '800' },
  saveBtn:       { backgroundColor: Colors.accent, borderRadius: R.xl, paddingVertical: 16, alignItems: 'center', marginTop: S.sm },
  saveBtnText:   { color: '#fff', fontSize: 16, fontWeight: '800' },
})
