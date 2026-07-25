/**
 * 无限滚动 composable
 */
import { onMounted, onUnmounted, onActivated, onDeactivated } from 'vue'

interface UseInfiniteScrollOptions {
  distance?: number
  onLoad: () => void | Promise<void>
  hasMore: () => boolean
  isLoading: () => boolean
}

export function useInfiniteScroll(options: UseInfiniteScrollOptions) {
  const { distance = 300, onLoad, hasMore, isLoading } = options

  function handleScroll() {
    const scrollTop = document.documentElement.scrollTop || document.body.scrollTop
    const clientHeight = window.innerHeight
    const scrollHeight = document.documentElement.scrollHeight || document.body.scrollHeight

    const shouldLoad = scrollTop + clientHeight >= scrollHeight - distance
    if (shouldLoad && hasMore() && !isLoading()) {
      onLoad()
    }
  }

  function addListener() {
    window.addEventListener('scroll', handleScroll, { passive: true })
  }

  function removeListener() {
    window.removeEventListener('scroll', handleScroll)
  }

  onMounted(addListener)
  onUnmounted(removeListener)
  onActivated(addListener)
  onDeactivated(removeListener)

  return { handleScroll }
}
