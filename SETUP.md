# CookMate AI — Complete Setup Guide
# Run these commands in order. Copy-paste each block.

## ── STEP 1: Create the project ──────────────────────

npx create-expo-app cookmate-ai --template blank-typescript
cd cookmate-ai

## ── STEP 2: Install ALL dependencies ────────────────
## (one big command — copy the whole block)

npx expo install \
  expo-router \
  expo-camera \
  expo-image-picker \
  expo-file-system \
  expo-speech \
  expo-haptics \
  expo-font \
  expo-linear-gradient \
  expo-blur \
  expo-av \
  react-native-reanimated \
  react-native-gesture-handler \
  react-native-safe-area-context \
  react-native-screens \
  react-native-svg \
  @react-native-async-storage/async-storage \
  react-native-url-polyfill

npm install @supabase/supabase-js zustand

## ── STEP 3: Download the fonts ──────────────────────
## Create the fonts folder:
mkdir -p assets/fonts

## Download Clash Display (free):
## → https://www.fontshare.com/fonts/clash-display
## → Download → extract → copy these files to assets/fonts/:
##   ClashDisplay-Regular.otf
##   ClashDisplay-Medium.otf
##   ClashDisplay-Semibold.otf
##   ClashDisplay-Bold.otf

## Download Satoshi (free):
## → https://www.fontshare.com/fonts/satoshi
## → Download → extract → copy these to assets/fonts/:
##   Satoshi-Regular.otf
##   Satoshi-Medium.otf
##   Satoshi-Bold.otf

## Download JetBrains Mono (free):
## → https://www.jetbrains.com/lp/mono/
## → Download → extract → copy these to assets/fonts/:
##   JetBrainsMono-Regular.ttf
##   JetBrainsMono-Medium.ttf

## ── STEP 4: Copy all the generated files ────────────
## Replace the files in your project with the ones I generated.
## The structure should look like:
##
##   cookmate-ai/
##   ├── app/
##   │   ├── _layout.tsx       ← root layout
##   │   ├── tabs/
##   │   │   ├── _layout.tsx   ← bottom nav
##   │   │   ├── index.tsx     ← home screen
##   │   │   ├── scan.tsx      ← scan screen
##   │   │   ├── recipes.tsx   ← recipes screen
##   │   │   ├── pantry.tsx    ← pantry screen
##   │   │   └── profile.tsx   ← profile screen
##   ├── components/ui/
##   │   ├── Button.tsx
##   │   └── ...more
##   ├── lib/
##   │   ├── gemini.ts         ← AI service
##   │   └── supabase.ts       ← database
##   ├── store/index.ts        ← global state
##   ├── constants/theme.ts    ← design tokens
##   ├── types/index.ts        ← TypeScript types
##   ├── .env                  ← your API keys
##   └── app.json              ← app config

## ── STEP 5: Add your API keys ───────────────────────
## Edit the .env file with your actual keys:

## 1. Gemini API key (FREE):
##    → Go to: https://aistudio.google.com
##    → Click "Get API key" → Create API key → Copy it
##    → Paste into .env: EXPO_PUBLIC_GEMINI_API_KEY=your_key_here

## 2. Supabase (FREE):
##    → Go to: https://supabase.com → New project
##    → Settings → API → copy "Project URL" and "anon public" key
##    → Paste into .env

## ── STEP 6: Set up Supabase database ────────────────
## In Supabase dashboard → SQL Editor → run this:

# (Copy the SQL from the bottom of lib/supabase.ts)
# It creates 3 tables: profiles, pantry, cook_history

## ── STEP 7: Start the app ───────────────────────────

npx expo start

## Then:
## - Press 'a' for Android emulator
## - Scan QR code with Expo Go app on your phone (FASTEST way to test)
## - Press 'w' for web browser

## ── STEP 8: Build for Play Store ────────────────────

## Install EAS CLI (free):
npm install -g eas-cli

## Login to Expo account (free):
eas login

## Initialize EAS in project:
eas build:configure

## Build APK for testing (free, ~10 minutes in cloud):
eas build --platform android --profile preview

## Build AAB for Play Store (free):
eas build --platform android --profile production

## ── DONE! ────────────────────────────────────────────
## Total cost so far: $0
## When ready for Play Store: pay $25 one-time at play.google.com/console
