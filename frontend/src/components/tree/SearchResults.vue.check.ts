
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { t } from '../../i18n'
import { findMatches, splitHighlight } from '../../lib/search'
import { useSearchStore } from '../../stores/search'
import { useTemplatesStore } from '../../stores/templates'
import { useUiStore } from '../../stores/ui'

const search = useSearchStore()
const templates = useTemplatesStore()
const ui = useUiStore()
const q = computed(() => search.query.trim())
const countLabel = computed(() => (search.total === 1 ? t('search.one') : t('search.many', { n: search.total })))
