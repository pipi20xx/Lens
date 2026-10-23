/** 文件图标：按扩展名映射，树和列表共用。 */
const EXT_ICONS: Record<string, string> = {
  js: 'mdi-language-javascript',
  mjs: 'mdi-language-javascript',
  cjs: 'mdi-language-javascript',
  ts: 'mdi-language-typescript',
  tsx: 'mdi-language-typescript',
  vue: 'mdi-vuejs',
  py: 'mdi-language-python',
  json: 'mdi-code-json',
  md: 'mdi-language-markdown',
  css: 'mdi-language-css3',
  scss: 'mdi-sass',
  sass: 'mdi-sass',
  less: 'mdi-language-css3',
  html: 'mdi-language-html5',
  yml: 'mdi-file-cog-outline',
  yaml: 'mdi-file-cog-outline',
  toml: 'mdi-file-cog-outline',
  ini: 'mdi-file-cog-outline',
  conf: 'mdi-file-cog-outline',
  env: 'mdi-file-cog-outline',
  sh: 'mdi-bash',
  bash: 'mdi-bash',
  zsh: 'mdi-bash',
  sql: 'mdi-database-outline',
  png: 'mdi-file-image-outline',
  jpg: 'mdi-file-image-outline',
  jpeg: 'mdi-file-image-outline',
  gif: 'mdi-file-image-outline',
  svg: 'mdi-svg',
  webp: 'mdi-file-image-outline',
  ico: 'mdi-file-image-outline',
  zip: 'mdi-folder-zip-outline',
  gz: 'mdi-folder-zip-outline',
  tar: 'mdi-folder-zip-outline',
  rar: 'mdi-folder-zip-outline',
  '7z': 'mdi-folder-zip-outline',
  pdf: 'mdi-file-pdf-box',
  txt: 'mdi-file-document-outline',
  log: 'mdi-text-box-outline',
  lock: 'mdi-lock-outline',
  gitignore: 'mdi-git',
  dockerfile: 'mdi-docker',
}

export function fileIcon(name: string, type?: string): string {
  if (type === 'dir') return 'mdi-folder-outline'
  if (type === 'link') return 'mdi-link-variant'
  const lower = name.toLowerCase()
  if (lower.startsWith('dockerfile')) return 'mdi-docker'
  if (lower === '.gitignore' || lower === '.gitattributes') return 'mdi-git'
  const ext = lower.includes('.') ? lower.split('.').pop()! : ''
  return EXT_ICONS[ext] || 'mdi-file-outline'
}
