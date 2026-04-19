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
