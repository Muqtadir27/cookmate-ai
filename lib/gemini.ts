import { ScannedIngredient, Recipe, PantryItem, TasteProfile } from '../types'

const GROQ_KEY = () => process.env.EXPO_PUBLIC_GROQ_API_KEY ?? ''
const GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions'

async function askGroq(prompt: string, maxTokens = 6000): Promise<string> {
  const res = await fetch(GROQ_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + GROQ_KEY() },
    body: JSON.stringify({
      model: 'llama-3.3-70b-versatile',
      messages: [{ role: 'user', content: prompt }],
      max_tokens: maxTokens,
      temperature: 0.4,
    })
  })
  if (!res.ok) {
    const e = await res.json()
    throw new Error('Groq ' + res.status + ': ' + (e?.error?.message ?? JSON.stringify(e)))
  }
  const data = await res.json()
  return data.choices[0].message.content.trim()
}

function parseJSON(text: string): any {
  const clean = text.replace(/```json|```/g, '').trim()
  const arrStart = clean.indexOf('[')
  const objStart = clean.indexOf('{')
  let start = -1
  let end = -1
  if (arrStart !== -1 && (objStart === -1 || arrStart < objStart)) {
    start = arrStart
    end = clean.lastIndexOf(']') + 1
  } else {
    start = objStart
    end = clean.lastIndexOf('}') + 1
  }
  if (start === -1) throw new Error('No JSON found in response')
  return JSON.parse(clean.slice(start, end))
}

export async function scanIngredientsGroq(base64Image: string): Promise<ScannedIngredient[]> {
  const res = await fetch(GROQ_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + GROQ_KEY() },
    body: JSON.stringify({
      model: 'meta-llama/llama-4-scout-17b-16e-instruct',
      messages: [{
        role: 'user',
        content: [
          { type: 'image_url', image_url: { url: 'data:image/jpeg;base64,' + base64Image } },
          { type: 'text', text: 'Identify all food ingredients in this image. Return ONLY a valid JSON array with no extra text: [{"name":"Tomatoes","emoji":"🍅","quantity":"3","unit":"pcs","category":"vegetables","confidence":0.95}]. Categories: vegetables, proteins, grains, dairy, spices, oils, other.' }
        ]
      }],
      max_tokens: 1000
    })
  })
  if (!res.ok) {
    const e = await res.json()
    throw new Error('Groq Vision ' + res.status + ': ' + (e?.error?.message ?? JSON.stringify(e)))
  }
  const data = await res.json()
  return parseJSON(data.choices[0].message.content)
}

export async function scanIngredients(base64Image: string): Promise<ScannedIngredient[]> {
  return scanIngredientsGroq(base64Image)
}

export async function generateRecipes(
  pantry: PantryItem[],
  prefs: any,
  tasteProfile?: TasteProfile | null
): Promise<Recipe[]> {
  const pantryList = pantry.map(p => p.name).join(', ')
  const cuisine = prefs.cuisines?.[0] === 'all' ? 'any cuisine' : (prefs.cuisines?.[0] ?? 'any')
  const tasteCtx = tasteProfile && tasteProfile.totalCooked > 0
    ? 'User previously cooked: ' + tasteProfile.favoriteDishes.slice(0, 3).join(', ') + '. '
    : ''

  const prompt = `You are a professional chef AI. Generate exactly 5 recipes.

PANTRY (what the user has): ${pantryList}

RULES:
- Prioritize recipes that use MOSTLY items from the pantry
- match_score should be 70-100 (integer, NOT decimal) based on how many pantry items are used
- missing_ingredients should be SHORT list of common items not in pantry
- Each recipe MUST have at least 5 detailed cooking steps
- Steps must include realistic timer_seconds (0 if no waiting needed)
- ingredients must mark have=true if ingredient is in pantry: [${pantryList}]
- ${tasteCtx}
- Cuisine preference: ${cuisine}
- Dietary: ${prefs.dietary || 'any'}
- Servings: ${prefs.servings || 2}

Return ONLY this JSON array, no markdown, no explanation:
[
  {
    "id": "r1",
    "name": "Recipe Name",
    "emoji": "🍛",
    "cuisine": "Indian",
    "dietary": "Vegetarian",
    "description": "One line description",
    "match_score": 85,
    "missing_ingredients": ["salt"],
    "ingredients": [
      {"name": "Tomatoes", "emoji": "🍅", "quantity": "3", "unit": "pcs", "have": true},
      {"name": "Salt", "emoji": "🧂", "quantity": "1", "unit": "tsp", "have": false}
    ],
    "steps": [
      {"number": 1, "title": "Prep vegetables", "instruction": "Chop tomatoes finely into small cubes.", "tip": "Removing seeds reduces water content", "timer_seconds": 0, "ingredients_used": ["Tomatoes"]},
      {"number": 2, "title": "Heat oil", "instruction": "Heat 2 tbsp oil in a pan over medium flame.", "tip": "Oil is ready when it shimmers", "timer_seconds": 60, "ingredients_used": []},
      {"number": 3, "title": "Cook base", "instruction": "Add onions and fry until golden brown.", "tip": "Stir every 30 seconds to prevent burning", "timer_seconds": 300, "ingredients_used": []},
      {"number": 4, "title": "Add spices", "instruction": "Add all spices and stir for 1 minute.", "tip": "Toast spices briefly to release aroma", "timer_seconds": 60, "ingredients_used": []},
      {"number": 5, "title": "Simmer", "instruction": "Add tomatoes, mix well and simmer for 15 minutes.", "tip": "Cover partially to retain moisture", "timer_seconds": 900, "ingredients_used": ["Tomatoes"]}
    ],
    "nutrition": {"calories": 320, "protein_g": 12, "carbs_g": 45, "fat_g": 10, "fiber_g": 6},
    "time_minutes": 30,
    "servings": 2,
    "difficulty": "Easy",
    "tips": ["Prep all ingredients before starting", "Taste and adjust salt at the end"],
    "generated_at": "${new Date().toISOString()}"
  }
]`

  const text = await askGroq(prompt, 7000)
  const recipes = parseJSON(text)
  if (!Array.isArray(recipes) || recipes.length === 0) {
    throw new Error('AI returned no recipes. Try adding more ingredients to your pantry.')
  }
  // Ensure match_score is always an integer percentage
  return recipes.map((r: any) => ({
    ...r,
    match_score: r.match_score > 1 ? Math.round(r.match_score) : Math.round(r.match_score * 100),
    steps: (r.steps || []).map((s: any, i: number) => ({ ...s, number: s.number ?? i + 1 })),
  }))
}

export async function askCookingQuestion(
  question: string,
  ctx: { recipeName: string; step: number; totalSteps: number; instruction: string; allIngredients: string[] }
): Promise<string> {
  const prompt = `You are a helpful chef assistant.
Recipe: "${ctx.recipeName}" | Step ${ctx.step}/${ctx.totalSteps}
Current step: "${ctx.instruction}"
Ingredients: ${ctx.allIngredients.join(', ')}
Question: "${question}"
Answer in 2-3 sentences. Be practical and direct.`
  return askGroq(prompt, 400)
}

export async function getSubstitute(
  missing: string,
  recipe: string,
  available: string[]
): Promise<{ substitute: string; ratio: string; note: string }> {
  const prompt = `Chef AI: Making "${recipe}", missing: ${missing}. Available: ${available.join(', ')}.
Best substitute? Return ONLY JSON: {"substitute":"yogurt","ratio":"1:1","note":"adds slight tang"}`
  const text = await askGroq(prompt, 200)
  try { return parseJSON(text) } catch { return { substitute: 'No substitute found', ratio: '-', note: 'This ingredient may be essential' } }
}

export async function generateTasteInsight(profile: TasteProfile): Promise<string> {
  if (profile.totalCooked < 2) return 'Cook more dishes to unlock your personalised taste profile!'
  const prompt = `Based on cooking history: favourite dishes: ${profile.favoriteDishes.join(', ')}, cuisines: ${profile.preferredCuisines.join(', ')}, total cooked: ${profile.totalCooked}.
Write ONE fun sentence (max 15 words) about this person's taste. No quotes.`
  return askGroq(prompt, 100)
}
