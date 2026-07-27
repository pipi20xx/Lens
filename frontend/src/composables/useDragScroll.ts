import { onUnmounted, type Ref } from 'vue'

/**
 * useDragScroll — 让容器支持鼠标左键按住拖拽横向/纵向滑动
 *
 * 用法：
 *   const containerRef = ref<HTMLElement | null>(null)
 *   useDragScroll(containerRef)
 *   <div ref="containerRef" style="overflow:auto">...</div>
 *
 * 特点：
 *   - 延迟绑定：兼容 v-window-item 懒加载
 *   - 自动穿透：优先查找 .v-table__wrapper，其次查找第一个 overflow 的子元素
 *   - 3px 死区：区分点击和拖拽，不影响内部按钮交互
 */
export function useDragScroll(containerRef: Ref<HTMLElement | null>) {
  let isDragging = false
  let startX = 0
  let startY = 0
  let scrollLeft = 0
  let scrollTop = 0
  let hasMoved = false
  let scrollTarget: HTMLElement | null = null
  let bound = false

  /** 查找实际可滚动的元素 */
  function findScrollTarget(el: HTMLElement): HTMLElement {
    // 优先找 Vuetify v-table 的 wrapper
    const wrapper = el.querySelector('.v-table__wrapper')
    if (wrapper) return wrapper as HTMLElement

    // 其次找带 overflow 的子元素
    const all = el.querySelectorAll('*')
    for (const child of all) {
      const c = child as HTMLElement
      const style = getComputedStyle(c)
      const overflow = style.overflow + style.overflowX + style.overflowY
      if (/auto|scroll/.test(overflow) && (c.scrollWidth > c.clientWidth || c.scrollHeight > c.clientHeight)) {
        return c
      }
    }

    // 兜底返回自身
    return el
  }

  function tryBind() {
    const el = containerRef.value
    if (!el || bound) return false

    scrollTarget = findScrollTarget(el)
    bound = true

    scrollTarget.style.cursor = 'grab'
    scrollTarget.addEventListener('mousedown', onMouseDown)

    return true
  }

  // ---- 事件处理 ----
  function onMouseDown(e: MouseEvent) {
    if (e.button !== 0) return
    const target = scrollTarget
    if (!target) return

    isDragging = true
    hasMoved = false
    startX = e.pageX
    startY = e.pageY
    scrollLeft = target.scrollLeft
    scrollTop = target.scrollTop

    target.style.cursor = 'grabbing'
    target.style.userSelect = 'none'

    e.preventDefault()
  }

  function onMouseMove(e: MouseEvent) {
    if (!isDragging) return
    const target = scrollTarget
    if (!target) return

    const dx = e.pageX - startX
    const dy = e.pageY - startY

    if (!hasMoved && (Math.abs(dx) > 3 || Math.abs(dy) > 3)) {
      hasMoved = true
    }

    if (hasMoved) {
      target.scrollLeft = scrollLeft - dx
      target.scrollTop = scrollTop - dy
    }
  }

  function onMouseUp() {
    if (!isDragging) return
    isDragging = false

    if (scrollTarget) {
      scrollTarget.style.cursor = 'grab'
      scrollTarget.style.userSelect = ''
    }
  }

  // 全局 move/up 始终监听
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)

  // 定时轮询等待元素挂载（兼容 v-window-item 懒加载）
  const timer = setInterval(() => {
    if (!bound && containerRef.value) {
      tryBind()
    }
  }, 300)

  // 立即尝试一次
  tryBind()

  onUnmounted(() => {
    clearInterval(timer)
    window.removeEventListener('mousemove', onMouseMove)
    window.removeEventListener('mouseup', onMouseUp)

    if (scrollTarget) {
      scrollTarget.removeEventListener('mousedown', onMouseDown)
      scrollTarget.style.cursor = ''
      scrollTarget.style.userSelect = ''
    }
  })
}
