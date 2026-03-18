<template>
  <div class="dedupe-container p-4">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">媒体查重与智能清理</h1>
      <div class="space-x-2 flex items-center">
        <n-button 
          type="primary"
          @click="syncMedia" 
          :loading="syncing"
          secondary
        >
          执行同步
        </n-button>
        <n-button 
          type="success"
          @click="fetchDuplicates" 
          secondary
        >
          执行搜索
        </n-button>
      </div>
    </div>

    <!-- 进度显示 -->
    <div v-if="syncing" class="mb-4 p-4 bg-blue-50/10 border border-blue-200/20 rounded text-blue-400">
      正在从 Emby 获取全量媒体数据并更新本地索引，请稍候...
    </div>

    <!-- 统计摘要 -->
    <div v-if="duplicateGroups.length > 0" class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      <n-card size="small" class="border-l-4 border-yellow-500">
        <div class="text-gray-500 text-sm">重复资源组</div>
        <div class="text-2xl font-bold">{{ duplicateGroups.length }}</div>
      </n-card>
      <n-card size="small" class="border-l-4 border-red-500">
        <div class="text-gray-500 text-sm">待清理项目 (建议)</div>
        <div class="text-2xl font-bold">{{ suggestedCount }}</div>
      </n-card>
      <n-card size="small" class="border-l-4 border-blue-500">
        <div class="text-gray-500 text-sm">选中的项目</div>
        <div class="text-2xl font-bold">{{ selectedIds.length }}</div>
      </n-card>
    </div>

    <!-- 操作栏 -->
    <div v-if="duplicateGroups.length > 0" class="mb-4 flex items-center justify-between bg-white/5 p-3 rounded">
      <n-space>
        <n-button type="warning" secondary size="small" @click="autoSelect">
          智能分析
        </n-button>
        <n-button type="primary" secondary size="small" @click="selectedIds = []">
          取消选中
        </n-button>
      </n-space>
      <n-button 
        type="error"
        secondary
        @click="confirmDelete" 
        :disabled="selectedIds.length === 0"
      >
        执行删除 ({{ selectedIds.length }})
      </n-button>
    </div>

    <!-- 重复项列表 -->
    <div v-if="duplicateGroups.length > 0" class="space-y-6">
      <n-card v-for="group in duplicateGroups" :key="group.tmdb_id" size="small" :title="`TMDB ID: ${group.tmdb_id} - ${group.items[0].name}`" header-style="background: rgba(255,255,255,0.05)">
        <template #header-extra>
          <n-tag size="small" round :bordered="false">{{ group.items.length }} 个副本</n-tag>
        </template>
        
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="text-xs uppercase text-gray-500 border-b border-gray-100/10">
              <th class="p-3 w-10">选</th>
              <th class="p-3">名称 / 路径</th>
              <th class="p-3">类型</th>
              <th class="p-3">规格</th>
              <th class="p-3">编码</th>
              <th class="p-3">动态范围</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in group.items" :key="item.emby_id" 
                class="border-t border-gray-100/5 hover:bg-white/5 transition-colors"
                :class="{'bg-red-500/10': selectedIds.includes(item.emby_id)}">
              <td class="p-3 text-center">
                <input type="checkbox" :value="item.emby_id" v-model:selectedIds="selectedIds" class="w-4 h-4" />
              </td>
              <td class="p-3">
                <div class="font-medium text-sm">{{ item.name }}</div>
                <div class="text-xs text-gray-500 font-mono truncate max-w-md">{{ item.path }}</div>
              </td>
              <td class="p-3 text-xs">{{ item.type }}</td>
              <td class="p-3"><n-tag size="mini" :bordered="false">{{ item.display_title }}</n-tag></td>
              <td class="p-3 text-xs">{{ item.video_codec }}</td>
              <td class="p-3 text-xs">
                <n-tag v-if="item.video_range && item.video_range !== 'SDR'" size="mini" type="warning" :bordered="false">{{ item.video_range }}</n-tag>
                <span v-else class="text-gray-500">{{ item.video_range }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </n-card>
    </div>

    <!-- 无数据展示 -->
    <div v-else-if="!syncing" class="flex flex-col items-center justify-center py-20 bg-white/5 rounded-xl border-2 border-dashed border-white/10 text-gray-500">
      <n-icon size="48" class="mb-4 opacity-20"><CopyIcon /></n-icon>
      <p>暂无重复项数据</p>
      <p class="text-sm">点击上方“执行同步”或“执行搜索”开始</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import axios from 'axios';
import { NButton, NIcon, NCard, NTag, NSpace } from 'naive-ui';
import { 
  SyncOutlined as SyncIcon,
  SearchOutlined as SearchIcon,
  DeleteOutlined as DeleteIcon,
  ScienceOutlined as LabIcon,
  ClearOutlined as ClearIcon,
  ContentCopyOutlined as CopyIcon
} from '@vicons/material';

const syncing = ref(false);
const duplicateGroups = ref<any[]>([]);
const selectedIds = ref<string[]>([]);
const suggestedCount = ref(0);

const fetchDuplicates = async () => {
  try {
    const res = await axios.get('/api/dedupe/duplicates');
    duplicateGroups.value = res.data;
    selectedIds.value = []; // 重置选中
  } catch (error) {
    alert('获取重复项失败');
  }
};

const syncMedia = async () => {
  if (!confirm('全量同步可能需要一些时间（取决于媒体库大小），确定开始吗？')) return;
  syncing.value = true;
  try {
    await axios.post('/api/dedupe/sync', { item_types: ['Movie', 'Series'] });
    alert('同步完成');
    await fetchDuplicates();
  } catch (error) {
    alert('同步失败');
  } finally {
    syncing.value = false;
  }
};

const autoSelect = async () => {
  if (duplicateGroups.value.length === 0) return;
  
  // 展平所有 item
  const allItems = duplicateGroups.value.flatMap(g => g.items);
  try {
    const res = await axios.post('/api/dedupe/smart-select', { items: allItems });
    selectedIds.value = res.data.to_delete;
    suggestedCount.value = selectedIds.length;
  } catch (error) {
    alert('智能选中算法执行失败');
  }
};

const confirmDelete = async () => {
  if (!confirm(`确定要永久删除选中的 ${selectedIds.value.length} 个项目吗？此操作无法撤销，文件将从磁盘移除。`)) return;
  
  try {
    const res = await axios.delete('/api/dedupe/items', { data: { item_ids: selectedIds.value } });
    alert(`清理完成: 成功 ${res.data.success}, 失败 ${res.data.total - res.data.success}`);
    await fetchDuplicates();
  } catch (error) {
    alert('删除请求执行失败');
  }
};

onMounted(() => {
  fetchDuplicates();
});
</script>

<style scoped>
.dedupe-container {
  max-width: 1200px;
  margin: 0 auto;
}
</style>