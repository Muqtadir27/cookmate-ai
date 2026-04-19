export const Colors = {
  bg:          '#070711',
  bg2:         '#0D0D1A',
  bg3:         '#13131F',
  surface:     '#1A1A2E',
  surface2:    '#222238',
  border:      'rgba(255,255,255,0.06)',
  border2:     'rgba(255,255,255,0.12)',
  text:        '#FFFFFF',
  text2:       '#8B87B0',
  text3:       '#4A4668',
  accent:      '#FF5722',
  accentGlow:  'rgba(255,87,34,0.18)',
  green:       '#00E5A0',
  greenDim:    'rgba(0,229,160,0.12)',
  purple:      '#B794F4',
  purpleDim:   'rgba(183,148,244,0.12)',
  pink:        '#F687B3',
  pinkDim:     'rgba(246,135,179,0.12)',
  yellow:      '#F6E05E',
  yellowDim:   'rgba(246,224,94,0.12)',
  blue:        '#63B3ED',
  blueDim:     'rgba(99,179,237,0.12)',
  cyan:        '#76E4F7',
  cyanDim:     'rgba(118,228,247,0.12)',
  red:         '#FC8181',
  redDim:      'rgba(252,129,129,0.12)',
} as const

export const Font = {
  display:     'System',
  displayBold: 'System',
  body:        'System',
  medium:      'System',
  bold:        'System',
  mono:        'monospace',
} as const

export const S = { xs:4, sm:8, md:12, base:16, lg:20, xl:24 } as const
export const R = { xs:6, sm:10, md:14, lg:18, xl:24, full:999 } as const

export const CUISINES = [
  { id:'all',    label:'All',    emoji:'⭐' },
  { id:'indian', label:'Indian', emoji:'🇮🇳' },
  { id:'asian',  label:'Asian',  emoji:'🍜' },
  { id:'quick',  label:'Quick',  emoji:'⚡' },
  { id:'veg',    label:'Veg',    emoji:'🥗' },
] as const
