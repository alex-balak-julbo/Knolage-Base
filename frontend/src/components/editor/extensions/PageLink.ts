import { mergeAttributes, Node } from '@tiptap/core'
import { VueNodeViewRenderer } from '@tiptap/vue-3'
import PageLinkView from '../PageLinkView.vue'

/** Block node pointing to a sub-page: { type: 'pageLink', attrs: { pageId } } (see backend content whitelist). */
export const PageLink = Node.create({
  name: 'pageLink',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: false,

  addAttributes() {
    return {
      pageId: {
        default: null,
        parseHTML: (el: HTMLElement) => el.getAttribute('data-page-id'),
        renderHTML: (attrs: Record<string, unknown>) => ({ 'data-page-id': attrs.pageId as string }),
      },
    }
  },
  parseHTML() {
    return [{ tag: 'div[data-page-link]' }]
  },
  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes(HTMLAttributes, { 'data-page-link': '' })]
  },
  addNodeView() {
    return VueNodeViewRenderer(PageLinkView)
  },
})
