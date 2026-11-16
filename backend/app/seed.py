"""Seed data: system templates, admin user and an optional demo tree."""
import uuid

from .auth import hash_password
from .domain import Template, User


def _p(text, **kw):
    return {"type": "paragraph", "content": [{"type": "text", "text": text}]} if text else {"type": "paragraph"}


def _h2(text):
    return {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": text}]}


def _list(kind, *items):
    return {"type": kind, "content": [{"type": "listItem", "content": [_p(i)]} for i in (items or ("",))]}


def system_templates():
    return [
        Template(id="blank", name="Page vierge", description="Page libre", icon="📄",
                 props_schema=[], default_content={"type": "doc", "content": [{"type": "paragraph"}]}, is_system=True),
        Template(id="procedure", name="Procédure", description="Application, but, prérequis, étapes", icon="🛠️",
                 props_schema=[
                     {"key": "app", "label": "Application / Spécialité", "type": "text"},
                     {"key": "purpose", "label": "But", "type": "text"},
                     {"key": "status", "label": "Statut", "type": "select", "options": ["Brouillon", "À valider", "Validée"]},
                 ],
                 default_content={"type": "doc", "content": [
                     _h2("Prérequis"), _list("bulletList"), _h2("Étapes"), _list("orderedList"),
                     _h2("Remarques"), {"type": "paragraph"}]}, is_system=True),
    ]


def ensure_templates(repo):
    for t in system_templates():
        if repo.get_template(t.id) is None:
            repo.save_template(t)


def ensure_user(repo, email, password, role="admin", name="Admin"):
    u = repo.get_user_by_email(email)
    if u is None:
        u = User(id=str(uuid.uuid4()), email=email.lower(), password_hash=hash_password(password),
                 display_name=name, role=role)
        repo.add_user(u)
    return u


def demo_data(tree, user):
    """A small tree: nested folders, a procedure with a sub-page and a root page."""
    it, _ = tree.create(user, type="folder", name="Informatique")
    bk, _ = tree.create(user, type="folder", parent_id=it.id, name="Sauvegardes")
    net, _ = tree.create(user, type="folder", parent_id=it.id, name="Réseau")
    vpn, _ = tree.create(user, type="folder", parent_id=net.id, name="VPN")
    rh, _ = tree.create(user, type="folder", name="Ressources humaines")
    main, _ = tree.create(user, type="page", parent_id=bk.id, name="Sauvegarde hebdomadaire", template_id="procedure",
                          props={"app": "Veeam Backup", "purpose": "Vérifier la sauvegarde du vendredi.", "status": "Validée"},
                          content={"type": "doc", "content": [_h2("Prérequis"), _list("bulletList", "Accès à la console"),
                                                              _h2("Étapes"), _list("orderedList", "Ouvrir la console", "Contrôler le statut")]})
    tree.create(user, type="page", parent_id=main.id, name="Que faire en cas d’échec ?")
    tree.create(user, type="page", parent_id=vpn.id, name="Configurer le client VPN", template_id="procedure",
                props={"app": "OpenVPN", "status": "Brouillon"})
    tree.create(user, type="page", parent_id=rh.id, name="Accueil d’un nouvel arrivant")
    tree.create(user, type="page", name="Bienvenue")
