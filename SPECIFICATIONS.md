# Cahier des charges — Application de base documentaire

| | |
|---|---|
| **Document** | specification_documentation.md |
| **Version** | 1.0 (brouillon à valider) |
| **Date** | 13 novembre 2026 |
| **Statut** | Prototype HTML disponible (v2), développement à planifier |
| **Langue de l'application** | Français |

---

## 1. Contexte et objectifs

### 1.1 Contexte

Le besoin est de disposer d'une application de prise de notes servant de **base documentaire de procédures** (informatique, ressources humaines, etc.). L'outil doit rester simple, proche de Notion dans son principe (pages composées de blocs), mais **sans la complexité** d'un outil généraliste.

### 1.2 Objectifs

1. Rédiger des procédures lisibles : titres, listes, images collées, sous-pages.
2. Organiser la connaissance dans une **arborescence claire** de dossiers et de pages.
3. Standardiser la rédaction grâce à des **modèles** (premier modèle : *Procédure*).
4. **Retrouver** une information rapidement (recherche par titre, par contenu, ou sur toute la base).
5. **Exporter** le contenu (Markdown, HTML, texte) pour le réutiliser ou l'archiver.

### 1.3 Ce qui change par rapport à la première version

| Demande | Impact |
|---|---|
| Ajouter une page **directement dans un dossier** | Une page n'a plus besoin d'une « sélection » intermédiaire |
| Créer des **dossiers dans des dossiers** | L'arborescence devient **récursive** (profondeur libre, avec une limite raisonnable) |
| **Glisser-déposer** les pages dans les dossiers depuis la liste de gauche | Nouveau comportement central de l'arbre : déplacement, réordonnancement, règles de validité |

---

## 2. Périmètre

### 2.1 Inclus

- Arborescence récursive de dossiers et de pages, avec glisser-déposer.
- Éditeur de pages par blocs (texte, titres, listes, sous-page, images collées).
- Modèles de pages avec propriétés (modèle *Procédure*).
- Recherche (tout, titre, contenu).
- Export de pages, de dossiers (récursif) en Markdown, HTML et texte.
- Sauvegarde automatique.

### 2.2 Exclu (pour l'instant)

- Édition collaborative en temps réel.
- Gestion fine des droits par page.
- Bases de données / vues tableau de type Notion.
- Application mobile native (le site doit être utilisable sur mobile).

### 2.3 Utilisateurs cibles

| Profil | Besoin principal |
|---|---|
| **Rédacteur** | Créer et mettre à jour des procédures rapidement |
| **Lecteur** | Retrouver une procédure et la suivre étape par étape |
| **Responsable** | Garder une base organisée, exporter, valider (statut) |

---

## 3. Analyse : le nouveau modèle d'organisation

### 3.1 Constat

La première version imposait **trois niveaux fixes** : Dossier → Sélection → Note. Les nouvelles demandes (page dans un dossier, dossier dans un dossier) montrent que cette structure est trop rigide : une « sélection » n'est en pratique **qu'un dossier de niveau 2**.

### 3.2 Décision proposée

> **Un seul type de conteneur, le Dossier, qui peut contenir des dossiers et des pages, sans limite fixe de niveaux.**

- La notion de **Sélection disparaît comme type** : elle devient un sous-dossier.
- Le terme **Note** est remplacé par **Page** (c'est le mot déjà utilisé dans la demande et dans le bloc « Page »).
- Les trois niveaux d'origine restent possibles : il suffit de créer Dossier → Sous-dossier → Page.

### 3.3 Glossaire

| Terme | Définition |
|---|---|
| **Dossier** | Conteneur. Contient des dossiers et/ou des pages. |
| **Page** | Document composé d'un titre, de propriétés (selon le modèle) et de blocs. |
| **Sous-page** | Page rattachée à une autre page via un bloc *Page*. |
| **Bloc** | Unité de contenu d'une page (texte, titre, élément de liste, page, image). |
| **Modèle** | Structure prédéfinie (propriétés + blocs initiaux) appliquée à la création d'une page. |
| **Propriété** | Champ structuré d'une page (ex. : Application / Spécialité, But, Statut). |
| **Racine** | Niveau supérieur de la base, au-dessus de tous les dossiers. |

### 3.4 Règles de contenance

| Élément parent ↓ / Élément enfant → | Dossier | Page |
|---|:---:|:---:|
| **Racine** | Oui | Oui (voir question Q2) |
| **Dossier** | Oui | Oui |
| **Page** (sous-page) | Non | Oui |

Une page ne peut **jamais** contenir un dossier. Un dossier ne peut jamais être déplacé dans **lui-même ni dans un de ses descendants**.

---

## 4. Modèle de données

### 4.1 Entités

Les dossiers et les pages sont stockés dans une structure commune (arbre), ce qui simplifie les déplacements et la recherche.

**Nœud (Node)**

| Champ | Type | Description |
|---|---|---|
| `id` | texte unique | Identifiant (UUID) |
| `type` | `folder` \| `page` | Nature du nœud |
| `parentId` | id \| null | Parent (dossier ou page) ; `null` = racine |
| `name` | texte | Nom du dossier **ou** titre de la page |
| `position` | nombre | Ordre parmi les frères (réordonnancement) |
| `icon` | emoji (optionnel) | Icône personnalisée |
| `createdAt`, `updatedAt` | date-heure | Horodatages |
| `deletedAt` | date-heure \| null | Suppression logique (corbeille) |

**Champs spécifiques aux pages**

| Champ | Type | Description |
|---|---|---|
| `templateId` | texte | Modèle utilisé (`vide`, `procedure`, …) |
| `props` | objet | Valeurs des propriétés du modèle |
| `blocks` | liste de blocs | Contenu de la page |

**Bloc**

| Champ | Type | Description |
|---|---|---|
| `id` | texte | Identifiant du bloc |
| `type` | `text` \| `h1` \| `h2` \| `ul` \| `ol` \| `page` | Type de bloc |
| `html` | texte (nettoyé) | Contenu riche (gras, italique, images) |
| `ref` | id (bloc `page`) | Page liée |

**Modèle (Template)**

| Champ | Description |
|---|---|
| `id`, `name`, `icon`, `description` | Identité du modèle |
| `props[]` | Propriétés : `key`, `label`, `type` (texte, liste de choix…), `options`, `required` |
| `blocks[]` | Blocs créés par défaut |

### 4.2 Exemple (JSON)

```json
{
  "id": "p_42",
  "type": "page",
  "parentId": "f_sauvegardes",
  "name": "Sauvegarde hebdomadaire",
  "position": 1,
  "templateId": "procedure",
  "props": {
    "app": "Veeam Backup",
    "but": "Vérifier que la sauvegarde du vendredi s'est bien déroulée.",
    "statut": "Validée"
  },
  "blocks": [
    { "id": "b1", "type": "h2", "html": "Prérequis" },
    { "id": "b2", "type": "ul", "html": "Accès à la console" },
    { "id": "b3", "type": "page", "ref": "p_43" }
  ]
}
```

### 4.3 Migration depuis le prototype v2

| Prototype v2 | Cible |
|---|---|
| Dossier | Nœud `folder` (parent = racine) |
| Sélection | Nœud `folder` (parent = dossier d'origine) |
| Note | Nœud `page` (parent = ancienne sélection) |
| Note avec `parent` (sous-page) | Nœud `page` (parent = page) |

---

## 5. Exigences fonctionnelles

Priorités : **D** = Doit (indispensable), **S** = Devrait (important), **P** = Pourrait (souhaitable).

### 5.1 Arborescence (dossiers et pages)

| ID | Exigence | Prio |
|---|---|:---:|
| ORG-01 | Créer un dossier à la racine | D |
| ORG-02 | Créer un **sous-dossier** dans un dossier | D |
| ORG-03 | Créer une **page directement dans un dossier** (bouton « + » sur la ligne du dossier, menu : *Nouvelle page* / *Nouveau dossier*) | D |
| ORG-04 | Créer une page via le bouton global « + Nouvelle page » ; elle est placée dans le dossier actuellement sélectionné (sinon à la racine) | S |
| ORG-05 | Renommer un dossier ou une page (double-clic ou icône) | D |
| ORG-06 | Supprimer un dossier ou une page avec **confirmation** indiquant le nombre d'éléments supprimés | D |
| ORG-07 | Corbeille : restauration possible pendant 30 jours | S |
| ORG-08 | Déplier / replier un dossier ; l'état est mémorisé | D |
| ORG-09 | Fil d'Ariane cliquable (chemin complet jusqu'à la page) | D |
| ORG-10 | Profondeur maximale de dossiers : 8 niveaux (configurable) | S |
| ORG-11 | Tri par défaut : dossiers d'abord, puis pages, dans l'ordre manuel (`position`) | D |
| ORG-12 | Icône personnalisable (emoji) pour un dossier ou une page | P |
| ORG-13 | Menu contextuel (clic droit / appui long) : nouvelle page, nouveau dossier, renommer, déplacer vers…, exporter, supprimer | S |
| ORG-14 | Noms en double autorisés (l'identité repose sur l'`id`) | D |

### 5.2 Glisser-déposer dans la liste de gauche

| ID | Exigence | Prio |
|---|---|:---:|
| DND-01 | Une **page** peut être glissée dans un dossier (à n'importe quelle profondeur) | D |
| DND-02 | Un **dossier** peut être glissé dans un autre dossier ou à la racine | D |
| DND-03 | Réordonnancement : glisser un élément **avant** ou **après** un frère | D |
| DND-04 | Trois zones de dépôt par ligne : **haut** (insérer avant), **milieu** (déposer dedans), **bas** (insérer après) | D |
| DND-05 | Retour visuel : ligne d'insertion pour avant/après, surbrillance de la ligne cible pour « dedans », élément déplacé semi-transparent | D |
| DND-06 | Dépôt **interdit** : un dossier dans lui-même ou dans l'un de ses descendants ; un dossier dans une page ; curseur « interdit » + aucune surbrillance | D |
| DND-07 | Un dossier replié s'**ouvre automatiquement** après 700 ms de survol pendant un glisser | S |
| DND-08 | Défilement automatique de la liste quand le curseur approche du bord haut ou bas | S |
| DND-09 | Zone de dépôt « Racine » (en-tête de l'arbre ou espace vide) pour sortir un élément de son dossier | D |
| DND-10 | **Alternative sans souris** : action « Déplacer vers… » ouvrant un sélecteur de dossier (accessibilité, mobile) | D |
| DND-11 | Support tactile : appui long (≈ 400 ms) pour démarrer le glisser | S |
| DND-12 | Après un déplacement, notification « Page déplacée vers *X* — **Annuler** » (délai 8 s) | S |
| DND-13 | L'ordre et l'emplacement sont **sauvegardés immédiatement** | D |
| DND-14 | La page ouverte reste ouverte après son déplacement ; le fil d'Ariane se met à jour | D |
| DND-15 | Dépôt d'une page **sur une autre page** : voir question Q3 (proposition : la transforme en sous-page, avec bloc *Page* ajouté au parent) | P |
| DND-16 | Sélection multiple (Ctrl/Maj + clic) et déplacement groupé | P |
| DND-17 | Le glisser-déposer est désactivé pendant l'affichage des résultats de recherche | D |

### 5.3 Pages et éditeur par blocs

| ID | Exigence | Prio |
|---|---|:---:|
| ED-01 | Chaque page a un **titre** (obligatoire ; « Sans titre » si vide à l'affichage) | D |
| ED-02 | Types de blocs : **Texte, Titre 1, Titre 2, Liste à puces, Liste numérotée, Page** | D |
| ED-03 | Insertion de bloc : bouton « + », saisie de `/`, bouton « + Ajouter un bloc » en bas de page | D |
| ED-04 | Raccourcis Markdown : `# `, `## `, `- `, `* `, `1. ` convertissent la ligne en bloc | S |
| ED-05 | Entrée crée un bloc ; dans une liste, crée un nouvel élément ; Entrée sur un élément vide ramène en texte | D |
| ED-06 | Retour arrière sur un bloc vide : le convertit en texte, puis le supprime | D |
| ED-07 | Menu du bloc (« ⋮⋮ ») : convertir, monter, descendre, supprimer | D |
| ED-08 | Mise en forme du texte : gras, italique (Ctrl+B / Ctrl+I) | D |
| ED-09 | Liens hypertextes (Ctrl+K) | S |
| ED-10 | **Coller une image** (Ctrl+V) dans un bloc ; redimensionnement automatique à la largeur de la page | D |
| ED-11 | Collage de texte formaté : nettoyé (texte brut par défaut) ; collage multi-lignes = plusieurs blocs | D |
| ED-12 | Bloc *Page* : crée une sous-page, affichée sous forme de carte cliquable | D |
| ED-13 | Supprimer un bloc *Page* supprime la sous-page (avec confirmation) | D |
| ED-14 | Sauvegarde automatique (< 1 s après la dernière frappe) avec indicateur « Enregistré » | D |
| ED-15 | Glisser-déposer des **blocs** pour les réordonner | S |
| ED-16 | Annuler / rétablir (Ctrl+Z / Ctrl+Y) | S |
| ED-17 | Blocs supplémentaires : case à cocher, citation, code, séparateur, tableau | P |
| ED-18 | Historique des versions d'une page | P |

### 5.4 Modèles (templates)

| ID | Exigence | Prio |
|---|---|:---:|
| TPL-01 | À la création d'une page, choix d'un modèle : *Note vierge* ou *Procédure* | D |
| TPL-02 | Le modèle **Procédure** fournit les propriétés : **Application / Spécialité** (texte), **But** (texte), **Statut** (Brouillon, À valider, Validée) | D |
| TPL-03 | Le modèle **Procédure** fournit les blocs initiaux : *Prérequis* (liste), *Étapes* (liste numérotée), *Remarques* (texte) | D |
| TPL-04 | Les propriétés s'affichent sous le titre, éditables directement | D |
| TPL-05 | Le modèle de la page est rappelé par un badge au-dessus du titre | S |
| TPL-06 | Créer, modifier et supprimer ses propres modèles | P |
| TPL-07 | Types de propriétés étendus : date, personne, étiquettes, case à cocher | P |
| TPL-08 | Propriétés obligatoires (blocage de la validation si vide) | P |
| TPL-09 | Modifier un modèle ne casse pas les pages existantes (les valeurs restent) | S |

Propositions de modèles futurs : *Compte rendu*, *FAQ*, *Fiche application*, *Incident / Post-mortem*.

### 5.5 Recherche

| ID | Exigence | Prio |
|---|---|:---:|
| SRC-01 | Champ de recherche permanent en haut de la liste de gauche | D |
| SRC-02 | Trois portées : **Titre + contenu**, **Titre seul**, **Contenu seul** | D |
| SRC-03 | Insensible à la casse **et aux accents** (« procedure » trouve « Procédure ») | D |
| SRC-04 | Résultats : icône, titre, chemin (Dossier › Sous-dossier), extrait avec le terme surligné, compteur | D |
| SRC-05 | La recherche porte sur les titres, le texte des blocs **et** les valeurs des propriétés | D |
| SRC-06 | Un clic sur un résultat ouvre la page ; le terme reste surligné dans la page | S |
| SRC-07 | Filtre « dans ce dossier » (recherche limitée à un sous-arbre) | S |
| SRC-08 | Filtres par modèle et par statut | P |
| SRC-09 | Tri par pertinence (titre avant contenu), puis par date de modification | S |
| SRC-10 | Recherche déclenchée après 2 caractères, avec temporisation de 200 ms | S |
| SRC-11 | Raccourci clavier global (Ctrl+K ou `/`) pour focaliser la recherche | P |

### 5.6 Export

| ID | Exigence | Prio |
|---|---|:---:|
| EXP-01 | Exporter une **page** en Markdown, HTML ou texte | D |
| EXP-02 | Exporter un **dossier** (récursif : sous-dossiers, pages, sous-pages) | D |
| EXP-03 | L'export reflète la hiérarchie : titres de niveau 1 (dossier), 2 (sous-dossier), 3 (page)… plafonnés à 6 | D |
| EXP-04 | Les propriétés sont exportées (ex. : `**But :** …` ou en-tête YAML en Markdown) | D |
| EXP-05 | Les sous-pages sont incluses à la suite de leur page parente | D |
| EXP-06 | Version finale : **téléchargement direct** du fichier (.md, .html, .txt) ; le prototype passe par « Copier » | D |
| EXP-07 | Export de dossier en **archive ZIP** reproduisant l'arborescence (un fichier par page, images dans `assets/`) | S |
| EXP-08 | Choix : images **intégrées** (base64) ou **séparées** dans `assets/` | S |
| EXP-09 | Export de plusieurs éléments sélectionnés | P |
| EXP-10 | Export complet de la base (sauvegarde JSON) et réimport | S |
| EXP-11 | Export PDF / impression d'une procédure (feuille de style d'impression) | P |

### 5.7 Import (évolution)

| ID | Exigence | Prio |
|---|---|:---:|
| IMP-01 | Importer un fichier Markdown ou HTML en tant que page | P |
| IMP-02 | Importer une archive ZIP (arborescence → dossiers et pages) | P |
| IMP-03 | Restaurer une sauvegarde JSON | S |

---

## 6. Interface utilisateur

### 6.1 Structure de l'écran

```
┌──────────────────────┬────────────────────────────────────────────┐
│ 📚 Base documentaire │  Fil d'Ariane : Informatique › Sauvegardes │ [Exporter]
│ [+ Nouveau dossier]  ├────────────────────────────────────────────┤
│ [ Rechercher…      ] │  🛠️ Procédure                              │
│ [ Titre + contenu ▾] │  Titre de la page                          │
├──────────────────────┤  ─────────────────────────────────────     │
│ ▾ 📁 Informatique    │  Application / Spécialité │ Veeam Backup   │
│   ▾ 📁 Sauvegardes   │  But                      │ …              │
│     📄 Sauvegarde…   │  Statut                   │ Validée        │
│       📄 En cas…     │  ─────────────────────────────────────     │
│   ▸ 📁 Comptes       │  Prérequis (Titre 2)                       │
│ ▸ 📁 RH              │  • …                                       │
└──────────────────────┴────────────────────────────────────────────┘
```

### 6.2 Arbre de gauche

- Indentation de 14 px par niveau ; icône 📁 pour les dossiers, icône du modèle pour les pages.
- Actions visibles au survol de la ligne : **+** (nouvelle page / nouveau dossier), ✎ renommer, ⤓ exporter, ✕ supprimer.
- Poignée de glisser implicite : toute la ligne est déplaçable.
- Ligne sélectionnée mise en évidence ; les parents de la page ouverte sont dépliés automatiquement.
- Sous-pages affichées sous leur page parente, avec une indentation supplémentaire.

### 6.3 Création d'une page (flux)

1. Clic sur **+** à côté d'un dossier → menu « Nouvelle page » / « Nouveau dossier ».
2. Boîte de dialogue : titre (facultatif) + choix du **modèle** (cartes).
3. La page est créée **dans ce dossier**, ouverte, et le titre est sélectionné.

### 6.4 Comportements transverses

- **Responsive** : sur mobile, l'arbre et la page s'empilent ; l'arbre est repliable.
- **Thème** : clair et sombre selon le réglage du système.
- **Raccourcis** : `/` insérer un bloc, `Ctrl+B`, `Ctrl+I`, `Ctrl+K` (lien), `Échap` fermer un menu.
- **Retours** : indicateur de sauvegarde, notifications avec « Annuler » pour les actions destructrices ou de déplacement.

---

## 7. Exigences non fonctionnelles

| Domaine | Exigence |
|---|---|
| **Performance** | Ouverture d'une page < 300 ms ; recherche < 200 ms jusqu'à 5 000 pages ; arbre fluide jusqu'à 2 000 nœuds visibles |
| **Fiabilité** | Aucune perte de données lors d'un rechargement ; sauvegarde automatique ; corbeille |
| **Sécurité** | Nettoyage (sanitisation) systématique du HTML collé ou importé contre les failles XSS ; aucune exécution de script dans le contenu |
| **Images** | Compression à la volée (largeur max 1 600 px, WebP/JPEG qualité 85) ; taille maximale 5 Mo par image |
| **Accessibilité** | Niveau WCAG 2.1 AA : navigation clavier complète, rôles ARIA `tree` / `treeitem`, contrastes suffisants, alternative clavier au glisser-déposer |
| **Compatibilité** | Navigateurs récents (Chrome, Edge, Firefox, Safari) sur ordinateur, tablette et mobile |
| **Maintenabilité** | Couche de stockage abstraite (changer de stockage sans réécrire l'interface) ; tests automatisés sur les règles de déplacement |
| **Confidentialité** | Données stockées localement ou sur le serveur de l'organisation, pas de service tiers imposé |

---

## 8. Architecture technique recommandée

### 8.1 Deux options

| | **A. Local d'abord (sans serveur)** | **B. Application web + serveur** |
|---|---|---|
| Stockage | IndexedDB dans le navigateur | Base de données (PostgreSQL ou SQLite) |
| Utilisateurs | Un seul, un seul appareil | Plusieurs, plusieurs appareils |
| Recherche | En mémoire dans le navigateur | Recherche plein texte du SGBD |
| Complexité | Faible | Moyenne à élevée |
| Partage / sauvegarde | Export / import JSON | Natifs |

**Recommandation** : démarrer en **option A** avec une couche de stockage abstraite (`StorageAdapter`), puis ajouter l'option B si le besoin de partage apparaît.

### 8.2 Composants conseillés

- **Interface** : application monopage (React ou équivalent).
- **Éditeur** : le prototype utilise `contenteditable` et `execCommand` (API dépréciée). Pour la production, adopter une bibliothèque d'édition par blocs (**TipTap / ProseMirror** ou **BlockNote**) qui gère proprement collage, annulation et sélection.
- **Glisser-déposer** : bibliothèque dédiée (par ex. **dnd-kit**) pour les zones haut / milieu / bas, l'accessibilité et le tactile.
- **Sanitisation** : DOMPurify.
- **Export ZIP** : JSZip ; téléchargement via `Blob` + `URL.createObjectURL`.
- **Conversion Markdown** : Turndown (HTML → Markdown) ou conversion maison (déjà esquissée dans le prototype).

### 8.3 Règles métier à tester en priorité

1. Interdiction des cycles (déplacement d'un dossier dans un descendant).
2. Recalcul des `position` lors d'un insertion avant / après.
3. Suppression récursive (dossier → sous-dossiers → pages → sous-pages) et nettoyage des blocs *Page* orphelins.
4. Export récursif avec plafonnement du niveau de titre.

---

## 9. Écart entre le prototype v2 et la cible

| Fonction | Prototype v2 | À faire |
|---|---|---|
| Hiérarchie | Dossier → Sélection → Note (3 niveaux fixes) | Arbre récursif unique (Dossier / Page) |
| Page dans un dossier | Non (une sélection est nécessaire) | Oui |
| Dossier dans un dossier | Non | Oui |
| Glisser-déposer de l'arbre | Non | Oui (règles DND-01 à DND-17) |
| Éditeur de blocs | Oui (6 types) | Bibliothèque d'édition, annuler / rétablir, liens, DnD de blocs |
| Modèle *Procédure* | Oui | Gestion de modèles personnalisés |
| Recherche | Titre / contenu / tout | Accents, filtres, surlignage dans la page, tri |
| Export | Copier / coller (MD, HTML, TXT) | Téléchargement, ZIP, images en `assets/` |
| Stockage | `localStorage` du navigateur | IndexedDB / serveur, corbeille, sauvegarde JSON |
| Images | Base64 dans le contenu | Compression + stockage séparé |
| Accessibilité | Partielle | Arbre ARIA, navigation clavier, « Déplacer vers… » |

---

## 10. Feuille de route proposée

| Phase | Contenu | Résultat attendu |
|---|---|---|
| **0 — Maquette** (fait) | Prototype HTML v2 | Validation du principe |
| **1 — Maquette v3** | Arbre récursif, page dans un dossier, glisser-déposer | Validation de l'ergonomie de l'arbre |
| **2 — MVP** | Modèle de données unifié, éditeur sur bibliothèque, sauvegarde IndexedDB, recherche, export téléchargeable | Application utilisable au quotidien |
| **3 — V1** | Corbeille, ZIP, import / sauvegarde JSON, filtres de recherche, annuler / rétablir, accessibilité complète | Version stable |
| **4 — V2** | Modèles personnalisés, versions de pages, multi-utilisateur (option B), droits | Partage en équipe |

---

## 11. Critères d'acceptation (extraits)

**CA-1 — Page dans un dossier**
- *Étant donné* un dossier « Sauvegardes », *quand* je clique sur **+** puis « Nouvelle page » et choisis *Procédure*, *alors* une page est créée **dans** « Sauvegardes », ouverte, avec les propriétés et blocs du modèle.

**CA-2 — Dossier dans un dossier**
- *Quand* je crée un dossier depuis le menu « + » de « Informatique », *alors* il apparaît **sous** « Informatique » avec une indentation supplémentaire.

**CA-3 — Déplacer une page par glisser-déposer**
- *Quand* je glisse la page « Création d'un compte » sur le milieu de la ligne du dossier « RH », *alors* la page est rangée dans « RH », « RH » est déplié, la page reste ouverte et son fil d'Ariane indique « RH ».

**CA-4 — Réordonner**
- *Quand* je dépose une page sur la zone haute d'une autre page du même dossier, *alors* une ligne d'insertion apparaît pendant le glisser, et l'ordre est conservé après rechargement.

**CA-5 — Dépôt interdit**
- *Quand* je glisse « Informatique » sur « Sauvegardes » (son sous-dossier), *alors* le dépôt est refusé (curseur « interdit »), et rien n'est modifié.

**CA-6 — Alternative clavier**
- *Quand* je choisis « Déplacer vers… » sur une page et sélectionne un dossier, *alors* le résultat est identique à un glisser-déposer.

**CA-7 — Recherche**
- *Quand* je tape « procedure » avec la portée « Titre seul », *alors* les pages dont le titre contient « Procédure » sont listées avec leur chemin complet.

**CA-8 — Export récursif**
- *Quand* j'exporte « Informatique » en Markdown, *alors* le fichier contient le dossier, ses sous-dossiers, leurs pages, leurs propriétés et leurs sous-pages, avec des niveaux de titre cohérents.

**CA-9 — Suppression**
- *Quand* je supprime un dossier contenant 2 sous-dossiers et 5 pages, *alors* la confirmation indique « 7 éléments », et ils sont placés en corbeille.

---

## 12. Risques

| Risque | Impact | Mesure |
|---|---|---|
| Éditeur maison fragile (collage, sélection, annulation) | Perte ou corruption de contenu | Adopter TipTap / BlockNote dès le MVP |
| Perte de données avec le stockage navigateur (cache vidé, changement d'appareil) | Perte de la base | Export JSON régulier, alerte de sauvegarde, option serveur |
| Images en base64 | Base volumineuse, lenteur | Compression et stockage séparé |
| Glisser-déposer imprécis sur mobile / pour certains utilisateurs | Mauvais classement | Alternative « Déplacer vers… », annulation |
| Arbre trop profond ou trop dense | Lisibilité | Limite de profondeur, recherche, fil d'Ariane |
| Contenu collé malveillant | Faille XSS | Sanitisation systématique |

---

## 13. Questions ouvertes (décisions à valider)

| N° | Question | Proposition |
|---|---|---|
| **Q1** | Garde-t-on le mot « Sélection » ? | Non : un sous-dossier remplace la sélection |
| **Q2** | Peut-on créer une page à la racine, hors de tout dossier ? | Oui, pour ne pas bloquer la saisie rapide ; une zone « Racine » est visible |
| **Q3** | Déposer une page **sur une autre page** : sous-page ou réordonnancement ? | Milieu de ligne = sous-page (bloc *Page* ajouté au parent) ; haut / bas = réordonnancement |
| **Q4** | Un dossier peut-il avoir une page d'accueil (description) ? | Optionnel, en V1 |
| **Q5** | Une seule personne ou plusieurs utilisateurs ? | Une seule personne au départ (option A), à confirmer |
| **Q6** | Faut-il un historique des versions des procédures ? | Utile pour des procédures validées ; en V2 |
| **Q7** | Workflow de validation du statut (qui peut passer en « Validée ») ? | Libre au départ ; à encadrer avec les droits en V2 |
| **Q8** | Quels autres modèles de pages sont attendus ? | À lister avec les utilisateurs (compte rendu, FAQ, fiche application…) |
| **Q9** | Faut-il pouvoir importer des documents existants (Word, Markdown) ? | Markdown / HTML en V1, Word à étudier |
| **Q10** | Limite de profondeur des dossiers | 8 niveaux, ajustable |

---

## Annexe A — Récapitulatif des actions par élément

| Action | Dossier | Page | Bloc |
|---|:---:|:---:|:---:|
| Créer | ✔ (racine ou dans un dossier) | ✔ (racine ou dans un dossier) | ✔ |
| Créer un enfant | Dossier, page | Sous-page (bloc *Page*) | — |
| Renommer | ✔ | ✔ (titre) | — |
| Déplacer (glisser / « Déplacer vers… ») | ✔ | ✔ | ✔ (monter / descendre, glisser) |
| Exporter | ✔ (récursif) | ✔ | — |
| Supprimer | ✔ (récursif) | ✔ (avec sous-pages) | ✔ |
| Convertir | — | Changer de modèle (P) | ✔ (type de bloc) |

## Annexe B — Règles de dépôt (glisser-déposer)

| Élément glissé | Cible | Zone | Résultat |
|---|---|---|---|
| Page | Dossier | milieu | Page rangée dans le dossier (en dernière position) |
| Page | Dossier | haut / bas | Page placée avant / après le dossier (même parent) |
| Page | Page | haut / bas | Réordonnancement parmi les frères |
| Page | Page | milieu | Devient sous-page (Q3) |
| Dossier | Dossier (non descendant) | milieu | Sous-dossier |
| Dossier | Dossier (non descendant) | haut / bas | Réordonnancement |
| Dossier | Lui-même ou un descendant | toutes | **Refusé** |
| Dossier | Page | toutes | **Refusé** |
| Page ou dossier | Racine | — | Placé à la racine |