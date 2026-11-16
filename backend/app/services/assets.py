"""Image upload (validate with Pillow, strip EXIF, resize, de-duplicate) and storage on disk."""
import hashlib
import io
import os
import uuid
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from ..domain import Asset
from ..errors import ApiError, unprocessable

FORMATS = {"PNG": ("image/png", "png"), "JPEG": ("image/jpeg", "jpg"),
           "WEBP": ("image/webp", "webp"), "GIF": ("image/gif", "gif")}
EXT_MIME = {ext: mime for mime, ext in FORMATS.values()}


class AssetService:
    def __init__(self, repo, cfg):
        self.repo, self.cfg = repo, cfg
        self.root = Path(cfg.UPLOAD_DIR)

    def upload(self, user, filename, data, node_id=None):
        limit = self.cfg.MAX_UPLOAD_MB * 1024 * 1024
        if len(data) > limit:
            raise ApiError(413, "Payload too large", f"Images are limited to {self.cfg.MAX_UPLOAD_MB} MB", "too_large")
        try:
            probe = Image.open(io.BytesIO(data))
            probe.verify()
            img = Image.open(io.BytesIO(data))
            fmt = img.format
        except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
            raise unprocessable("File is not a valid image", "invalid_image")
        if fmt not in FORMATS:
            raise unprocessable("Allowed image types: PNG, JPEG, WebP, GIF", "unsupported_image")
        mime, ext = FORMATS[fmt]
        if fmt == "GIF" and getattr(img, "is_animated", False):
            out, (w, h) = data, img.size  # keep animation untouched
        else:
            img = ImageOps.exif_transpose(img)
            if img.width > self.cfg.MAX_IMAGE_WIDTH:
                ratio = self.cfg.MAX_IMAGE_WIDTH / img.width
                img = img.resize((self.cfg.MAX_IMAGE_WIDTH, max(1, round(img.height * ratio))), Image.LANCZOS)
            buf = io.BytesIO()
            if fmt == "JPEG":
                img.convert("RGB").save(buf, "JPEG", quality=85, optimize=True)  # EXIF dropped
            elif fmt == "PNG":
                img.save(buf, "PNG", optimize=True)
            elif fmt == "WEBP":
                img.save(buf, "WEBP", quality=85)
            else:
                img.save(buf, "GIF")
            out, (w, h) = buf.getvalue(), img.size
        sha = hashlib.sha256(out).hexdigest()
        existing = self.repo.find_asset_by_sha(user.id, sha)
        if existing:
            return existing, False
        rel = f"{sha[:2]}/{sha}.{ext}"
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(out)
        asset = Asset(id=str(uuid.uuid4()), owner_id=user.id, filename=(os.path.basename(filename or "image") or "image")[:255],
                      mime_type=mime, size_bytes=len(out), width=w, height=h, sha256=sha,
                      storage_path=rel, node_id=node_id)
        self.repo.add_asset(asset)
        return asset, True

    def path(self, asset):
        return self.root / asset.storage_path

    def read(self, asset):
        return self.path(asset).read_bytes()

    @staticmethod
    def ext(asset):
        return asset.storage_path.rsplit(".", 1)[-1]
