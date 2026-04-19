import { createClient } from '@supabase/supabase-js'
import AsyncStorage from '@react-native-async-storage/async-storage'
import { Platform } from 'react-native'
import { PantryItem, ScannedIngredient } from '../types'

export const supabase = createClient(
  process.env.EXPO_PUBLIC_SUPABASE_URL!,
  process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY!,
  {
    auth: {
      storage: Platform.OS === 'web' ? undefined : AsyncStorage,
      autoRefreshToken: true,
      persistSession: Platform.OS !== 'web',
      detectSessionInUrl: Platform.OS === 'web',
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
    await supabase.from('profiles').upsert({
      id: data.user.id, name, email,
      cuisine_preference: ['indian', 'south-indian'],
      dietary_preference: 'all',
      spice_level: 'Medium',
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
  const { data } = await supabase.from('profiles').select('*').eq('id', user.id).single()
  return data
}

export async function getPantry(userId: string): Promise<PantryItem[]> {
  const { data, error } = await supabase
    .from('pantry').select('*').eq('user_id', userId).order('category')
  if (error) throw error
  return data ?? []
}

export async function addPantryItems(items: ScannedIngredient[], userId: string) {
  const rows = items.map(i => ({
    user_id: userId, name: i.name, emoji: i.emoji,
    quantity: i.quantity, unit: i.unit, category: i.category,
    confidence: i.confidence, added_at: new Date().toISOString(),
  }))
  const { error } = await supabase.from('pantry').upsert(rows, { onConflict: 'user_id,name' })
  if (error) throw error
}

export async function addManualItem(item: Omit<PantryItem, 'id' | 'added_at'>) {
  const { data, error } = await supabase
    .from('pantry').insert({ ...item, added_at: new Date().toISOString() }).select().single()
  if (error) throw error
  return data
}

export async function deletePantryItem(id: string) {
  const { error } = await supabase.from('pantry').delete().eq('id', id)
  if (error) throw error
}

export async function saveCookHistory(userId: string, recipeName: string, emoji: string, cuisine: string) {
  await supabase.from('cook_history').insert({
    user_id: userId, recipe_name: recipeName, emoji, cuisine,
    completed: true, cooked_at: new Date().toISOString(),
  })
}

export async function getStats(userId: string) {
  const { data } = await supabase
    .from('cook_history').select('id').eq('user_id', userId).eq('completed', true)
  return { recipes_cooked: data?.length ?? 0 }
}
