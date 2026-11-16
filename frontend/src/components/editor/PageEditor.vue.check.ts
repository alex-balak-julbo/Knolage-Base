
import Image from '@tiptap/extension-image'
import Link from '@tiptap/extension-link'
import ListItem from '@tiptap/extension-list-item'
import Placeholder from '@tiptap/extension-placeholder'
import StarterKit from '@tiptap/starter-kit'
import { Editor, EditorContent } from '@tiptap/vue-3'
import { onBeforeUnmount, ref, shallowRef } from 'vue'
import { assetsApi } from '../../api/endpoints'
import { t } from '../../i18n'
import { normalizeHref, type DocNode } from '../../lib/doc'
import { usePageStore } from '../../stores/page'
import { useTemplatesStore } from '../../stores/templates'
import { useTreeStore } from '../../stores/tree'
import { useUiStore } from '../../stores/ui'
import { PageLink } from './extensions/PageLink'
import { SlashCommand, type SlashItem } from './extensions/SlashCommand'
import SlashMenu from './SlashMenu.vue'

const props = defineProps<{ pageId: string; doc: DocNode }>()

const page = usePageStore()
const tree = useTreeStore()
const ui = useUiStore()
const templates = useTemplatesStore()

const uploading = ref(0)
const fileInput = ref<HTMLInputElement | null>(null)
const editor = shallowRef<Editor>()

// ---- actions shared by the toolbar and the "/" menu ----
function pickImage() {
  fileInput.value?.click()
}

async function uploadImages(files: File[], pos?: number) {
  for (const file of files) {
    uploading.value++
    try {
      const res = await assetsApi.upload(file, props.pageId)
      const image = { type: 'image', attrs: { src: res.url, alt: file.name } }
      const chain = editor.value!.chain().focus()
      if (pos !== undefined) chain.insertContentAt(pos, image)
      else chain.insertContent(image)
      chain.run()
    } catch {
      ui.toast(t('upload.error'))
    } finally {
      uploading.value--
    }
  }
}

function onFilesChosen(e: Event) {
  const input = e.target as HTMLInputElement
  void uploadImages(Array.from(input.files ?? []))
  input.value = ''
}

async function insertSubPage() {
  const parent = page.current
  if (!parent) return
  const picked = await ui.pickTemplate({ parentName: parent.name, title: t('dlg.newSubPage') })
  if (!picked) return
  try {
    await page.flush() // settle any in-flight save of this page first
    const name = picked.name.trim() || templates.byId.get(picked.templateId)?.name || t('page.untitled')
    // link:false -> the editor places the pageLink at the cursor; the next save never duplicates it
    const child = await tree.create({ type: 'page', name, parent_id: parent.id, template_id: picked.templateId, link: false })
    editor.value?.chain().focus().insertContent({ type: 'pageLink', attrs: { pageId: child.id } }).run()
  } catch (e) {
    ui.toastError(e)
  }
}

async function editLink() {
  const ed = editor.value
  if (!ed) return
  const current = ed.getAttributes('link').href as string | undefined
  const raw = await ui.prompt({ title: t('dlg.link'), initial: current ?? 'https://', hint: t('dlg.linkHint'), allowEmpty: true })
  if (raw === undefined) return
  if (raw === '' || raw === 'https://') {
    ed.chain().focus().extendMarkRange('link').unsetLink().run()
    return
  }
  const href = normalizeHref(raw)
  if (!href) return void ui.toast(t('dlg.linkInvalid'))
  ed.chain().focus().extendMarkRange('link').setLink({ href }).run()
}

const slashItems = (): SlashItem[] => [
  { id: 'text', label: t('slash.text'), icon: '¶', keywords: 'paragraph text texte', run: (e) => void e.chain().focus().setParagraph().run() },
  { id: 'h1', label: t('slash.h1'), icon: 'H1', keywords: 'heading title titre', run: (e) => void e.chain().focus().setHeading({ level: 1 }).run() },
  { id: 'h2', label: t('slash.h2'), icon: 'H2', keywords: 'heading title titre', run: (e) => void e.chain().focus().setHeading({ level: 2 }).run() },
  { id: 'ul', label: t('slash.bullet'), icon: '•', keywords: 'list bullet liste puces', run: (e) => void e.chain().focus().toggleBulletList().run() },
  { id: 'ol', label: t('slash.ordered'), icon: '1.', keywords: 'list numbered liste numerotee', run: (e) => void e.chain().focus().toggleOrderedList().run() },
  { id: 'img', label: t('slash.image'), icon: '🖼', keywords: 'image picture photo', run: () => pickImage() },
  { id: 'page', label: t('slash.subpage'), icon: '📄', keywords: 'page sub subpage sous-page', run: () => void insertSubPage() },
]

const imageFiles = (dt: DataTransfer | null) => Array.from(dt?.files ?? []).filter((f) => f.type.startsWith('image/'))

// The extension set mirrors the server whitelist: paragraph, headings 1-2, lists, image, pageLink; bold, italic, link.
editor.value = new Editor({
  content: props.doc,
  extensions: [
    StarterKit.configure({ heading: { levels: [1, 2] }, blockquote: false, code: false, codeBlock: false, horizontalRule: false, strike: false, listItem: false }),
    // list items may only hold a paragraph followed by nested lists (what the server accepts)
    ListItem.extend({ content: 'paragraph (bulletList | orderedList)*' }),
    Link.configure({ openOnClick: false, autolink: true, protocols: ['mailto'], HTMLAttributes: { rel: 'noopener noreferrer', target: '_blank' } }),
    Image,
    Placeholder.configure({ placeholder: () => t('editor.placeholder') }),
    PageLink,
    SlashCommand.configure({ items: slashItems }),
  ],
  editorProps: {
    attributes: { class: 'doc-editor', spellcheck: 'true' },
    handlePaste: (_view, event) => {
      const files = imageFiles(event.clipboardData)
      if (!files.length) return false
      void uploadImages(files)
      return true
    },
    handleDrop: (view, event, _slice, moved) => {
      if (moved) return false
      const files = imageFiles(event.dataTransfer)
      if (!files.length) return false
      event.preventDefault()
      void uploadImages(files, view.posAtCoords({ left: event.clientX, top: event.clientY })?.pos)
      return true
    },
  },
  onUpdate: ({ editor: ed }) => page.schedule({ content: ed.getJSON() as DocNode }),
})

onBeforeUnmount(() => editor.value?.destroy())

interface Btn {
  id: string
  label: string
  text: string
  active: () => boolean
  run: () => void
}
const buttons: Btn[] = [
  { id: 'p', label: t('tb.text'), text: '¶', active: () => !!editor.value?.isActive('paragraph'), run: () => void editor.value?.chain().focus().setParagraph().run() },
  { id: 'h1', label: t('slash.h1'), text: 'H1', active: () => !!editor.value?.isActive('heading', { level: 1 }), run: () => void editor.value?.chain().focus().toggleHeading({ level: 1 }).run() },
  { id: 'h2', label: t('slash.h2'), text: 'H2', active: () => !!editor.value?.isActive('heading', { level: 2 }), run: () => void editor.value?.chain().focus().toggleHeading({ level: 2 }).run() },
  { id: 'b', label: t('tb.bold'), text: 'B', active: () => !!editor.value?.isActive('bold'), run: () => void editor.value?.chain().focus().toggleBold().run() },
  { id: 'i', label: t('tb.italic'), text: 'I', active: () => !!editor.value?.isActive('italic'), run: () => void editor.value?.chain().focus().toggleItalic().run() },
  { id: 'ul', label: t('slash.bullet'), text: '•', active: () => !!editor.value?.isActive('bulletList'), run: () => void editor.value?.chain().focus().toggleBulletList().run() },
  { id: 'ol', label: t('slash.ordered'), text: '1.', active: () => !!editor.value?.isActive('orderedList'), run: () => void editor.value?.chain().focus().toggleOrderedList().run() },
  { id: 'link', label: t('tb.link'), text: '🔗', active: () => !!editor.value?.isActive('link'), run: () => void editLink() },
  { id: 'img', label: t('slash.image'), text: '🖼', active: () => false, run: pickImage },
  { id: 'page', label: t('slash.subpage'), text: '📄', active: () => false, run: () => void insertSubPage() },
]
