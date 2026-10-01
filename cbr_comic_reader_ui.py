import sys
import os
import json
import zipfile
import re
import tempfile
import shutil
import sqlite3
import time
import hashlib
import base64
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from PyQt6.QtCore import (
    Qt, QUrl, QRect, QThread, pyqtSignal, QTimer, QSize,
    QPropertyAnimation, QEasingCurve, QPoint,
    QObject, QRunnable, QThreadPool
)
from PyQt6.QtGui import (
    QColor, QLinearGradient, QPixmap, QPainter, QPainterPath,
    QPen, QFont, QWheelEvent, QKeySequence, QShortcut, QAction
)
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QLineEdit, QScrollArea,
    QFrame, QProgressBar, QFileDialog, QStackedWidget, QMessageBox,
    QComboBox, QGraphicsDropShadowEffect, QSpinBox, QCheckBox,
    QMenu
)


# =====================================================================
# CONFIGURAÇÕES GERAIS
# =====================================================================

# =====================================================================
# DIRETÓRIO DE TRABALHO (garante que arquivos fiquem ao lado do .exe)
# =====================================================================

if getattr(sys, 'frozen', False):
    # Estamos rodando como executável PyInstaller
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    # Rodando como script Python normal
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(_BASE_DIR)

COMIC_IMAGE_URLS = [
    "https://images.unsplash.com/photo-1612036782180-6f0b6cd846fe?auto=format&fit=crop&w=300&q=80",
    "https://images.unsplash.com/photo-1534447677768-be436bb09401?auto=format&fit=crop&w=300&q=80",
    "https://images.unsplash.com/photo-1563089145-599997674d42?auto=format&fit=crop&w=300&q=80",
    "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?auto=format&fit=crop&w=300&q=80",
    "https://images.unsplash.com/photo-1578632767115-351597cf2477?auto=format&fit=crop&w=300&q=80",
    "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=300&q=80",
    "https://images.unsplash.com/photo-1569003339405-ea396a5a8a90?auto=format&fit=crop&w=300&q=80",
    "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=300&q=80"
]

CONFIG_FILE = "greencbr_config.json"
FAVORITES_FILE = "greencbr_favorites.json"
HISTORY_FILE = "greencbr_history.json"
CACHE_FILE = "greencbr_cache.json"
CACHE_DB_FILE = "greencbr_cache.db"

COVERS_DIR = "cache_covers"

COMIC_VALID_EXTS = ('.cbr', '.cbz', '.cb7')
IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif')
VIDEO_EXTS = ('.mp4',)
MEDIA_EXTS = IMAGE_EXTS + VIDEO_EXTS

DEFAULT_UNREAD_LIMIT = 50
DEFAULT_SEARCH_LIMIT = 20

# Largura fixa de cada card (ComicThumbnail / FolderCard)
CARD_WIDTH = 140
CARD_SPACING = 12

QSS_STYLE = """
QMainWindow {
    background-color: #030f16;
}

QWidget#CentralWidget {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #030f16, stop:0.5 #061720, stop:1 #0a1f29);
}

/* Scrollbars */
QScrollBar:horizontal {
    border: none;
    background: #061720;
    height: 8px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #00b87c;
    min-width: 20px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal:hover {
    background: #00e699;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    border: none;
    background: none;
}

QScrollBar:vertical {
    border: none;
    background: #061720;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #00b87c;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #00e699;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

/* Sidebar */
QFrame#Sidebar {
    background-color: rgba(6, 23, 32, 0.85);
    border-right: 1px solid #0d2a36;
}

/* Header & Controls */
QLineEdit#SearchBar {
    background-color: rgba(10, 31, 41, 0.8);
    border: 1px solid #133a4a;
    border-radius: 8px;
    padding: 6px 14px;
    color: #e0f2fe;
    font-size: 13px;
}
QLineEdit#SearchBar:focus {
    border: 1px solid #00b87c;
}

/* Section Titles */
QLabel.SectionTitle {
    color: #f0fdf4;
    font-size: 18px;
    font-weight: bold;
    margin-top: 10px;
    margin-bottom: 5px;
}

/* Progress bars */
QProgressBar {
    background-color: #081a24;
    border: none;
    border-radius: 2px;
    max-height: 4px;
    color: transparent;
}
QProgressBar::chunk {
    background-color: #00b87c;
    border-radius: 2px;
}

/* Tooltip */
QToolTip {
    background-color: #0d2a36;
    color: #e0f2fe;
    border: 1px solid #00b87c;
    padding: 4px 8px;
    font-size: 12px;
}

/* SpinBox */
QSpinBox {
    background-color: rgba(10, 31, 41, 0.8);
    border: 1px solid #133a4a;
    border-radius: 8px;
    padding: 4px 10px;
    color: #e0f2fe;
    font-size: 13px;
}
QSpinBox:focus {
    border: 1px solid #00b87c;
}

/* CheckBox */
QCheckBox {
    color: #e0f2fe;
    font-size: 13px;
    font-weight: bold;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #133a4a;
    background-color: rgba(10, 31, 41, 0.8);
}
QCheckBox::indicator:hover {
    border: 2px solid #00b87c;
}
QCheckBox::indicator:checked {
    background-color: #00b87c;
    border: 2px solid #00e699;
    image: none;
}
"""


# =====================================================================
# UTILITÁRIOS
# =====================================================================

def _resource_path(relative_path: str) -> str:
    """Resolve o caminho de um recurso (logo, ícone...), tanto em dev quanto
    em executável PyInstaller."""
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class HorizontalScrollArea(QScrollArea):
    def wheelEvent(self, event: QWheelEvent):
        if event.angleDelta().y() != 0:
            delta = event.angleDelta().y()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta
            )
            event.accept()
        else:
            super().wheelEvent(event)


def create_placeholder_cover(title: str, subtitle: str = "",
                             color_theme: str = "#0d3a4a",
                             width: int = 120, height: int = 170) -> QPixmap:
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    gradient = QLinearGradient(0, 0, width, height)
    if color_theme == "purple":
        gradient.setColorAt(0, QColor("#3a0ca3"))
        gradient.setColorAt(1, QColor("#7209b7"))
    elif color_theme == "teal":
        gradient.setColorAt(0, QColor("#005f73"))
        gradient.setColorAt(1, QColor("#0a9396"))
    elif color_theme == "red":
        gradient.setColorAt(0, QColor("#9b5de5"))
        gradient.setColorAt(1, QColor("#f15bb5"))
    else:
        gradient.setColorAt(0, QColor("#0a2533"))
        gradient.setColorAt(1, QColor("#005f73"))

    path = QPainterPath()
    path.addRoundedRect(0, 0, width, height, 8, 8)
    painter.fillPath(path, gradient)

    painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
    painter.drawRoundedRect(4, 4, width - 8, height - 8, 6, 6)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(255, 255, 255, 25))
    painter.drawEllipse(int(width * 0.2), int(height * 0.2),
                        int(width * 0.6), int(width * 0.6))

    painter.setPen(QColor("#ffffff"))
    font_title = QFont("Arial", 11, QFont.Weight.Bold)
    painter.setFont(font_title)
    painter.drawText(
        QRect(6, int(height * 0.35), width - 12, 40),
        Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
        title
    )

    if subtitle:
        font_sub = QFont("Arial", 8)
        painter.setFont(font_sub)
        painter.setPen(QColor("#00e699"))
        painter.drawText(
            QRect(6, int(height * 0.75), width - 12, 20),
            Qt.AlignmentFlag.AlignCenter,
            subtitle
        )

    painter.end()
    return pixmap


def load_remote_image(label: QLabel, image_url: str, width: int, height: int):
    if not image_url:
        return

    network_manager = QNetworkAccessManager(label)

    def on_loaded(reply):
        if reply.error() == reply.NetworkError.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                scaled_pixmap = pixmap.scaled(
                    width, height,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation
                )

                rounded = QPixmap(width, height)
                rounded.fill(Qt.GlobalColor.transparent)

                painter = QPainter(rounded)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                path = QPainterPath()
                path.addRoundedRect(0, 0, width, height, 6, 6)
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, scaled_pixmap)
                painter.end()

                label.setPixmap(rounded)
        reply.deleteLater()

    network_manager.finished.connect(on_loaded)
    request = QNetworkRequest(QUrl(image_url))
    network_manager.get(request)


def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'(\d+)', s)]


def make_rounded_pixmap(pixmap: QPixmap, width: int, height: int,
                        radius: int = 6) -> QPixmap:
    if pixmap is None or pixmap.isNull():
        return QPixmap()

    scaled = pixmap.scaled(
        width, height,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation
    )

    rounded = QPixmap(width, height)
    rounded.fill(Qt.GlobalColor.transparent)

    painter = QPainter(rounded)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    path = QPainterPath()
    path.addRoundedRect(0, 0, width, height, radius, radius)
    painter.setClipPath(path)

    offset_x = (scaled.width() - width) // 2
    offset_y = (scaled.height() - height) // 2
    painter.drawPixmap(-offset_x, -offset_y, scaled)
    painter.end()

    return rounded


def overlay_folder_icon(pixmap: QPixmap, size: int = 30) -> QPixmap:
    if pixmap is None or pixmap.isNull():
        return pixmap

    result = QPixmap(pixmap)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    badge_rect = QRect(4, 4, size, size)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(3, 15, 22, 190))
    painter.drawRoundedRect(badge_rect, size // 2, size // 2)

    font = QFont("Segoe UI Emoji", int(size * 0.55))
    painter.setFont(font)
    painter.setPen(QColor("#ffffff"))
    painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, "📁")

    painter.end()
    return result


# =====================================================================
# PERSISTÊNCIA
# =====================================================================

def load_favorites() -> set:
    if not os.path.exists(FAVORITES_FILE):
        return set()
    try:
        with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            return set(data)
    except Exception as e:
        print(f"[AVISO] Falha ao carregar favoritos: {e}")
    return set()


def save_favorites(favorites: set):
    try:
        with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
            json.dump(sorted(list(favorites)), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERRO] Falha ao salvar favoritos: {e}")


def load_history() -> dict:
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception as e:
        print(f"[AVISO] Falha ao carregar histórico: {e}")
    return {}


def save_history_item(file_path: str, page: int, total: int):
    import datetime
    history = load_history()
    history[file_path] = {
        "page": page,
        "total": total,
        "last_read": datetime.datetime.now().isoformat()
    }
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERRO] Falha ao salvar histórico: {e}")


def remove_from_history(file_path: str):
    history = load_history()
    if file_path in history:
        del history[file_path]
        try:
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ERRO] Falha ao remover do histórico: {e}")


def load_cache() -> dict:
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(data: dict):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERRO] Falha ao salvar cache: {e}")


# =====================================================================
# CACHE SQLITE + MINIATURAS EM DISCO
# =====================================================================

_db_conn = None
_covers_dir_cache = None


def _get_covers_dir() -> Path:
    global _covers_dir_cache
    if _covers_dir_cache is None:
        p = Path(COVERS_DIR)
        p.mkdir(parents=True, exist_ok=True)
        _covers_dir_cache = p
    return _covers_dir_cache


def _cover_hash(file_path: str, mtime: float, size: int) -> str:
    base = f"{file_path}|{mtime:.6f}|{size}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


def _get_db():
    global _db_conn
    if _db_conn is not None:
        return _db_conn
    try:
        _db_conn = sqlite3.connect(CACHE_DB_FILE, check_same_thread=False)
        _db_conn.execute("PRAGMA journal_mode=WAL;")
        _db_conn.execute("PRAGMA synchronous=NORMAL;")
        _db_conn.execute("""
            CREATE TABLE IF NOT EXISTS covers_cache (
                folder_root TEXT NOT NULL,
                file_path   TEXT NOT NULL,
                mtime       REAL NOT NULL,
                size        INTEGER NOT NULL,
                page_count  INTEGER NOT NULL,
                cover_hash  TEXT,
                PRIMARY KEY (folder_root, file_path)
            );
        """)
        _db_conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_folder_root
            ON covers_cache(folder_root);
        """)
        _db_conn.commit()
    except Exception as e:
        print(f"[ERRO] Falha ao abrir cache SQLite: {e}")
        _db_conn = None
    return _db_conn


def db_load_folder_cache(folder_root: str) -> dict:
    conn = _get_db()
    if conn is None:
        return {}
    result = {}
    try:
        cur = conn.execute(
            "SELECT file_path, mtime, size, page_count, cover_hash "
            "FROM covers_cache WHERE folder_root = ?",
            (folder_root,)
        )
        for file_path, mtime, size, page_count, cover_hash in cur.fetchall():
            result[file_path] = {
                "mtime": mtime,
                "size": size,
                "page_count": page_count,
                "cover_hash": cover_hash,
            }
    except Exception as e:
        print(f"[AVISO] Falha ao ler cache SQLite: {e}")
    return result


def db_save_folder_cache(folder_root: str, items: dict):
    conn = _get_db()
    if conn is None:
        return
    try:
        rows = []
        for file_path, data in items.items():
            rows.append((
                folder_root,
                file_path,
                float(data.get("mtime", 0)),
                int(data.get("size", 0)),
                int(data.get("page_count", 0)),
                data.get("cover_hash"),
            ))
        conn.executemany(
            "INSERT OR REPLACE INTO covers_cache "
            "(folder_root, file_path, mtime, size, page_count, cover_hash) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows
        )
        conn.commit()
    except Exception as e:
        print(f"[AVISO] Falha ao salvar cache SQLite: {e}")


def save_cover_to_disk(file_path: str, mtime: float, size: int,
                       pixmap: QPixmap) -> str:
    if pixmap is None or pixmap.isNull():
        return ""
    h = _cover_hash(file_path, mtime, size)
    destino = _get_covers_dir() / f"{h}.png"

    if destino.exists():
        return h

    try:
        thumb = pixmap
        if pixmap.width() > 256 or pixmap.height() > 256:
            thumb = pixmap.scaled(
                256, 256,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        thumb.save(str(destino), "PNG")
        return h
    except Exception as e:
        print(f"[AVISO] Falha ao salvar miniatura: {e}")
        return ""


def load_cover_from_disk(cover_hash: str) -> QPixmap:
    if not cover_hash:
        return QPixmap()
    destino = _get_covers_dir() / f"{cover_hash}.png"
    if not destino.exists():
        return QPixmap()
    try:
        pm = QPixmap(str(destino))
        return pm
    except Exception:
        return QPixmap()


def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(config: dict):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERRO] Falha ao salvar config: {e}")


def get_unread_limit() -> int:
    cfg = load_config()
    try:
        return int(cfg.get("unread_limit", DEFAULT_UNREAD_LIMIT))
    except Exception:
        return DEFAULT_UNREAD_LIMIT


def get_search_limit() -> int:
    cfg = load_config()
    try:
        return int(cfg.get("search_limit", DEFAULT_SEARCH_LIMIT))
    except Exception:
        return DEFAULT_SEARCH_LIMIT


# =====================================================================
# EXTRAÇÃO
# =====================================================================

_rarfile_configured = False


def _configure_rarfile():
    global _rarfile_configured
    if _rarfile_configured:
        return True

    try:
        import rarfile
    except ImportError:
        return False

    try:
        rarfile.tool_setup()
        _rarfile_configured = True
        return True
    except Exception:
        pass

    possible_paths = [
        r"C:\Program Files\WinRAR\UnRAR.exe",
        r"C:\Program Files (x86)\WinRAR\UnRAR.exe",
        r"C:\Program Files\WinRAR\Rar.exe",
        r"C:\Program Files (x86)\WinRAR\Rar.exe",
    ]

    for path in possible_paths:
        if os.path.exists(path):
            try:
                rarfile.UNRAR_TOOL = path
                rarfile.tool_setup()
                _rarfile_configured = True
                return True
            except Exception:
                continue

    return False


def _detect_archive_type(file_path: str) -> str:
    try:
        with open(file_path, 'rb') as f:
            header = f.read(8)
    except Exception:
        return 'unknown'

    if header[:4] == b'PK\x03\x04' or header[:4] == b'PK\x05\x06':
        return 'zip'
    if header[:4] == b'Rar!' or header[:7] == b'Rar!\x1a\x07\x00' \
            or header[:8] == b'Rar!\x1a\x07\x01\x00':
        return 'rar'
    if header[:6] == b'7z\xbc\xaf\x27\x1c':
        return '7z'
    return 'unknown'


class _BytesReader:
    def __init__(self, data: bytes):
        self._data = data
        self._pos = 0

    def read(self, n: int = -1) -> bytes:
        if n < 0:
            data = self._data[self._pos:]
            self._pos = len(self._data)
            return data
        data = self._data[self._pos:self._pos + n]
        self._pos += len(data)
        return data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _open_zip(file_path):
    zf = zipfile.ZipFile(file_path, 'r')
    return zf, zf.namelist(), zf.open


def _open_rar(file_path):
    if not _configure_rarfile():
        raise RuntimeError(
            "rarfile não pôde ser configurado. Instale o WinRAR ou o unrar."
        )
    import rarfile
    rf = rarfile.RarFile(file_path, 'r')
    return rf, rf.namelist(), rf.open


def _open_7z(file_path):
    try:
        import py7zr
    except ImportError:
        raise RuntimeError("py7zr não instalado. Instale com: pip install py7zr")

    archive = py7zr.SevenZipFile(file_path, mode='r')
    names = archive.getnames()
    cache = {}

    def open_member(name):
        if name not in cache:
            extracted = archive.read([name])
            if name not in extracted:
                raise FileNotFoundError(name)
            cache[name] = extracted[name].read()
        return _BytesReader(cache[name])

    return archive, names, open_member


def _open_archive(file_path):
    archive_type = _detect_archive_type(file_path)
    if archive_type == 'zip':
        return _open_zip(file_path)
    if archive_type == 'rar':
        return _open_rar(file_path)
    if archive_type == '7z':
        return _open_7z(file_path)
    raise RuntimeError(f"Formato desconhecido: {file_path}")


def _list_media_files(namelist) -> list:
    media = [
        f for f in namelist
        if f.lower().endswith(MEDIA_EXTS)
        and '__MACOSX' not in f
        and not f.split('/')[-1].startswith('.')
    ]
    media.sort(key=natural_sort_key)
    return media


def extract_cover_and_pagecount(file_path: str):
    try:
        archive, namelist, open_func = _open_archive(file_path)
    except Exception as e:
        print(f"[ERRO] Não foi possível abrir {file_path}: {e}")
        return None, 0

    try:
        media_files = _list_media_files(namelist)
        page_count = len(media_files)

        pixmap = None
        for candidate in media_files[:5]:
            if candidate.lower().endswith(IMAGE_EXTS):
                try:
                    with open_func(candidate) as img_file:
                        data = img_file.read()
                        pm = QPixmap()
                        if pm.loadFromData(data) and not pm.isNull():
                            pixmap = pm
                            break
                except Exception as e:
                    print(f"[AVISO] Falha ao ler {candidate}: {e}")
                    continue

        return pixmap, page_count
    finally:
        try:
            archive.close()
        except Exception:
            pass


def load_comic_pages_data(file_path: str, temp_dir: str) -> list:
    pages_data = []
    try:
        archive, namelist, open_func = _open_archive(file_path)
    except Exception as e:
        print(f"[ERRO] Falha ao ler arquivo do quadrinho: {e}")
        return []

    try:
        media_files = _list_media_files(namelist)
        for idx, media_name in enumerate(media_files):
            ext = os.path.splitext(media_name)[1].lower()
            try:
                with open_func(media_name) as f:
                    data = f.read()

                if ext in IMAGE_EXTS:
                    pm = QPixmap()
                    if pm.loadFromData(data) and not pm.isNull():
                        pages_data.append({'type': 'image', 'pixmap': pm, 'data': data})
                elif ext in VIDEO_EXTS:
                    v_path = os.path.join(temp_dir, f"page_{idx}_{os.path.basename(media_name)}")
                    with open(v_path, 'wb') as vf:
                        vf.write(data)
                    pages_data.append({'type': 'video', 'path': v_path})
            except Exception as e:
                print(f"[AVISO] Falha ao carregar página {media_name}: {e}")
    finally:
        try:
            archive.close()
        except Exception:
            pass

    return pages_data


# =====================================================================
# SCAN
# =====================================================================

def scan_comic_folder(folder_path: str) -> dict:
    result = {"loose_files": [], "folders": {}}
    if not folder_path or not os.path.isdir(folder_path):
        return result

    try:
        entries = list(os.scandir(folder_path))
    except Exception as e:
        print(f"[ERRO] Falha ao listar pasta {folder_path}: {e}")
        return result

    entries.sort(key=lambda e: natural_sort_key(e.name))

    for entry in entries:
        try:
            if entry.is_file(follow_symlinks=False):
                if entry.name.lower().endswith(COMIC_VALID_EXTS):
                    result["loose_files"].append(entry.path)
            elif entry.is_dir(follow_symlinks=False):
                sub_result = scan_comic_folder(entry.path)
                if sub_result["loose_files"] or sub_result["folders"]:
                    result["folders"][entry.name] = sub_result
        except Exception as e:
            print(f"[AVISO] Falha ao processar {entry.path}: {e}")
            continue

    return result


def _collect_all_files(scan_node: dict) -> list:
    files = list(scan_node.get("loose_files", []))
    for sub in scan_node.get("folders", {}).values():
        files.extend(_collect_all_files(sub))
    return files


def _count_all_comics(scan_node: dict) -> int:
    return len(_collect_all_files(scan_node))


def _find_first_cover(scan_node: dict, covers: dict):
    for f in scan_node.get("loose_files", []):
        h = covers.get(f)
        if h:
            pm = load_cover_from_disk(h)
            if not pm.isNull():
                return pm
    for sub in scan_node.get("folders", {}).values():
        pm = _find_first_cover(sub, covers)
        if pm is not None:
            return pm
    return None


def _extrair_capa_worker(args):
    file_path, mtime, size = args
    try:
        pixmap, count = extract_cover_and_pagecount(file_path)
        cover_hash = ""
        if pixmap is not None and not pixmap.isNull():
            cover_hash = save_cover_to_disk(file_path, mtime, size, pixmap)
            del pixmap
        return file_path, mtime, size, count, cover_hash
    except Exception as e:
        print(f"[AVISO] Falha ao processar {file_path}: {e}")
        return file_path, mtime, size, 0, ""


class ComicScannerThread(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(dict)

    MAX_WORKERS = 4

    def __init__(self, folder_path: str, force_rescan: bool = False):
        super().__init__()
        self.folder_path = folder_path
        self.force_rescan = force_rescan
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        t0 = time.time()

        result = scan_comic_folder(self.folder_path)
        all_files = _collect_all_files(result)
        total = len(all_files)

        covers = {}
        page_counts = {}
        new_cache = {}

        if total == 0:
            result["covers"] = covers
            result["page_counts"] = page_counts
            self.finished.emit(result)
            return

        self.progress.emit(0, total, "Lendo cache SQLite...")

        cache_data = db_load_folder_cache(self.folder_path)

        files_cached = []
        files_to_extract = []

        for file_path in all_files:
            if self._cancelled:
                return
            try:
                st = os.stat(file_path)
                mtime = st.st_mtime
                size = st.st_size
            except Exception:
                mtime = 0
                size = 0

            cached_item = cache_data.get(file_path)
            cache_ok = (
                cached_item is not None
                and cached_item.get("mtime") == mtime
                and cached_item.get("size") == size
                and cached_item.get("cover_hash")
            )
            if cache_ok:
                h = cached_item.get("cover_hash")
                destino = _get_covers_dir() / f"{h}.png"
                if not destino.exists():
                    cache_ok = False

            if cache_ok:
                files_cached.append((file_path, mtime, size, cached_item))
            else:
                files_to_extract.append((file_path, mtime, size))

        for file_path, mtime, size, cached_item in files_cached:
            page_counts[file_path] = cached_item.get("page_count", 0)
            covers[file_path] = cached_item.get("cover_hash", "")
            new_cache[file_path] = cached_item

        n_cached = len(files_cached)
        n_new = len(files_to_extract)

        if n_cached > 0:
            self.progress.emit(
                n_cached, total,
                f"✓ {n_cached} do cache — extraindo {n_new} nova(s)..."
            )

        if files_to_extract and not self._cancelled:
            done = n_cached
            with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as ex:
                futures = {
                    ex.submit(_extrair_capa_worker, item): item[0]
                    for item in files_to_extract
                }

                for fut in as_completed(futures):
                    if self._cancelled:
                        return
                    try:
                        fp, mtime, size, count, cover_hash = fut.result()
                    except Exception as e:
                        print(f"[AVISO] Erro em thread: {e}")
                        done += 1
                        continue

                    covers[fp] = cover_hash
                    page_counts[fp] = count
                    new_cache[fp] = {
                        "mtime": mtime,
                        "size": size,
                        "page_count": count,
                        "cover_hash": cover_hash,
                    }

                    done += 1
                    self.progress.emit(done, total, os.path.basename(fp))

        if self._cancelled:
            return

        db_save_folder_cache(self.folder_path, new_cache)

        result["covers"] = covers
        result["page_counts"] = page_counts

        dt = time.time() - t0
        print(f"[SCAN] {total} arquivos em {dt:.2f}s "
              f"({n_cached} do cache, {n_new} extraídos)")

        self.finished.emit(result)


# =====================================================================
# LOADER DE QUADRINHO (para abrir sem travar a UI)
# =====================================================================

class ComicLoaderThread(QThread):
    """Carrega as páginas de um quadrinho em background.

    Emite 'finished' com a lista de páginas ou 'error' com mensagem.
    """
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, file_path: str, temp_dir: str):
        super().__init__()
        self.file_path = file_path
        self.temp_dir = temp_dir

    def run(self):
        try:
            pages = load_comic_pages_data(self.file_path, self.temp_dir)
            if not pages:
                self.error.emit("Não foi possível extrair páginas do arquivo.")
                return
            self.finished.emit(pages)
        except Exception as e:
            self.error.emit(str(e))


# =====================================================================
# SPINNER
# =====================================================================

class LoadingSpinner(QWidget):
    def __init__(self, text: str = "Carregando", parent=None):
        super().__init__(parent)
        self.base_text = text
        self.dots = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.setInterval(300)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.lbl = QLabel(f"{text}...")
        self.lbl.setStyleSheet(
            "color: #00e699; font-size: 12px; font-style: italic;"
        )
        layout.addWidget(self.lbl)
        layout.addStretch()

    def _tick(self):
        self.dots = (self.dots + 1) % 4
        self.lbl.setText(self.base_text + "." * self.dots)

    def start(self):
        self._timer.start()

    def stop(self):
        self._timer.stop()


# =====================================================================
# LEITOR
# =====================================================================

class ComicReaderPage(QWidget):
    page_changed = pyqtSignal(str, int, int)
    back_requested = pyqtSignal()
    unread_requested = pyqtSignal(str)
    favorite_toggled = pyqtSignal(str, bool)
    read_toggled = pyqtSignal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path = ""
        self.pages = []
        self.current_page_idx = 0
        self.fit_mode = "width"
        self.temp_dir = None
        self.zoom_factor = 1.0
        self._current_page_data = None
        self._loader_thread = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        top_bar = QHBoxLayout()

        btn_back = QPushButton("← Voltar")
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.setStyleSheet("""
            QPushButton {
                background-color: rgba(10, 31, 41, 0.9);
                color: #00e699;
                border: 1px solid #00b87c;
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00b87c;
                color: #030f16;
            }
        """)
        btn_back.clicked.connect(self._on_back_clicked)

        btn_close = QPushButton("✖ Fechar Leitura")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: rgba(180, 40, 40, 0.8);
                color: #ffffff;
                border: 1px solid #ff4d4d;
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff4d4d;
                color: #ffffff;
            }
        """)
        btn_close.clicked.connect(self.close_comic)

        self.btn_toggle_thumbs = QPushButton("🖼️ Miniaturas")
        self.btn_toggle_thumbs.setCheckable(True)
        self.btn_toggle_thumbs.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_thumbs.setStyleSheet("""
            QPushButton {
                background-color: rgba(10, 31, 41, 0.9);
                color: #00e699;
                border: 1px solid #00b87c;
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: #00b87c;
                color: #030f16;
            }
            QPushButton:hover {
                background-color: #00e699;
                color: #030f16;
            }
        """)
        self.btn_toggle_thumbs.toggled.connect(self.toggle_thumbnails)

        # ----- Checkbox "Lido" -----
        self.chk_read = QCheckBox("Lido")
        self.chk_read.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_read.setToolTip("Marcar este quadrinho como lido")
        self.chk_read.toggled.connect(self._on_chk_read_toggled)

        # ----- Botão Favoritar -----
        self.btn_fav = QPushButton("🤍 Favoritar")
        self.btn_fav.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fav.setCheckable(True)
        self.btn_fav.setStyleSheet("""
            QPushButton {
                background-color: rgba(10, 31, 41, 0.9);
                color: #e0f2fe;
                border: 1px solid #133a4a;
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: rgba(231, 88, 43, 0.9);
                color: #ffffff;
                border: 1px solid #ff6b3d;
            }
            QPushButton:hover {
                background-color: #00b87c;
                color: #030f16;
            }
        """)
        self.btn_fav.toggled.connect(self._on_fav_toggled)

        self.lbl_title = QLabel("Leitor de Quadrinho")
        self.lbl_title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold;")

        self.combo_fit = QComboBox()
        self.combo_fit.addItems(["Ajustar à Largura", "Ajustar à Tela", "Tamanho Real"])
        self.combo_fit.setStyleSheet("""
            QComboBox {
                background-color: #0a1f29;
                color: #e0f2fe;
                border: 1px solid #133a4a;
                border-radius: 6px;
                padding: 4px 8px;
            }
        """)
        self.combo_fit.currentIndexChanged.connect(self._on_fit_mode_changed)

        btn_prev = QPushButton("◀ Anterior")
        btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_prev.setStyleSheet("color: #e0f2fe; background: #0a1f29; border: 1px solid #133a4a; border-radius: 6px; padding: 5px 12px;")
        btn_prev.clicked.connect(self.prev_page)

        self.lbl_page_counter = QLabel("Página 0 / 0")
        self.lbl_page_counter.setStyleSheet("color: #00e699; font-weight: bold; font-size: 13px;")

        btn_next = QPushButton("Próxima ▶")
        btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_next.setStyleSheet("color: #e0f2fe; background: #0a1f29; border: 1px solid #133a4a; border-radius: 6px; padding: 5px 12px;")
        btn_next.clicked.connect(self.next_page)

        top_bar.addWidget(btn_back)
        top_bar.addWidget(btn_close)
        top_bar.addWidget(self.btn_toggle_thumbs)
        top_bar.addWidget(self.chk_read)
        top_bar.addWidget(self.btn_fav)
        top_bar.addWidget(self.lbl_title, 1)
        top_bar.addWidget(QLabel("Modo:"))
        top_bar.addWidget(self.combo_fit)
        top_bar.addSpacing(15)
        top_bar.addWidget(btn_prev)
        top_bar.addWidget(self.lbl_page_counter)
        top_bar.addWidget(btn_next)

        layout.addLayout(top_bar)

        self.reader_container = QWidget()
        self.reader_container_layout = QVBoxLayout(self.reader_container)
        self.reader_container_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setStyleSheet("background-color: #030a0e; border: 1px solid #0d2a36; border-radius: 8px;")

        self.display_stack = QStackedWidget()

        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.img_label.customContextMenuRequested.connect(self._show_image_context_menu)

        self.video_widget = QVideoWidget()
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)

        self.display_stack.addWidget(self.img_label)
        self.display_stack.addWidget(self.video_widget)

        self.scroll_area.setWidget(self.display_stack)
        self.scroll_area.setWidgetResizable(True)

        self.reader_container_layout.addWidget(self.scroll_area)
        layout.addWidget(self.reader_container, 1)

        # ---------- Overlay de carregamento ----------
        self.loading_overlay = QFrame(self.reader_container)
        self.loading_overlay.setStyleSheet("""
            QFrame {
                background-color: rgba(3, 15, 22, 0.85);
                border-radius: 8px;
            }
        """)
        loading_layout = QVBoxLayout(self.loading_overlay)
        loading_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.loading_spinner = LoadingSpinner("Carregando leitura")
        self.loading_spinner.setStyleSheet("""
            QLabel {
                color: #00e699;
                font-size: 18px;
                font-weight: bold;
                font-style: italic;
            }
        """)
        self.loading_spinner.lbl.setStyleSheet("""
            color: #00e699;
            font-size: 18px;
            font-weight: bold;
            font-style: italic;
        """)
        loading_layout.addWidget(self.loading_spinner)

        self.loading_overlay.hide()

        self.btn_next_floating = QPushButton("Próxima Página ➔", self)
        self.btn_next_floating.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next_floating.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: #000000;
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #ffa000;
                border-radius: 20px;
                padding: 10px 24px;
            }
            QPushButton:hover {
                background-color: #ffca28;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 4)
        self.btn_next_floating.setGraphicsEffect(shadow)
        self.btn_next_floating.hide()
        self.btn_next_floating.clicked.connect(self.next_page)

        self.thumbs_panel = QFrame(self)
        self.thumbs_panel.setStyleSheet("""
            QFrame {
                background-color: rgba(6, 23, 32, 0.95);
                border-top: 2px solid #00b87c;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }
        """)
        self.thumbs_panel.setFixedHeight(120)

        thumbs_panel_layout = QVBoxLayout(self.thumbs_panel)
        thumbs_panel_layout.setContentsMargins(10, 8, 10, 8)

        self.thumbs_scroll = HorizontalScrollArea()
        self.thumbs_scroll.setWidgetResizable(True)
        self.thumbs_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.thumbs_scroll.setStyleSheet("background: transparent;")

        self.thumbs_container = QWidget()
        self.thumbs_hbox = QHBoxLayout(self.thumbs_container)
        self.thumbs_hbox.setContentsMargins(0, 0, 0, 0)
        self.thumbs_hbox.setSpacing(10)

        self.thumbs_scroll.setWidget(self.thumbs_container)
        thumbs_panel_layout.addWidget(self.thumbs_scroll)
        self.thumbs_panel.hide()

        self.thumbs_anim = QPropertyAnimation(self.thumbs_panel, b"pos")
        self.thumbs_anim.setDuration(250)
        self.thumbs_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll)

        self.reader_pbar = QProgressBar()
        self.reader_pbar.setRange(0, 100)
        self.reader_pbar.setValue(0)
        self.reader_pbar.setStyleSheet("""
            QProgressBar {
                background-color: #061720;
                border: none;
                height: 6px;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #00b87c;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.reader_pbar)

        shortcut_left = QShortcut(QKeySequence(Qt.Key.Key_Left), self)
        shortcut_left.activated.connect(self.prev_page)
        shortcut_right = QShortcut(QKeySequence(Qt.Key.Key_Right), self)
        shortcut_right.activated.connect(self.next_page)
        shortcut_space = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        shortcut_space.activated.connect(self.next_page)

    def _cleanup_temp_dir(self):
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass
        self.temp_dir = None

    def _on_chk_read_toggled(self, checked: bool):
        if not self.file_path:
            return
        if checked:
            # Marca como lido (vai para a última página)
            if self.pages:
                self.current_page_idx = len(self.pages) - 1
                save_history_item(self.file_path, len(self.pages), len(self.pages))
                self.read_toggled.emit(self.file_path, True)
                self.render_current_page()
        else:
            # Desmarca como lido (remove do histórico)
            remove_from_history(self.file_path)
            self.read_toggled.emit(self.file_path, False)
            self.page_changed.emit(self.file_path, self.current_page_idx + 1, len(self.pages))

    def _on_fav_toggled(self, checked: bool):
        if not self.file_path:
            return
        self.btn_fav.setText("❤️ Favoritado" if checked else "🤍 Favoritar")
        self.favorite_toggled.emit(self.file_path, checked)

    def set_favorite_state(self, is_fav: bool):
        self.btn_fav.blockSignals(True)
        self.btn_fav.setChecked(is_fav)
        self.btn_fav.setText("❤️ Favoritado" if is_fav else "🤍 Favoritar")
        self.btn_fav.blockSignals(False)

    def _show_image_context_menu(self, pos):
        if not self._current_page_data or self._current_page_data.get('type') != 'image':
            return
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0d2a36;
                color: #e0f2fe;
                border: 1px solid #00b87c;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px 6px 12px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #00b87c;
                color: #030f16;
            }
        """)
        save_action = QAction("💾 Salvar como...", self)
        save_action.triggered.connect(self._save_current_image)
        menu.addAction(save_action)
        menu.exec(self.img_label.mapToGlobal(pos))

    def _save_current_image(self):
        if not self._current_page_data or self._current_page_data.get('type') != 'image':
            return
        pixmap = self._current_page_data.get('pixmap')
        if not pixmap or pixmap.isNull():
            return
        base_name = os.path.splitext(os.path.basename(self.file_path))[0]
        default_name = f"{base_name}_pagina_{self.current_page_idx + 1}.png"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Salvar imagem como...", default_name,
            "Imagens (*.png *.jpg *.jpeg *.bmp);;Todos os arquivos (*)"
        )
        if file_path:
            try:
                pixmap.save(file_path)
                QMessageBox.information(self, "Salvo", f"Imagem salva em:\n{file_path}")
            except Exception as e:
                QMessageBox.warning(self, "Erro", f"Falha ao salvar imagem:\n{e}")

    def close_comic(self):
        if self._loader_thread is not None and self._loader_thread.isRunning():
            try:
                self._loader_thread.quit()
                self._loader_thread.wait(2000)
            except Exception:
                pass
            self._loader_thread = None
        self.media_player.stop()
        self._cleanup_temp_dir()
        self.file_path = ""
        self.pages = []
        self.current_page_idx = 0
        self.zoom_factor = 1.0
        self._current_page_data = None
        self.img_label.clear()
        self.lbl_title.setText("Leitor de Quadrinho")
        self.lbl_page_counter.setText("Página 0 / 0")
        self.reader_pbar.setValue(0)
        self.btn_next_floating.hide()
        self.loading_overlay.hide()
        if self.btn_toggle_thumbs.isChecked():
            self.btn_toggle_thumbs.setChecked(False)

    def open_comic(self, file_path: str, start_page: int = 1):
        self.close_comic()
        self.file_path = file_path
        self.temp_dir = tempfile.mkdtemp(prefix="greencbr_")
        title = os.path.splitext(os.path.basename(file_path))[0]
        self.lbl_title.setText(f"📖 {title}")
        self._start_page = start_page

        # Mostra o overlay de carregamento
        self.loading_overlay.show()
        self.loading_overlay.raise_()
        self.loading_spinner.start()
        self._update_loading_overlay_geometry()

        # Inicia a thread de carregamento
        self._loader_thread = ComicLoaderThread(file_path, self.temp_dir)
        self._loader_thread.finished.connect(self._on_pages_loaded)
        self._loader_thread.error.connect(self._on_load_error)
        self._loader_thread.start()

    def _on_pages_loaded(self, pages):
        self.loading_spinner.stop()
        self.loading_overlay.hide()
        self._loader_thread = None

        self.pages = pages
        total_pages = len(self.pages)
        self.current_page_idx = max(0, min(self._start_page - 1, total_pages - 1))
        self.zoom_factor = 1.0

        # Estado "Lido" — marcado se o histórico já indicar última página
        history = load_history()
        h = history.get(self.file_path, {})
        is_read = (h.get("page", 0) >= total_pages and total_pages > 0)
        self.chk_read.blockSignals(True)
        self.chk_read.setChecked(is_read)
        self.chk_read.blockSignals(False)

        # Estado "Favorito"
        favs = load_favorites()
        self.set_favorite_state(self.file_path in favs)

        self.populate_thumbnails()
        self.render_current_page()

    def _on_load_error(self, msg):
        self.loading_spinner.stop()
        self.loading_overlay.hide()
        self._loader_thread = None
        QMessageBox.warning(self, "Erro ao abrir", f"Não foi possível abrir o quadrinho:\n{msg}")
        self.close_comic()

    def render_current_page(self):
        self.media_player.stop()
        self.btn_next_floating.hide()

        if not self.pages or self.current_page_idx < 0 or self.current_page_idx >= len(self.pages):
            return

        page = self.pages[self.current_page_idx]
        self._current_page_data = page

        if page['type'] == 'image':
            self.display_stack.setCurrentWidget(self.img_label)
            pixmap = page['pixmap']
            if not pixmap.isNull():
                viewport_size = self.scroll_area.viewport().size()
                v_width = viewport_size.width() - 20
                v_height = viewport_size.height() - 20

                base = pixmap
                if self.fit_mode == "width" and v_width > 50:
                    base = pixmap.scaledToWidth(v_width, Qt.TransformationMode.SmoothTransformation)
                elif self.fit_mode == "fit" and v_width > 50 and v_height > 50:
                    base = pixmap.scaled(v_width, v_height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

                # Aplica zoom
                if abs(self.zoom_factor - 1.0) > 0.001:
                    new_w = max(1, int(base.width() * self.zoom_factor))
                    new_h = max(1, int(base.height() * self.zoom_factor))
                    base = base.scaled(new_w, new_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

                self.img_label.setPixmap(base)
                self.img_label.adjustSize()

        elif page['type'] == 'video':
            self.display_stack.setCurrentWidget(self.video_widget)
            self.media_player.setSource(QUrl.fromLocalFile(page['path']))
            self.media_player.play()

        total = len(self.pages)
        curr = self.current_page_idx + 1
        self.lbl_page_counter.setText(f"Página {curr} / {total}")
        progress = int((curr / total) * 100) if total > 0 else 0
        self.reader_pbar.setValue(progress)

        # Atualiza o checkbox "Lido" baseado na última página
        is_last_page = (curr == total and total > 0)
        self.chk_read.blockSignals(True)
        self.chk_read.setChecked(is_last_page)
        self.chk_read.blockSignals(False)

        QTimer.singleShot(10, lambda: self.scroll_area.verticalScrollBar().setValue(0))
        self.update_thumbnails_selection()
        self.page_changed.emit(self.file_path, curr, total)
        save_history_item(self.file_path, curr, total)

    def populate_thumbnails(self):
        while self.thumbs_hbox.count():
            item = self.thumbs_hbox.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        for idx, page in enumerate(self.pages):
            thumb_btn = QPushButton()
            thumb_btn.setFixedSize(60, 85)
            thumb_btn.setCursor(Qt.CursorShape.PointingHandCursor)

            if page['type'] == 'image':
                pix = make_rounded_pixmap(page['pixmap'], 60, 85, radius=4)
                icon = QLabel(thumb_btn)
                icon.setPixmap(pix)
                icon.setGeometry(0, 0, 60, 85)
            else:
                lbl_v = QLabel("🎬\nVídeo", thumb_btn)
                lbl_v.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_v.setGeometry(0, 0, 60, 85)
                lbl_v.setStyleSheet("color: #00e699; font-weight: bold; background: #0a2533; border-radius: 4px;")

            thumb_btn.clicked.connect(lambda _, i=idx: self.go_to_page(i))
            self.thumbs_hbox.addWidget(thumb_btn)

        self.update_thumbnails_selection()

    def update_thumbnails_selection(self):
        for idx in range(self.thumbs_hbox.count()):
            item = self.thumbs_hbox.itemAt(idx)
            w = item.widget()
            if w:
                if idx == self.current_page_idx:
                    w.setStyleSheet("border: 2px solid #ffc107; border-radius: 6px;")
                    QTimer.singleShot(50, lambda widget=w: self.thumbs_scroll.ensureWidgetVisible(widget))
                else:
                    w.setStyleSheet("border: 1px solid #133a4a; border-radius: 6px;")

    def go_to_page(self, index: int):
        if 0 <= index < len(self.pages):
            self.current_page_idx = index
            self.render_current_page()

    def toggle_thumbnails(self, checked: bool):
        self.update_layout_positions()
        end_y = self.height() - self.thumbs_panel.height() - 25 if checked else self.height()

        if checked:
            self.thumbs_panel.show()

        self.thumbs_anim.stop()
        self.thumbs_anim.setStartValue(self.thumbs_panel.pos())
        self.thumbs_anim.setEndValue(QPoint(self.thumbs_panel.x(), end_y))

        if not checked:
            self.thumbs_anim.finished.connect(self._hide_thumbs_on_finish)
        else:
            try:
                self.thumbs_anim.finished.disconnect(self._hide_thumbs_on_finish)
            except Exception:
                pass

        self.thumbs_anim.start()

    def _hide_thumbs_on_finish(self):
        self.thumbs_panel.hide()

    def _on_scroll(self, value):
        max_val = self.scroll_area.verticalScrollBar().maximum()
        if max_val > 0 and value >= max_val - 10:
            if not self.btn_next_floating.isVisible() and self.current_page_idx < len(self.pages) - 1:
                self.btn_next_floating.show()
                self.update_layout_positions()
        else:
            if self.btn_next_floating.isVisible():
                self.btn_next_floating.hide()

    def update_layout_positions(self):
        btn_w = 180
        btn_h = 45
        x = (self.width() - btn_w) // 2
        y = self.height() - btn_h - 40
        self.btn_next_floating.setGeometry(x, y, btn_w, btn_h)

        panel_w = min(700, self.width() - 40)
        panel_x = (self.width() - panel_w) // 2
        panel_y = self.thumbs_panel.y()
        self.thumbs_panel.setGeometry(panel_x, panel_y, panel_w, 120)

        self._update_loading_overlay_geometry()

    def _update_loading_overlay_geometry(self):
        if hasattr(self, "loading_overlay"):
            self.loading_overlay.setGeometry(self.reader_container.rect())

    def next_page(self):
        if self.pages and self.current_page_idx < len(self.pages) - 1:
            self.current_page_idx += 1
            self.render_current_page()

    def prev_page(self):
        if self.pages and self.current_page_idx > 0:
            self.current_page_idx -= 1
            self.render_current_page()

    def _on_fit_mode_changed(self, index):
        modes = ["width", "fit", "original"]
        self.fit_mode = modes[index]
        self.zoom_factor = 1.0
        self.render_current_page()

    def _on_back_clicked(self):
        self.back_requested.emit()

    def wheelEvent(self, event: QWheelEvent):
        # Ctrl + Scroll = zoom
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_factor *= 1.1
            else:
                self.zoom_factor /= 1.1
            self.zoom_factor = max(0.1, min(self.zoom_factor, 10.0))
            self.render_current_page()
            event.accept()
            return
        super().wheelEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_layout_positions()
        self.render_current_page()


# =====================================================================
# PÁGINA DE CONFIGURAÇÕES
# =====================================================================

class SettingsPage(QWidget):
    folder_selected = pyqtSignal(str)
    rescan_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        title = QLabel("⚙️ Configurações")
        title.setStyleSheet("color: #ffffff; font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: rgba(10, 31, 41, 0.7);
                border: 1px solid #133a4a;
                border-radius: 12px;
                padding: 20px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(15)

        lbl_folder = QLabel("📁 Pasta de Quadrinhos")
        lbl_folder.setStyleSheet(
            "color: #f0fdf4; font-size: 16px; font-weight: bold;"
        )

        lbl_desc = QLabel(
            "Selecione a pasta onde estão seus arquivos .cbr/.cbz. "
            "O sistema irá escanear subpastas automaticamente."
        )
        lbl_desc.setStyleSheet("color: #8da3b0; font-size: 12px;")
        lbl_desc.setWordWrap(True)

        folder_row = QHBoxLayout()
        folder_row.setSpacing(10)

        self.folder_input = QLineEdit()
        self.folder_input.setObjectName("SearchBar")
        self.folder_input.setPlaceholderText("Nenhuma pasta selecionada...")
        self.folder_input.setReadOnly(True)

        btn_browse = QPushButton("📂 Escolher Pasta")
        btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse.setStyleSheet("""
            QPushButton {
                background-color: #00b87c;
                color: #030f16;
                border: none;
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #00e699;
            }
        """)
        btn_browse.clicked.connect(self.choose_folder)

        folder_row.addWidget(self.folder_input, 1)
        folder_row.addWidget(btn_browse)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        btn_save = QPushButton("💾 Salvar Configuração")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #005f73;
                color: #ffffff;
                border: 1px solid #00b87c;
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #00b87c;
                color: #030f16;
            }
        """)
        btn_save.clicked.connect(self.save_config)

        btn_rescan = QPushButton("🔄 Escanear Pasta Novamente")
        btn_rescan.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_rescan.setStyleSheet("""
            QPushButton {
                background-color: rgba(10, 31, 41, 0.9);
                color: #00e699;
                border: 1px solid #00b87c;
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #00b87c;
                color: #030f16;
            }
        """)
        btn_rescan.clicked.connect(self.rescan_folder)

        action_row.addWidget(btn_save)
        action_row.addWidget(btn_rescan)
        action_row.addStretch()

        card_layout.addWidget(lbl_folder)
        card_layout.addWidget(lbl_desc)
        card_layout.addLayout(folder_row)
        card_layout.addLayout(action_row)

        layout.addWidget(card)

        card2 = QFrame()
        card2.setStyleSheet("""
            QFrame {
                background-color: rgba(10, 31, 41, 0.7);
                border: 1px solid #133a4a;
                border-radius: 12px;
                padding: 20px;
            }
        """)
        card2_layout = QVBoxLayout(card2)
        card2_layout.setSpacing(15)

        lbl_unread = QLabel("🆕 Exibir quantidade de quadrinhos novos")
        lbl_unread.setStyleSheet(
            "color: #f0fdf4; font-size: 16px; font-weight: bold;"
        )

        lbl_unread_desc = QLabel(
            "Define quantos quadrinhos não lidos serão exibidos na seção "
            "'Quadrinhos não lidos'. Ao final da lista aparecerá um botão "
            "'Exibir todos'. Padrão: 50."
        )
        lbl_unread_desc.setStyleSheet("color: #8da3b0; font-size: 12px;")
        lbl_unread_desc.setWordWrap(True)

        unread_row = QHBoxLayout()
        unread_row.setSpacing(10)

        lbl_num = QLabel("Quantidade:")
        lbl_num.setStyleSheet("color: #e0f2fe; font-size: 13px;")

        self.spin_unread = QSpinBox()
        self.spin_unread.setRange(1, 9999)
        self.spin_unread.setValue(get_unread_limit())
        self.spin_unread.setFixedWidth(120)

        btn_save_unread = QPushButton("💾 Salvar")
        btn_save_unread.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save_unread.setStyleSheet("""
            QPushButton {
                background-color: #005f73;
                color: #ffffff;
                border: 1px solid #00b87c;
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #00b87c;
                color: #030f16;
            }
        """)
        btn_save_unread.clicked.connect(self.save_unread_config)

        unread_row.addWidget(lbl_num)
        unread_row.addWidget(self.spin_unread)
        unread_row.addWidget(btn_save_unread)
        unread_row.addStretch()

        card2_layout.addWidget(lbl_unread)
        card2_layout.addWidget(lbl_unread_desc)
        card2_layout.addLayout(unread_row)

        layout.addWidget(card2)

        # ---------- Card 3: Limite de resultados da busca ----------
        card3 = QFrame()
        card3.setStyleSheet("""
            QFrame {
                background-color: rgba(10, 31, 41, 0.7);
                border: 1px solid #133a4a;
                border-radius: 12px;
                padding: 20px;
            }
        """)
        card3_layout = QVBoxLayout(card3)
        card3_layout.setSpacing(15)

        lbl_search = QLabel("🔍 Limite de Resultados da Busca")
        lbl_search.setStyleSheet(
            "color: #f0fdf4; font-size: 16px; font-weight: bold;"
        )

        lbl_search_desc = QLabel(
            "Define quantos resultados serão exibidos no dropdown da barra "
            "de pesquisa. Padrão: 20."
        )
        lbl_search_desc.setStyleSheet("color: #8da3b0; font-size: 12px;")
        lbl_search_desc.setWordWrap(True)

        search_row = QHBoxLayout()
        search_row.setSpacing(10)

        lbl_search_num = QLabel("Quantidade:")
        lbl_search_num.setStyleSheet("color: #e0f2fe; font-size: 13px;")

        self.spin_search = QSpinBox()
        self.spin_search.setRange(1, 200)
        self.spin_search.setValue(get_search_limit())
        self.spin_search.setFixedWidth(120)

        btn_save_search = QPushButton("💾 Salvar")
        btn_save_search.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save_search.setStyleSheet("""
            QPushButton {
                background-color: #005f73;
                color: #ffffff;
                border: 1px solid #00b87c;
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #00b87c;
                color: #030f16;
            }
        """)
        btn_save_search.clicked.connect(self.save_search_config)

        search_row.addWidget(lbl_search_num)
        search_row.addWidget(self.spin_search)
        search_row.addWidget(btn_save_search)
        search_row.addStretch()

        card3_layout.addWidget(lbl_search)
        card3_layout.addWidget(lbl_search_desc)
        card3_layout.addLayout(search_row)

        layout.addWidget(card3)

        self.result_label = QLabel("")
        self.result_label.setStyleSheet("color: #00e699; font-size: 13px;")
        layout.addWidget(self.result_label)

        layout.addStretch()

        self.load_config()

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            folder = config.get("comic_folder", "")
            if folder and os.path.isdir(folder):
                self.folder_input.setText(folder)
            try:
                self.spin_unread.setValue(int(config.get("unread_limit", DEFAULT_UNREAD_LIMIT)))
            except Exception:
                pass
            try:
                self.spin_search.setValue(int(config.get("search_limit", DEFAULT_SEARCH_LIMIT)))
            except Exception:
                pass
        except Exception:
            pass

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Selecionar Pasta de Quadrinhos"
        )
        if folder:
            self.folder_input.setText(folder)

    def save_config(self):
        folder = self.folder_input.text().strip()
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(
                self, "Aviso", "Por favor, selecione uma pasta válida."
            )
            return

        try:
            config = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            config["comic_folder"] = folder
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self.result_label.setText(f"✅ Configuração salva! Pasta: {folder}")
            self.folder_selected.emit(folder)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar configuração: {e}")

    def save_unread_config(self):
        try:
            config = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            config["unread_limit"] = int(self.spin_unread.value())
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self.result_label.setText(
                f"✅ Quantidade de novos salva: {self.spin_unread.value()}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar: {e}")

    def save_search_config(self):
        try:
            config = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            config["search_limit"] = int(self.spin_search.value())
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self.result_label.setText(
                f"✅ Limite de busca salvo: {self.spin_search.value()}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar: {e}")

    def rescan_folder(self):
        folder = self.folder_input.text().strip()
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(
                self, "Aviso",
                "Nenhuma pasta válida configurada. Selecione uma pasta primeiro."
            )
            return

        self.result_label.setText(f"🔄 Reescanenando a pasta: {folder}")
        self.rescan_requested.emit()


# =====================================================================
# WIDGETS DA COLEÇÃO
# =====================================================================

class ComicThumbnail(QFrame):
    clicked = pyqtSignal(str)
    double_clicked = pyqtSignal(str)
    favorite_toggled = pyqtSignal(str, bool)

    def __init__(self, title, file_path, pixmap=None, page_count=0,
                 is_favorite=False, is_completed=False, is_new=False,
                 parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.title = title
        self.is_favorite = is_favorite
        self.is_completed = is_completed
        self.is_new = is_new
        self.page_count = page_count

        self.setFixedSize(140, 230)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(title)

        if self.is_completed:
            self.setStyleSheet("""
                QFrame {
                    background-color: rgba(255, 220, 100, 0.25);
                    border: 2px solid #ffca28;
                    border-radius: 10px;
                }
                QFrame:hover {
                    border: 2px solid #ffe082;
                    background-color: rgba(255, 230, 120, 0.35);
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: rgba(10, 31, 41, 0.65);
                    border: 1px solid #103342;
                    border-radius: 10px;
                }
                QFrame:hover {
                    border: 1px solid #00b87c;
                    background-color: rgba(13, 42, 54, 0.85);
                }
            """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(3)

        cover_container = QWidget()
        cover_container.setFixedSize(128, 170)
        cover_container.setStyleSheet("border: none; background: transparent;")
        cover_container.setToolTip(title)
        cover_container.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        cover_lbl = QLabel(cover_container)
        cover_lbl.setGeometry(0, 0, 128, 170)
        cover_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover_lbl.setStyleSheet("border: none; background: transparent;")
        cover_lbl.setToolTip(title)

        rounded = make_rounded_pixmap(pixmap, 128, 170) if pixmap else QPixmap()
        if rounded.isNull():
            rounded = create_placeholder_cover(title, "", "teal", 128, 170)
        cover_lbl.setPixmap(rounded)

        self._cover_lbl = cover_lbl

        if self.is_completed:
            star_lbl = QLabel("⭐", cover_container)
            star_lbl.setToolTip("Capítulo finalizado")
            star_lbl.setGeometry(4, 4, 26, 26)
            star_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            star_lbl.setStyleSheet("""
                QLabel {
                    background-color: rgba(3, 15, 22, 0.75);
                    border-radius: 13px;
                    font-size: 14px;
                    border: none;
                }
            """)

        if self.is_new:
            new_lbl = QLabel("Novo!", cover_container)
            new_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            new_lbl.setGeometry(0, 0, 50, 22)
            new_lbl.setStyleSheet("""
                QLabel {
                    background-color: #ff9f1c;
                    color: #000000;
                    font-weight: bold;
                    font-size: 11px;
                    border-top-left-radius: 6px;
                    border-bottom-right-radius: 6px;
                    border: none;
                }
            """)

        self.btn_fav = QPushButton(cover_container)
        self.btn_fav.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fav.setGeometry(128 - 30, 4, 26, 26)
        self.btn_fav.setText("❤️" if is_favorite else "🤍")
        self.btn_fav.setStyleSheet("""
            QPushButton {
                background-color: rgba(3, 15, 22, 0.55);
                border: none;
                border-radius: 13px;
                font-size: 14px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: rgba(0, 184, 124, 0.85);
            }
        """)
        self.btn_fav.clicked.connect(self._on_fav_clicked)

        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet(
            "color: #ffffff; font-size: 10px; font-weight: bold; "
            "border: none; background: transparent;"
        )
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setWordWrap(False)
        self.lbl_title.setFixedHeight(14)
        self.lbl_title.setText(self._elide(title, 18))
        self.lbl_title.setToolTip(title)

        self.lbl_pages = QLabel(
            f"{page_count} pág." if page_count > 0 else "—"
        )
        self.lbl_pages.setStyleSheet(
            "color: #8da3b0; font-size: 9px; "
            "border: none; background: transparent;"
        )
        self.lbl_pages.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_pages.setToolTip(title)

        layout.addWidget(cover_container)
        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_pages)

    @staticmethod
    def _elide(text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        return text[:max_chars - 1].rstrip() + "…"

    def set_cover_pixmap(self, pixmap):
        try:
            rounded = make_rounded_pixmap(pixmap, 128, 170)
            if not rounded.isNull() and hasattr(self, "_cover_lbl"):
                self._cover_lbl.setPixmap(rounded)
        except Exception as e:
            print(f"[AVISO] Falha ao setar capa: {e}")

    def _on_fav_clicked(self):
        self.is_favorite = not self.is_favorite
        self.btn_fav.setText("❤️" if self.is_favorite else "🤍")
        self.favorite_toggled.emit(self.file_path, self.is_favorite)

    def mousePressEvent(self, event):
        if self.btn_fav.geometry().contains(event.pos()):
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.file_path)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.btn_fav.geometry().contains(event.pos()):
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.file_path)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class FolderCard(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, folder_name, count, cover_pixmap=None, parent=None):
        super().__init__(parent)
        self.folder_name = folder_name
        self.setFixedSize(140, 230)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(folder_name)

        self.setStyleSheet("""
            QFrame {
                background-color: rgba(10, 31, 41, 0.65);
                border: 1px solid #103342;
                border-radius: 10px;
            }
            QFrame:hover {
                border: 1px solid #ff9f1c;
                background-color: rgba(13, 42, 54, 0.85);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(3)

        cover_container = QWidget()
        cover_container.setFixedSize(128, 170)
        cover_container.setStyleSheet("border: none; background: transparent;")
        cover_container.setToolTip(folder_name)

        cover_lbl = QLabel(cover_container)
        cover_lbl.setGeometry(0, 0, 128, 170)
        cover_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover_lbl.setStyleSheet("border: none; background: transparent;")
        cover_lbl.setToolTip(folder_name)

        rounded = make_rounded_pixmap(cover_pixmap, 128, 170) if cover_pixmap else QPixmap()
        if rounded.isNull():
            rounded = create_placeholder_cover(folder_name, "", "teal", 128, 170)
        else:
            rounded = overlay_folder_icon(rounded, size=30)
        cover_lbl.setPixmap(rounded)

        lbl_name = QLabel(folder_name)
        lbl_name.setStyleSheet(
            "color: #ff9f1c; font-size: 10px; font-weight: bold; "
            "border: none; background: transparent;"
        )
        lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_name.setWordWrap(False)
        lbl_name.setFixedHeight(14)
        elided = folder_name if len(folder_name) <= 18 else folder_name[:17] + "…"
        lbl_name.setText(elided)
        lbl_name.setToolTip(folder_name)

        lbl_count = QLabel(f"{count} arquivo(s)")
        lbl_count.setStyleSheet(
            "color: #8da3b0; font-size: 9px; "
            "border: none; background: transparent;"
        )
        lbl_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_count.setToolTip(folder_name)

        layout.addWidget(cover_container)
        layout.addWidget(lbl_name)
        layout.addWidget(lbl_count)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.folder_name)
        super().mousePressEvent(event)


class FavoriteFolderCard(QFrame):
    """Card que representa um QUADRINHO FAVORITO que está dentro de uma pasta.

    Exibe: capa do quadrinho + ícone 📁 no canto sup. esq. + coração no
    canto sup. dir. + legenda superior com o NOME DA PASTA + legenda
    inferior "NN/MM favoritos".

    Duplo clique → vai para a página Favoritos naquela pasta.
    """
    clicked = pyqtSignal(str, str)          # folder_name, file_path
    double_clicked = pyqtSignal(str, str)   # folder_name, file_path
    favorite_toggled = pyqtSignal(str, bool)  # file_path, is_favorite

    def __init__(self, folder_name, file_path, title, cover_pixmap=None,
                 fav_counter=1, fav_total=1, is_favorite=True, parent=None):
        super().__init__(parent)
        self.folder_name = folder_name
        self.file_path = file_path
        self.title = title
        self.is_favorite = is_favorite
        self.setFixedSize(140, 230)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Tooltip com nome completo do quadrinho + pasta
        self.setToolTip(f"{title}\n📁 {folder_name}")

        self.setStyleSheet("""
            QFrame {
                background-color: rgba(10, 31, 41, 0.65);
                border: 1px solid #104f3f;
                border-radius: 10px;
            }
            QFrame:hover {
                border: 1px solid #00b87c;
                background-color: rgba(13, 42, 54, 0.85);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(3)

        cover_container = QWidget()
        cover_container.setFixedSize(128, 170)
        cover_container.setStyleSheet("border: none; background: transparent;")
        cover_container.setToolTip(f"{title}\n📁 {folder_name}")

        cover_lbl = QLabel(cover_container)
        cover_lbl.setGeometry(0, 0, 128, 170)
        cover_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover_lbl.setStyleSheet("border: none; background: transparent;")
        cover_lbl.setToolTip(f"{title}\n📁 {folder_name}")

        # Capa do QUADRINHO FAVORITO
        if cover_pixmap is not None and not cover_pixmap.isNull():
            rounded = make_rounded_pixmap(cover_pixmap, 128, 170)
            cover_lbl.setPixmap(rounded)
        else:
            cover_lbl.setPixmap(create_placeholder_cover(
                title, "", "teal", 128, 170
            ))

        # Ícone de pasta no canto superior ESQUERDO
        badge = QLabel("📁", cover_container)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setGeometry(4, 4, 30, 30)
        badge.setToolTip(f"Pasta: {folder_name}")
        badge.setStyleSheet("""
            QLabel {
                background-color: rgba(3, 15, 22, 0.75);
                border-radius: 15px;
                font-size: 16px;
                border: none;
            }
        """)

        # Botão de favoritar no canto superior DIREITO
        self.btn_fav = QPushButton(cover_container)
        self.btn_fav.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fav.setGeometry(128 - 30, 4, 26, 26)
        self.btn_fav.setText("❤️" if is_favorite else "🤍")
        self.btn_fav.setStyleSheet("""
            QPushButton {
                background-color: rgba(3, 15, 22, 0.65);
                border: none;
                border-radius: 13px;
                font-size: 14px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: rgba(0, 184, 124, 0.85);
            }
        """)
        self.btn_fav.clicked.connect(self._on_fav_clicked)

        # ---------- Legenda SUPERIOR: NOME DA PASTA ----------
        lbl_folder = QLabel(folder_name)
        lbl_folder.setStyleSheet(
            "color: #ff9f1c; font-size: 10px; font-weight: bold; "
            "border: none; background: transparent;"
        )
        lbl_folder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_folder.setWordWrap(False)
        lbl_folder.setFixedHeight(14)
        elided_folder = folder_name if len(folder_name) <= 18 else folder_name[:17] + "…"
        lbl_folder.setText(elided_folder)
        lbl_folder.setToolTip(f"Pasta: {folder_name}")

        # Nome do quadrinho (com elisão) — mantido para referência visual
        self.lbl_name = QLabel(title)
        self.lbl_name.setStyleSheet(
            "color: #ffffff; font-size: 10px; font-weight: bold; "
            "border: none; background: transparent;"
        )
        self.lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_name.setWordWrap(False)
        self.lbl_name.setFixedHeight(14)
        elided = title if len(title) <= 18 else title[:17] + "…"
        self.lbl_name.setText(elided)
        self.lbl_name.setToolTip(title)

        # Legenda: "NN/MM favoritos" (contador/total da pasta)
        try:
            counter_str = f"{int(fav_counter):02d}"
        except Exception:
            counter_str = str(fav_counter)
        try:
            total_str = f"{int(fav_total):02d}"
        except Exception:
            total_str = str(fav_total)

        lbl_count = QLabel(f"{counter_str}/{total_str} favoritos")
        lbl_count.setStyleSheet(
            "color: #8da3b0; font-size: 9px; "
            "border: none; background: transparent;"
        )
        lbl_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_count.setToolTip(f"📁 {folder_name}: {counter_str}/{total_str} favoritos")

        layout.addWidget(cover_container)
        layout.addWidget(lbl_folder)   # <- NOME DA PASTA (superior)
        layout.addWidget(lbl_count)    # <- NN/MM favoritos (inferior)

    def _on_fav_clicked(self):
        self.is_favorite = not self.is_favorite
        self.btn_fav.setText("❤️" if self.is_favorite else "🤍")
        self.favorite_toggled.emit(self.file_path, self.is_favorite)

    def mousePressEvent(self, event):
        if self.btn_fav.geometry().contains(event.pos()):
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.folder_name, self.file_path)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.btn_fav.geometry().contains(event.pos()):
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.folder_name, self.file_path)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


# =====================================================================
# CARREGADOR DE CAPA SOB DEMANDA
# =====================================================================

class _CoverLoaderSignals(QObject):
    finished = pyqtSignal(str, str, int)


class _CoverLoaderWorker(QRunnable):
    def __init__(self, file_path, mtime, size):
        super().__init__()
        self.file_path = file_path
        self.mtime = mtime
        self.size = size
        self.signals = _CoverLoaderSignals()

    def run(self):
        try:
            pixmap, count = extract_cover_and_pagecount(self.file_path)
            cover_hash = ""
            if pixmap is not None and not pixmap.isNull():
                cover_hash = save_cover_to_disk(
                    self.file_path, self.mtime, self.size, pixmap
                )
                del pixmap
        except Exception:
            cover_hash = ""
            count = 0
        self.signals.finished.emit(self.file_path, cover_hash, count)


# =====================================================================
# WIDGET DE RESULTADO DA BUSCA (DROPDOWN)
# =====================================================================

class SearchResultItem(QFrame):
    """Item individual do dropdown de resultados da busca."""
    read_now_requested = pyqtSignal(str)

    def __init__(self, title, page_info, file_path, pixmap=None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setFixedHeight(60)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(title)

        self.setStyleSheet("""
            QFrame {
                background-color: rgba(13, 42, 54, 0.85);
                border: 1px solid #133a4a;
                border-radius: 8px;
            }
            QFrame:hover {
                border: 1px solid #00b87c;
                background-color: rgba(13, 42, 54, 0.95);
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 8, 4)
        layout.setSpacing(8)

        cover_lbl = QLabel()
        cover_lbl.setFixedSize(40, 52)
        cover_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover_lbl.setStyleSheet("border: none; background: transparent;")

        if pixmap is not None and not pixmap.isNull():
            rounded = make_rounded_pixmap(pixmap, 40, 52, radius=4)
            cover_lbl.setPixmap(rounded)
        else:
            placeholder = create_placeholder_cover(title, "", "teal", 40, 52)
            cover_lbl.setPixmap(placeholder)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(
            "color: #ffffff; font-size: 12px; font-weight: bold; "
            "border: none; background: transparent;"
        )
        lbl_title.setToolTip(title)

        lbl_page = QLabel(page_info)
        lbl_page.setStyleSheet(
            "color: #8da3b0; font-size: 10px; "
            "border: none; background: transparent;"
        )
        lbl_page.setToolTip(title)

        info_layout.addWidget(lbl_title)
        info_layout.addWidget(lbl_page)
        info_layout.addStretch()

        btn_read = QPushButton("Ler Agora")
        btn_read.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_read.setFixedHeight(26)
        btn_read.setStyleSheet("""
            QPushButton {
                background-color: #00b87c;
                color: #030f16;
                border: none;
                border-radius: 6px;
                padding: 4px 10px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #00e699;
            }
        """)
        btn_read.clicked.connect(lambda: self.read_now_requested.emit(self.file_path))

        layout.addWidget(cover_lbl)
        layout.addLayout(info_layout, 1)
        layout.addWidget(btn_read)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.read_now_requested.emit(self.file_path)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class SearchDropdown(QFrame):
    """Dropdown com resultados da busca, posicionado abaixo do input."""
    read_now_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SearchDropdown")
        self.setStyleSheet("""
            QFrame#SearchDropdown {
                background-color: rgba(3, 15, 22, 0.98);
                border: 1px solid #00b87c;
                border-radius: 8px;
            }
        """)
        self.setWindowFlags(Qt.WindowType.Widget)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(5)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.items_layout = QVBoxLayout(self.scroll_content)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(5)
        self.items_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)

        self.hide()

    def clear_items(self):
        while self.items_layout.count():
            item = self.items_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def add_item(self, title, page_info, file_path, pixmap=None):
        item = SearchResultItem(title, page_info, file_path, pixmap)
        item.read_now_requested.connect(self.read_now_requested.emit)
        self.items_layout.addWidget(item)
        return item

    def has_items(self):
        return self.items_layout.count() > 0

    def count_items(self):
        return self.items_layout.count()


# =====================================================================
# COLEÇÃO (responsiva)
# =====================================================================

class CollectionWidget(QWidget):
    favorite_changed = pyqtSignal()
    comic_double_clicked = pyqtSignal(str)
    scan_completed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self.current_folder = None
        self.scan_result = None
        self.scanner_thread = None

        self._current_path = []

        self.favorites = load_favorites()

        self._pending_cover_loads = set()
        self._cover_pool = QThreadPool()
        self._cover_pool.setMaxThreadCount(3)

        self._last_render_width = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.breadcrumb_widget = QWidget()
        self.breadcrumb_widget.setStyleSheet("background: transparent;")
        self.breadcrumb = QHBoxLayout(self.breadcrumb_widget)
        self.breadcrumb.setContentsMargins(0, 0, 0, 0)
        self.breadcrumb.setSpacing(8)
        layout.addWidget(self.breadcrumb_widget)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #081a24;
                border: 1px solid #133a4a;
                border-radius: 4px;
                height: 8px;
                color: transparent;
            }
            QProgressBar::chunk {
                background-color: #00b87c;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.progress_bar)

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setContentsMargins(0, 0, 10, 0)
        self.grid_layout.setSpacing(CARD_SPACING)
        self.grid_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )

        layout.addWidget(self.scroll_content, 1)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #8da3b0; font-size: 13px;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

    def _calc_max_cols(self, for_comic=True) -> int:
        try:
            vw = self.width()
        except Exception:
            vw = 800

        if vw <= 0:
            vw = 800

        available = max(0, vw - 18)

        n = int((available + CARD_SPACING) // (CARD_WIDTH + CARD_SPACING))
        return max(1, n)

    def resizeEvent(self, event):
        super().resizeEvent(event)

        try:
            vw = self.width()
        except Exception:
            return

        if vw <= 0:
            return

        if abs(vw - self._last_render_width) < 20:
            return

        self._last_render_width = vw

        if self.scan_result is not None:
            QTimer.singleShot(120, self._delayed_rerender)

    def _delayed_rerender(self):
        try:
            vw = self.width()
        except Exception:
            return
        if abs(vw - self._last_render_width) >= 20:
            QTimer.singleShot(120, self._delayed_rerender)
            return
        if self.scan_result is not None:
            self.show_current_view()

    def _stop_current_scanner(self):
        if self.scanner_thread is None:
            return
        try:
            self.scanner_thread.cancel()
            try:
                self.scanner_thread.progress.disconnect()
            except (TypeError, RuntimeError):
                pass
            try:
                self.scanner_thread.finished.disconnect()
            except (TypeError, RuntimeError):
                pass
            if self.scanner_thread.isRunning():
                self.scanner_thread.quit()
                if not self.scanner_thread.wait(8000):
                    self.scanner_thread.terminate()
                    self.scanner_thread.wait(2000)
        except Exception as e:
            print(f"[AVISO] Erro ao parar scanner anterior: {e}")
        finally:
            self.scanner_thread = None

    def load_folder(self, folder_path, force_rescan=False):
        self._stop_current_scanner()

        self.current_folder = folder_path
        self.scan_result = None
        self._current_path = []
        self.clear_grid()
        self.clear_breadcrumb()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)

        if not folder_path or not os.path.isdir(folder_path):
            self.status_label.setText(
                "⚠️ Nenhuma pasta configurada. "
                "Vá em Configurações e selecione uma pasta."
            )
            return

        self.status_label.setText(f"🔍 Verificando pasta: {folder_path}")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.scanner_thread = ComicScannerThread(folder_path, force_rescan=force_rescan)
        self.scanner_thread.progress.connect(self.on_scan_progress)
        self.scanner_thread.finished.connect(self.on_scan_finished)
        self.scanner_thread.start()

    def on_scan_progress(self, current, total, filename):
        if total > 0:
            pct = int((current / total) * 100)
            self.progress_bar.setValue(pct)
        else:
            self.progress_bar.setValue(0)
        self.status_label.setText(
            f"🔍 Escaneando ({current}/{total}): {filename}"
        )

    def on_scan_finished(self, result):
        self.scan_result = result
        self.progress_bar.setVisible(False)
        self.show_root_view()
        self.scan_completed.emit()

    def clear_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def clear_breadcrumb(self):
        while self.breadcrumb.count():
            item = self.breadcrumb.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def _get_node_at_path(self, path):
        if self.scan_result is None:
            return None
        node = self.scan_result
        for part in path:
            folders = node.get("folders", {})
            if part not in folders:
                return None
            node = folders[part]
        return node

    def _load_cover_pixmap_for(self, file_path) -> QPixmap:
        if self.scan_result is None:
            return QPixmap()
        h = self.scan_result.get("covers", {}).get(file_path, "")
        if not h:
            return QPixmap()
        return load_cover_from_disk(h)

    def _add_comic_cards(self, files, start_row=0, start_col=0, max_cols=None):
        if max_cols is None:
            max_cols = self._calc_max_cols()

        history = load_history()
        row, col = start_row, start_col
        for file_path in files:
            title = os.path.splitext(os.path.basename(file_path))[0]
            pixmap = self._load_cover_pixmap_for(file_path)
            page_count = self.scan_result["page_counts"].get(file_path, 0)
            is_fav = file_path in self.favorites

            h_data = history.get(file_path, {})
            p_curr = h_data.get("page", 0)
            p_tot = h_data.get("total", 0)
            is_completed = (p_tot > 0 and p_curr >= p_tot)

            card = ComicThumbnail(
                title, file_path, pixmap,
                page_count=page_count, is_favorite=is_fav, is_completed=is_completed
            )
            card.clicked.connect(self.on_comic_clicked)
            card.double_clicked.connect(self.on_comic_double_clicked)
            card.favorite_toggled.connect(self.on_favorite_toggled)
            self.grid_layout.addWidget(card, row, col)

            if not pixmap or pixmap.isNull():
                self._schedule_cover_load(file_path, card)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        return row, col

    def _schedule_cover_load(self, file_path, card):
        if file_path in self._pending_cover_loads:
            return
        try:
            st = os.stat(file_path)
            mtime = st.st_mtime
            size = st.st_size
        except Exception:
            mtime = 0
            size = 0
        self._pending_cover_loads.add(file_path)
        worker = _CoverLoaderWorker(file_path, mtime, size)
        worker.signals.finished.connect(
            lambda fp, h, cnt: self._on_cover_loaded(fp, h, cnt, card)
        )
        self._cover_pool.start(worker)

    def _on_cover_loaded(self, file_path, cover_hash, page_count, card):
        self._pending_cover_loads.discard(file_path)
        try:
            _ = card.isVisible()
        except RuntimeError:
            return
        if self.scan_result is not None:
            self.scan_result["covers"][file_path] = cover_hash
            self.scan_result["page_counts"][file_path] = page_count
            try:
                st = os.stat(file_path)
                mtime = st.st_mtime
                size = st.st_size
            except Exception:
                mtime, size = 0, 0
            db_save_folder_cache(self.current_folder or "", {
                file_path: {
                    "mtime": mtime,
                    "size": size,
                    "page_count": page_count,
                    "cover_hash": cover_hash,
                }
            })
        if cover_hash:
            pm = load_cover_from_disk(cover_hash)
            try:
                if not pm.isNull():
                    card.set_cover_pixmap(pm)
            except (RuntimeError, AttributeError):
                pass

    def show_root_view(self):
        self._current_path = []
        self.show_current_view()

    def show_current_view(self):
        self.clear_grid()
        self.clear_breadcrumb()

        if self.scan_result is None:
            self.status_label.setText("⚠️ Nenhum dado escaneado ainda.")
            return

        self._build_breadcrumb()

        node = self._get_node_at_path(self._current_path)
        if node is None:
            self._current_path = []
            node = self.scan_result

        max_cols = self._calc_max_cols()
        row, col = 0, 0

        for folder_name, sub_node in sorted(
            node.get("folders", {}).items(),
            key=lambda kv: natural_sort_key(kv[0])
        ):
            total_files = _count_all_comics(sub_node)
            cover = _find_first_cover(sub_node, self.scan_result["covers"])
            if cover is None:
                for f in _collect_all_files(sub_node):
                    pm = self._load_cover_pixmap_for(f)
                    if pm is not None and not pm.isNull():
                        cover = pm
                        break

            card = FolderCard(folder_name, total_files, cover)
            card.clicked.connect(
                lambda checked, fn=folder_name: self.enter_folder(fn)
            )
            self.grid_layout.addWidget(card, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        self._add_comic_cards(
            node.get("loose_files", []),
            start_row=row, start_col=col, max_cols=max_cols
        )

        total_items = (
            len(node.get("loose_files", []))
            + len(node.get("folders", {}))
        )
        if self._current_path:
            caminho_str = " › ".join(self._current_path)
            self.status_label.setText(
                f"📚 {total_items} item(ns) em: {caminho_str}"
            )
        else:
            total_comics = _count_all_comics(self.scan_result)
            self.status_label.setText(
                f"📚 {total_items} item(ns) na raiz — "
                f"{total_comics} quadrinho(s) no total"
            )

    def _build_breadcrumb(self):
        if not self._current_path:
            lbl_home = QLabel("🏠 Início")
            lbl_home.setStyleSheet(
                "color: #00e699; font-size: 14px; font-weight: bold;"
            )
            self.breadcrumb.addWidget(lbl_home)
        else:
            btn_home = QPushButton("🏠 Início")
            btn_home.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_home.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #00e699;
                    border: none;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 2px 8px;
                }
                QPushButton:hover {
                    color: #00ffaa;
                }
            """)
            btn_home.clicked.connect(self.show_root_view)
            self.breadcrumb.addWidget(btn_home)

        for i, part in enumerate(self._current_path):
            sep = QLabel("›")
            sep.setStyleSheet("color: #8da3b0; font-size: 14px;")
            self.breadcrumb.addWidget(sep)

            is_last = (i == len(self._current_path) - 1)
            if is_last:
                lbl_part = QLabel(f"📁 {part}")
                lbl_part.setStyleSheet(
                    "color: #ff9f1c; font-size: 14px; font-weight: bold;"
                )
                lbl_part.setToolTip(part)
                self.breadcrumb.addWidget(lbl_part)
            else:
                btn_part = QPushButton(f"📁 {part}")
                btn_part.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_part.setToolTip(part)
                btn_part.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: #8da3b0;
                        border: none;
                        font-size: 14px;
                        padding: 2px 4px;
                    }
                    QPushButton:hover {
                        color: #00e699;
                    }
                """)
                target_path = self._current_path[:i + 1]
                btn_part.clicked.connect(
                    lambda checked, p=target_path: self.go_to_path(p)
                )
                self.breadcrumb.addWidget(btn_part)

        if self.current_folder and not self._current_path:
            lbl_path = QLabel(f"  ›  {self.current_folder}")
            lbl_path.setStyleSheet("color: #8da3b0; font-size: 12px;")
            self.breadcrumb.addWidget(lbl_path)

        self.breadcrumb.addStretch()

    def enter_folder(self, folder_name):
        self._current_path.append(folder_name)
        self.show_current_view()

    def go_to_path(self, path):
        self._current_path = list(path)
        self.show_current_view()

    def show_folder(self, folder_name):
        if self.scan_result and folder_name in self.scan_result.get("folders", {}):
            self._current_path = [folder_name]
            self.show_current_view()
        else:
            self.show_root_view()

    def on_comic_clicked(self, file_path):
        pass

    def on_comic_double_clicked(self, file_path):
        self.comic_double_clicked.emit(file_path)

    def on_favorite_toggled(self, file_path, is_favorite):
        if is_favorite:
            self.favorites.add(file_path)
        else:
            self.favorites.discard(file_path)
        save_favorites(self.favorites)
        self.favorite_changed.emit()


# =====================================================================
# PÁGINA DE FAVORITOS
# =====================================================================

class FavoritesPage(QWidget):
    comic_double_clicked = pyqtSignal(str)

    def __init__(self, favorites_provider, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self.favorites_provider = favorites_provider
        self._current_folder_name = None
        self.on_favorite_removed = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        title = QLabel("💚 Favoritos")
        title.setStyleSheet(
            "color: #ffffff; font-size: 22px; font-weight: bold;"
        )
        layout.addWidget(title)

        self.breadcrumb_widget = QWidget()
        self.breadcrumb_widget.setStyleSheet("background: transparent;")
        self.breadcrumb = QHBoxLayout(self.breadcrumb_widget)
        self.breadcrumb.setContentsMargins(0, 0, 0, 0)
        self.breadcrumb.setSpacing(8)
        layout.addWidget(self.breadcrumb_widget)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent;")

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setContentsMargins(0, 0, 10, 0)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )

        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area, 1)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #8da3b0; font-size: 13px;")
        layout.addWidget(self.status_label)

    def clear_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def clear_breadcrumb(self):
        while self.breadcrumb.count():
            item = self.breadcrumb.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def _classify_favorites(self, favorites, folders_map):
        loose = []
        by_folder = {}
        assigned = set()

        def visit(node, folder_name):
            for f in node.get("loose_files", []):
                if f in favorites:
                    by_folder.setdefault(folder_name, []).append(f)
                    assigned.add(f)
            for sub_name, sub_node in node.get("folders", {}).items():
                visit(sub_node, sub_name)

        for folder_name, sub_node in folders_map.items():
            visit(sub_node, folder_name)

        for path in favorites:
            if path not in assigned:
                loose.append(path)

        loose.sort()
        for k in by_folder:
            by_folder[k].sort()
        return loose, by_folder

    def _load_cover_for(self, file_path, covers) -> QPixmap:
        h = covers.get(file_path, "")
        if not h:
            return QPixmap()
        return load_cover_from_disk(h)

    def _show_root_view(self, favorites, covers, page_counts, folders_map):
        """Visão raiz da página Favoritos: mostra uma pasta por pasta com a
        capa do 1º quadrinho favoritado dentro dela e legenda NN/MM."""
        self.clear_grid()
        self.clear_breadcrumb()

        history = load_history()

        lbl_home = QLabel("🏠 Início")
        lbl_home.setStyleSheet(
            "color: #00e699; font-size: 14px; font-weight: bold;"
        )
        self.breadcrumb.addWidget(lbl_home)
        self.breadcrumb.addStretch()

        loose, by_folder = self._classify_favorites(favorites, folders_map)

        total_folder_groups = max(1, len(by_folder))
        folder_idx = 0

        row, col = 0, 0
        max_cols = 6

        for folder_name, files in sorted(by_folder.items()):
            folder_idx += 1
            cover = None
            first_fav_path = files[0] if files else ""
            for f in files:
                pm = self._load_cover_for(f, covers)
                if pm is not None and not pm.isNull():
                    cover = pm
                    break

            card = FavoriteFolderCard(
                folder_name,
                first_fav_path,
                title=os.path.splitext(os.path.basename(first_fav_path))[0] if first_fav_path else folder_name,
                cover_pixmap=cover,
                fav_counter=folder_idx,
                fav_total=total_folder_groups,
                is_favorite=True,
            )
            card.clicked.connect(
                lambda _fn, _fp, fn=folder_name: self.show_folder_view(
                    fn, favorites, covers, page_counts, folders_map
                )
            )
            card.double_clicked.connect(
                lambda _fn, _fp, fn=folder_name: self.show_folder_view(
                    fn, favorites, covers, page_counts, folders_map
                )
            )
            card.favorite_toggled.connect(self._on_fav_toggled)
            self.grid_layout.addWidget(card, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        for file_path in loose:
            title = os.path.splitext(os.path.basename(file_path))[0]
            pixmap = self._load_cover_for(file_path, covers)
            page_count = page_counts.get(file_path, 0)

            h_data = history.get(file_path, {})
            p_curr = h_data.get("page", 0)
            p_tot = h_data.get("total", 0)
            is_completed = (p_tot > 0 and p_curr >= p_tot)

            card = ComicThumbnail(
                title, file_path, pixmap,
                page_count=page_count, is_favorite=True, is_completed=is_completed
            )
            card.double_clicked.connect(lambda fp=file_path: self.comic_double_clicked.emit(fp))
            card.favorite_toggled.connect(self._on_fav_toggled)
            self.grid_layout.addWidget(card, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        total_loose = len(loose)
        total_folders = len(by_folder)
        total_favs = len(favorites)
        self.status_label.setText(
            f"💚 {total_favs} favorito(s) — "
            f"{total_folders} pasta(s), {total_loose} arquivo(s) solto(s)"
        )

    def show_folder_view(self, folder_name, favorites=None, covers=None,
                          page_counts=None, folders_map=None):
        if favorites is None or covers is None or page_counts is None or folders_map is None:
            favorites, covers, page_counts, folders_map = self.favorites_provider()

        self._current_folder_name = folder_name

        self.clear_grid()
        self.clear_breadcrumb()

        history = load_history()

        btn_back = QPushButton("← Voltar")
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #00e699;
                border: none;
                font-size: 14px;
                font-weight: bold;
                padding: 2px 8px;
            }
            QPushButton:hover {
                color: #00ffaa;
            }
        """)
        btn_back.clicked.connect(lambda: self.refresh())

        lbl_sep = QLabel("›")
        lbl_sep.setStyleSheet("color: #8da3b0; font-size: 14px;")

        lbl_folder = QLabel(f"📁 {folder_name}")
        lbl_folder.setStyleSheet(
            "color: #ff9f1c; font-size: 14px; font-weight: bold;"
        )
        lbl_folder.setToolTip(folder_name)

        self.breadcrumb.addWidget(btn_back)
        self.breadcrumb.addWidget(lbl_sep)
        self.breadcrumb.addWidget(lbl_folder)
        self.breadcrumb.addStretch()

        _, by_folder = self._classify_favorites(favorites, folders_map)
        files = by_folder.get(folder_name, [])

        row, col = 0, 0
        max_cols = 6

        for file_path in files:
            title = os.path.splitext(os.path.basename(file_path))[0]
            pixmap = self._load_cover_for(file_path, covers)
            page_count = page_counts.get(file_path, 0)

            h_data = history.get(file_path, {})
            p_curr = h_data.get("page", 0)
            p_tot = h_data.get("total", 0)
            is_completed = (p_tot > 0 and p_curr >= p_tot)

            card = ComicThumbnail(
                title, file_path, pixmap,
                page_count=page_count, is_favorite=True, is_completed=is_completed
            )
            card.double_clicked.connect(lambda fp=file_path: self.comic_double_clicked.emit(fp))
            card.favorite_toggled.connect(self._on_fav_toggled)
            self.grid_layout.addWidget(card, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        self.status_label.setText(
            f"💚 {len(files)} favorito(s) em: {folder_name}"
        )

    def refresh(self):
        self.clear_grid()
        self.clear_breadcrumb()
        self._current_folder_name = None

        favorites, covers, page_counts, folders_map = self.favorites_provider()

        if not favorites:
            self.status_label.setText(
                "Nenhum quadrinho favoritado ainda. "
                "Clique no 🤍 em qualquer quadrinho da sua coleção."
            )
            return

        self._show_root_view(favorites, covers, page_counts, folders_map)

    def _on_fav_toggled(self, file_path, is_favorite):
        if callable(self.on_favorite_removed):
            self.on_favorite_removed(file_path, is_favorite)
        self.refresh()


# =====================================================================
# CARDS DA HOME
# =====================================================================

class RecentComicCard(QFrame):
    double_clicked = pyqtSignal(str)

    def __init__(self, title, page_info, progress, file_path, pixmap=None,
                 theme="teal", is_completed=False, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.is_completed = is_completed

        self.setFixedSize(260, 100)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(title)

        if self.is_completed:
            self.setStyleSheet("""
                QFrame {
                    background-color: rgba(255, 220, 100, 0.25);
                    border: 2px solid #ffca28;
                    border-radius: 10px;
                }
                QFrame:hover {
                    border: 2px solid #ffe082;
                    background-color: rgba(255, 230, 120, 0.35);
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: rgba(10, 31, 41, 0.65);
                    border: 1px solid #103342;
                    border-radius: 10px;
                }
                QFrame:hover {
                    border: 1px solid #00b87c;
                    background-color: rgba(13, 42, 54, 0.85);
                }
            """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 12, 8)
        layout.setSpacing(10)

        cover_container = QWidget()
        cover_container.setFixedSize(60, 84)
        cover_container.setStyleSheet("border: none; background: transparent;")
        cover_container.setToolTip(title)

        cover_lbl = QLabel(cover_container)
        cover_lbl.setGeometry(0, 0, 60, 84)
        cover_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover_lbl.setStyleSheet("border: none; background: transparent;")
        cover_lbl.setToolTip(title)

        rounded = make_rounded_pixmap(pixmap, 60, 84) if pixmap else QPixmap()
        if rounded.isNull():
            rounded = create_placeholder_cover(title, "", theme, 60, 84)
        cover_lbl.setPixmap(rounded)

        if self.is_completed:
            star_lbl = QLabel("⭐", cover_container)
            star_lbl.setToolTip("Capítulo finalizado")
            star_lbl.setGeometry(2, 2, 22, 22)
            star_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            star_lbl.setStyleSheet("""
                QLabel {
                    background-color: rgba(3, 15, 22, 0.75);
                    border-radius: 11px;
                    font-size: 12px;
                    border: none;
                }
            """)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(
            "color: #ffffff; font-weight: bold; font-size: 12px; "
            "border: none; background: transparent;"
        )
        lbl_title.setToolTip(title)

        lbl_page = QLabel(f"Última página: {page_info}")
        lbl_page.setStyleSheet(
            "color: #8da3b0; font-size: 11px; "
            "border: none; background: transparent;"
        )
        lbl_page.setToolTip(title)

        pbar = QProgressBar()
        pbar.setRange(0, 100)
        pbar.setValue(progress)

        btn_continue = QPushButton("Continuar Lendo")
        btn_continue.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_continue.setStyleSheet("""
            QPushButton {
                background-color: #00b87c;
                color: #030f16;
                border: none;
                border-radius: 10px;
                padding: 5px 12px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #00e699;
            }
        """)
        btn_continue.clicked.connect(lambda: self.double_clicked.emit(self.file_path))

        info_layout.addWidget(lbl_title)
        info_layout.addWidget(lbl_page)
        info_layout.addWidget(pbar)
        info_layout.addStretch()
        info_layout.addWidget(btn_continue)

        layout.addWidget(cover_container)
        layout.addLayout(info_layout)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.file_path)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class UnreadComicCard(QFrame):
    double_clicked = pyqtSignal(str)

    def __init__(self, title, subtitle, file_path, pixmap=None,
                 theme="purple", parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setFixedSize(125, 185)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        full_name = f"{title} {subtitle}".strip()
        self.setToolTip(full_name)

        self.setStyleSheet("""
            QFrame {
                background-color: rgba(10, 31, 41, 0.65);
                border: 1px solid #103342;
                border-radius: 10px;
            }
            QFrame:hover {
                border: 1px solid #00b87c;
                background-color: rgba(13, 42, 54, 0.85);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        cover_container = QWidget()
        cover_container.setFixedSize(113, 145)
        cover_container.setStyleSheet("border: none; background: transparent;")
        cover_container.setToolTip(full_name)

        cover_lbl = QLabel(cover_container)
        cover_lbl.setGeometry(0, 0, 113, 145)
        cover_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover_lbl.setStyleSheet("border: none; background: transparent;")
        cover_lbl.setToolTip(full_name)

        rounded = make_rounded_pixmap(pixmap, 113, 145) if pixmap else QPixmap()
        if rounded.isNull():
            rounded = create_placeholder_cover(title, subtitle, theme, 113, 145)
        cover_lbl.setPixmap(rounded)

        badge = QLabel("Novo!", cover_container)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setGeometry(0, 0, 50, 22)
        badge.setStyleSheet("""
            QLabel {
                background-color: #ff9f1c;
                color: #000000;
                font-weight: bold;
                font-size: 11px;
                border-top-left-radius: 6px;
                border-bottom-right-radius: 6px;
                border: none;
            }
        """)

        lbl_title = QLabel(f"{title} {subtitle}")
        lbl_title.setStyleSheet(
            "color: #ffffff; font-size: 11px; font-weight: bold; "
            "border: none; background: transparent;"
        )
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setToolTip(full_name)

        layout.addWidget(cover_container)
        layout.addWidget(lbl_title)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.file_path)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class FavoriteComicCard(QFrame):
    double_clicked = pyqtSignal(str)

    def __init__(self, title, page_info, file_path, pixmap=None, theme="red", parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setFixedSize(140, 230)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(title)

        self.setStyleSheet("""
            QFrame {
                background-color: rgba(10, 31, 41, 0.65);
                border: 1px solid #104f3f;
                border-radius: 10px;
            }
            QFrame:hover {
                border: 1px solid #00b87c;
                background-color: rgba(13, 42, 54, 0.85);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(3)

        cover_container = QWidget()
        cover_container.setFixedSize(128, 170)
        cover_container.setStyleSheet("border: none; background: transparent;")
        cover_container.setToolTip(title)

        cover_lbl = QLabel(cover_container)
        cover_lbl.setGeometry(0, 0, 128, 170)
        cover_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover_lbl.setStyleSheet("border: none; background: transparent;")
        cover_lbl.setToolTip(title)

        rounded = make_rounded_pixmap(pixmap, 128, 170) if pixmap else QPixmap()
        if rounded.isNull():
            rounded = create_placeholder_cover(title, "", theme, 128, 170)
        cover_lbl.setPixmap(rounded)

        heart = QLabel("❤️", cover_container)
        heart.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heart.setGeometry(128 - 30, 4, 26, 26)
        heart.setStyleSheet("""
            QLabel {
                background-color: rgba(3, 15, 22, 0.65);
                border-radius: 13px;
                font-size: 14px;
                border: none;
            }
        """)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(
            "color: #ffffff; font-size: 10px; font-weight: bold; "
            "border: none; background: transparent;"
        )
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setWordWrap(False)
        lbl_title.setFixedHeight(14)
        elided = title if len(title) <= 18 else title[:17] + "…"
        lbl_title.setText(elided)
        lbl_title.setToolTip(title)

        lbl_page = QLabel(f"Última página: {page_info}")
        lbl_page.setStyleSheet(
            "color: #8da3b0; font-size: 9px; "
            "border: none; background: transparent;"
        )
        lbl_page.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_page.setToolTip(title)

        btn_read = QPushButton("Ler Agora")
        btn_read.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_read.setStyleSheet("""
            QPushButton {
                background-color: #e7582b;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #ff6b3d;
            }
        """)
        btn_read.clicked.connect(lambda: self.double_clicked.emit(self.file_path))

        layout.addWidget(cover_container)
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_page)
        layout.addWidget(btn_read)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.file_path)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


# =====================================================================
# CARD DE ITEM DO HISTÓRICO (LISTA)
# =====================================================================

class HistoryListItemCard(QFrame):
    read_requested = pyqtSignal(str)

    def __init__(self, title, date_str, page_curr, page_tot, file_path, pixmap=None, parent=None):
        super().__init__(parent)
        self.file_path = file_path

        self.setFixedHeight(120)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(title)

        self.setStyleSheet("""
            QFrame {
                background-color: rgba(10, 31, 41, 0.65);
                border: 1px solid #103342;
                border-radius: 10px;
            }
            QFrame:hover {
                border: 1px solid #00b87c;
                background-color: rgba(13, 42, 54, 0.85);
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 16, 10)
        layout.setSpacing(16)

        cover_container = QWidget()
        cover_container.setFixedSize(70, 100)
        cover_container.setStyleSheet("border: none; background: transparent;")
        cover_container.setToolTip(title)

        cover_lbl = QLabel(cover_container)
        cover_lbl.setGeometry(0, 0, 70, 100)
        cover_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover_lbl.setStyleSheet("border: none; background: transparent;")
        cover_lbl.setToolTip(title)

        rounded = make_rounded_pixmap(pixmap, 70, 100) if pixmap else QPixmap()
        if rounded.isNull():
            rounded = create_placeholder_cover(title, "", "teal", 70, 100)
        cover_lbl.setPixmap(rounded)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(
            "color: #ffffff; font-weight: bold; font-size: 14px; "
            "border: none; background: transparent;"
        )
        lbl_title.setToolTip(title)

        lbl_date = QLabel(f"📅 {date_str}")
        lbl_date.setStyleSheet(
            "color: #8da3b0; font-size: 11px; "
            "border: none; background: transparent;"
        )

        pct = int((page_curr / page_tot) * 100) if page_tot > 0 else 0

        pbar = QProgressBar()
        pbar.setRange(0, 100)
        pbar.setValue(pct)

        lbl_progress = QLabel(f"Última página lida: {page_curr} / {page_tot} ({pct}%)")
        lbl_progress.setStyleSheet(
            "color: #8da3b0; font-size: 11px; "
            "border: none; background: transparent;"
        )

        lbl_path = QLabel(f"📁 {file_path}")
        lbl_path.setStyleSheet(
            "color: #8da3b0; font-size: 10px; "
            "border: none; background: transparent;"
        )
        lbl_path.setToolTip(file_path)

        info_layout.addWidget(lbl_title)
        info_layout.addWidget(lbl_date)
        info_layout.addWidget(pbar)
        info_layout.addWidget(lbl_progress)
        info_layout.addWidget(lbl_path)

        btn_read = QPushButton("Ler Agora")
        btn_read.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_read.setStyleSheet("""
            QPushButton {
                background-color: #00b87c;
                color: #030f16;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #00e699;
            }
        """)
        btn_read.clicked.connect(lambda: self.read_requested.emit(self.file_path))

        layout.addWidget(cover_container)
        layout.addLayout(info_layout, 1)
        layout.addWidget(btn_read, 0, Qt.AlignmentFlag.AlignVCenter)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.read_requested.emit(self.file_path)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


# =====================================================================
# PÁGINA: BIBLIOTECA (antiga "Novos Quadrinhos")
# =====================================================================

class LibraryPage(QWidget):
    """Página Biblioteca: exibe TODOS os quadrinhos organizados por pastas,
    com tag 'Novo!' apenas nos que ainda não foram lidos.
    Responsiva à largura do sistema.
    """
    comic_double_clicked = pyqtSignal(str)

    def __init__(self, provider, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self.provider = provider

        self._current_path = []
        self._scan_structure = None
        self._last_render_width = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        self.title = QLabel("📚 Biblioteca")
        self.title.setStyleSheet(
            "color: #ffffff; font-size: 22px; font-weight: bold;"
        )
        layout.addWidget(self.title)

        self.breadcrumb_widget = QWidget()
        self.breadcrumb_widget.setStyleSheet("background: transparent;")
        self.breadcrumb = QHBoxLayout(self.breadcrumb_widget)
        self.breadcrumb.setContentsMargins(0, 0, 0, 0)
        self.breadcrumb.setSpacing(8)
        layout.addWidget(self.breadcrumb_widget)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent;")

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setContentsMargins(0, 0, 10, 0)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )

        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area, 1)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #8da3b0; font-size: 13px;")
        layout.addWidget(self.status_label)

    def set_scan_structure(self, scan_result):
        self._scan_structure = scan_result

    def clear_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def clear_breadcrumb(self):
        while self.breadcrumb.count():
            item = self.breadcrumb.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def _build_breadcrumb(self):
        if not self._current_path:
            lbl_home = QLabel("🏠 Início")
            lbl_home.setStyleSheet(
                "color: #00e699; font-size: 14px; font-weight: bold;"
            )
            self.breadcrumb.addWidget(lbl_home)
        else:
            btn_home = QPushButton("🏠 Início")
            btn_home.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_home.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #00e699;
                    border: none;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 2px 8px;
                }
                QPushButton:hover {
                    color: #00ffaa;
                }
            """)
            btn_home.clicked.connect(self._go_root)
            self.breadcrumb.addWidget(btn_home)

        for i, part in enumerate(self._current_path):
            sep = QLabel("›")
            sep.setStyleSheet("color: #8da3b0; font-size: 14px;")
            self.breadcrumb.addWidget(sep)

            is_last = (i == len(self._current_path) - 1)
            if is_last:
                lbl_part = QLabel(f"📁 {part}")
                lbl_part.setStyleSheet(
                    "color: #ff9f1c; font-size: 14px; font-weight: bold;"
                )
                lbl_part.setToolTip(part)
                self.breadcrumb.addWidget(lbl_part)
            else:
                btn_part = QPushButton(f"📁 {part}")
                btn_part.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_part.setToolTip(part)
                btn_part.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: #8da3b0;
                        border: none;
                        font-size: 14px;
                        padding: 2px 4px;
                    }
                    QPushButton:hover {
                        color: #00e699;
                    }
                """)
                target_path = self._current_path[:i + 1]
                btn_part.clicked.connect(
                    lambda checked, p=target_path: self._go_to_path(p)
                )
                self.breadcrumb.addWidget(btn_part)

        self.breadcrumb.addStretch()

    def _go_root(self):
        self._current_path = []
        self.refresh()

    def _go_to_path(self, path):
        self._current_path = list(path)
        self.refresh()

    def _enter_folder(self, folder_name):
        self._current_path.append(folder_name)
        self.refresh()

    def _get_read_paths(self):
        return set(load_history().keys())

    def _load_cover(self, file_path, covers):
        h = covers.get(file_path, "")
        if not h:
            return QPixmap()
        return load_cover_from_disk(h)

    def _calc_max_cols(self):
        try:
            vw = self.scroll_area.viewport().width()
        except Exception:
            vw = 800
        if vw <= 0:
            vw = 800
        available = max(0, vw - 18)
        n = int((available + CARD_SPACING) // (CARD_WIDTH + CARD_SPACING))
        return max(1, n)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            vw = self.width()
        except Exception:
            return
        if vw <= 0:
            return
        if abs(vw - self._last_render_width) < 20:
            return
        self._last_render_width = vw
        if self._scan_structure is not None:
            QTimer.singleShot(120, self._delayed_rerender)

    def _delayed_rerender(self):
        try:
            vw = self.width()
        except Exception:
            return
        if abs(vw - self._last_render_width) >= 20:
            QTimer.singleShot(120, self._delayed_rerender)
            return
        if self._scan_structure is not None:
            self.refresh()

    def _get_node_at_path(self, path):
        if self._scan_structure is None:
            return None
        node = self._scan_structure
        for part in path:
            folders = node.get("folders", {})
            if part not in folders:
                return None
            node = folders[part]
        return node

    def refresh(self):
        self.clear_grid()
        self.clear_breadcrumb()
        self._build_breadcrumb()

        if self._scan_structure is None:
            lbl = QLabel("Nenhum quadrinho encontrado. Configure uma pasta nas Configurações.")
            lbl.setStyleSheet("color: #8da3b0; font-size: 13px; font-style: italic;")
            self.grid_layout.addWidget(lbl, 0, 0)
            self.status_label.setText("")
            return

        all_files, covers, page_counts = self.provider()
        read_paths = self._get_read_paths()

        # Nó atual
        node = self._get_node_at_path(self._current_path)
        if node is None:
            self._current_path = []
            node = self._scan_structure

        max_cols = self._calc_max_cols()
        row, col = 0, 0

        # Pastas primeiro
        for folder_name, sub_node in sorted(
            node.get("folders", {}).items(),
            key=lambda kv: natural_sort_key(kv[0])
        ):
            # Conta quantos arquivos totais e quantos novos nessa pasta
            sub_files = _collect_all_files(sub_node)
            total_sub = len(sub_files)
            if total_sub == 0:
                continue

            # Capa representativa
            cover = None
            for f in sub_files:
                pm = self._load_cover(f, covers)
                if pm is not None and not pm.isNull():
                    cover = pm
                    break
            if cover is None:
                cover = _find_first_cover(sub_node, covers)

            card = FolderCard(folder_name, total_sub, cover)
            card.clicked.connect(
                lambda checked, fn=folder_name: self._enter_folder(fn)
            )
            self.grid_layout.addWidget(card, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        if col != 0:
            col = 0
            row += 1

        # Arquivos soltos da pasta atual
        loose = list(node.get("loose_files", []))
        loose.sort(key=lambda x: os.path.basename(x).lower())

        for file_path in loose:
            title = os.path.splitext(os.path.basename(file_path))[0]
            pixmap = self._load_cover(file_path, covers)
            page_count = page_counts.get(file_path, 0)
            is_new = file_path not in read_paths

            h_data = load_history().get(file_path, {})
            p_curr = h_data.get("page", 0)
            p_tot = h_data.get("total", 0)
            is_completed = (p_tot > 0 and p_curr >= p_tot)
            is_fav = file_path in load_favorites()

            card = ComicThumbnail(
                title, file_path, pixmap,
                page_count=page_count,
                is_favorite=is_fav,
                is_completed=is_completed,
                is_new=is_new,
            )
            card.double_clicked.connect(self.comic_double_clicked.emit)
            card.favorite_toggled.connect(self._on_fav_toggled)
            self.grid_layout.addWidget(card, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        total_items = len(loose) + len(node.get("folders", {}))
        if self._current_path:
            caminho_str = " › ".join(self._current_path)
            self.status_label.setText(
                f"📚 {total_items} item(ns) em: {caminho_str}"
            )
        else:
            total_comics = len(all_files)
            self.status_label.setText(
                f"📚 {total_items} item(ns) na raiz — "
                f"{total_comics} quadrinho(s) no total"
            )

    def _on_fav_toggled(self, file_path, is_favorite):
        favs = load_favorites()
        if is_favorite:
            favs.add(file_path)
        else:
            favs.discard(file_path)
        save_favorites(favs)


# =====================================================================
# PÁGINA: HISTÓRICO COMPLETO
# =====================================================================

class HistoryPage(QWidget):
    comic_double_clicked = pyqtSignal(str)

    def __init__(self, provider, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self.provider = provider

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        self.title = QLabel("📜 Histórico de Leitura")
        self.title.setStyleSheet(
            "color: #ffffff; font-size: 22px; font-weight: bold;"
        )
        layout.addWidget(self.title)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent;")

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.vbox_layout = QVBoxLayout(self.scroll_content)
        self.vbox_layout.setContentsMargins(0, 0, 10, 0)
        self.vbox_layout.setSpacing(12)
        self.vbox_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area, 1)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #8da3b0; font-size: 13px;")
        layout.addWidget(self.status_label)

    def clear_list(self):
        while self.vbox_layout.count():
            item = self.vbox_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def refresh(self):
        self.clear_list()

        history_data, covers = self.provider()

        if not history_data:
            lbl = QLabel("Nenhum histórico de leitura encontrado. 📖")
            lbl.setStyleSheet("color: #8da3b0; font-size: 13px; font-style: italic;")
            self.vbox_layout.addWidget(lbl)
            self.status_label.setText("")
            return

        import datetime

        sorted_history = sorted(
            history_data.items(),
            key=lambda item: item[1].get("last_read", ""),
            reverse=True
        )

        for file_path, data in sorted_history:
            title = os.path.splitext(os.path.basename(file_path))[0]
            p_curr = data.get("page", 1)
            p_tot = data.get("total", 1)
            last_read_raw = data.get("last_read", "")

            date_str = ""
            if last_read_raw:
                try:
                    dt = datetime.datetime.fromisoformat(last_read_raw)
                    date_str = dt.strftime("%d/%m/%Y às %H:%M")
                except Exception:
                    date_str = last_read_raw

            h = covers.get(file_path, "")
            pixmap = load_cover_from_disk(h) if h else QPixmap()

            card = HistoryListItemCard(
                title=title,
                date_str=date_str,
                page_curr=p_curr,
                page_tot=p_tot,
                file_path=file_path,
                pixmap=pixmap
            )
            card.read_requested.connect(self.comic_double_clicked.emit)
            self.vbox_layout.addWidget(card)

        self.status_label.setText(f"📜 {len(sorted_history)} item(ns) no histórico")


# =====================================================================
# JANELA PRINCIPAL
# =====================================================================

class GreenCBRMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GreenCBR Reader")
        self.resize(1180, 820)
        self.setMinimumSize(900, 600)

        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Guardamos referência aos botões de navegação para destacar o ativo
        self._nav_buttons = {}

        # Referência ao dropdown de busca
        self._search_dropdown = None

        main_layout.addWidget(self.build_sidebar())

        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background: transparent;")
        self.stacked_widget.currentChanged.connect(self._on_page_changed)

        self.collection_widget = CollectionWidget()
        self.collection_widget.comic_double_clicked.connect(self.open_comic_in_reader)
        self.collection_widget.scan_completed.connect(self.on_scan_completed_update_home)

        self.home_page = self.build_content_area()
        self.stacked_widget.addWidget(self.home_page)  # 0

        self.settings_page = SettingsPage()
        self.settings_page.folder_selected.connect(self.on_folder_selected)
        self.settings_page.rescan_requested.connect(self.on_rescan_requested)
        self.stacked_widget.addWidget(self.settings_page)  # 1

        self.favorites_page = FavoritesPage(
            favorites_provider=self._favorites_provider
        )
        self.favorites_page.on_favorite_removed = self._on_favorite_removed
        self.favorites_page.comic_double_clicked.connect(self.open_comic_in_reader)
        self.stacked_widget.addWidget(self.favorites_page)  # 2

        self.reader_page = ComicReaderPage()
        self.reader_page.back_requested.connect(self.close_reader_page)
        self.reader_page.page_changed.connect(self.on_reader_page_changed)
        self.reader_page.unread_requested.connect(self.on_unread_requested)
        self.reader_page.favorite_toggled.connect(self.on_reader_favorite_toggled)
        self.reader_page.read_toggled.connect(self.on_reader_read_toggled)
        self.stacked_widget.addWidget(self.reader_page)  # 3

        self.library_page = LibraryPage(provider=self._library_provider)
        self.library_page.comic_double_clicked.connect(self.open_comic_in_reader)
        self.stacked_widget.addWidget(self.library_page)  # 4

        self.history_page = HistoryPage(provider=self._history_provider)
        self.history_page.comic_double_clicked.connect(self.open_comic_in_reader)
        self.stacked_widget.addWidget(self.history_page)  # 5

        self.collection_widget.favorite_changed.connect(
            self.on_favorites_changed
        )

        main_layout.addWidget(self.stacked_widget, 1)

        # Aplica o destaque inicial (home = índice 0)
        self._update_active_nav(0)

        QTimer.singleShot(100, self.load_saved_folder)

    # ----------------------------------------------------------------
    # NAVEGAÇÃO: destaca o botão correspondente à página atual
    # ----------------------------------------------------------------

    def _on_page_changed(self, index):
        self._update_active_nav(index)
        # Esconde o dropdown de busca ao trocar de página
        self._hide_search_dropdown()

    def _update_active_nav(self, index):
        """Aplica o estilo 'ativo' ao botão correspondente ao índice e
        reseta os demais. Índices: 0=home, 1=config, 2=favoritos,
        3=leitor, 4=biblioteca, 5=histórico."""
        # Mapeia índice da página -> chave do botão
        mapa = {
            0: "home",
            1: "settings",
            2: "favorites",
            3: "reader",
            4: "library",
            5: "history",
        }
        chave_ativa = mapa.get(index)

        estilo_ativo = """
            QPushButton {
                background-color: #0d383b;
                color: #00e699;
                border-left: 3px solid #00e699;
                border-radius: 6px;
                text-align: left;
                padding: 10px 15px;
                font-size: 13px;
                font-weight: bold;
            }
        """

        estilo_inativo = """
            QPushButton {
                background-color: transparent;
                color: #8da3b0;
                border: none;
                border-radius: 8px;
                text-align: left;
                padding: 10px 15px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(13, 42, 54, 0.6);
                color: #ffffff;
            }
        """

        for chave, btn in self._nav_buttons.items():
            try:
                if chave == chave_ativa:
                    btn.setStyleSheet(estilo_ativo)
                else:
                    btn.setStyleSheet(estilo_inativo)
            except Exception:
                pass

    # ----------------------------------------------------------------
    # BUSCA
    # ----------------------------------------------------------------

    def _on_search_text_changed(self, text):
        """Executa a busca conforme o usuário digita."""
        text = text.strip()

        if not text:
            self._hide_search_dropdown()
            return

        if self.collection_widget.scan_result is None:
            self._hide_search_dropdown()
            return

        # Coleta todos os arquivos
        all_files = _collect_all_files(self.collection_widget.scan_result)
        if not all_files:
            self._hide_search_dropdown()
            return

        # Filtra por nome (case-insensitive, contém)
        text_lower = text.lower()
        matches = []
        for f in all_files:
            base = os.path.splitext(os.path.basename(f))[0].lower()
            if text_lower in base:
                matches.append(f)

        if not matches:
            self._hide_search_dropdown()
            return

        # Limita ao configurado
        limit = get_search_limit()
        matches = matches[:limit]

        # Obtém dados para exibir
        covers = self.collection_widget.scan_result.get("covers", {})
        history = load_history()

        # Constrói/atualiza dropdown
        if self._search_dropdown is None:
            self._search_dropdown = SearchDropdown(self)
            self._search_dropdown.read_now_requested.connect(self.open_comic_in_reader)

        self._search_dropdown.clear_items()

        for file_path in matches:
            title = os.path.splitext(os.path.basename(file_path))[0]

            h_data = history.get(file_path, {})
            p_curr = h_data.get("page", 0)
            p_tot = h_data.get("total", 0)
            if p_tot > 0:
                page_info = f"Última página lida: {p_curr} / {p_tot}"
            else:
                page_info = "Não iniciado"

            h = covers.get(file_path, "")
            pixmap = load_cover_from_disk(h) if h else QPixmap()

            self._search_dropdown.add_item(title, page_info, file_path, pixmap)

        # Calcula a altura com base no conteúdo real, para não cortar o final.
        # Cada item = 60px + 5px de gap = 65px. Margens internas = 6+6 = 12.
        # Padding extra para garantir que a última linha fique visível.
        n_items = self._search_dropdown.count_items()
        content_height = n_items * 65 + 12 + 10
        # Limite máximo de altura para não estourar a tela
        max_height = min(content_height, 500)
        self._search_dropdown.setFixedHeight(max_height)

        # Posiciona abaixo do input
        self._position_search_dropdown()
        self._search_dropdown.show()
        self._search_dropdown.raise_()

    def _position_search_dropdown(self):
        """Posiciona o dropdown abaixo do input de busca, com a mesma largura."""
        if self._search_dropdown is None or self._search_input is None:
            return
        try:
            input_pos = self._search_input.mapTo(self, QPoint(0, 0))
            x = input_pos.x()
            y = input_pos.y() + self._search_input.height() + 2
            w = self._search_input.width()
            h = self._search_dropdown.height()
            self._search_dropdown.setGeometry(x, y, w, h)
        except Exception:
            pass

    def _hide_search_dropdown(self):
        if self._search_dropdown is not None:
            try:
                self._search_dropdown.hide()
            except Exception:
                pass

    # ----------------------------------------------------------------

    def _library_provider(self):
        """Provider para a página Biblioteca: retorna todos os arquivos,
        covers e page_counts do scan atual."""
        if not self.collection_widget.scan_result:
            return [], {}, {}

        covers = self.collection_widget.scan_result.get("covers", {})
        page_counts = self.collection_widget.scan_result.get("page_counts", {})
        all_files = _collect_all_files(self.collection_widget.scan_result)
        return all_files, covers, page_counts

    def _history_provider(self):
        history = load_history()
        covers = {}
        if self.collection_widget.scan_result:
            covers = self.collection_widget.scan_result.get("covers", {})
        return history, covers

    def open_comic_in_reader(self, file_path: str):
        self._hide_search_dropdown()
        history = load_history()
        item = history.get(file_path, {})
        start_page = item.get("page", 1)

        self.reader_page.open_comic(file_path, start_page)
        self.stacked_widget.setCurrentWidget(self.reader_page)

    def close_reader_page(self):
        self.update_recent_comics_section()
        self.update_favorites_section()
        self.update_unread_section()
        if self.collection_widget.scan_result:
            self.collection_widget.show_current_view()
        self.stacked_widget.setCurrentIndex(0)

    def on_unread_requested(self, file_path):
        self.update_recent_comics_section()
        self.update_favorites_section()
        self.update_unread_section()
        self.library_page.refresh()

    def on_reader_page_changed(self, file_path, page, total):
        self.update_recent_comics_section()
        self.update_favorites_section()
        self.update_unread_section()

    def on_reader_favorite_toggled(self, file_path, is_favorite):
        if is_favorite:
            self.collection_widget.favorites.add(file_path)
        else:
            self.collection_widget.favorites.discard(file_path)
        save_favorites(self.collection_widget.favorites)
        self.update_favorites_section()
        try:
            self.favorites_page.refresh()
        except Exception:
            pass

    def on_reader_read_toggled(self, file_path, is_read):
        # Se foi marcado como lido, salva no histórico a última página
        if is_read:
            total = len(self.reader_page.pages)
            if total > 0:
                save_history_item(file_path, total, total)
        self.update_recent_comics_section()
        self.update_favorites_section()
        self.update_unread_section()
        try:
            self.history_page.refresh()
        except Exception:
            pass
        try:
            self.library_page.refresh()
        except Exception:
            pass

    def on_scan_completed_update_home(self):
        if hasattr(self, "_loading_recent"):
            self._loading_recent.stop()
            self._loading_recent.setVisible(False)
        if hasattr(self, "_loading_favs"):
            self._loading_favs.stop()
            self._loading_favs.setVisible(False)
        if hasattr(self, "_loading_unread"):
            self._loading_unread.stop()
            self._loading_unread.setVisible(False)

        self.library_page.set_scan_structure(self.collection_widget.scan_result)

        self.update_recent_comics_section()
        self.update_favorites_section()
        self.update_unread_section()
        self.library_page.refresh()

    def on_favorites_changed(self):
        self.favorites_page.refresh()
        self.update_favorites_section()

    # ----------------------------------------------------------------

    def _load_cover_for(self, file_path):
        if not self.collection_widget.scan_result:
            return QPixmap()
        h = self.collection_widget.scan_result.get("covers", {}).get(file_path, "")
        if not h:
            return QPixmap()
        return load_cover_from_disk(h)

    def update_recent_comics_section(self):
        history = load_history()

        while self.recent_hbox.count():
            child = self.recent_hbox.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not history:
            lbl_empty = QLabel("Nenhum quadrinho lido recentemente.")
            lbl_empty.setStyleSheet("color: #8da3b0; font-size: 12px; font-style: italic;")
            self.recent_hbox.addWidget(lbl_empty)
            self.recent_hbox.addStretch()
            return

        sorted_items = sorted(
            history.items(),
            key=lambda x: x[1].get("last_read", ""),
            reverse=True
        )

        for file_path, data in sorted_items[:10]:
            if not os.path.exists(file_path):
                continue

            title = os.path.splitext(os.path.basename(file_path))[0]
            curr_p = data.get("page", 1)
            tot_p = data.get("total", 1)
            prog = int((curr_p / tot_p) * 100) if tot_p > 0 else 0
            page_info = f"{curr_p}/{tot_p}"
            is_completed = (tot_p > 0 and curr_p >= tot_p)

            pixmap = self._load_cover_for(file_path)

            card = RecentComicCard(
                title=title,
                page_info=page_info,
                progress=prog,
                file_path=file_path,
                pixmap=pixmap,
                theme="teal",
                is_completed=is_completed
            )
            card.double_clicked.connect(self.open_comic_in_reader)
            self.recent_hbox.addWidget(card)

        self.recent_hbox.addStretch()

    def update_unread_section(self):
        while self.unread_hbox.count():
            child = self.unread_hbox.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not self.collection_widget.scan_result:
            lbl_empty = QLabel("Nenhum quadrinho encontrado.")
            lbl_empty.setStyleSheet("color: #8da3b0; font-size: 12px; font-style: italic;")
            self.unread_hbox.addWidget(lbl_empty)
            self.unread_hbox.addStretch()
            return

        unread_files, covers, page_counts = self._library_provider()
        read_paths = set(load_history().keys())
        unread_files = [f for f in unread_files if f not in read_paths]

        if not unread_files:
            lbl_empty = QLabel("Todos os quadrinhos já foram lidos. 🎉")
            lbl_empty.setStyleSheet("color: #8da3b0; font-size: 12px; font-style: italic;")
            self.unread_hbox.addWidget(lbl_empty)
            self.unread_hbox.addStretch()
            return

        unread_files.sort(key=lambda x: os.path.basename(x).lower())
        themes = ["purple", "teal", "red"]

        limit = get_unread_limit()
        total_unread = len(unread_files)
        show_files = unread_files[:limit]

        for i, file_path in enumerate(show_files):
            title_full = os.path.splitext(os.path.basename(file_path))[0]
            if "#" in title_full:
                parts = title_full.split("#", 1)
                title = parts[0].strip()
                subtitle = f"#{parts[1].strip()}"
            else:
                title = title_full
                subtitle = ""

            h = covers.get(file_path, "")
            pixmap = load_cover_from_disk(h) if h else QPixmap()

            theme = themes[i % len(themes)]
            card = UnreadComicCard(
                title=title,
                subtitle=subtitle,
                file_path=file_path,
                pixmap=pixmap,
                theme=theme,
            )
            card.double_clicked.connect(self.open_comic_in_reader)
            self.unread_hbox.addWidget(card)

        # Botão "+N" — mais largo, fonte menor e altura reduzida,
        # para não cortar o texto e ficar mais compacto.
        if total_unread > limit:
            restantes = total_unread - limit
            btn_show_all = QPushButton(f"+{restantes}")
            btn_show_all.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_show_all.setFixedHeight(130)      # altura reduzida
            btn_show_all.setMinimumWidth(110)     # mais largo
            btn_show_all.setToolTip(f"Exibir todos os {total_unread} não lidos")
            btn_show_all.setStyleSheet("""
                QPushButton {
                    background-color: rgba(0, 184, 124, 0.15);
                    color: #00e699;
                    border: 2px solid #00e699;
                    border-radius: 10px;
                    padding: 8px 16px;
                    font-weight: 900;
                    font-size: 14px;
                    letter-spacing: 1px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 184, 124, 0.35);
                    border: 2px solid #00ffaa;
                    color: #ffffff;
                }
                QPushButton:pressed {
                    background-color: #00b87c;
                    color: #030f16;
                }
            """)
            btn_show_all.clicked.connect(self._go_to_library)
            self.unread_hbox.addWidget(btn_show_all)

        self.unread_hbox.addStretch()

    def _go_to_library(self):
        self.library_page.set_scan_structure(self.collection_widget.scan_result)
        self.library_page.refresh()
        self.stacked_widget.setCurrentWidget(self.library_page)

    def update_favorites_section(self):
        """Seção 'Marcados como Favorito' na home. Agrupa por pasta.
        Exibe um único card por pasta que contém quadrinhos favoritados.
        O card mostra a capa de um dos favoritos da pasta, o ícone de pasta,
        e a legenda inferior NN/MM favoritos (total de favoritos na pasta / total de
        quadrinhos na pasta). A legenda SUPERIOR exibe o NOME DA PASTA.
        Duplo clique abre a página Favoritos naquela pasta.
        """
        while self.fav_hbox.count():
            child = self.fav_hbox.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        favorites = self.collection_widget.favorites
        if not favorites:
            lbl_empty = QLabel("Nenhum quadrinho marcado como favorito.")
            lbl_empty.setStyleSheet("color: #8da3b0; font-size: 12px; font-style: italic;")
            self.fav_hbox.addWidget(lbl_empty)
            self.fav_hbox.addStretch()
            return

        # Obtém dados do escaneamento
        covers = {}
        page_counts = {}
        folders_map = {}
        if self.collection_widget.scan_result:
            covers = self.collection_widget.scan_result.get("covers", {})
            page_counts = self.collection_widget.scan_result.get("page_counts", {})
            # A estrutura de pastas na raiz está em scan_result["folders"]
            folders_map = self.collection_widget.scan_result.get("folders", {})

        # Mapeia cada arquivo favoritado para sua pasta (se estiver dentro de uma)
        path_to_folder = {}
        def visit_folder(node, folder_name):
            for f in node.get("loose_files", []):
                if f in favorites:
                    path_to_folder[f] = folder_name
            for sub_name, sub_node in node.get("folders", {}).items():
                visit_folder(sub_node, sub_name)

        for folder_name, sub_node in folders_map.items():
            visit_folder(sub_node, folder_name)

        # Agrupa os favoritos por pasta
        by_folder = {}
        loose = []
        for path in favorites:
            folder_name = path_to_folder.get(path)
            if folder_name:
                by_folder.setdefault(folder_name, []).append(path)
            else:
                loose.append(path)

        # Para cada pasta que tem favoritos, cria um card agrupado
        for folder_name in sorted(by_folder.keys()):
            fav_files = by_folder[folder_name]
            if not fav_files:
                continue

            # Encontra uma capa representativa (primeira capa disponível)
            cover = None
            for f in fav_files:
                h = covers.get(f, "")
                if h:
                    pm = load_cover_from_disk(h)
                    if not pm.isNull():
                        cover = pm
                        break
            if cover is None:
                # Tenta carregar qualquer capa da pasta
                for f in fav_files:
                    pm = self._load_cover_for(f)
                    if pm is not None and not pm.isNull():
                        cover = pm
                        break

            # Total de quadrinhos na pasta (todos os arquivos, não só favoritos)
            # Precisamos encontrar o nó da pasta no scan_result
            def find_folder_node(root_folders, target_name):
                """Busca recursivamente o nó da pasta pelo nome."""
                if target_name in root_folders:
                    return root_folders[target_name]
                for sub_name, sub_node in root_folders.items():
                    found = find_folder_node(sub_node.get("folders", {}), target_name)
                    if found is not None:
                        return found
                return None

            folder_node = None
            for fn, sn in folders_map.items():
                if fn == folder_name:
                    folder_node = sn
                    break
                else:
                    folder_node = find_folder_node(sn.get("folders", {}), folder_name)
                    if folder_node is not None:
                        break

            total_in_folder = _count_all_comics(folder_node) if folder_node else len(fav_files)

            card = FavoriteFolderCard(
                folder_name=folder_name,
                file_path=fav_files[0],  # usado para duplo clique, mas não é crucial
                title=f"{len(fav_files)}/{total_in_folder} favoritos",
                cover_pixmap=cover,
                fav_counter=len(fav_files),
                fav_total=total_in_folder,
                is_favorite=True,
            )
            # Duplo clique leva à página Favoritos na pasta correspondente
            card.double_clicked.connect(
                lambda _fn, _fp, fn=folder_name: self._open_favorites_in_folder(fn)
            )
            # Clique simples também pode levar (mantendo consistência)
            card.clicked.connect(
                lambda _fn, _fp, fn=folder_name: self._open_favorites_in_folder(fn)
            )
            # Botão de coração: remove o favorito? Neste card agrupado, o toggle
            # não é usado diretamente, mas podemos desabilitar ou deixar sem efeito.
            card.btn_fav.setVisible(False)  # esconde o coração, pois é um agrupamento
            self.fav_hbox.addWidget(card)

        # Adiciona os favoritos soltos (que não estão em pastas) como cards individuais
        for file_path in loose:
            if not os.path.exists(file_path):
                continue

            title = os.path.splitext(os.path.basename(file_path))[0]

            h = covers.get(file_path, "")
            pixmap = load_cover_from_disk(h) if h else QPixmap()

            card = FavoriteComicCard(
                title=title,
                page_info="",
                file_path=file_path,
                pixmap=pixmap,
                theme="red"
            )
            card.double_clicked.connect(self.open_comic_in_reader)
            self.fav_hbox.addWidget(card)

        self.fav_hbox.addStretch()

    def _on_favorite_card_clicked(self, folder_name, file_path):
        """Clique simples no card de favorito dentro de pasta:
        leva à página Favoritos já naquela pasta."""
        self._open_favorites_in_folder(folder_name)

    def _on_favorite_card_double_clicked(self, folder_name, file_path):
        """Duplo clique: leva à página Favoritos já naquela pasta."""
        self._open_favorites_in_folder(folder_name)

    def _on_favorite_card_toggled(self, file_path, is_favorite):
        """Quando o usuário clica no coração de um card de favorito:
        remove/adiciona dos favoritos e atualiza a home."""
        if is_favorite:
            self.collection_widget.favorites.add(file_path)
        else:
            self.collection_widget.favorites.discard(file_path)
        save_favorites(self.collection_widget.favorites)
        self.update_favorites_section()
        # Atualiza também a página de Favoritos
        try:
            self.favorites_page.refresh()
        except Exception:
            pass

    def _open_favorites_in_folder(self, folder_name):
        favorites, covers, page_counts, folders_map = self._favorites_provider()
        self.stacked_widget.setCurrentWidget(self.favorites_page)
        self.favorites_page.show_folder_view(
            folder_name, favorites, covers, page_counts, folders_map
        )

    # ----------------------------------------------------------------

    def _favorites_provider(self):
        if self.collection_widget.scan_result is None:
            return set(self.collection_widget.favorites), {}, {}, {}
        covers = self.collection_widget.scan_result.get("covers", {})
        page_counts = self.collection_widget.scan_result.get("page_counts", {})
        folders_map = self.collection_widget.scan_result.get("folders", {})
        return (
            set(self.collection_widget.favorites),
            covers,
            page_counts,
            folders_map,
        )

    def _on_favorite_removed(self, file_path, is_favorite):
        if not is_favorite:
            self.collection_widget.favorites.discard(file_path)
        else:
            self.collection_widget.favorites.add(file_path)
        save_favorites(self.collection_widget.favorites)
        self.update_favorites_section()

    def load_saved_folder(self):
        if not os.path.exists(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            folder = config.get("comic_folder", "")
            if folder and os.path.isdir(folder):
                self._show_loading_placeholders()
                self.collection_widget.load_folder(folder, force_rescan=False)
        except Exception:
            pass

    def _show_loading_placeholders(self):
        while self.recent_hbox.count():
            child = self.recent_hbox.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._loading_recent = LoadingSpinner("Carregando últimos lidos")
        self._loading_recent.start()
        self.recent_hbox.addWidget(self._loading_recent)
        self.recent_hbox.addStretch()

        while self.fav_hbox.count():
            child = self.fav_hbox.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._loading_favs = LoadingSpinner("Carregando favoritos")
        self._loading_favs.start()
        self.fav_hbox.addWidget(self._loading_favs)
        self.fav_hbox.addStretch()

        while self.unread_hbox.count():
            child = self.unread_hbox.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._loading_unread = LoadingSpinner("Carregando não lidos")
        self._loading_unread.start()
        self.unread_hbox.addWidget(self._loading_unread)
        self.unread_hbox.addStretch()

    def on_folder_selected(self, folder):
        self._show_loading_placeholders()
        self.collection_widget.load_folder(folder, force_rescan=False)

    def on_rescan_requested(self):
        folder = self.settings_page.folder_input.text().strip()
        if folder and os.path.isdir(folder):
            self.stacked_widget.setCurrentIndex(0)
            self._show_loading_placeholders()
            self.collection_widget.load_folder(folder, force_rescan=False)

    def on_home_rescan_clicked(self):
        folder = self.collection_widget.current_folder
        if not folder or not os.path.isdir(folder):
            if os.path.exists(CONFIG_FILE):
                try:
                    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    folder = config.get("comic_folder", "")
                except Exception:
                    folder = None

        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(
                self, "Aviso",
                "Nenhuma pasta válida configurada. "
                "Vá em Configurações e selecione uma pasta."
            )
            return

        self._show_loading_placeholders()
        self.collection_widget.load_folder(folder, force_rescan=False)

    # ----------------------------------------------------------------

    def build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(200)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(8)

        # -------- Logo da sidebar (assets/logo.png) --------
        logo_layout = QHBoxLayout()
        logo_layout.setContentsMargins(4, 0, 4, 0)

        # -------- Logo da sidebar (assets/logo.png) --------
        logo_path = _resource_path(os.path.join("assets", "logo.png"))
        logo_lbl = QLabel()
        if os.path.exists(logo_path):
            pm = QPixmap(logo_path)
            if not pm.isNull():
                pm_scaled = pm.scaledToHeight(
                    80, Qt.TransformationMode.SmoothTransformation
                )
                logo_lbl.setPixmap(pm_scaled)
            else:
                logo_lbl.setText("GreenCBR")
                logo_lbl.setStyleSheet(
                    "color: #00e699; font-size: 20px; font-weight: bold;"
                )
        else:
            logo_lbl.setText("GreenCBR")
            logo_lbl.setStyleSheet(
                "color: #00e699; font-size: 20px; font-weight: bold;"
            )

        logo_lbl.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        logo_layout.addWidget(logo_lbl)
        logo_layout.addStretch()

        layout.addLayout(logo_layout)
        layout.addSpacing(20)

        nav_btn_style = """
            QPushButton {
                background-color: transparent;
                color: #8da3b0;
                border: none;
                border-radius: 8px;
                text-align: left;
                padding: 10px 15px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(13, 42, 54, 0.6);
                color: #ffffff;
            }
        """

        btn_home = QPushButton(" 🏠  Página Inicial")
        btn_home.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_home.setStyleSheet(nav_btn_style)
        btn_home.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))

        btn_reader = QPushButton(" 📖  Leitor")
        btn_reader.setStyleSheet(nav_btn_style)
        btn_reader.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reader.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.reader_page))

        btn_library = QPushButton(" 📚  Biblioteca")
        btn_library.setStyleSheet(nav_btn_style)
        btn_library.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_library.clicked.connect(self._go_to_library)

        btn_fav = QPushButton(" 💚  Favoritos")
        btn_fav.setStyleSheet(nav_btn_style)
        btn_fav.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_fav.clicked.connect(self._go_to_favorites)

        btn_hist = QPushButton(" ⏱️  Histórico")
        btn_hist.setStyleSheet(nav_btn_style)
        btn_hist.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_hist.clicked.connect(self._go_to_history)

        btn_profile = QPushButton(" 👤  Perfil")
        btn_profile.setStyleSheet(nav_btn_style)
        btn_profile.setCursor(Qt.CursorShape.PointingHandCursor)

        layout.addWidget(btn_home)
        layout.addWidget(btn_reader)
        layout.addWidget(btn_library)
        layout.addWidget(btn_fav)
        layout.addWidget(btn_hist)
        layout.addWidget(btn_profile)

        layout.addStretch()

        btn_settings = QPushButton(" ⚙️  Configurações")
        btn_settings.setStyleSheet(nav_btn_style)
        btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_settings.clicked.connect(
            lambda: self.stacked_widget.setCurrentIndex(1)
        )

        layout.addWidget(btn_settings)

        # Guarda referências para aplicar o destaque de "ativo"
        self._nav_buttons = {
            "home": btn_home,
            "reader": btn_reader,
            "library": btn_library,
            "favorites": btn_fav,
            "history": btn_hist,
            "settings": btn_settings,
        }

        return sidebar

    def _go_to_favorites(self):
        self.favorites_page.refresh()
        self.stacked_widget.setCurrentIndex(2)

    def _go_to_history(self):
        self.history_page.refresh()
        self.stacked_widget.setCurrentIndex(5)

    # ----------------------------------------------------------------

    def build_content_area(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        header_layout = QHBoxLayout()

        page_title = QLabel("Página Inicial")
        page_title.setStyleSheet(
            "color: #ffffff; font-size: 22px; font-weight: bold;"
        )

        # ----- Campo de busca com dropdown -----
        # Aumentado para o input ficar bem mais largo (como destacado em vermelho).
        self._search_input = QLineEdit()
        self._search_input.setObjectName("SearchBar")
        self._search_input.setPlaceholderText("🔍 Buscar Quadrinhos...")
        self._search_input.setMinimumWidth(600)
        self._search_input.textChanged.connect(self._on_search_text_changed)

        hdr_btn_style = """
            QPushButton {
                background-color: rgba(10, 31, 41, 0.9);
                color: #e0f2fe;
                border: 1px solid #133a4a;
                border-radius: 8px;
                padding: 7px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #00b87c;
                color: #030f16;
                border: 1px solid #00b87c;
            }
        """

        btn_import = QPushButton("📄 Importar CBR")
        btn_import.setStyleSheet(hdr_btn_style)
        btn_import.setCursor(Qt.CursorShape.PointingHandCursor)

        header_layout.addWidget(page_title)
        header_layout.addSpacing(20)
        header_layout.addWidget(self._search_input, 1)  # expande para ocupar o espaço
        header_layout.addStretch()
        header_layout.addWidget(btn_import)

        layout.addLayout(header_layout)

        main_scroll = QScrollArea()
        main_scroll.setWidgetResizable(True)
        main_scroll.setFrameShape(QFrame.Shape.NoFrame)
        main_scroll.setStyleSheet("background: transparent;")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(0, 0, 10, 0)
        content_layout.setSpacing(18)

        lbl_recent = QLabel("Últimos Quadrinhos Lidos")
        lbl_recent.setProperty("class", "SectionTitle")
        lbl_recent.setStyleSheet("color: #f0fdf4; font-size: 18px; font-weight: bold;")
        content_layout.addWidget(lbl_recent)

        recent_scroll = HorizontalScrollArea()
        recent_scroll.setWidgetResizable(True)
        recent_scroll.setFrameShape(QFrame.Shape.NoFrame)
        recent_scroll.setFixedHeight(120)
        recent_scroll.setStyleSheet("background: transparent;")

        recent_container = QWidget()
        self.recent_hbox = QHBoxLayout(recent_container)
        self.recent_hbox.setContentsMargins(0, 0, 0, 0)
        self.recent_hbox.setSpacing(12)

        recent_scroll.setWidget(recent_container)
        content_layout.addWidget(recent_scroll)

        lbl_unread = QLabel("Quadrinhos não lidos")
        lbl_unread.setStyleSheet("color: #f0fdf4; font-size: 18px; font-weight: bold;")
        content_layout.addWidget(lbl_unread)

        unread_scroll = HorizontalScrollArea()
        unread_scroll.setWidgetResizable(True)
        unread_scroll.setFrameShape(QFrame.Shape.NoFrame)
        unread_scroll.setFixedHeight(200)
        unread_scroll.setStyleSheet("background: transparent;")

        unread_container = QWidget()
        self.unread_hbox = QHBoxLayout(unread_container)
        self.unread_hbox.setContentsMargins(0, 0, 0, 0)
        self.unread_hbox.setSpacing(12)

        unread_scroll.setWidget(unread_container)
        content_layout.addWidget(unread_scroll)

        lbl_favs = QLabel("Marcados como Favorito")
        lbl_favs.setStyleSheet("color: #f0fdf4; font-size: 18px; font-weight: bold;")
        content_layout.addWidget(lbl_favs)

        fav_scroll = HorizontalScrollArea()
        fav_scroll.setWidgetResizable(True)
        fav_scroll.setFrameShape(QFrame.Shape.NoFrame)
        fav_scroll.setFixedHeight(240)
        fav_scroll.setStyleSheet("background: transparent;")

        fav_container = QWidget()
        self.fav_hbox = QHBoxLayout(fav_container)
        self.fav_hbox.setContentsMargins(0, 0, 0, 0)
        self.fav_hbox.setSpacing(12)

        fav_scroll.setWidget(fav_container)
        content_layout.addWidget(fav_scroll)

        collection_header = QHBoxLayout()

        lbl_collection = QLabel("Minha Coleção")
        lbl_collection.setStyleSheet("color: #f0fdf4; font-size: 18px; font-weight: bold;")

        btn_update_collection = QPushButton("🔄 Atualizar")
        btn_update_collection.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_update_collection.setToolTip("Verifica se houve inclusão, exclusão ou renomeação de quadrinhos na pasta")
        btn_update_collection.setStyleSheet("""
            QPushButton {
                background-color: rgba(10, 31, 41, 0.9);
                color: #00e699;
                border: 1px solid #00b87c;
                border-radius: 6px;
                padding: 4px 12px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #00b87c;
                color: #030f16;
            }
        """)
        btn_update_collection.clicked.connect(self.on_home_rescan_clicked)

        collection_header.addWidget(lbl_collection)
        collection_header.addWidget(btn_update_collection)
        collection_header.addStretch()

        content_layout.addLayout(collection_header)
        content_layout.addWidget(self.collection_widget, 1)

        main_scroll.setWidget(scroll_content)
        layout.addWidget(main_scroll, 1)

        return container

    # ----------------------------------------------------------------
    # RESIZE: reposiciona o dropdown de busca
    # ----------------------------------------------------------------
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._search_dropdown is not None and self._search_dropdown.isVisible():
            self._position_search_dropdown()


# =====================================================================
# MAIN
# =====================================================================

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(QSS_STYLE)

    window = GreenCBRMainWindow()
    window.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()