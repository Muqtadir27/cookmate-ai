import { useState, useEffect, useRef } from 'react'
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, Alert, TextInput, Modal } from 'react-native'
import { router } from 'expo-router'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { Colors, S, R } from '../../constants/theme'
import { askCookingQuestion } from '../../lib/gemini'
import { useStore } from '../../store'
import { Recipe } from '../../types'

const EQUIPMENT_OPTIONS = [
  { id:'stovetop',   label:'Stovetop',         emoji:'🔥' },
  { id:'oven',       label:'Oven',              emoji:'🫙' },
  { id:'microwave',  label:'Microwave',         emoji:'📦' },
  { id:'pressure',   label:'Pressure Cooker',   emoji:'⚡' },
  { id:'airfryer',   label:'Air Fryer',         emoji:'💨' },
  { id:'blender',    label:'Blender/Mixer',     emoji:'🌀' },
]

function scaleQty(qty: string, from: number, to: number): string {
  const n = parseFloat(qty)
  if (isNaN(n)) return qty
  const scaled = (n * to) / from
  return scaled % 1 === 0 ? String(scaled) : scaled.toFixed(1)
}

export default function CookScreen() {
  const insets = useSafeAreaInsets()
  const { activeRecipe: recipe, cookStep, setCookStep, pantry, addCookHistory, updateTasteProfile } = useStore()

  const [showSetup, setShowSetup] = useState(true)
  const [servings, setServings] = useState(recipe?.servings ?? 2)
  const [equipment, setEquipment] = useState<string[]>(['stovetop'])
  const [timerVal, setTimerVal] = useState(0)
  const [timerRunning, setTimerRunning] = useState(false)
  const [timerMax, setTimerMax] = useState(0)
  const [question, setQuestion] = useState('')
  const [aiAnswer, setAiAnswer] = useState('')
  const [aiLoading, setAiLoading] = useState(false)
  const [showQA, setShowQA] = useState(false)
  const [showIngredients, setShowIngredients] = useState(false)
  const intervalRef = useRef<any>(null)

  if (!recipe) return (
    <View style={[styles.root, { alignItems: 'center', justifyContent: 'center' }]}>
      <Text style={{ fontSize: 48, marginBottom: 16 }}>🍽️</Text>
      <Text style={{ color: Colors.text2, fontSize: 16, marginBottom: 24 }}>No recipe selected</Text>
      <TouchableOpacity onPress={() => router.back()}>
        <Text style={{ color: Colors.accent, fontWeight: '700' }}>← Go back</Text>
      </TouchableOpacity>
    </View>
  )

  const baseServings = recipe.servings ?? 2
  const steps = (recipe.steps || []).map((s, i) => ({ ...s, number: s.number ?? i + 1 }))
  const step = steps[cookStep] || { title: 'Done!', instruction: 'Recipe complete.', ingredients_used: [], timer_seconds: 0, number: steps.length, tip: '' }
  const progress = ((cookStep + 1) / (steps.length || 1)) * 100
  const pantryNames = pantry.map(p => p.name.toLowerCase())

  // Detect required equipment from recipe steps
  const requiredEquipment = (() => {
    const text = steps.map(s => (s.instruction ?? '') + (s.title ?? '')).join(' ').toLowerCase()
    const found: string[] = ['stovetop']
    if (text.includes('oven') || text.includes('bake') || text.includes('roast')) found.push('oven')
    if (text.includes('microwave')) found.push('microwave')
    if (text.includes('pressure') || text.includes('whistle')) found.push('pressure')
    if (text.includes('air fry')) found.push('airfryer')
    if (text.includes('blend') || text.includes('grind') || text.includes('mixer')) found.push('blender')
    return [...new Set(found)]
  })()

  const missingEquipment = requiredEquipment.filter(e => !equipment.includes(e))

  useEffect(() => {
    setCookStep(0)
  }, [recipe.id])

  useEffect(() => {
    if (step?.timer_seconds) {
      setTimerVal(step.timer_seconds)
      setTimerMax(step.timer_seconds)
      setTimerRunning(false)
    }
    clearInterval(intervalRef.current)
    setAiAnswer('')
    setQuestion('')
  }, [cookStep])

  useEffect(() => {
    if (timerRunning && timerVal > 0) {
      intervalRef.current = setInterval(() => setTimerVal(v => {
        if (v <= 1) { clearInterval(intervalRef.current); setTimerRunning(false); Alert.alert('⏰ Done!', 'Timer finished!'); return 0 }
        return v - 1
      }), 1000)
    }
    return () => clearInterval(intervalRef.current)
  }, [timerRunning])

  async function handleAskAI() {
    if (!question.trim()) return
    setAiLoading(true)
    try {
      const ans = await askCookingQuestion(question, {
        recipeName: recipe.name, step: cookStep + 1, totalSteps: steps.length,
        instruction: step.instruction ?? '', allIngredients: (recipe.ingredients || []).map((i: any) => i.name)
      })
      setAiAnswer(ans)
    } catch (e: any) { setAiAnswer('Could not get answer: ' + e.message) }
    finally { setAiLoading(false) }
  }

  async function handleFinish() {
    await addCookHistory({ id: Date.now().toString(), recipeName: recipe.name, recipeEmoji: recipe.emoji, cuisine: recipe.cuisine, cookedAt: new Date().toISOString() })
    await updateTasteProfile(recipe)
    Alert.alert('Recipe Complete! 🎉', 'Great cooking! This has been added to your cook history.', [
      { text: 'Back to Recipes', onPress: () => router.push('/(tabs)/recipes') }
    ])
  }

  const fmt = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
  const timerPct = timerMax > 0 ? (timerVal / timerMax) * 100 : 0

  // ── SETUP MODAL ──────────────────────────────────────────
  if (showSetup) return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <View style={styles.setupHeader}>
        <TouchableOpacity onPress={() => router.back()}>
          <Text style={{ color: Colors.text2, fontSize: 22 }}>←</Text>
        </TouchableOpacity>
        <Text style={styles.setupHeaderTitle}>Cook Session Setup</Text>
        <View style={{ width: 40 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: S.xl, paddingBottom: 60, gap: S.xl }}>

        {/* Recipe Hero */}
        <View style={styles.setupHero}>
          <Text style={{ fontSize: 72 }}>{recipe.emoji}</Text>
          <Text style={styles.setupRecipeName}>{recipe.name}</Text>
          <Text style={styles.setupRecipeMeta}>{recipe.cuisine} · {recipe.dietary} · {recipe.time_minutes} min</Text>
        </View>

        {/* Required Equipment Notice */}
        {requiredEquipment.length > 0 && (
          <View style={styles.equipNotice}>
            <Text style={styles.equipNoticeTitle}>This recipe needs:</Text>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>
              {requiredEquipment.map(id => {
                const eq = EQUIPMENT_OPTIONS.find(e => e.id === id)
                if (!eq) return null
                return (
                  <View key={id} style={styles.equipNeededChip}>
                    <Text>{eq.emoji}</Text>
                    <Text style={styles.equipNeededText}>{eq.label}</Text>
                  </View>
                )
              })}
            </View>
          </View>
        )}

        {/* Servings */}
        <View>
          <Text style={styles.setupSectionTitle}>How many people?</Text>
          <Text style={styles.setupSectionSub}>Ingredient quantities will scale automatically</Text>
          <View style={styles.servingsRow}>
            {[1, 2, 3, 4, 6, 8].map(n => (
              <TouchableOpacity key={n} style={[styles.servingBtn, servings === n && styles.servingBtnOn]}
                onPress={() => setServings(n)}>
                <Text style={[styles.servingNum, servings === n && styles.servingNumOn]}>{n}</Text>
                <Text style={[styles.servingLabel, servings === n && styles.servingLabelOn]}>
                  {n === 1 ? 'Just me' : n === 2 ? 'Couple' : n <= 4 ? 'Family' : 'Party'}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Equipment */}
        <View>
          <Text style={styles.setupSectionTitle}>What do you have?</Text>
          <Text style={styles.setupSectionSub}>Select available kitchen equipment</Text>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10 }}>
            {EQUIPMENT_OPTIONS.map(eq => {
              const on = equipment.includes(eq.id)
              const required = requiredEquipment.includes(eq.id)
              return (
                <TouchableOpacity key={eq.id}
                  style={[styles.eqBtn, on && styles.eqBtnOn, required && !on && styles.eqBtnMissing]}
                  onPress={() => setEquipment(prev => on ? prev.filter(e => e !== eq.id) : [...prev, eq.id])}>
                  <Text style={{ fontSize: 22 }}>{eq.emoji}</Text>
                  <Text style={[styles.eqLabel, on && styles.eqLabelOn]}>{eq.label}</Text>
                  {required && <View style={styles.requiredDot} />}
                </TouchableOpacity>
              )
            })}
          </View>
        </View>

        {/* Scaled ingredients preview */}
        {recipe.ingredients && recipe.ingredients.length > 0 && (
          <View>
            <Text style={styles.setupSectionTitle}>Ingredients for {servings} {servings === 1 ? 'person' : 'people'}</Text>
            <View style={styles.ingrPreviewCard}>
              {(recipe.ingredients || []).map((ing: any, i: number) => {
                const have = ing.have || pantryNames.includes(ing.name.toLowerCase())
                const scaledQty = scaleQty(ing.quantity, baseServings, servings)
                return (
                  <View key={i} style={[styles.ingrPreviewRow, i > 0 && styles.ingrPreviewBorder]}>
                    <View style={[styles.haveDot, { backgroundColor: have ? Colors.green : Colors.red }]} />
                    <Text style={{ fontSize: 18 }}>{ing.emoji}</Text>
                    <Text style={[styles.ingrPreviewName, { color: have ? Colors.text : Colors.text2 }]}>{ing.name}</Text>
                    <Text style={styles.ingrPreviewQty}>{scaledQty} {ing.unit}</Text>
                    {!have && <Text style={styles.missingLabel}>Missing</Text>}
                  </View>
                )
              })}
            </View>
          </View>
        )}

        {/* Warning if missing equipment */}
        {missingEquipment.length > 0 && (
          <View style={styles.warningBox}>
            <Text style={styles.warningTitle}>⚠️ Missing Equipment</Text>
            <Text style={styles.warningText}>
              This recipe uses {missingEquipment.map(id => EQUIPMENT_OPTIONS.find(e => e.id === id)?.label).join(', ')} which you haven't selected. You can still proceed but may need to adapt the steps.
            </Text>
          </View>
        )}

        <TouchableOpacity style={styles.startBtn} onPress={() => setShowSetup(false)} activeOpacity={0.88}>
          <Text style={styles.startBtnText}>Start Cooking →</Text>
        </TouchableOpacity>

      </ScrollView>
    </View>
  )

  // ── COOK MODE ────────────────────────────────────────────
  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <View style={styles.header}>
        <TouchableOpacity style={styles.backBtn} onPress={() => setShowSetup(true)}>
          <Text style={{ color: Colors.text2, fontSize: 22 }}>←</Text>
        </TouchableOpacity>
        <View style={{ flex: 1, marginHorizontal: 12 }}>
          <Text style={styles.recipeName} numberOfLines={1}>{recipe.emoji} {recipe.name}</Text>
          <Text style={styles.stepCount}>Step {cookStep + 1} of {steps.length} · {servings} {servings === 1 ? 'person' : 'people'}</Text>
        </View>
        <TouchableOpacity style={styles.ingrBtn} onPress={() => setShowIngredients(!showIngredients)}>
          <Text style={{ fontSize: 20 }}>🧺</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.progressBg}>
        <View style={[styles.progressFill, { width: `${progress}%` as any }]} />
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: 120 }}>

        {/* Ingredient Checklist */}
        {showIngredients && (
          <View style={styles.ingrList}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: S.sm }}>
              <Text style={styles.ingrTitle}>Ingredients · {servings} servings</Text>
              <View style={styles.servingsMini}>
                <TouchableOpacity onPress={() => setServings(s => Math.max(1, s - 1))}><Text style={{ color: Colors.text, fontSize: 18 }}>−</Text></TouchableOpacity>
                <Text style={styles.servingsMiniNum}>{servings}</Text>
                <TouchableOpacity onPress={() => setServings(s => s + 1)}><Text style={{ color: Colors.text, fontSize: 18 }}>+</Text></TouchableOpacity>
              </View>
            </View>
            {(recipe.ingredients || []).map((ing: any, i: number) => {
              const have = ing.have || pantryNames.includes(ing.name.toLowerCase())
              const scaledQty = scaleQty(ing.quantity, baseServings, servings)
              return (
                <View key={i} style={styles.ingrRow}>
                  <View style={[styles.ingrTick, { backgroundColor: have ? Colors.green + '22' : Colors.red + '22' }]}>
                    <Text style={{ color: have ? Colors.green : Colors.red, fontSize: 12, fontWeight: '800' }}>{have ? '✓' : '✗'}</Text>
                  </View>
                  <Text style={{ fontSize: 16 }}>{ing.emoji}</Text>
                  <Text style={[styles.ingrName, { color: have ? Colors.text : Colors.text2 }]}>{ing.name}</Text>
                  <Text style={styles.ingrQty}>{scaledQty} {ing.unit}</Text>
                  {!have && <View style={styles.missingBadge}><Text style={styles.missingText}>Missing</Text></View>}
                </View>
              )
            })}
          </View>
        )}

        {/* Step Card */}
        <View style={styles.stepCard}>
          <View style={styles.stepNumRow}>
            <View style={styles.stepNumBadge}>
              <Text style={styles.stepNumText}>STEP {step.number ?? cookStep + 1}</Text>
            </View>
            {(step.ingredients_used || []).length > 0 && (
              <View style={styles.usingRow}>
                {(step.ingredients_used || []).slice(0, 3).map((n: string, i: number) => (
                  <View key={i} style={styles.usingChip}><Text style={styles.usingText}>{n}</Text></View>
                ))}
              </View>
            )}
          </View>
          <Text style={styles.stepTitle}>{step.title ?? ''}</Text>
          <Text style={styles.stepInstruction}>{step.instruction ?? ''}</Text>
          {step.tip ? (
            <View style={styles.tipCard}>
              <Text style={{ fontSize: 16 }}>💡</Text>
              <Text style={styles.tipText}>{step.tip}</Text>
            </View>
          ) : null}
        </View>

        {/* Timer */}
        {(step.timer_seconds ?? 0) > 0 && (
          <View style={styles.timerCard}>
            <View style={styles.timerCircle}>
              <Text style={styles.timerVal}>{fmt(timerVal)}</Text>
              <Text style={styles.timerLabel}>remaining</Text>
            </View>
            <View style={styles.timerBarBg}>
              <View style={[styles.timerBarFill, { width: `${timerPct}%` as any }]} />
            </View>
            <TouchableOpacity style={styles.timerBtn} onPress={() => {
              if (timerVal === 0) { setTimerVal(step.timer_seconds!); setTimerMax(step.timer_seconds!) }
              setTimerRunning(r => !r)
            }}>
              <Text style={styles.timerBtnText}>{timerRunning ? '⏸ Pause' : timerVal === 0 ? '↺ Restart' : '▶ Start Timer'}</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* AI Q&A */}
        <View style={styles.qaCard}>
          <TouchableOpacity style={styles.qaToggle} onPress={() => setShowQA(!showQA)}>
            <Text style={{ fontSize: 18 }}>🤖</Text>
            <Text style={styles.qaToggleText}>Ask Chef AI a question</Text>
            <Text style={{ color: Colors.text3 }}>{showQA ? '▲' : '▼'}</Text>
          </TouchableOpacity>
          {showQA && (
            <View style={{ marginTop: S.md, gap: S.sm }}>
              <TextInput style={styles.qaInput} placeholder="e.g. Can I use butter instead of oil?"
                placeholderTextColor={Colors.text3} value={question} onChangeText={setQuestion} multiline />
              <TouchableOpacity style={[styles.qaBtn, aiLoading && { opacity: 0.6 }]} onPress={handleAskAI} disabled={aiLoading}>
                <Text style={styles.qaBtnText}>{aiLoading ? 'Asking...' : 'Ask ✨'}</Text>
              </TouchableOpacity>
              {aiAnswer ? (
                <View style={styles.qaAnswer}><Text style={styles.qaAnswerText}>{aiAnswer}</Text></View>
              ) : null}
            </View>
          )}
        </View>

      </ScrollView>

      {/* Navigation */}
      <View style={[styles.navBar, { paddingBottom: insets.bottom + 8 }]}>
        <TouchableOpacity style={[styles.navBtn, styles.navBtnSecondary]}
          onPress={() => { if (cookStep > 0) setCookStep(cookStep - 1) }} disabled={cookStep === 0}>
          <Text style={[styles.navBtnText, { color: cookStep === 0 ? Colors.text3 : Colors.text }]}>← Prev</Text>
        </TouchableOpacity>
        {cookStep < steps.length - 1 ? (
          <TouchableOpacity style={[styles.navBtn, styles.navBtnPrimary]} onPress={() => setCookStep(cookStep + 1)}>
            <Text style={[styles.navBtnText, { color: '#fff' }]}>Next Step →</Text>
          </TouchableOpacity>
        ) : (
          <TouchableOpacity style={[styles.navBtn, { backgroundColor: Colors.green }]} onPress={handleFinish}>
            <Text style={[styles.navBtnText, { color: '#fff' }]}>🎉 Finish!</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  root:              { flex: 1, backgroundColor: Colors.bg },
  setupHeader:       { flexDirection: 'row', alignItems: 'center', paddingHorizontal: S.base, paddingVertical: S.md, borderBottomWidth: 1, borderBottomColor: Colors.border },
  setupHeaderTitle:  { flex: 1, fontSize: 18, fontWeight: '800', color: Colors.text, textAlign: 'center' },
  setupHero:         { alignItems: 'center', gap: 8 },
  setupRecipeName:   { fontSize: 26, fontWeight: '800', color: Colors.text, textAlign: 'center' },
  setupRecipeMeta:   { fontSize: 13, color: Colors.text2 },
  equipNotice:       { backgroundColor: Colors.blueDim, borderWidth: 1, borderColor: Colors.blue + '44', borderRadius: R.xl, padding: S.base },
  equipNoticeTitle:  { fontSize: 13, fontWeight: '700', color: Colors.blue },
  equipNeededChip:   { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: Colors.blue + '22', borderRadius: R.full, paddingHorizontal: 12, paddingVertical: 6 },
  equipNeededText:   { fontSize: 12, fontWeight: '700', color: Colors.blue },
  setupSectionTitle: { fontSize: 18, fontWeight: '800', color: Colors.text, marginBottom: 4 },
  setupSectionSub:   { fontSize: 13, color: Colors.text2, marginBottom: S.md },
  servingsRow:       { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  servingBtn:        { width: 90, backgroundColor: Colors.bg3, borderWidth: 1.5, borderColor: Colors.border2, borderRadius: R.lg, padding: 12, alignItems: 'center', gap: 3 },
  servingBtnOn:      { borderColor: Colors.accent, backgroundColor: Colors.accentGlow },
  servingNum:        { fontSize: 26, fontWeight: '800', color: Colors.text2 },
  servingNumOn:      { color: Colors.accent },
  servingLabel:      { fontSize: 10, color: Colors.text3, fontWeight: '600' },
  servingLabelOn:    { color: Colors.accent },
  eqBtn:             { width: '47%', flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: Colors.bg3, borderWidth: 1.5, borderColor: Colors.border2, borderRadius: R.lg, padding: 14, position: 'relative' },
  eqBtnOn:           { borderColor: Colors.green, backgroundColor: Colors.greenDim },
  eqBtnMissing:      { borderColor: Colors.yellow + '80', backgroundColor: Colors.yellowDim },
  eqLabel:           { fontSize: 13, fontWeight: '600', color: Colors.text2 },
  eqLabelOn:         { color: Colors.green },
  requiredDot:       { position: 'absolute', top: 6, right: 6, width: 8, height: 8, borderRadius: 4, backgroundColor: Colors.yellow },
  ingrPreviewCard:   { backgroundColor: Colors.bg3, borderWidth: 1, borderColor: Colors.border2, borderRadius: R.xl, overflow: 'hidden' },
  ingrPreviewRow:    { flexDirection: 'row', alignItems: 'center', gap: 10, padding: 12 },
  ingrPreviewBorder: { borderTopWidth: 1, borderTopColor: Colors.border },
  haveDot:           { width: 8, height: 8, borderRadius: 4 },
  ingrPreviewName:   { flex: 1, fontSize: 14, fontWeight: '600' },
  ingrPreviewQty:    { fontSize: 13, color: Colors.text2, fontWeight: '700' },
  missingLabel:      { fontSize: 10, fontWeight: '700', color: Colors.red, backgroundColor: Colors.redDim, borderRadius: R.full, paddingHorizontal: 7, paddingVertical: 2 },
  warningBox:        { backgroundColor: Colors.yellowDim, borderWidth: 1, borderColor: Colors.yellow + '44', borderRadius: R.xl, padding: S.base },
  warningTitle:      { fontSize: 14, fontWeight: '800', color: Colors.yellow, marginBottom: 4 },
  warningText:       { fontSize: 13, color: Colors.text2, lineHeight: 20 },
  startBtn:          { backgroundColor: Colors.accent, borderRadius: R.xl, paddingVertical: 18, alignItems: 'center' },
  startBtnText:      { fontSize: 18, fontWeight: '800', color: '#fff' },
  header:            { flexDirection: 'row', alignItems: 'center', paddingHorizontal: S.base, paddingVertical: S.md, borderBottomWidth: 1, borderBottomColor: Colors.border },
  backBtn:           { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  recipeName:        { fontSize: 16, fontWeight: '800', color: Colors.text },
  stepCount:         { fontSize: 11, color: Colors.text2, marginTop: 2 },
  ingrBtn:           { width: 40, height: 40, borderRadius: R.full, backgroundColor: Colors.surface, alignItems: 'center', justifyContent: 'center' },
  progressBg:        { height: 3, backgroundColor: Colors.surface },
  progressFill:      { height: 3, backgroundColor: Colors.accent },
  ingrList:          { margin: S.base, backgroundColor: Colors.bg3, borderWidth: 1, borderColor: Colors.border2, borderRadius: R.xl, padding: S.base, gap: 10 },
  ingrTitle:         { fontSize: 13, fontWeight: '700', color: Colors.text3, letterSpacing: 1 },
  servingsMini:      { flexDirection: 'row', alignItems: 'center', gap: 14, backgroundColor: Colors.surface, borderRadius: R.full, paddingHorizontal: 14, paddingVertical: 6 },
  servingsMiniNum:   { fontSize: 16, fontWeight: '800', color: Colors.accent, minWidth: 20, textAlign: 'center' },
  ingrRow:           { flexDirection: 'row', alignItems: 'center', gap: 10 },
  ingrTick:          { width: 24, height: 24, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  ingrName:          { flex: 1, fontSize: 14, fontWeight: '600' },
  ingrQty:           { fontSize: 12, color: Colors.text2 },
  missingBadge:      { backgroundColor: Colors.redDim, borderRadius: R.full, paddingHorizontal: 8, paddingVertical: 2 },
  missingText:       { fontSize: 9, fontWeight: '700', color: Colors.red },
  stepCard:          { margin: S.base, backgroundColor: Colors.bg3, borderWidth: 1, borderColor: Colors.border2, borderRadius: R.xl, padding: S.lg, gap: S.md },
  stepNumRow:        { flexDirection: 'row', alignItems: 'center', gap: 10, flexWrap: 'wrap' },
  stepNumBadge:      { backgroundColor: Colors.accent, borderRadius: R.full, paddingHorizontal: 12, paddingVertical: 5 },
  stepNumText:       { fontSize: 11, fontWeight: '800', color: '#fff', letterSpacing: 1 },
  usingRow:          { flexDirection: 'row', gap: 6, flexWrap: 'wrap' },
  usingChip:         { backgroundColor: Colors.greenDim, borderRadius: R.full, paddingHorizontal: 8, paddingVertical: 3 },
  usingText:         { fontSize: 10, fontWeight: '600', color: Colors.green },
  stepTitle:         { fontSize: 20, fontWeight: '800', color: Colors.text },
  stepInstruction:   { fontSize: 15, color: Colors.text2, lineHeight: 24 },
  tipCard:           { flexDirection: 'row', gap: 10, backgroundColor: Colors.yellowDim, borderRadius: R.lg, padding: S.md, alignItems: 'flex-start' },
  tipText:           { flex: 1, fontSize: 13, color: Colors.yellow, lineHeight: 20 },
  timerCard:         { margin: S.base, marginTop: 0, backgroundColor: Colors.bg3, borderWidth: 1, borderColor: Colors.border2, borderRadius: R.xl, padding: S.lg, alignItems: 'center', gap: S.md },
  timerCircle:       { alignItems: 'center' },
  timerVal:          { fontSize: 48, fontWeight: '800', color: Colors.accent },
  timerLabel:        { fontSize: 12, color: Colors.text2 },
  timerBarBg:        { width: '100%', height: 6, backgroundColor: Colors.surface2, borderRadius: 3 },
  timerBarFill:      { height: 6, backgroundColor: Colors.accent, borderRadius: 3 },
  timerBtn:          { backgroundColor: Colors.accentGlow, borderWidth: 1, borderColor: Colors.accent + '44', borderRadius: R.full, paddingHorizontal: 28, paddingVertical: 12 },
  timerBtnText:      { fontSize: 15, fontWeight: '700', color: Colors.accent },
  qaCard:            { margin: S.base, marginTop: 0, backgroundColor: Colors.bg3, borderWidth: 1, borderColor: Colors.border2, borderRadius: R.xl, padding: S.base },
  qaToggle:          { flexDirection: 'row', alignItems: 'center', gap: 10 },
  qaToggleText:      { flex: 1, fontSize: 14, fontWeight: '600', color: Colors.text },
  qaInput:           { backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border2, borderRadius: R.lg, padding: S.md, fontSize: 14, color: Colors.text, minHeight: 60 },
  qaBtn:             { backgroundColor: Colors.purple, borderRadius: R.lg, paddingVertical: 12, alignItems: 'center' },
  qaBtnText:         { color: '#fff', fontWeight: '800', fontSize: 14 },
  qaAnswer:          { backgroundColor: Colors.purpleDim, borderRadius: R.lg, padding: S.md },
  qaAnswerText:      { fontSize: 14, color: Colors.text, lineHeight: 22 },
  navBar:            { position: 'absolute', bottom: 0, left: 0, right: 0, flexDirection: 'row', gap: 12, padding: S.base, backgroundColor: Colors.bg, borderTopWidth: 1, borderTopColor: Colors.border2 },
  navBtn:            { flex: 1, paddingVertical: 16, borderRadius: R.xl, alignItems: 'center', justifyContent: 'center' },
  navBtnPrimary:     { backgroundColor: Colors.accent },
  navBtnSecondary:   { backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border2 },
  navBtnText:        { fontSize: 15, fontWeight: '800' },
})
