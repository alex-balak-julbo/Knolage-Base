<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import AppShell from './components/layout/AppShell.vue'
import DialogHost from './components/dialogs/DialogHost.vue'
import ToastHost from './components/common/ToastHost.vue'
import { usePageStore } from './stores/page'

const route = useRoute()
const bare = computed(() => route.meta.public === true)
const page = usePageStore()

// last-chance save when the tab is closed or reloaded
const onUnload = () => page.flushKeepalive()
onMounted(() => window.addEventListener('beforeunload', onUnload))
onBeforeUnmount(() => window.removeEventListener('beforeunload', onUnload))
</script>

<template>
  <RouterView v-if="bare" />
  <AppShell v-else><RouterView /></AppShell>
  <DialogHost />
  <ToastHost />
</template>
