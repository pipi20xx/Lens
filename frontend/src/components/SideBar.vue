<script setup lang="ts">
import { ref, watch, computed, onMounted, h } from 'vue'
import { 
  NLayoutSider, 
  NMenu, 
  NScrollbar,
  NButton,
  NIcon,
  NSpace,
  NTooltip
} from 'naive-ui'
import { groupedMenuOptions, SettingIcon, ConsoleIcon } from '../config/menu'
import MenuManagerModal from './MenuManagerModal.vue'
import { currentViewKey, activeGroupKey, isLogConsoleOpen, menuSettings, isLoggedIn, logout, uiAuthEnabled } from '../store/navigationStore'
import { 
  DragHandleOutlined as MenuManageIcon,
  ExitToAppOutlined as LogoutIcon,
  DnsOutlined as ServerIcon,
  LightModeOutlined as LightIcon,
  DarkModeOutlined as DarkIcon
} from '@vicons/material'
import { useRouter } from 'vue-router'
import { servers, activeServerId, fetchServers, activateServer } from '../store/serverStore'
import { useMessage } from 'naive-ui'

const props = defineProps<{
  isDark: boolean
}>()

const emit = defineEmits(['toggleTheme'])
const router = useRouter()
const message = useMessage()

const collapsed = ref(localStorage.getItem('lens_sidebar_collapsed') === 'true')
const showMenuManager = ref(false)

const serverOptions = computed(() => {
  return servers.value.map(s => ({
    label: s.name,
    key: s.id,
    icon: () => h(NIcon, null, { default: () => h(ServerIcon) })
  }))
})

const activeServerName = computed(() => {
  const active = servers.value.find(s => s.id === activeServerId.value)
  return active ? active.name : '未选择'
})

const handleServerSelect = async (serverId: string) => {
  const success = await activateServer(serverId)
  if (success) {
    message.success(`已切换至服务器: ${activeServerName.value}`)
    window.location.reload()
  }
}

onMounted(() => {
  fetchServers()
})

const handleLogout = () => {
  logout()
  router.push('/login')
}

// 根据顶部选中的 activeGroupKey 动态计算侧边菜单项
const filteredMenuOptions = computed(() => {
  const visibleKeys = new Set(menuSettings.value.filter(s => s.visible).map(s => s.key))
  
  // 找到当前激活的组
  const group = groupedMenuOptions.find(g => g.key === activeGroupKey.value)
  if (!group || !group.children) return []
  
  // 过滤该组下可见的子项
  return group.children.filter(child => child && visibleKeys.has(child.key as string))
})

watch(collapsed, (val) => {
  localStorage.setItem('lens_sidebar_collapsed', String(val))
})

const handleToggleTheme = () => {
  emit('toggleTheme')
}
</script>

<template>
  <n-layout-sider
    bordered
    collapse-mode="width"
    :collapsed-width="64"
    :width="200"
    v-model:collapsed="collapsed"
    class="main-sider"
    :class="{ 'transparent-sider': currentViewKey === 'SiteNavView' }"
  >
    <div class="sidebar-wrapper">
      <!-- 服务器选择器 - 放在侧边栏顶部作为功能项 -->
      <div class="server-switcher" :class="{ 'collapsed': collapsed }">
        <n-dropdown trigger="click" :options="serverOptions" @select="handleServerSelect">
          <n-button quaternary block :size="collapsed ? 'medium' : 'small'" :style="{ padding: collapsed ? '0' : '0 12px', justifyContent: collapsed ? 'center' : 'flex-start' }">
            <template #icon>
              <n-icon color="var(--primary-color)" :size="20"><ServerIcon /></n-icon>
            </template>
            <span v-if="!collapsed" class="server-name-text">{{ activeServerName }}</span>
          </n-button>
        </n-dropdown>
      </div>

      <n-scrollbar style="flex: 1;" class="menu-scrollbar">
        <n-menu
          v-model:value="currentViewKey"
          :collapsed-width="64"
          :collapsed-icon-size="22"
          :options="filteredMenuOptions"
          :indent="18"
          class="side-menu"
        />
      </n-scrollbar>

      <!-- 底部工具栏 -->
      <div class="sidebar-footer" :class="{ 'collapsed': collapsed }">
        <n-space :vertical="collapsed" justify="space-around" align="center" :size="[8, 12]">
          <n-tooltip placement="right" v-if="collapsed">
            <template #trigger>
              <n-button circle secondary size="medium" @click="showMenuManager = true">
                <template #icon><n-icon><MenuManageIcon /></n-icon></template>
              </n-button>
            </template>
            菜单管理
          </n-tooltip>
          <n-button v-else circle secondary size="small" @click="showMenuManager = true">
            <template #icon><n-icon><MenuManageIcon /></n-icon></template>
          </n-button>

          <n-button 
            circle 
            secondary 
            :size="collapsed ? 'medium' : 'small'" 
            :type="isDark ? 'default' : 'primary'"
            @click="handleToggleTheme"
          >
            <template #icon>
              <n-icon>
                <DarkIcon v-if="isDark" />
                <LightIcon v-else />
              </n-icon>
            </template>
          </n-button>
          
          <n-button 
            circle 
            secondary 
            :size="collapsed ? 'medium' : 'small'" 
            :type="currentViewKey === 'SettingsView' ? 'primary' : 'default'" 
            @click="currentViewKey = 'SettingsView'"
          >
            <template #icon><n-icon><SettingIcon /></n-icon></template>
          </n-button>

          <n-button circle secondary :size="collapsed ? 'medium' : 'small'" type="info" @click="isLogConsoleOpen = true">
            <template #icon><n-icon><ConsoleIcon /></n-icon></template>
          </n-button>

          <n-button 
            v-if="isLoggedIn && uiAuthEnabled"
            circle 
            secondary 
            :size="collapsed ? 'medium' : 'small'" 
            type="error" 
            @click="handleLogout"
          >
            <template #icon><n-icon><LogoutIcon /></n-icon></template>
          </n-button>
        </n-space>
      </div>
    </div>

    <MenuManagerModal v-model:show="showMenuManager" />
  </n-layout-sider>
</template>

<style scoped>
.main-sider { 
  background-color: var(--sidebar-bg-color); 
  border-right: 1px solid var(--border-color) !important; 
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding-top: 8px;
}

.server-switcher { 
  padding: 8px 12px 16px 12px; 
  margin-bottom: 4px;
}
.server-switcher.collapsed { padding: 8px 4px 16px 4px; }
.server-name-text { font-size: 0.85rem; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 110px; }

.menu-scrollbar {
  padding: 0 4px;
}

.sidebar-footer { 
  padding: 12px; 
  border-top: 1px solid var(--border-color); 
  margin-top: auto;
}
.sidebar-footer.collapsed { padding: 12px 4px; }

.transparent-sider {
  background-color: transparent !important;
  border-right: none !important;
}

.transparent-sider :deep(.n-layout-sider-scroll-container) {
  background-color: transparent !important;
}

/* 菜单样式调整 */
:deep(.side-menu .n-menu-item-content) {
  border-radius: 8px;
  margin: 2px 0;
}

:deep(.side-menu .n-menu-item-content--selected) {
  background-color: var(--hover-bg) !important;
}

:deep(.side-menu .n-menu-item-content:hover) {
  background-color: var(--hover-bg) !important;
}

:deep(.side-menu .n-menu-item-content--selected .n-menu-item-content__icon),
:deep(.side-menu .n-menu-item-content--selected .n-menu-item-content-header) {
  color: var(--primary-color) !important;
}

:deep(.side-menu .n-menu-item-content__icon) {
  color: var(--text-secondary);
}

:deep(.side-menu .n-menu-item-content-header) {
  color: var(--text-color);
}
</style>
