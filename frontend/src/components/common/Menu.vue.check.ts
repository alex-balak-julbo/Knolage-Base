
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import type { MenuItem } from './types'

const props = defineProps<{ x: number; y: number; items: MenuItem[] }>()
const emit = defineEmits<{ (e: 'close'): void }>()

const el = ref<HTMLElement | null>(null)
const pos = ref({ left: props.x, top: props.y })

function onPointerDown(e: PointerEvent) {
  if (!el.value?.contains(e.target as Node)) emit('close')
}
function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') return emit('close')
  if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return
  e.preventDefault()
  const btns = Array.from(el.value?.querySelectorAll<HTMLButtonElement>('button') ?? [])
  const i = btns.indexOf(document.activeElement as HTMLButtonElement)
  btns[(i + (e.key === 'ArrowDown' ? 1 : -1) + btns.length) % btns.length]?.focus()
}
async function run(item: MenuItem) {
  emit('close')
  await item.run()
}
const onResize = () => emit('close')

onMounted(async () => {
  document.addEventListener('pointerdown', onPointerDown, true)
  document.addEventListener('keydown', onKey)
  window.addEventListener('resize', onResize)
  await nextTick()
  const r = el.value?.getBoundingClientRect()
  if (r) pos.value = { left: Math.max(8, Math.min(props.x, innerWidth - r.width - 8)), top: Math.max(8, Math.min(props.y, innerHeight - r.height - 8)) }
  el.value?.querySelector<HTMLButtonElement>('button')?.focus()
})
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onPointerDown, true)
  document.removeEventListener('keydown', onKey)
  window.removeEventListener('resize', onResize)
})
