import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert, ScrollView } from 'react-native'
import { router } from 'expo-router'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { Colors, S, R } from '../constants/theme'
import { signIn, signUp } from '../lib/supabase'
import { useStore } from '../store'

export default function AuthScreen() {
  const insets = useSafeAreaInsets()
  const { setUser, fetchPantry } = useStore()
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit() {
    if (!email || !password) { Alert.alert('Missing fields', 'Fill in all fields'); return }
    if (mode === 'signup' && !name) { Alert.alert('Missing name', 'Enter your name'); return }
    setLoading(true)
    try {
      if (mode === 'login') {
        const data = await signIn(email, password)
        if (data && data.user) {
          setUser(data.user as any)
          fetchPantry(data.user.id)
          router.back()
        }
      } else {
        await signUp(email, password, name)
        Alert.alert('Account created!', 'Check your email to verify, then sign in.')
        setMode('login')
      }
    } catch (e: any) {
      Alert.alert('Error', e.message ?? 'Something went wrong')
    } finally { setLoading(false) }
  }

  return (
    <ScrollView
      contentContainerStyle={[styles.root, { paddingTop: insets.top + 20, paddingBottom: 60 }]}
      keyboardShouldPersistTaps="handled"
    >
      <TouchableOpacity style={styles.closeBtn} onPress={() => router.back()}>
        <Text style={{ fontSize: 16, color: Colors.text2 }}>Close</Text>
      </TouchableOpacity>

      <Text style={styles.title}>{mode === 'login' ? 'Welcome back' : 'Create account'}</Text>
      <Text style={styles.sub}>
        {mode === 'login' ? 'Sign in to sync your pantry' : 'Join to save your recipes'}
      </Text>

      <View style={styles.form}>
        {mode === 'signup' && (
          <TextInput style={styles.input} placeholder="Your name"
            placeholderTextColor={Colors.text3} value={name}
            onChangeText={setName} autoCapitalize="words" />
        )}
        <TextInput style={styles.input} placeholder="Email"
          placeholderTextColor={Colors.text3} value={email}
          onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" />
        <TextInput style={styles.input} placeholder="Password"
          placeholderTextColor={Colors.text3} value={password}
          onChangeText={setPassword} secureTextEntry />

        <TouchableOpacity
          style={[styles.btn, loading && { opacity: 0.6 }]}
          onPress={handleSubmit} disabled={loading}>
          <Text style={styles.btnText}>
            {loading ? 'Please wait...' : mode === 'login' ? 'Sign In' : 'Create Account'}
          </Text>
        </TouchableOpacity>

        <TouchableOpacity onPress={() => setMode(mode === 'login' ? 'signup' : 'login')} style={styles.switch}>
          <Text style={styles.switchText}>
            {mode === 'login' ? "No account? " : "Have account? "}
            <Text style={{ color: Colors.accent, fontWeight: '800' }}>
              {mode === 'login' ? 'Sign Up' : 'Sign In'}
            </Text>
          </Text>
        </TouchableOpacity>

        <TouchableOpacity onPress={() => router.back()} style={styles.skip}>
          <Text style={styles.skipText}>Continue without account</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  root:      { flexGrow: 1, backgroundColor: Colors.bg, paddingHorizontal: 24, alignItems: 'center' },
  closeBtn:  { alignSelf: 'flex-end', paddingVertical: 8, paddingHorizontal: 4, marginBottom: 24 },
  title:     { fontSize: 30, color: Colors.text, fontWeight: '800', marginBottom: 8, textAlign: 'center' },
  sub:       { fontSize: 14, color: Colors.text2, textAlign: 'center', marginBottom: 32, lineHeight: 22 },
  form:      { width: '100%', gap: 12 },
  input:     { backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border2,
               borderRadius: 10, paddingHorizontal: 16, paddingVertical: 14, fontSize: 15, color: Colors.text },
  btn:       { backgroundColor: Colors.accent, borderRadius: 10, paddingVertical: 16, alignItems: 'center', marginTop: 8 },
  btnText:   { fontSize: 16, color: '#fff', fontWeight: '800' },
  switch:    { alignItems: 'center', paddingVertical: 12 },
  switchText:{ fontSize: 14, color: Colors.text2 },
  skip:      { alignItems: 'center', paddingVertical: 8 },
  skipText:  { fontSize: 13, color: Colors.text3 },
})
