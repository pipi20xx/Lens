<script setup lang="ts">
import { useConfirm } from '@/composables'

const { show, options, onConfirm, onCancel } = useConfirm()
</script>

<template>
  <v-dialog v-model="show" max-width="420">
    <v-card rounded="xl" class="pa-2">
      <v-card-title class="text-h6 font-weight-bold pa-4">
        {{ options.title }}
      </v-card-title>
      <v-card-text class="px-4 pb-2">
        {{ options.content }}
      </v-card-text>
      <v-card-actions class="px-4 pb-4">
        <v-spacer />
        <v-btn variant="tonal" color="grey" prepend-icon="mdi-close" @click="onCancel">
          {{ options.cancelText }}
        </v-btn>
        <v-btn :color="options.confirmColor" variant="flat" prepend-icon="mdi-check" @click="onConfirm">
          {{ options.confirmText }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
