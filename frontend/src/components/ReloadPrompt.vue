<script setup lang="ts">
import { useRegisterSW } from 'virtual:pwa-register/vue'
import { useNotification } from 'naive-ui'
import { watch } from 'vue'

const {
  offlineReady,
  needRefresh,
  updateServiceWorker,
} = useRegisterSW()

const notification = useNotification()

const close = () => {
  offlineReady.value = false
  needRefresh.value = false
}

watch(needRefresh, (val) => {
  if (val) {
    notification.info({
      title: '发现新版本',
      content: '应用内容已更新，是否立即刷新以加载新功能？',
      duration: 0,
      action: () => [
        'div',
        { style: 'display: flex; gap: 8px;' },
        [
          'button',
          {
            style: 'padding: 4px 12px; border-radius: 4px; background: var(--primary-color); color: white; cursor: pointer;',
            onClick: () => updateServiceWorker(true)
          },
          '立即更新'
        ],
        [
          'button',
          {
            style: 'padding: 4px 12px; border-radius: 4px; background: transparent; border: 1px solid var(--border-color); cursor: pointer;',
            onClick: close
          },
          '稍后再说'
        ]
      ],
      onClose: close
    })
  }
})

watch(offlineReady, (val) => {
  if (val) {
    notification.success({
      title: '离线就绪',
      content: '应用已缓存，现在可以在无网络状态下快速启动。',
      duration: 3000
    })
  }
})
</script>

<template>
  <div v-if="false"></div>
</template>