import { ref } from 'vue'

type Dict = Record<string, string>
export type Locale = 'fr' | 'en'

const fr: Dict = {
  'app.title': 'Base documentaire',
  'nav.newFolder': '+ Dossier', 'nav.newPage': '+ Page',
  'search.placeholder': 'Rechercher…', 'search.scope.all': 'Titre + contenu', 'search.scope.title': 'Titre seul',
  'search.scope.content': 'Contenu seul', 'search.inFolder': 'Dans le dossier sélectionné', 'search.none': 'Aucun résultat',
  'search.tooShort': 'Tapez au moins 2 caractères', 'search.one': '1 résultat', 'search.many': '{n} résultats',
  'search.clear': 'Effacer la recherche', 'search.error': 'La recherche a échoué',
  'tree.empty': 'Aucun élément. Créez un dossier ou une page.', 'tree.dropRoot': 'Déposer ici pour placer à la racine',
  'tree.label': 'Arborescence', 'tree.more': 'Actions', 'tree.add': 'Ajouter',
  'menu.newPage': 'Nouvelle page', 'menu.newFolder': 'Nouveau dossier', 'menu.rename': 'Renommer',
  'menu.move': 'Déplacer vers…', 'menu.export': 'Exporter', 'menu.delete': 'Supprimer',
  'dlg.cancel': 'Annuler', 'dlg.ok': 'OK', 'dlg.close': 'Fermer', 'dlg.create': 'Créer',
  'dlg.folderName': 'Nom du dossier', 'dlg.rename': 'Renommer', 'dlg.newPage': 'Nouvelle page',
  'dlg.newSubPage': 'Nouvelle sous-page', 'dlg.pageTitle': 'Titre (facultatif)',
  'dlg.chooseTemplate': 'Choisissez un modèle', 'dlg.in': 'Dans : {name}', 'dlg.moveTo': 'Déplacer « {name} » vers…',
  'dlg.export': 'Exporter « {name} »', 'dlg.download': 'Télécharger', 'dlg.zipHint': 'Archive ZIP : un fichier .md par page, images dans assets/',
  'dlg.link': 'Adresse du lien', 'dlg.linkHint': 'Laisser vide pour retirer le lien', 'dlg.linkInvalid': 'Adresse invalide (http, https ou mailto)',
  'confirm.deleteTitle': 'Supprimer ?', 'confirm.deleteOne': '« {name} » sera placé dans la corbeille.',
  'confirm.deleteMany': '« {name} » et ses {n} sous-éléments seront placés dans la corbeille.',
  'confirm.purgeTitle': 'Supprimer définitivement ?', 'confirm.purgeMsg': 'Cette action est irréversible.',
  'confirm.emptyTitle': 'Vider la corbeille ?', 'confirm.emptyMsg': 'Tous les éléments seront supprimés définitivement.',
  'confirm.subpage': 'La sous-page « {name} » sera placée dans la corbeille.',
  'toast.moved': '« {name} » déplacé vers « {to} »', 'toast.movedRoot': '« {name} » déplacé à la racine',
  'toast.reordered': 'Ordre modifié', 'toast.deleted': '« {name} » placé dans la corbeille', 'toast.undo': 'Annuler',
  'toast.restored': 'Restauré', 'toast.subDeleted': 'Sous-page placée dans la corbeille',
  'toast.moveError': 'Déplacement impossible : {reason}', 'toast.error': 'Une erreur est survenue',
  'err.cycle': 'un dossier ne peut pas être déplacé dans lui-même', 'err.invalid_parent': 'un dossier ne peut pas être placé dans une page',
  'err.max_depth': 'profondeur maximale de dossiers atteinte', 'err.self': 'même élément', 'err.not_found': 'élément introuvable',
  'page.untitled': 'Sans titre', 'page.titlePlaceholder': 'Titre de la page', 'page.notFound': 'Page introuvable',
  'page.saved': 'Enregistré', 'page.saving': 'Enregistrement…', 'page.dirty': 'Modifications en attente',
  'page.error': 'Échec de l’enregistrement', 'page.conflict': 'Conflit de version', 'page.retry': 'Réessayer',
  'page.export': 'Exporter', 'page.delete': 'Supprimer', 'page.loading': 'Chargement…',
  'conflict.title': 'La page a été modifiée ailleurs', 'conflict.msg': 'Une version plus récente existe. Que voulez-vous faire ?',
  'conflict.reload': 'Recharger (perdre mes changements)', 'conflict.overwrite': 'Écraser avec ma version',
  'editor.placeholder': 'Tapez « / » pour insérer un bloc…', 'editor.hint': '« / » insère un bloc · Ctrl+V colle une image',
  'slash.text': 'Texte', 'slash.h1': 'Titre 1', 'slash.h2': 'Titre 2', 'slash.bullet': 'Liste à puces',
  'slash.ordered': 'Liste numérotée', 'slash.image': 'Image', 'slash.subpage': 'Sous-page',
  'tb.bold': 'Gras', 'tb.italic': 'Italique', 'tb.link': 'Lien', 'tb.text': 'Texte',
  'upload.busy': 'Envoi de l’image…', 'upload.error': 'Échec de l’envoi de l’image',
  'trash.title': 'Corbeille', 'trash.empty': 'La corbeille est vide', 'trash.restore': 'Restaurer',
  'trash.purge': 'Supprimer définitivement', 'trash.emptyAll': 'Vider la corbeille', 'trash.deletedOn': 'Supprimé le {date}',
  'login.title': 'Connexion', 'login.email': 'E-mail', 'login.password': 'Mot de passe', 'login.submit': 'Se connecter',
  'login.bad': 'E-mail ou mot de passe incorrect', 'login.tooMany': 'Trop de tentatives, réessayez dans une minute',
  'home.welcome': 'Bienvenue', 'home.recent': 'Pages récentes', 'home.hint': 'Sélectionnez une page dans l’arborescence, ou créez-en une.',
  'home.none': 'Aucune page pour le moment.',
  'footer.theme': 'Thème', 'theme.system': 'Système', 'theme.light': 'Clair', 'theme.dark': 'Sombre',
  'footer.logout': 'Se déconnecter', 'footer.lang': 'Langue', 'footer.trash': 'Corbeille',
  'crumb.root': 'Racine', 'nav.menu': 'Menu',
}

const en: Dict = {
  'app.title': 'Documentation base',
  'nav.newFolder': '+ Folder', 'nav.newPage': '+ Page',
  'search.placeholder': 'Search…', 'search.scope.all': 'Title + content', 'search.scope.title': 'Title only',
  'search.scope.content': 'Content only', 'search.inFolder': 'In the selected folder', 'search.none': 'No results',
  'search.tooShort': 'Type at least 2 characters', 'search.one': '1 result', 'search.many': '{n} results',
  'search.clear': 'Clear search', 'search.error': 'Search failed',
  'tree.empty': 'Nothing here yet. Create a folder or a page.', 'tree.dropRoot': 'Drop here to move to the root',
  'tree.label': 'Tree', 'tree.more': 'Actions', 'tree.add': 'Add',
  'menu.newPage': 'New page', 'menu.newFolder': 'New folder', 'menu.rename': 'Rename',
  'menu.move': 'Move to…', 'menu.export': 'Export', 'menu.delete': 'Delete',
  'dlg.cancel': 'Cancel', 'dlg.ok': 'OK', 'dlg.close': 'Close', 'dlg.create': 'Create',
  'dlg.folderName': 'Folder name', 'dlg.rename': 'Rename', 'dlg.newPage': 'New page',
  'dlg.newSubPage': 'New sub-page', 'dlg.pageTitle': 'Title (optional)',
  'dlg.chooseTemplate': 'Choose a template', 'dlg.in': 'In: {name}', 'dlg.moveTo': 'Move “{name}” to…',
  'dlg.export': 'Export “{name}”', 'dlg.download': 'Download', 'dlg.zipHint': 'ZIP archive: one .md file per page, images in assets/',
  'dlg.link': 'Link address', 'dlg.linkHint': 'Leave empty to remove the link', 'dlg.linkInvalid': 'Invalid address (http, https or mailto)',
  'confirm.deleteTitle': 'Delete?', 'confirm.deleteOne': '“{name}” will be moved to the trash.',
  'confirm.deleteMany': '“{name}” and its {n} sub-items will be moved to the trash.',
  'confirm.purgeTitle': 'Delete permanently?', 'confirm.purgeMsg': 'This cannot be undone.',
  'confirm.emptyTitle': 'Empty the trash?', 'confirm.emptyMsg': 'Everything in it will be deleted permanently.',
  'confirm.subpage': 'The sub-page “{name}” will be moved to the trash.',
  'toast.moved': '“{name}” moved to “{to}”', 'toast.movedRoot': '“{name}” moved to the root',
  'toast.reordered': 'Order changed', 'toast.deleted': '“{name}” moved to the trash', 'toast.undo': 'Undo',
  'toast.restored': 'Restored', 'toast.subDeleted': 'Sub-page moved to the trash',
  'toast.moveError': 'Cannot move: {reason}', 'toast.error': 'Something went wrong',
  'err.cycle': 'a folder cannot be moved into itself', 'err.invalid_parent': 'a folder cannot be placed inside a page',
  'err.max_depth': 'maximum folder depth reached', 'err.self': 'same item', 'err.not_found': 'item not found',
  'page.untitled': 'Untitled', 'page.titlePlaceholder': 'Page title', 'page.notFound': 'Page not found',
  'page.saved': 'Saved', 'page.saving': 'Saving…', 'page.dirty': 'Changes pending',
  'page.error': 'Could not save', 'page.conflict': 'Version conflict', 'page.retry': 'Retry',
  'page.export': 'Export', 'page.delete': 'Delete', 'page.loading': 'Loading…',
  'conflict.title': 'This page was changed elsewhere', 'conflict.msg': 'A newer version exists. What do you want to do?',
  'conflict.reload': 'Reload (lose my changes)', 'conflict.overwrite': 'Overwrite with my version',
  'editor.placeholder': 'Type “/” to insert a block…', 'editor.hint': '“/” inserts a block · Ctrl+V pastes an image',
  'slash.text': 'Text', 'slash.h1': 'Heading 1', 'slash.h2': 'Heading 2', 'slash.bullet': 'Bulleted list',
  'slash.ordered': 'Numbered list', 'slash.image': 'Image', 'slash.subpage': 'Sub-page',
  'tb.bold': 'Bold', 'tb.italic': 'Italic', 'tb.link': 'Link', 'tb.text': 'Text',
  'upload.busy': 'Uploading image…', 'upload.error': 'Image upload failed',
  'trash.title': 'Trash', 'trash.empty': 'The trash is empty', 'trash.restore': 'Restore',
  'trash.purge': 'Delete permanently', 'trash.emptyAll': 'Empty trash', 'trash.deletedOn': 'Deleted on {date}',
  'login.title': 'Sign in', 'login.email': 'Email', 'login.password': 'Password', 'login.submit': 'Sign in',
  'login.bad': 'Wrong email or password', 'login.tooMany': 'Too many attempts, try again in a minute',
  'home.welcome': 'Welcome', 'home.recent': 'Recent pages', 'home.hint': 'Pick a page in the tree, or create one.',
  'home.none': 'No pages yet.',
  'footer.theme': 'Theme', 'theme.system': 'System', 'theme.light': 'Light', 'theme.dark': 'Dark',
  'footer.logout': 'Sign out', 'footer.lang': 'Language', 'footer.trash': 'Trash',
  'crumb.root': 'Root', 'nav.menu': 'Menu',
}

const dicts: Record<Locale, Dict> = { fr, en }
const KEY = 'docbase.locale'

function initial(): Locale {
  try {
    const saved = localStorage.getItem(KEY)
    if (saved === 'fr' || saved === 'en') return saved
  } catch {
    /* storage unavailable */
  }
  return typeof navigator !== 'undefined' && navigator.language.toLowerCase().startsWith('en') ? 'en' : 'fr'
}

export const locale = ref<Locale>(initial())

export function setLocale(l: Locale): void {
  locale.value = l
  try {
    localStorage.setItem(KEY, l)
  } catch {
    /* ignore */
  }
  document.documentElement.lang = l
}

/** Translate a key; {name}-style placeholders are replaced. Reactive: reads `locale` while rendering. */
export function t(key: string, params?: Record<string, string | number>): string {
  let s = dicts[locale.value][key] ?? fr[key] ?? key
  if (params) for (const [k, v] of Object.entries(params)) s = s.split(`{${k}}`).join(String(v))
  return s
}

export const dictionaries = dicts
