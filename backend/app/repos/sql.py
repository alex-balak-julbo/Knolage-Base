"""SQLAlchemy 2.x repository (MySQL 8 in production, SQLite for quick local runs).

Models use utf8mb4 / utf8mb4_0900_ai_ci on MySQL so LIKE is case- and accent-insensitive.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (JSON, BigInteger, DateTime, Enum, ForeignKey, Index, Integer, String, Text, create_engine,
                        delete, event, or_, select, update)
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool

from ..domain import Asset, Node, Template, User
from ..textutil import fold
from .base import Repo

MYSQL_OPTS = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_0900_ai_ci"}
LONGTEXT = Text().with_variant(MEDIUMTEXT(), "mysql")


class Base(DeclarativeBase):
    pass


class UserRow(Base):
    __tablename__ = "users"
    __table_args__ = (MYSQL_OPTS,)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120), default="")
    role: Mapped[str] = mapped_column(Enum("admin", "editor", "reader", name="user_role"), default="editor")
    created_at: Mapped[datetime] = mapped_column(DateTime)


class TemplateRow(Base):
    __tablename__ = "templates"
    __table_args__ = (MYSQL_OPTS,)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(500), default="")
    icon: Mapped[str] = mapped_column(String(16), default="📄")
    props_schema: Mapped[list] = mapped_column(JSON)
    default_content: Mapped[dict] = mapped_column(JSON)
    is_system: Mapped[bool] = mapped_column(default=False)


class NodeRow(Base):
    __tablename__ = "nodes"
    __table_args__ = (
        Index("ix_nodes_parent_pos", "parent_id", "position"),
        Index("ix_nodes_deleted", "deleted_at"),
        Index("ix_nodes_owner_type", "owner_id", "type"),
        Index("ft_nodes_text", "name", "search_text", mysql_prefix="FULLTEXT"),  # reserved for MATCH() search
        MYSQL_OPTS,
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    type: Mapped[str] = mapped_column(Enum("folder", "page", name="node_type"))
    parent_id: Mapped[Optional[str]] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    icon: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    position: Mapped[int] = mapped_column(BigInteger, default=0)
    template_id: Mapped[Optional[str]] = mapped_column(ForeignKey("templates.id"), nullable=True)
    props: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    content: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    search_text: Mapped[str] = mapped_column(LONGTEXT, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AssetRow(Base):
    __tablename__ = "assets"
    __table_args__ = (Index("ix_assets_owner_sha", "owner_id", "sha256"), MYSQL_OPTS)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    node_id: Mapped[Optional[str]] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    storage_path: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime)


NODE_FIELDS = ("id", "type", "parent_id", "name", "icon", "position", "template_id", "content", "search_text",
               "version", "owner_id", "created_at", "updated_at", "deleted_at")


def _to_node(r):
    return Node(**{f: getattr(r, f) for f in NODE_FIELDS}, props=r.props or {}) if r else None


def _fill_node(r, n):
    for f in NODE_FIELDS:
        setattr(r, f, getattr(n, f))
    r.props = n.props or {}
    return r


def _chunks(seq, size=500):
    seq = list(seq)
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


class SqlRepo(Repo):
    def __init__(self, url, **engine_kw):
        if url in ("sqlite://", "sqlite:///:memory:"):
            engine_kw.update(poolclass=StaticPool, connect_args={"check_same_thread": False})
        self.engine = create_engine(url, pool_pre_ping=True, **engine_kw)
        if self.engine.dialect.name == "sqlite":
            event.listen(self.engine, "connect", lambda c, _: c.execute("PRAGMA foreign_keys=ON"))
        self.Session = scoped_session(sessionmaker(bind=self.engine, expire_on_commit=False))

    @property
    def s(self):
        return self.Session()

    @property
    def dialect(self):
        return self.engine.dialect.name

    def create_all(self):
        Base.metadata.create_all(self.engine)

    # lifecycle
    def commit(self): self.s.commit()
    def rollback(self): self.s.rollback()
    def cleanup(self): self.Session.remove()

    def ping(self):
        self.s.execute(select(1))
        return True

    def _bulk(self, stmt):
        self.s.flush()
        self.s.execute(stmt)
        self.s.expire_all()

    # users
    def get_user(self, user_id):
        r = self.s.get(UserRow, user_id)
        return User(r.id, r.email, r.password_hash, r.display_name, r.role, r.created_at) if r else None

    def get_user_by_email(self, email):
        r = self.s.scalars(select(UserRow).where(UserRow.email == (email or "").strip().lower())).first()
        return User(r.id, r.email, r.password_hash, r.display_name, r.role, r.created_at) if r else None

    def add_user(self, u):
        self.s.add(UserRow(id=u.id, email=u.email.lower(), password_hash=u.password_hash,
                           display_name=u.display_name, role=u.role, created_at=u.created_at))
        self.s.flush()

    def count_users(self):
        return len(self.s.scalars(select(UserRow.id)).all())

    # templates
    @staticmethod
    def _tpl(r):
        return Template(r.id, r.name, r.description, r.icon, r.props_schema, r.default_content, r.is_system)

    def list_templates(self):
        return [self._tpl(r) for r in self.s.scalars(select(TemplateRow).order_by(TemplateRow.name))]

    def get_template(self, template_id):
        r = self.s.get(TemplateRow, template_id) if template_id else None
        return self._tpl(r) if r else None

    def save_template(self, t):
        r = self.s.get(TemplateRow, t.id) or TemplateRow(id=t.id)
        r.name, r.description, r.icon = t.name, t.description, t.icon
        r.props_schema, r.default_content, r.is_system = t.props_schema, t.default_content, t.is_system
        self.s.add(r)
        self.s.flush()

    # nodes
    def get_node(self, node_id, include_deleted=False):
        r = self.s.get(NodeRow, node_id) if node_id else None
        if r is None or (r.deleted_at and not include_deleted):
            return None
        return _to_node(r)

    def list_active(self, owner_id):
        q = select(NodeRow).where(NodeRow.owner_id == owner_id, NodeRow.deleted_at.is_(None))
        return [_to_node(r) for r in self.s.scalars(q)]

    def children(self, parent_id, owner_id, include_deleted=False):
        q = select(NodeRow).where(NodeRow.owner_id == owner_id)
        q = q.where(NodeRow.parent_id.is_(None) if parent_id is None else NodeRow.parent_id == parent_id)
        if not include_deleted:
            q = q.where(NodeRow.deleted_at.is_(None))
        return [_to_node(r) for r in self.s.scalars(q.order_by(NodeRow.position, NodeRow.id))]

    def add_node(self, node):
        self.s.add(_fill_node(NodeRow(), node))
        self.s.flush()

    def save_node(self, node):
        r = self.s.get(NodeRow, node.id)
        if r is None:
            raise KeyError(node.id)
        _fill_node(r, node)
        self.s.flush()

    def descendant_ids(self, node_id, include_deleted=False):
        ids, frontier = [node_id], [node_id]
        while frontier:
            found = []
            for chunk in _chunks(frontier):
                q = select(NodeRow.id).where(NodeRow.parent_id.in_(chunk))
                if not include_deleted:
                    q = q.where(NodeRow.deleted_at.is_(None))
                found += [i for i in self.s.scalars(q) if i not in ids]
            ids += found
            frontier = found
        return ids

    def set_deleted(self, ids, when):
        for c in _chunks(ids):
            self._bulk(update(NodeRow).where(NodeRow.id.in_(c)).values(deleted_at=when))

    def clear_deleted(self, ids):
        for c in _chunks(ids):
            self._bulk(update(NodeRow).where(NodeRow.id.in_(c)).values(deleted_at=None))

    def delete_hard(self, ids):
        for c in _chunks(ids):
            self._bulk(delete(NodeRow).where(NodeRow.id.in_(c)))

    def list_deleted(self, owner_id=None):
        q = select(NodeRow).where(NodeRow.deleted_at.is_not(None))
        if owner_id:
            q = q.where(NodeRow.owner_id == owner_id)
        return [_to_node(r) for r in self.s.scalars(q)]

    def search_candidates(self, owner_id, q, scope, restrict_ids=None, template_id=None):
        stmt = select(NodeRow).where(NodeRow.owner_id == owner_id, NodeRow.type == "page", NodeRow.deleted_at.is_(None))
        if template_id:
            stmt = stmt.where(NodeRow.template_id == template_id)
        if self.dialect == "mysql":  # collation makes LIKE case/accent-insensitive
            like = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            t, c = NodeRow.name.like(like, escape="\\"), NodeRow.search_text.like(like, escape="\\")
            stmt = stmt.where(t if scope == "title" else c if scope == "content" else or_(t, c))
            nodes = [_to_node(r) for r in self.s.scalars(stmt)]
        else:  # portable fallback (SQLite): fold in Python
            fq, nodes = fold(q), []
            for r in self.s.scalars(stmt):
                t, c = fq in fold(r.name), fq in fold(r.search_text or "")
                if (scope == "title" and t) or (scope == "content" and c) or (scope == "all" and (t or c)):
                    nodes.append(_to_node(r))
        return [n for n in nodes if restrict_ids is None or n.id in restrict_ids]

    # assets
    @staticmethod
    def _asset(r):
        return Asset(r.id, r.owner_id, r.filename, r.mime_type, r.size_bytes, r.width, r.height, r.sha256,
                     r.storage_path, r.node_id, r.created_at)

    def add_asset(self, a):
        self.s.add(AssetRow(id=a.id, owner_id=a.owner_id, node_id=a.node_id, filename=a.filename, mime_type=a.mime_type,
                            size_bytes=a.size_bytes, width=a.width, height=a.height, sha256=a.sha256,
                            storage_path=a.storage_path, created_at=a.created_at))
        self.s.flush()

    def get_asset(self, asset_id):
        r = self.s.get(AssetRow, asset_id)
        return self._asset(r) if r else None

    def find_asset_by_sha(self, owner_id, sha):
        r = self.s.scalars(select(AssetRow).where(AssetRow.owner_id == owner_id, AssetRow.sha256 == sha)).first()
        return self._asset(r) if r else None
