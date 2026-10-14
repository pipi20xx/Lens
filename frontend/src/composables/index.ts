export { useAuth } from './useAuth'
export { useConfirm } from './useConfirm'
export { useNotification } from './useNotification'
export { useClipboard } from './useClipboard'
export { useDragScroll } from './useDragScroll'

// 已移除两个零引用 composable 的转出（2025 卡片/组件清理）：
//   useInfiniteScroll — 全项目零使用；项目已启用 unplugin-auto-import，
//                       需要时可直接用 @vueuse/core 的 auto-import 版本
//                       （见 src/auto-imports.d.ts）。
//   useStorage        — 同上，@vueuse/core 的 useLocalStorage / useSessionStorage /
//                       useStorage 已在 auto-imports.d.ts 中自动可用。
// 对应文件 useInfiniteScroll.ts / useStorage.ts 已一并删除；
// 若确实需要项目自己的封装版，请从版本历史取回并从本文件重新转出。
