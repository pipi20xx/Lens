import { ref, computed, watch } from 'vue'
import { dockerApi } from '@/api/docker'
import { useNotification } from '@/composables'

const { error: showError } = useNotification()

// 单例模式 —— 整个页面共享同一份主机状态
const hosts = ref<any[]>([])
const selectedHostId = ref<string | null>(null)

const currentHost = computed(() => hosts.value.find((h: any) => h.id === selectedHostId.value))
const hostOptions = computed(() => hosts.value.map((h: any) => ({ title: h.name, value: h.id })))

async function fetchHosts() {
  try {
    const data = await dockerApi.getHosts()
    hosts.value = Array.isArray(data) ? data : []
    if (hosts.value.length > 0) {
      const saved = localStorage.getItem('lens_selected_docker_host')
      if (saved && hosts.value.some((h: any) => h.id === saved)) {
        selectedHostId.value = saved
      } else if (!selectedHostId.value) {
        selectedHostId.value = hosts.value[0].id
      }
    }
  } catch { showError('加载主机列表失败') }
}

function persistHostId(val: string | null) {
  if (val) localStorage.setItem('lens_selected_docker_host', val)
}

watch(selectedHostId, persistHostId)

export function useDockerHost() {
  return {
    hosts,
    selectedHostId,
    currentHost,
    hostOptions,
    fetchHosts,
  }
}
