"""Domain objects shared by services and repositories (storage-agnostic)."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

FOLDER = "folder"
PAGE = "page"
STEP = 1024  # gap between sibling positions


def utcnow() -> datetime:
    """Naive UTC datetime without microseconds (MySQL DATETIME friendly)."""
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() + "Z" if dt else None


@dataclass
class Node:
    id: str
    type: str
    owner_id: str
    name: str
    parent_id: Optional[str] = None
    position: int = 0
    icon: Optional[str] = None
    template_id: Optional[str] = None
    props: dict = field(default_factory=dict)
    content: Optional[dict] = None
    search_text: str = ""
    version: int = 1
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
    deleted_at: Optional[datetime] = None

    def clone(self) -> "Node":
        return copy.deepcopy(self)


@dataclass
class User:
    id: str
    email: str
    password_hash: str
    display_name: str = ""
    role: str = "editor"  # admin | editor | reader
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class Template:
    id: str
    name: str
    description: str = ""
    icon: str = "📄"
    props_schema: list = field(default_factory=list)
    default_content: dict = field(default_factory=dict)
    is_system: bool = False


@dataclass
class Asset:
    id: str
    owner_id: str
    filename: str
    mime_type: str
    size_bytes: int
    width: int
    height: int
    sha256: str
    storage_path: str
    node_id: Optional[str] = None
    created_at: datetime = field(default_factory=utcnow)
