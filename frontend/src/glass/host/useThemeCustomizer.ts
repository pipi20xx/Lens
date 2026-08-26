import { computed, onMounted, onScopeDispose, readonly, ref } from 'vue'
import {
  GLASS_OPTICAL_STRENGTH_DEFAULT,
  GLASS_OPTICAL_STRENGTH_MAX,
  getGlassCssFrostBlur,
  getGlassMaterialResponse,
  getGlassOverlayClarityBlur,
  getGlassOpticalCssTransmissionBrightness,
  getGlassOpticalPresetKey,
  getGlassOpticalPresetParameters,
  getGlassOpticalPresetParametersWithOverrides,
  getGlassOpticalTransmissionStrength,
  normalizeGlassOpticalStrength,
  type GlassOpticalParameters,
  type GlassOpticalPreset,
  type GlassOpticalPresetOverrides,
} from '../utils/glassOptics'
import { normalizeThemeMaterialAccent } from '../utils/glassColor'

// ─── 类型定义 ───────────────────────────────────────────────

export type ThemeCustomizerGlassAppearance = 'clear' | 'frosted' | 'tinted' | 'transparent'
export type ThemeCustomizerGlassDynamicsMode = 'fluid' | 'ripple' | 'off'
export type ThemeCustomizerGlassQuality = 'balanced' | 'css' | 'high'
export type ThemeCustomizerGlassSurfaceMode = 'card' | 'page'
export type ThemeCustomizerGlassWallpaperBrightnessMode = 'auto' | 'manual'
export type ThemeCustomizerLayout = 'collapsed' | 'horizontal' | 'vertical'
export type ThemeCustomizerBorder = 'default' | 'dramatic' | 'none' | 'prominent' | 'subtle'
export type ThemeCustomizerRadius = 'default' | 'extra' | 'large' | 'none' | 'small'
export type ThemeCustomizerShadow = 'default' | 'dramatic' | 'none' | 'prominent' | 'subtle'
export type ThemeCustomizerSkin = 'bordered' | 'default'
export type ThemeCustomizerTheme = 'auto' | 'dark' | 'glass' | 'light' | 'purple' | 'transparent'

export interface ThemeCustomizerSettings {
  glassAppearance: ThemeCustomizerGlassAppearance
  glassDynamicsMode: ThemeCustomizerGlassDynamicsMode
  glassDeformationStrength: number
  glassFlowStrength: number
  glassPreset: GlassOpticalPreset
  glassPresetOverrides: GlassOpticalPresetOverrides
  glassQuality: ThemeCustomizerGlassQuality
  glassReflectionStrength: number
  glassSurfaceMode: ThemeCustomizerGlassSurfaceMode
  glassTransmissionStrength: number
  glassTranslationStrength: number
  glassTransparencyStrength: number
  glassWallpaperBrightnessMode: ThemeCustomizerGlassWallpaperBrightnessMode
  glassWallpaperBrightness: number
  border: ThemeCustomizerBorder
  layout: ThemeCustomizerLayout
  primaryColor: string
  radius: ThemeCustomizerRadius
  semiDarkMenu: boolean
  shadow: ThemeCustomizerShadow
  skin: ThemeCustomizerSkin
  theme: ThemeCustomizerTheme
}

export type ThemeCustomizerGlassSettings = Pick<
  ThemeCustomizerSettings,
  | 'glassAppearance'
  | 'glassDeformationStrength'
  | 'glassDynamicsMode'
  | 'glassFlowStrength'
  | 'glassPreset'
  | 'glassPresetOverrides'
  | 'glassQuality'
  | 'glassReflectionStrength'
  | 'glassSurfaceMode'
  | 'glassTransmissionStrength'
  | 'glassTranslationStrength'
  | 'glassTransparencyStrength'
  | 'glassWallpaperBrightnessMode'
  | 'glassWallpaperBrightness'
>

// ─── 常量 ───────────────────────────────────────────────────

export const THEME_CUSTOMIZER_STORAGE_KEY = 'moviepilot-theme-customizer'
export const THEME_CUSTOMIZER_CHANGE_EVENT = 'moviepilot-theme-customizer-change'
export const THEME_CUSTOMIZER_OPEN_EVENT = 'moviepilot-theme-customizer-open'

export const themeCustomizerPrimaryColors = [
  { name: 'Purple', value: '#8D51F9' },
  { name: 'Indigo', value: '#3F51B5' },
  { name: 'Blue', value: '#1976D2' },
  { name: 'Cyan', value: '#00BCD4' },
  { name: 'Teal', value: '#009688' },
  { name: 'Green', value: '#4CAF50' },
  { name: 'Amber', value: '#FFB400' },
  { name: 'Orange', value: '#FF9800' },
  { name: 'Coral', value: '#FF4C51' },
  { name: 'Pink', value: '#E91E63' },
  { name: 'Sky', value: '#16B1FF' },
  { name: 'Slate', value: '#607D8B' },
] as const

const defaultPrimaryColor = themeCustomizerPrimaryColors[0].value
const validGlassAppearances: ThemeCustomizerGlassAppearance[] = ['clear', 'tinted', 'frosted', 'transparent']
const validGlassDynamicsModes: ThemeCustomizerGlassDynamicsMode[] = ['fluid', 'ripple', 'off']
const validGlassPresets: GlassOpticalPreset[] = ['natural', 'glide', 'liquid']
const validGlassQualities: ThemeCustomizerGlassQuality[] = ['css', 'balanced', 'high']
const validGlassSurfaceModes: ThemeCustomizerGlassSurfaceMode[] = ['card', 'page']
const defaultGlassQuality: ThemeCustomizerGlassQuality = 'balanced'
const validLayouts: ThemeCustomizerLayout[] = ['vertical', 'collapsed', 'horizontal']
const validBorders: ThemeCustomizerBorder[] = ['none', 'subtle', 'default', 'prominent', 'dramatic']
const validRadii: ThemeCustomizerRadius[] = ['none', 'small', 'default', 'large', 'extra']
const validShadows: ThemeCustomizerShadow[] = ['none', 'subtle', 'default', 'prominent', 'dramatic']
const validSkins: ThemeCustomizerSkin[] = ['default', 'bordered']
const validThemes: ThemeCustomizerTheme[] = ['auto', 'light', 'dark', 'purple', 'transparent', 'glass']

// ─── 工具函数 ───────────────────────────────────────────────

function isBrowser() {
  return typeof window !== 'undefined'
}

function isHexColor(color: unknown): color is string {
  return typeof color === 'string' && /^#[\da-f]{6}$/i.test(color)
}

/** 将 #RRGGBB 转为 "R, G, B" 字符串，供 CSS 变量使用。 */
function hexToRgb(hex: string): string | undefined {
  if (!isHexColor(hex)) return undefined
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `${r}, ${g}, ${b}`
}

function clampGlass(value: unknown, min: number, max: number, fallback: number): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) return fallback
  return Math.min(max, Math.max(min, value))
}

// ─── 默认设置 ───────────────────────────────────────────────

export function getDefaultGlassCustomizerSettings(
  quality: ThemeCustomizerGlassQuality = defaultGlassQuality,
): ThemeCustomizerGlassSettings {
  const glassParameters = getGlassOpticalPresetParameters('clear', quality, 'natural')

  return {
    glassAppearance: 'clear',
    glassDeformationStrength: glassParameters.deformation,
    glassDynamicsMode: 'ripple',
    glassFlowStrength: glassParameters.flow,
    glassPreset: 'natural',
    glassPresetOverrides: {},
    glassQuality: quality,
    glassReflectionStrength: glassParameters.reflection,
    glassSurfaceMode: 'card',
    glassTransmissionStrength: glassParameters.transmission,
    glassTranslationStrength: glassParameters.translation,
    glassTransparencyStrength: glassParameters.transparency,
    glassWallpaperBrightnessMode: 'auto',
    glassWallpaperBrightness: 0.86,
  }
}

function getDefaultThemeCustomizerSettings(): ThemeCustomizerSettings {
  return {
    ...getDefaultGlassCustomizerSettings(),
    border: 'default',
    layout: 'vertical',
    primaryColor: defaultPrimaryColor,
    radius: 'default',
    semiDarkMenu: false,
    shadow: 'default',
    skin: 'default',
    theme: 'glass',
  }
}

// ─── 设置校验与读取 ─────────────────────────────────────────

function normalizeThemeCustomizerSettings(raw: Partial<ThemeCustomizerSettings>): ThemeCustomizerSettings {
  const defaults = getDefaultThemeCustomizerSettings()

  const glassAppearance = validGlassAppearances.includes(raw.glassAppearance as ThemeCustomizerGlassAppearance)
    ? (raw.glassAppearance as ThemeCustomizerGlassAppearance)
    : defaults.glassAppearance

  const glassDynamicsMode = validGlassDynamicsModes.includes(raw.glassDynamicsMode as ThemeCustomizerGlassDynamicsMode)
    ? (raw.glassDynamicsMode as ThemeCustomizerGlassDynamicsMode)
    : defaults.glassDynamicsMode

  const glassQuality = validGlassQualities.includes(raw.glassQuality as ThemeCustomizerGlassQuality)
    ? (raw.glassQuality as ThemeCustomizerGlassQuality)
    : defaults.glassQuality

  const glassSurfaceMode = validGlassSurfaceModes.includes(raw.glassSurfaceMode as ThemeCustomizerGlassSurfaceMode)
    ? (raw.glassSurfaceMode as ThemeCustomizerGlassSurfaceMode)
    : defaults.glassSurfaceMode
  const glassWallpaperBrightnessMode = raw.glassWallpaperBrightnessMode === 'manual' ? 'manual' : 'auto'
  const glassWallpaperBrightness = clampGlass(raw.glassWallpaperBrightness, 0.2, 1.5, defaults.glassWallpaperBrightness)

  const glassPreset = validGlassPresets.includes(raw.glassPreset as GlassOpticalPreset)
    ? (raw.glassPreset as GlassOpticalPreset)
    : defaults.glassPreset

  const border = validBorders.includes(raw.border as ThemeCustomizerBorder)
    ? (raw.border as ThemeCustomizerBorder)
    : defaults.border

  const layout = validLayouts.includes(raw.layout as ThemeCustomizerLayout)
    ? (raw.layout as ThemeCustomizerLayout)
    : defaults.layout

  const radius = validRadii.includes(raw.radius as ThemeCustomizerRadius)
    ? (raw.radius as ThemeCustomizerRadius)
    : defaults.radius

  const skin = validSkins.includes(raw.skin as ThemeCustomizerSkin)
    ? (raw.skin as ThemeCustomizerSkin)
    : defaults.skin

  const theme = validThemes.includes(raw.theme as ThemeCustomizerTheme)
    ? (raw.theme as ThemeCustomizerTheme)
    : defaults.theme

  const primaryColor = isHexColor(raw.primaryColor) ? raw.primaryColor : defaults.primaryColor
  const semiDarkMenu = typeof raw.semiDarkMenu === 'boolean' ? raw.semiDarkMenu : defaults.semiDarkMenu
  const shadow = validShadows.includes(raw.shadow as ThemeCustomizerShadow)
    ? (raw.shadow as ThemeCustomizerShadow)
    : defaults.shadow

  return {
    glassAppearance,
    glassDynamicsMode,
    glassDeformationStrength: clampGlass(raw.glassDeformationStrength, 0, 100, defaults.glassDeformationStrength),
    glassFlowStrength: clampGlass(raw.glassFlowStrength, 0, 100, defaults.glassFlowStrength),
    glassPreset,
    glassPresetOverrides:
      raw.glassPresetOverrides && typeof raw.glassPresetOverrides === 'object'
        ? raw.glassPresetOverrides
        : defaults.glassPresetOverrides,
    glassQuality,
    glassReflectionStrength: clampGlass(raw.glassReflectionStrength, 0, 100, defaults.glassReflectionStrength),
    glassSurfaceMode,
    glassTransmissionStrength: clampGlass(raw.glassTransmissionStrength, 0, 100, defaults.glassTransmissionStrength),
    glassTranslationStrength: clampGlass(raw.glassTranslationStrength, 0, 100, defaults.glassTranslationStrength),
    glassTransparencyStrength: clampGlass(raw.glassTransparencyStrength, 0, 100, defaults.glassTransparencyStrength),
    glassWallpaperBrightnessMode,
    glassWallpaperBrightness,
    border,
    layout,
    primaryColor,
    radius,
    semiDarkMenu,
    shadow,
    skin,
    theme,
  }
}

function readThemeCustomizerSettings(): ThemeCustomizerSettings {
  if (!isBrowser()) return getDefaultThemeCustomizerSettings()

  try {
    const stored = localStorage.getItem(THEME_CUSTOMIZER_STORAGE_KEY)
    if (!stored) return getDefaultThemeCustomizerSettings()

    const parsed = JSON.parse(stored) as Partial<ThemeCustomizerSettings>
    return normalizeThemeCustomizerSettings(parsed)
  } catch {
    return getDefaultThemeCustomizerSettings()
  }
}

// ─── 状态 ───────────────────────────────────────────────────

const settingsState = ref<ThemeCustomizerSettings>(readThemeCustomizerSettings())
const glassPreviewState = ref<ThemeCustomizerGlassSettings | null>(null)

const effectiveGlassSettings = computed(() => ({
  glassAppearance: glassPreviewState.value?.glassAppearance ?? settingsState.value.glassAppearance,
  glassDeformationStrength:
    glassPreviewState.value?.glassDeformationStrength ?? settingsState.value.glassDeformationStrength,
  glassDynamicsMode: glassPreviewState.value?.glassDynamicsMode ?? settingsState.value.glassDynamicsMode,
  glassFlowStrength: glassPreviewState.value?.glassFlowStrength ?? settingsState.value.glassFlowStrength,
  glassPreset: glassPreviewState.value?.glassPreset ?? settingsState.value.glassPreset,
  glassPresetOverrides: glassPreviewState.value?.glassPresetOverrides ?? settingsState.value.glassPresetOverrides,
  glassQuality: glassPreviewState.value?.glassQuality ?? settingsState.value.glassQuality,
  glassReflectionStrength:
    glassPreviewState.value?.glassReflectionStrength ?? settingsState.value.glassReflectionStrength,
  glassSurfaceMode: glassPreviewState.value?.glassSurfaceMode ?? settingsState.value.glassSurfaceMode,
  glassTransmissionStrength:
    glassPreviewState.value?.glassTransmissionStrength ?? settingsState.value.glassTransmissionStrength,
  glassTranslationStrength:
    glassPreviewState.value?.glassTranslationStrength ?? settingsState.value.glassTranslationStrength,
  glassTransparencyStrength:
    glassPreviewState.value?.glassTransparencyStrength ?? settingsState.value.glassTransparencyStrength,
  glassWallpaperBrightnessMode:
    glassPreviewState.value?.glassWallpaperBrightnessMode ?? settingsState.value.glassWallpaperBrightnessMode,
  glassWallpaperBrightness:
    glassPreviewState.value?.glassWallpaperBrightness ?? settingsState.value.glassWallpaperBrightness,
}))

/** 提供当前实际生效的玻璃设置；临时预览优先于已持久化设置。 */
export function useEffectiveGlassSettings() {
  return readonly(effectiveGlassSettings)
}

// ─── 持久化与广播 ───────────────────────────────────────────

function persistThemeCustomizerSettings(settings: ThemeCustomizerSettings) {
  if (!isBrowser()) return
  localStorage.setItem(THEME_CUSTOMIZER_STORAGE_KEY, JSON.stringify(settings))
}

function dispatchThemeCustomizerChange(settings: ThemeCustomizerSettings) {
  if (!isBrowser()) return
  window.dispatchEvent(
    new CustomEvent<ThemeCustomizerSettings>(THEME_CUSTOMIZER_CHANGE_EVENT, {
      detail: settings,
    }),
  )
}

// ─── 根节点属性同步 ─────────────────────────────────────────

/** 将外观设置同步为根节点属性，使主题 CSS 无需刷新即可响应。 */
export function applyThemeCustomizerRootSettings(
  settings: Pick<
    ThemeCustomizerSettings,
    | 'border'
    | 'glassAppearance'
    | 'glassQuality'
    | 'glassReflectionStrength'
    | 'glassSurfaceMode'
    | 'glassTransmissionStrength'
    | 'glassTransparencyStrength'
    | 'layout'
    | 'primaryColor'
    | 'radius'
    | 'semiDarkMenu'
    | 'shadow'
    | 'skin'
  >,
) {
  if (!isBrowser()) return

  const materialResponse = getGlassMaterialResponse(settings.glassAppearance, settings.glassTransparencyStrength)
  const frostBlur = getGlassCssFrostBlur(settings.glassTransparencyStrength)
  const overlayClarityBlur = getGlassOverlayClarityBlur(settings.glassTransparencyStrength)
  const materialAccent =
    normalizeThemeMaterialAccent(settings.primaryColor) ?? normalizeThemeMaterialAccent(defaultPrimaryColor)!
  /** 将 hex 主色转为 "R, G, B" 字符串，用于覆盖 --v-theme-primary 和自定义变量。 */
  const primaryRgb = hexToRgb(settings.primaryColor) ?? hexToRgb(defaultPrimaryColor)!
  const applyGlassResponse = (element: HTMLElement) => {
    element.style.setProperty('--glass-background-visibility', String(materialResponse.backgroundVisibility))
    element.style.setProperty('--glass-frost-blur-scale', String(materialResponse.frostBlurScale))
    element.style.setProperty('--glass-frost-detail-level', String(materialResponse.frostDetailLevel))
    element.style.setProperty('--glass-surface-density', String(materialResponse.surfaceDensity))
    element.style.setProperty('--glass-tint-density', String(materialResponse.tintDensity))
    element.style.setProperty('--glass-blur-surface', `${frostBlur.surface}px`)
    element.style.setProperty('--glass-blur-raised', `${frostBlur.raised}px`)
    element.style.setProperty('--glass-overlay-clarity-blur', `${overlayClarityBlur}px`)
    element.style.setProperty('--glass-material-accent-rgb', materialAccent.rgb)
  }

  // ── 主题色应用 ──
  // 主色不分白天/夜晚，统一写入 :root 的 --v-theme-primary 和 --am-primary-rgb，
  // Vuetify 组件通过 CSS 变量继承自动响应。
  // JS 侧的 Vuetify theme 对象同步由 App.vue 中 watch primaryColor 完成。
  document.documentElement.style.setProperty('--v-theme-primary', primaryRgb)
  document.documentElement.style.setProperty('--am-primary-rgb', primaryRgb)
  document.documentElement.style.setProperty('--am-primary-hex', settings.primaryColor)

  document.documentElement.setAttribute('data-glass-appearance', settings.glassAppearance)
  document.documentElement.setAttribute('data-glass-quality', settings.glassQuality)
  document.documentElement.setAttribute('data-glass-surface-mode', settings.glassSurfaceMode)
  document.documentElement.style.setProperty(
    '--glass-reflection',
    String(normalizeGlassOpticalStrength(settings.glassReflectionStrength) / GLASS_OPTICAL_STRENGTH_MAX),
  )
  document.documentElement.style.setProperty(
    '--glass-transmission',
    String(getGlassOpticalTransmissionStrength(settings.glassTransmissionStrength)),
  )
  document.documentElement.style.setProperty(
    '--glass-transmission-brightness',
    String(getGlassOpticalCssTransmissionBrightness(settings.glassTransmissionStrength)),
  )
  applyGlassResponse(document.documentElement)
  document.documentElement.setAttribute('data-theme-border', settings.border)
  document.documentElement.setAttribute('data-theme-layout', settings.layout)
  document.documentElement.setAttribute('data-theme-radius', settings.radius)
  document.documentElement.setAttribute('data-theme-semi-dark-menu', String(settings.semiDarkMenu))
  document.documentElement.setAttribute('data-theme-shadow', settings.shadow)
  document.documentElement.setAttribute('data-theme-skin', settings.skin)
  document.body.setAttribute('data-glass-appearance', settings.glassAppearance)
  document.body.setAttribute('data-glass-quality', settings.glassQuality)
  document.body.setAttribute('data-glass-surface-mode', settings.glassSurfaceMode)
  document.body.style.setProperty(
    '--glass-reflection',
    String(normalizeGlassOpticalStrength(settings.glassReflectionStrength) / GLASS_OPTICAL_STRENGTH_MAX),
  )
  document.body.style.setProperty(
    '--glass-transmission',
    String(getGlassOpticalTransmissionStrength(settings.glassTransmissionStrength)),
  )
  document.body.style.setProperty(
    '--glass-transmission-brightness',
    String(getGlassOpticalCssTransmissionBrightness(settings.glassTransmissionStrength)),
  )
  applyGlassResponse(document.body)
  document.body.setAttribute('data-theme-border', settings.border)
  document.body.setAttribute('data-theme-layout', settings.layout)
  document.body.setAttribute('data-theme-radius', settings.radius)
  document.body.setAttribute('data-theme-semi-dark-menu', String(settings.semiDarkMenu))
  document.body.setAttribute('data-theme-shadow', settings.shadow)
  document.body.setAttribute('data-theme-skin', settings.skin)
}

// ─── 持久化部分设置 ─────────────────────────────────────────

export function persistPartialThemeCustomizerSettings(patch: Partial<ThemeCustomizerSettings>) {
  const nextSettings = normalizeThemeCustomizerSettings({
    ...readThemeCustomizerSettings(),
    ...patch,
  })

  glassPreviewState.value = null
  settingsState.value = nextSettings
  persistThemeCustomizerSettings(nextSettings)
  applyThemeCustomizerRootSettings(nextSettings)
  dispatchThemeCustomizerChange(nextSettings)

  return nextSettings
}

// ─── 玻璃预览 ───────────────────────────────────────────────

/** 临时应用玻璃设置，不写入存储或广播持久化变更。 */
export function previewGlassSettings(patch: Partial<ThemeCustomizerGlassSettings>) {
  const previewSettings = normalizeThemeCustomizerSettings({
    ...settingsState.value,
    ...glassPreviewState.value,
    ...patch,
  })

  glassPreviewState.value = {
    glassAppearance: previewSettings.glassAppearance,
    glassDeformationStrength: previewSettings.glassDeformationStrength,
    glassDynamicsMode: previewSettings.glassDynamicsMode,
    glassFlowStrength: previewSettings.glassFlowStrength,
    glassPreset: previewSettings.glassPreset,
    glassPresetOverrides: previewSettings.glassPresetOverrides,
    glassQuality: previewSettings.glassQuality,
    glassReflectionStrength: previewSettings.glassReflectionStrength,
    glassSurfaceMode: previewSettings.glassSurfaceMode,
    glassTransmissionStrength: previewSettings.glassTransmissionStrength,
    glassTranslationStrength: previewSettings.glassTranslationStrength,
    glassTransparencyStrength: previewSettings.glassTransparencyStrength,
    glassWallpaperBrightnessMode: previewSettings.glassWallpaperBrightnessMode,
    glassWallpaperBrightness: previewSettings.glassWallpaperBrightness,
  }
  applyThemeCustomizerRootSettings({
    ...settingsState.value,
    ...glassPreviewState.value,
  })

  return glassPreviewState.value
}

/** 将当前玻璃预览作为一个设置事务持久化，避免外观与质量分步提交。 */
export function commitGlassPreview() {
  const previewSettings = glassPreviewState.value

  if (!previewSettings) return settingsState.value

  glassPreviewState.value = null

  return persistPartialThemeCustomizerSettings(previewSettings)
}

/** 丢弃临时玻璃预览并恢复已保存设置。 */
export function cancelGlassPreview() {
  if (!glassPreviewState.value) return settingsState.value

  glassPreviewState.value = null
  applyThemeCustomizerRootSettings(settingsState.value)

  return settingsState.value
}

// ─── 默认值判断 ─────────────────────────────────────────────

export function isDefaultThemeCustomizerSettings(settings: ThemeCustomizerSettings) {
  const defaults = getDefaultThemeCustomizerSettings()

  return (
    settings.glassAppearance === defaults.glassAppearance &&
    settings.glassDeformationStrength === defaults.glassDeformationStrength &&
    settings.glassDynamicsMode === defaults.glassDynamicsMode &&
    settings.glassFlowStrength === defaults.glassFlowStrength &&
    settings.glassPreset === defaults.glassPreset &&
    settings.glassQuality === defaults.glassQuality &&
    settings.glassReflectionStrength === defaults.glassReflectionStrength &&
    settings.glassSurfaceMode === defaults.glassSurfaceMode &&
    settings.glassTransmissionStrength === defaults.glassTransmissionStrength &&
    settings.glassTranslationStrength === defaults.glassTranslationStrength &&
    settings.glassTransparencyStrength === defaults.glassTransparencyStrength
  )
}

// ─── 应用已保存的外观 ───────────────────────────────────────

/** 应用已保存的主色和外观，供 App 启动阶段使用。 */
export function applyStoredThemeCustomizerAppearance() {
  const settings = readThemeCustomizerSettings()

  glassPreviewState.value = null
  settingsState.value = settings
  applyThemeCustomizerRootSettings(settings)

  return settings
}

// ─── Composable ─────────────────────────────────────────────

export function useThemeCustomizer() {
  const settings = settingsState

  /** 合并、保存并应用一组主题定制设置。 */
  function updateSettings(patch: Partial<ThemeCustomizerSettings>) {
    const nextSettings = normalizeThemeCustomizerSettings({
      ...settings.value,
      ...patch,
    })

    glassPreviewState.value = null
    settings.value = nextSettings
    persistThemeCustomizerSettings(nextSettings)
    applyThemeCustomizerRootSettings(nextSettings)
    dispatchThemeCustomizerChange(nextSettings)
  }

  function setPrimaryColor(color: string) {
    return updateSettings({ primaryColor: color })
  }

  function getCurrentGlassParameters(): GlassOpticalParameters {
    return {
      deformation: settings.value.glassDeformationStrength,
      flow: settings.value.glassFlowStrength,
      reflection: settings.value.glassReflectionStrength,
      transmission: settings.value.glassTransmissionStrength,
      translation: settings.value.glassTranslationStrength,
      transparency: settings.value.glassTransparencyStrength,
    }
  }

  function updateGlassPresetOverride(patch: Partial<GlassOpticalParameters>) {
    const parameters = {
      ...getCurrentGlassParameters(),
      ...patch,
    }
    const key = getGlassOpticalPresetKey(
      settings.value.glassAppearance,
      settings.value.glassQuality,
      settings.value.glassPreset,
    )

    return updateSettings({
      glassDeformationStrength: parameters.deformation,
      glassFlowStrength: parameters.flow,
      glassPresetOverrides: {
        ...settings.value.glassPresetOverrides,
        [key]: parameters,
      },
      glassReflectionStrength: parameters.reflection,
      glassTransmissionStrength: parameters.transmission,
      glassTranslationStrength: parameters.translation,
      glassTransparencyStrength: parameters.transparency,
    })
  }

  function setGlassAppearance(glassAppearance: ThemeCustomizerGlassAppearance) {
    const glassPreset = settings.value.glassQuality === 'css' ? 'natural' : settings.value.glassPreset
    const parameters = getGlassOpticalPresetParametersWithOverrides(
      glassAppearance,
      settings.value.glassQuality,
      glassPreset,
      settings.value.glassPresetOverrides,
    )

    return updateSettings({
      glassAppearance,
      glassDeformationStrength: parameters.deformation,
      glassFlowStrength: parameters.flow,
      glassPreset,
      glassReflectionStrength: parameters.reflection,
      glassTransmissionStrength: parameters.transmission,
      glassTranslationStrength: parameters.translation,
      glassTransparencyStrength: parameters.transparency,
    })
  }

  function setGlassDeformationStrength(glassDeformationStrength: number) {
    return updateGlassPresetOverride({ deformation: normalizeGlassOpticalStrength(glassDeformationStrength) })
  }

  function setGlassDynamicsMode(glassDynamicsMode: ThemeCustomizerGlassDynamicsMode) {
    return updateSettings({ glassDynamicsMode })
  }

  function setGlassSurfaceMode(glassSurfaceMode: ThemeCustomizerGlassSurfaceMode) {
    return updateSettings({ glassSurfaceMode })
  }

  function setGlassFlowStrength(glassFlowStrength: number) {
    return updateGlassPresetOverride({ flow: normalizeGlassOpticalStrength(glassFlowStrength) })
  }

  function setGlassPreset(glassPreset: GlassOpticalPreset) {
    const effectivePreset = settings.value.glassQuality === 'css' ? 'natural' : glassPreset
    const parameters = getGlassOpticalPresetParametersWithOverrides(
      settings.value.glassAppearance,
      settings.value.glassQuality,
      effectivePreset,
      settings.value.glassPresetOverrides,
    )

    return updateSettings({
      glassDeformationStrength: parameters.deformation,
      glassFlowStrength: parameters.flow,
      glassPreset: effectivePreset,
      glassReflectionStrength: parameters.reflection,
      glassTransmissionStrength: parameters.transmission,
      glassTranslationStrength: parameters.translation,
      glassTransparencyStrength: parameters.transparency,
    })
  }

  function setGlassQuality(glassQuality: ThemeCustomizerGlassQuality) {
    const glassPreset: GlassOpticalPreset = glassQuality === 'css' ? 'natural' : settings.value.glassPreset
    const parameters = getGlassOpticalPresetParametersWithOverrides(
      settings.value.glassAppearance,
      glassQuality,
      glassPreset,
      settings.value.glassPresetOverrides,
    )

    return updateSettings({
      glassDeformationStrength: parameters.deformation,
      glassFlowStrength: parameters.flow,
      glassPreset,
      glassQuality,
      glassReflectionStrength: parameters.reflection,
      glassTransmissionStrength: parameters.transmission,
      glassTranslationStrength: parameters.translation,
      glassTransparencyStrength: parameters.transparency,
    })
  }

  function setGlassReflectionStrength(glassReflectionStrength: number) {
    return updateGlassPresetOverride({ reflection: normalizeGlassOpticalStrength(glassReflectionStrength) })
  }

  function setGlassTransmissionStrength(glassTransmissionStrength: number) {
    return updateGlassPresetOverride({ transmission: normalizeGlassOpticalStrength(glassTransmissionStrength) })
  }

  function setGlassTranslationStrength(glassTranslationStrength: number) {
    return updateGlassPresetOverride({ translation: normalizeGlassOpticalStrength(glassTranslationStrength) })
  }

  function setGlassTransparencyStrength(glassTransparencyStrength: number) {
    return updateGlassPresetOverride({ transparency: normalizeGlassOpticalStrength(glassTransparencyStrength) })
  }

  function setRadius(radius: ThemeCustomizerRadius) {
    return updateSettings({ radius })
  }

  function setTheme(theme: ThemeCustomizerTheme) {
    return updateSettings({ theme })
  }

  function setShadow(shadow: ThemeCustomizerShadow) {
    return updateSettings({ shadow })
  }

  function setSkin(skin: ThemeCustomizerSkin) {
    return updateSettings({ skin })
  }

  function setBorder(border: ThemeCustomizerBorder) {
    return updateSettings({ border })
  }

  function setLayout(layout: ThemeCustomizerLayout) {
    return updateSettings({ layout })
  }

  function setSemiDarkMenu(semiDarkMenu: boolean) {
    return updateSettings({ semiDarkMenu })
  }

  function resetSettings() {
    updateSettings({
      ...getDefaultGlassCustomizerSettings(),
      border: 'default',
      layout: 'vertical',
      primaryColor: defaultPrimaryColor,
      radius: 'default',
      semiDarkMenu: false,
      shadow: 'default',
      skin: 'default',
      theme: 'glass',
    })
  }

  onMounted(() => {
    settings.value = readThemeCustomizerSettings()
    applyThemeCustomizerRootSettings(settings.value)
  })

  onScopeDispose(() => {
    // 模块级状态不需要清理
  })

  return {
    isCustomized: computed(() => !isDefaultThemeCustomizerSettings(settings.value)),
    resetSettings,
    setGlassAppearance,
    setGlassDeformationStrength,
    setGlassDynamicsMode,
    setGlassFlowStrength,
    setGlassPreset,
    setGlassQuality,
    setGlassReflectionStrength,
    setGlassSurfaceMode,
    setGlassTransmissionStrength,
    setGlassTranslationStrength,
    setGlassTransparencyStrength,
    setBorder,
    setLayout,
    setPrimaryColor,
    setRadius,
    setSemiDarkMenu,
    setShadow,
    setSkin,
    setTheme,
    settings: readonly(settings),
  }
}
