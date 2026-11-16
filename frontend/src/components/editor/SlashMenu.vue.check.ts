
import { computed } from 'vue'
import { slashState } from './extensions/SlashCommand'

const style = computed(() => {
  const r = slashState.rect
  if (!r) return { display: 'none' }
  const left = Math.max(8, Math.min(r.left, innerWidth - 232))
  const below = r.bottom + 6
  const top = below + 280 > innerHeight ? Math.max(8, r.top - 6 - Math.min(280, slashState.items.length * 36 + 8)) : below
  return { left: left + 'px', top: top + 'px' }
})
