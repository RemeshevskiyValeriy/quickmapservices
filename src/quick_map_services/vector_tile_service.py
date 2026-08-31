from typing import Any, Callable, Dict, Mapping, Optional, Tuple
from urllib.parse import urljoin

from qgis.core import QgsApplication

from quick_map_services.core.exceptions import QmsError


def resolve_vector_tile_service(
    service: Mapping[str, Any], load_json: Callable[[str], Any]
) -> Tuple[Dict[str, Any], int]:
    """Resolve the first vector source declared by a Web QMS style."""
    style_url = service.get("style_url")
    if not isinstance(style_url, str) or not style_url:
        style_url = _required_string(service, "url")
    style = _required_mapping(load_json(style_url), "style document")
    sources = _required_mapping(style.get("sources"), "style sources")

    vector_sources = []
    for source_name, source in sources.items():
        if not isinstance(source_name, str):
            continue
        if not isinstance(source, Mapping) or source.get("type") != "vector":
            continue
        vector_sources.append((source_name, source))

    if not vector_sources:
        raise _resolution_error(
            "The vector tile style does not contain a vector source."
        )

    source_name, source = vector_sources[0]
    tile_url, source_minimum, source_maximum = _resolve_source(
        source, style_url, load_json
    )
    service_minimum = _optional_zoom(service.get("z_min"), "service z_min")
    service_maximum = _optional_zoom(service.get("z_max"), "service z_max")
    z_min, z_max = _zoom_range(
        service_minimum,
        service_maximum,
        source_minimum,
        source_maximum,
    )

    resolved_service = dict(service)
    resolved_service.update(
        {
            "type": "mvt",
            "url": tile_url,
            "style_url": style_url,
            "z_min": z_min,
            "z_max": z_max,
            "mvt_url_name": source_name,
        }
    )
    return resolved_service, len(vector_sources)


def _resolve_source(
    source: Mapping[str, Any],
    style_url: str,
    load_json: Callable[[str], Any],
) -> Tuple[str, Optional[int], Optional[int]]:
    source_url = style_url
    tile_urls = _optional_strings(source.get("tiles"), "vector source tiles")
    source_data = source
    if tile_urls is None:
        tilejson_url = urljoin(style_url, _required_string(source, "url"))
        source_url = tilejson_url
        source_data = _required_mapping(load_json(tilejson_url), "TileJSON")
        tile_urls = _required_strings(
            source_data.get("tiles"), "TileJSON tiles"
        )

    return (
        urljoin(source_url, tile_urls[0]),
        _optional_zoom(source_data.get("minzoom"), "vector source minzoom"),
        _optional_zoom(source_data.get("maxzoom"), "vector source maxzoom"),
    )


def _zoom_range(
    service_minimum: Optional[int],
    service_maximum: Optional[int],
    source_minimum: Optional[int],
    source_maximum: Optional[int],
) -> Tuple[Optional[int], Optional[int]]:
    minimum_values = tuple(
        value
        for value in (service_minimum, source_minimum)
        if value is not None
    )
    maximum_values = tuple(
        value
        for value in (service_maximum, source_maximum)
        if value is not None
    )
    z_min = max(minimum_values) if minimum_values else None
    z_max = min(maximum_values) if maximum_values else None
    if z_min is not None and z_max is not None and z_min > z_max:
        raise _resolution_error(
            "The vector source zoom range does not overlap the service zoom range."
        )
    return z_min, z_max


def _required_mapping(value: Any, context: str) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    raise _resolution_error("Expected an object for {}.".format(context))


def _required_string(value: Mapping[str, Any], key: str) -> str:
    result = value.get(key)
    if isinstance(result, str) and result:
        return result
    raise _resolution_error("Missing {} URL.".format(key))


def _optional_strings(value: Any, context: str) -> Optional[Tuple[str, ...]]:
    if value is None:
        return None
    return _required_strings(value, context)


def _required_strings(value: Any, context: str) -> Tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise _resolution_error("Expected non-empty {}.".format(context))
    if not all(isinstance(item, str) and item for item in value):
        raise _resolution_error("Expected URL strings for {}.".format(context))
    return tuple(value)


def _optional_zoom(value: Any, context: str) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise _resolution_error("Expected an integer for {}.".format(context))


def _resolution_error(detail: str) -> QmsError:
    return QmsError(
        "Failed to resolve vector tile service: {}".format(detail),
        user_message=QgsApplication.translate(
            "QuickMapServices", "Failed to read vector tile service data."
        ),
        detail=detail,
    )
