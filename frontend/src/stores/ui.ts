import { defineStore } from 'pinia'
import { ref, shallowRef } from 'vue'
import { ApiError } from '../api/client.ts'
import { t } from '../i18n.ts'

export type Theme = 'system' | 'light' | 'dark'
export type DialogKind = 'prompt' | 'confirm' | 'template' | 'move' | 'export' | 'conflict'

export interface Toast {
  id: number
  message: string
  action?: { label: string; run: () => void | Promise<void> }
}

interface DialogState {
  id: number
  kind: DialogKind
  props: Record<string, unknown>
  resolve: (value: unknown) => void
}

const THEME_KEY = 'docbase.theme'

function readTheme(): Theme {
  try {
    const v = localStorage.getItem(THEME_KEY)
    if (v === 'light' || v === 'dark' || v === 'system') return v
  } catch {
    /* storage unavailable */
  }
  return 'system'
}

export const useUiStore = defineStore('ui', () => {
  const theme = ref<Theme>(readTheme())
  const toasts = ref<Toast[]>([])
  const dialog = shallowRef<DialogState | null>(null)
  const sidebarOpen = ref(false)
  let toastSeq = 0
  let dialogSeq = 0

  // ---- theme ----
  function applyTheme(): void {
    const dark = theme.value === 'dark' || (theme.value === 'system' && matchMedia('(prefers-color-scheme: dark)').matches)
    document.documentElement.classList.toggle('dark', dark)
  }
  function setTheme(next: Theme): void {
    theme.value = next
    try {
      localStorage.setItem(THEME_KEY, next)
    } catch {
      /* ignore */
    }
    applyTheme()
  }
  function initTheme(): void {
    applyTheme()
    matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => theme.value === 'system' && applyTheme())
  }

  // ---- toasts ----
  function dismissToast(id: number): void {
    toasts.value = toasts.value.filter((x) => x.id !== id)
  }
  function toast(message: string, action?: Toast['action'], timeout?: number): number {
    const id = ++toastSeq
    toasts.value = [...toasts.value, { id, message, action }]
    setTimeout(() => dismissToast(id), timeout ?? (action ? 8000 : 4000))
    return id
  }
  function toastError(e: unknown): void {
    if (e instanceof ApiError) {
      const known = ['cycle', 'invalid_parent', 'max_depth'].includes(e.code ?? '')
      toast(known ? t(`err.${e.code}`) : e.detail || e.message)
    } else {
      toast(t('toast.error'))
    }
  }

  // ---- dialogs (promise based) ----
  function ask<T>(kind: DialogKind, props: Record<string, unknown> = {}): Promise<T | undefined> {
    dialog.value?.resolve(undefined)
    return new Promise<T | undefined>((resolve) => {
      dialog.value = { id: ++dialogSeq, kind, props, resolve: resolve as (v: unknown) => void }
    })
  }
  function close(value?: unknown): void {
    const d = dialog.value
    dialog.value = null
    d?.resolve(value)
  }

  const prompt = (props: { title: string; label?: string; initial?: string; placeholder?: string; hint?: string; confirmLabel?: string; allowEmpty?: boolean }) =>
    ask<string>('prompt', props)
  const confirm = async (props: { title: string; message: string; confirmLabel: string; danger?: boolean }) =>
    (await ask<boolean>('confirm', props)) === true
  const pickTemplate = (props: { parentName: string; title?: string }) =>
    ask<{ templateId: string; name: string }>('template', props)
  const pickFolder = (props: { nodeId: string }) => ask<{ parentId: string | null }>('move', props)
  const exportNode = (props: { nodeId: string }) => ask<boolean>('export', props)
  const conflict = () => ask<'reload' | 'overwrite'>('conflict')

  return {
    theme, toasts, dialog, sidebarOpen,
    setTheme, initTheme, toast, toastError, dismissToast, ask, close, prompt, confirm, pickTemplate, pickFolder, exportNode, conflict,
  }
})
