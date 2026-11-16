import { Extension, type Editor } from '@tiptap/core'
import Suggestion from '@tiptap/suggestion'
import { reactive } from 'vue'
import { fold } from '../../../lib/search'

export interface SlashItem {
  id: string
  label: string
  icon: string
  keywords: string
  run: (editor: Editor) => void
}

/** Shared, reactive state read by SlashMenu.vue (one editor is open at a time). */
export const slashState = reactive({
  open: false,
  items: [] as SlashItem[],
  index: 0,
  rect: null as DOMRect | null,
  select: (_item: SlashItem): void => {},
})

export const SlashCommand = Extension.create<{ items: () => SlashItem[] }>({
  name: 'slashCommand',

  addOptions() {
    return { items: () => [] }
  },

  addProseMirrorPlugins() {
    return [
      Suggestion({
        editor: this.editor,
        char: '/',
        startOfLine: false,
        items: ({ query }: { query: string }) => {
          const q = fold(query)
          return this.options.items().filter((i) => fold(`${i.label} ${i.keywords}`).includes(q))
        },
        command: ({ editor, range, props }: { editor: Editor; range: { from: number; to: number }; props: SlashItem }) => {
          editor.chain().focus().deleteRange(range).run()
          props.run(editor)
        },
        render: () => {
          const sync = (p: { items: SlashItem[]; clientRect?: (() => DOMRect | null) | null; command: (i: SlashItem) => void }) => {
            slashState.items = p.items
            slashState.rect = p.clientRect?.() ?? null
            slashState.select = (item) => p.command(item)
          }
          return {
            onStart: (p: any) => {
              sync(p)
              slashState.index = 0
              slashState.open = true
            },
            onUpdate: (p: any) => {
              sync(p)
              slashState.index = Math.min(slashState.index, Math.max(0, p.items.length - 1))
            },
            onKeyDown: ({ event }: { event: KeyboardEvent }) => {
              const n = slashState.items.length
              if (!slashState.open || !n) return false
              if (event.key === 'ArrowDown') { slashState.index = (slashState.index + 1) % n; return true }
              if (event.key === 'ArrowUp') { slashState.index = (slashState.index - 1 + n) % n; return true }
              if (event.key === 'Enter' || event.key === 'Tab') { slashState.select(slashState.items[slashState.index]); return true }
              return false
            },
            onExit: () => {
              slashState.open = false
              slashState.items = []
            },
          }
        },
      }),
    ]
  },
})
