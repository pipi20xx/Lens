<script setup lang="ts">
import { useConfirm } from '@/composables'
import GlassDialog from '@/components/common/GlassDialog.vue'

const { show, options, onConfirm, onCancel } = useConfirm()
</script>

<template>
  <GlassDialog v-model="show" :max-width="420" :scrollable="false"
    :title="options.title" :cancel-text="options.cancelText"
    @cancel="onCancel"
  >
    {{ options.content }}
    <template #actions>
      <v-btn :color="options.confirmColor" variant="flat" prepend-icon="mdi-check" @click="onConfirm">
        {{ options.confirmText }}
      </v-btn>
    </template>
  </GlassDialog>
</template>
