import { Tabs } from 'expo-router'
import { View, Text, StyleSheet } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { Colors } from '../../constants/theme'

function TabIcon({ emoji, label, focused }: { emoji: string; label: string; focused: boolean }) {
  return (
    <View style={[styles.wrap, focused && styles.wrapActive]}>
      <Text style={styles.emoji}>{emoji}</Text>
      <Text style={[styles.label, focused && styles.labelActive]}>{label}</Text>
      {focused && <View style={styles.dot} />}
    </View>
  )
}

export default function TabLayout() {
  const insets = useSafeAreaInsets()
  return (
    <Tabs screenOptions={{
      headerShown: false,
      tabBarShowLabel: false,
      tabBarStyle: {
        position: 'absolute', bottom: 0, left: 0, right: 0,
        height: 64 + insets.bottom,
        backgroundColor: 'rgba(7,7,17,0.98)',
        borderTopWidth: 1,
        borderTopColor: Colors.border2,
        elevation: 0,
      },
    }}>
      <Tabs.Screen name="index"   options={{ tabBarIcon: ({ focused }) => <TabIcon emoji="🏠" label="Home"    focused={focused} /> }} />
      <Tabs.Screen name="scan"    options={{ tabBarIcon: ({ focused }) => <TabIcon emoji="📸" label="Scan"    focused={focused} /> }} />
      <Tabs.Screen name="recipes" options={{ tabBarIcon: ({ focused }) => <TabIcon emoji="🍽️" label="Recipes" focused={focused} /> }} />
      <Tabs.Screen name="pantry"  options={{ tabBarIcon: ({ focused }) => <TabIcon emoji="🧺" label="Pantry"  focused={focused} /> }} />
      <Tabs.Screen name="profile" options={{ tabBarIcon: ({ focused }) => <TabIcon emoji="👤" label="Profile" focused={focused} /> }} />
    </Tabs>
  )
}

const styles = StyleSheet.create({
  wrap:        { alignItems:'center', paddingTop:8, minWidth:56, position:'relative' },
  wrapActive:  {},
  emoji:       { fontSize:22 },
  label:       { fontSize:10, marginTop:2, color:Colors.text3, fontWeight:'500' },
  labelActive: { color:Colors.accent, fontWeight:'700' },
  dot:         { position:'absolute', bottom:-4, width:4, height:4, borderRadius:2, backgroundColor:Colors.accent },
})
