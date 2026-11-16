import type { DocNode } from '../lib/doc.ts'
import type { TreeNode } from '../lib/tree.ts'

export type { TreeNode }

export interface User {
  id: string
  email: string
  display_name: string
  role: 'admin' | 'editor' | 'reader'
}

export interface LoginResponse {
  access_token: string
  token_type: 'Bearer'
  expires_in: number
  user: User
}

export interface NodeFull {
  id: string
  type: 'folder' | 'page'
  parent_id: string | null
  name: string
  icon: string | null
  position: number
  template_id: string | null
  version: number
  created_at: string
  updated_at: string
  props?: Record<string, string>
  content?: DocNode | null
  /** pages whose content the server changed as a side effect (sub-page links) */
  affected_ids?: string[]
  /** sub-pages the server moved to the trash because their link was removed */
  deleted_ids?: string[]
  restored?: number
}

export interface PropField {
  key: string
  label: string
  type: 'text' | 'select'
  options?: string[]
}

export interface Template {
  id: string
  name: string
  description: string
  icon: string
  props_schema: PropField[]
  default_content: DocNode
  is_system: boolean
}

export interface SearchItem {
  id: string
  name: string
  icon: string | null
  template_id: string | null
  path: { id: string; name: string; type: string }[]
  snippet: string
  matches: [number, number][]
  title_match: boolean
  updated_at: string
}

export type SearchScope = 'all' | 'title' | 'content'

export interface TrashItem extends TreeNode {
  deleted_at: string
}

export interface CreateNodeInput {
  type: 'folder' | 'page'
  name: string
  parent_id?: string | null
  template_id?: string
  props?: Record<string, string>
  content?: DocNode
  icon?: string | null
  id?: string
  /** false when the editor inserts the pageLink itself */
  link?: boolean
}

export interface MoveInput {
  parent_id: string | null
  before_id?: string
  after_id?: string
}
