from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from qgis.core import QgsApplication, QgsFields, QgsIconUtils
from qgis.PyQt.QtCore import (
    QBuffer,
    QByteArray,
    QFile,
    QIODevice,
    QRectF,
    QSize,
    Qt,
)
from qgis.PyQt.QtGui import QIcon, QPainter, QPixmap
from qgis.PyQt.QtSvg import QSvgRenderer
from qgis.PyQt.QtWidgets import QLabel

from quick_map_services.core.constants import PACKAGE_NAME
from quick_map_services.core.logging import logger

MATERIAL_ICON_FILL_SELECTORS = {
    "fill_0": 0,
    "fill0": 0,
    "outline": 0,
    "fill_1": 1,
    "fill1": 1,
    "filled": 1,
}


def _plugin_path() -> Path:
    return Path(__file__).resolve().parents[2]


def _plugin_icon_source(
    icon_path: Union[Path, str],
) -> Tuple[Path, Optional[str]]:
    plugin_icons_path = _plugin_path() / "icons"
    filesystem_path = plugin_icons_path / icon_path
    qrc_icon_path = str(icon_path).replace("\\", "/")
    qrc_path = f":/plugins/{PACKAGE_NAME}/icons/{qrc_icon_path}"

    if filesystem_path.exists():
        return filesystem_path, str(filesystem_path)
    if QFile(qrc_path).exists():
        return filesystem_path, qrc_path

    return filesystem_path, None


def _qgis_icon_source(icon_name: str) -> Optional[str]:
    resource_paths = [
        f":images/themes/default/{icon_name}",
        f":images/themes/default/propertyicons/{icon_name}",
        f":images/themes/default/console/{icon_name}",
    ]
    for resource_path in resource_paths:
        if QFile(resource_path).exists():
            return resource_path

    return None


def qgis_icon(icon_name: str) -> QIcon:
    """Return a QGIS theme icon by name.

    :param icon_name: Name of the icon.

    :return: QIcon instance for the QGIS theme icon.
    """
    icon = QgsApplication.getThemeIcon(icon_name)
    if not icon.isNull():
        return icon

    resource_path = _qgis_icon_source(icon_name)
    if resource_path is not None:
        return QIcon(resource_path)

    return icon


def qgis_checkable_icon(off_icon_name: str, on_icon_name: str) -> QIcon:
    """Return a QGIS icon with separate off and on states.

    :param off_icon_name: Icon name for the unchecked state.
    :param on_icon_name: Icon name for the checked state.
    :return: QIcon instance with configured states.
    """
    icon = qgis_icon(off_icon_name)
    on_resource_path = _qgis_icon_source(on_icon_name)
    if on_resource_path is not None:
        icon.addFile(on_resource_path, state=QIcon.State.On)
        return icon

    on_icon = qgis_icon(on_icon_name)
    icon.addPixmap(
        on_icon.pixmap(on_icon.actualSize(QSize(24, 24))),
        state=QIcon.State.On,
    )
    return icon


def field_type_icon(field_type: Any) -> QIcon:
    """Return a QGIS field type icon.

    :param field_type: QGIS field type value.
    :return: QIcon instance for the field type.
    """
    return QgsFields.iconForFieldType(field_type)


def wkb_type_icon(geometry_type: Any) -> QIcon:
    """Return a QGIS geometry type icon.

    :param geometry_type: QGIS WKB geometry type.
    :return: QIcon instance for the geometry type.
    """
    return QgsIconUtils.iconForWkbType(geometry_type)


def plugin_icon(
    icon_path: Union[Path, str, None] = None,
    color: Optional[str] = None,
    size: Optional[int] = None,
    replacements: Optional[Dict[str, str]] = None,
) -> QIcon:
    """Return the plugin icon as QIcon.

    :param icon_path: Path or name of the icon file.
    :param color: Color to apply instead of white fill for SVG icons.
        If None, keep the original fills unchanged.
    :param size: Optional size for rendered SVG icons.
    :param replacements: Optional literal SVG text replacements.
    :return: QIcon instance for the plugin icon.
    """
    if icon_path is None:
        icon_path = "qms_logo.svg"

    filesystem_path, result_path = _plugin_icon_source(icon_path)
    if result_path is None:
        logger.warning(f"Icon {icon_path} does not exist")
        return QIcon(str(filesystem_path))

    # Repaint only when needed and only for SVG icons
    if result_path.lower().endswith(".svg") and (
        color is not None or size is not None or replacements is not None
    ):
        return render_svg_icon(
            result_path, color=color, size=size, replacements=replacements
        )

    return QIcon(result_path)


def plugin_icon_file_path(icon_path: Union[Path, str]) -> Path:
    """Return a filesystem path to a plugin icon asset.

    :param icon_path: Path or name of the file under the plugin icons folder.
    :return: Filesystem path to the icon.
    """
    filesystem_path, _ = _plugin_icon_source(icon_path)
    return filesystem_path


def material_icon_path(
    name: str,
    *,
    fill: Optional[int] = None,
) -> Optional[Path]:
    """Return a material SVG path from plugin assets.

    :param name: Name of the material icon (without .svg extension).
    :param fill: Optional Material Symbols fill selector.
    :return: SVG path or None if it is not found.
    """
    material_icons_path = _plugin_path() / "icons" / "material"
    base_name, selected_fill = _material_icon_selector(name, fill)

    for icon_directory in (
        material_icons_path,
        material_icons_path / "custom",
    ):
        for path in sorted(icon_directory.glob(f"{base_name}*")):
            if not path.is_file() or path.suffix.lower() != ".svg":
                continue

            if not _matches_material_icon_fill(path, selected_fill):
                continue

            suffix = path.name[len(base_name) :]
            if suffix == ".svg":
                return path
            if (
                suffix.startswith("_")
                and len(suffix) > 1
                and suffix[1].isdigit()
            ):
                return path

            size_part = base_name.rsplit("_", 1)[-1]
            if (
                suffix.startswith("_")
                and size_part.endswith("dp")
                and size_part[:-2].isdigit()
            ):
                return path

    return None


def _material_icon_selector(
    name: str,
    fill: Optional[int],
) -> Tuple[str, Optional[int]]:
    normalized_name = name.strip().replace("-", "_").replace(" ", "_")

    for suffix, selector_fill in MATERIAL_ICON_FILL_SELECTORS.items():
        selector_suffix = f"_{suffix}"
        if normalized_name.endswith(selector_suffix):
            return normalized_name[: -len(selector_suffix)], selector_fill

    return normalized_name, fill


def _matches_material_icon_fill(
    path: Path,
    fill: Optional[int],
) -> bool:
    if fill is None:
        return True

    return f"_FILL{fill}_" in path.name


def icon_from_pixmap(pixmap: QPixmap) -> QIcon:
    """Return a QIcon from a QPixmap.

    :param pixmap: Source pixmap.
    :return: QIcon instance for the pixmap.
    """
    return QIcon(pixmap)


def icon_with_disabled_pixmap(icon: QIcon, size: QSize) -> QIcon:
    """Return a QIcon that keeps the same pixmap when disabled.

    :param icon: Source icon.
    :param size: Target pixmap size.
    :return: QIcon with Normal and Disabled pixmaps.
    """
    pixmap = icon.pixmap(size)
    result_icon = QIcon()
    result_icon.addPixmap(pixmap, QIcon.Mode.Normal)
    result_icon.addPixmap(pixmap, QIcon.Mode.Disabled)
    return result_icon


def material_icon(
    name: str,
    *,
    color: str = "",
    size: Optional[int] = None,
    fill: Optional[int] = None,
) -> QIcon:
    """Return a material icon as QIcon, optionally recolored and resized.

    :param name: Name of the material icon (without .svg extension).
    :param color: Color to apply to the icon (hex string).
    :param size: Size of the icon in pixels.
    :param fill: Optional Material Symbols fill selector.

    :return: QIcon instance for the material icon.

    :raises FileNotFoundError: If the SVG file is not found.
    :raises ValueError: If the SVG cannot be loaded.
    """
    svg_path = material_icon_path(name, fill=fill)

    if svg_path is None:
        message = f"SVG file not found: {name}"
        raise FileNotFoundError(message)

    effective_color = color or QgsApplication.palette().text().color().name()
    return render_svg_icon(svg_path, color=effective_color, size=size)


def render_svg_content_icon(
    svg_content: str,
    *,
    color: Optional[str] = None,
    size: Optional[int] = None,
    replacements: Optional[Dict[str, str]] = None,
) -> QIcon:
    """Render SVG text into a QIcon with optional recolor and resize.

    :param svg_content: SVG text.
    :param color: Color to apply instead of white fill. If None, keep the
        original fills unchanged.
    :param size: Output icon size in pixels. If None, use SVG default size.
    :param replacements: Optional literal SVG text replacements.
    :return: Rendered QIcon.
    :raises ValueError: If the SVG cannot be loaded.
    """
    # Replace only pure white fills to preserve multi-colored icons
    if color:
        modified_svg = svg_content.replace('fill="#ffffff"', f'fill="{color}"')
        modified_svg = modified_svg.replace('fill="#fff"', f'fill="{color}"')
        modified_svg = modified_svg.replace("fill:#ffffff", f"fill:{color}")
        modified_svg = modified_svg.replace("fill:#fff", f"fill:{color}")
    else:
        modified_svg = svg_content

    if replacements:
        for key, value in replacements.items():
            modified_svg = modified_svg.replace(key, value)

    byte_array = QByteArray(modified_svg.encode("utf-8"))
    renderer = QSvgRenderer()
    if not renderer.load(byte_array):
        message = "Failed to load SVG content"
        raise ValueError(message)

    target_size = renderer.defaultSize() if size is None else QSize(size, size)
    pixmap = QPixmap(target_size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    renderer.render(
        painter,
        QRectF(0, 0, target_size.width(), target_size.height()),
    )
    painter.end()

    return QIcon(pixmap)


def render_svg_icon(
    svg_path: Union[Path, str],
    *,
    color: Optional[str] = None,
    size: Optional[int] = None,
    replacements: Optional[Dict[str, str]] = None,
) -> QIcon:
    """Render an SVG file into a QIcon with optional recolor and resize.

    :param svg_path: Filesystem path to the SVG file.
    :param color: Color to apply instead of white fill. If None, keep the
        original fills unchanged.
    :param size: Output icon size in pixels. If None, use SVG default size.
    :param replacements: Optional literal SVG text replacements.
    :return: Rendered QIcon.
    :raises ValueError: If the SVG cannot be loaded.
    """
    if isinstance(svg_path, Path):
        svg_content = svg_path.read_text(encoding="utf-8")
    else:
        file = QFile(svg_path)
        if not file.open(
            QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text
        ):
            message = f"Failed to open SVG file: {svg_path}"
            raise ValueError(message)
        svg_content = file.readAll().data().decode("utf-8")
        file.close()

    return render_svg_content_icon(
        svg_content,
        color=color,
        size=size,
        replacements=replacements,
    )


def draw_icon(label: QLabel, icon: QIcon, *, size: int = 24) -> None:
    """Draw an icon on a QLabel with specified size.

    :param label: QLabel to draw the icon on.
    :param icon: QIcon to be drawn.
    :param size: Size of the icon in pixels.
    """
    pixmap = icon.pixmap(icon.actualSize(QSize(size, size)))
    label.setPixmap(pixmap)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)


def icon_to_base64(icon: QIcon, size: Optional[int] = None) -> str:
    """Convert a QIcon to a base64-encoded PNG string.

    :param icon: QIcon to convert.
    :param size: Size of the icon in pixels. If None, use 32x32.
    :return: Base64-encoded PNG string of the icon.
    """
    icon_size = QSize(32, 32) if size is None else QSize(size, size)
    pixmap = icon.pixmap(icon_size)

    buffer = QByteArray()
    qbuffer = QBuffer(buffer)
    qbuffer.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.save(qbuffer, "PNG")
    qbuffer.close()

    data = buffer.toBase64().data()
    if not isinstance(data, str):
        data = data.decode("utf-8")

    return "data:image/png;base64, " + data
