"""Namespace-agnostic XML element search for CODICE/PLACSP XML.

All parsers use these functions instead of raw XPath. Handles CODICE XML
with or without namespace prefixes by matching on local element names.
"""

from datetime import date, time
from decimal import Decimal, InvalidOperation

from lxml import etree

# ATOM namespace for feed-level elements
NS_ATOM = "http://www.w3.org/2005/Atom"
NS_TOMBSTONE = "http://purl.org/atompub/tombstones/1.0"


def parse_xml(content: bytes) -> etree._Element:
    """Parse XML bytes into an lxml Element."""
    return etree.fromstring(content)


def _is_element(elem: etree._Element) -> bool:
    """Check if node is a real element (not a comment or PI)."""
    return isinstance(elem.tag, str)


def _local_name(elem: etree._Element) -> str:
    """Return the local name of an element, stripping any namespace."""
    tag = elem.tag
    if not isinstance(tag, str):
        return ""
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def find_first(parent: etree._Element, tag: str) -> etree._Element | None:
    """Find first descendant matching tag by local name (namespace-agnostic)."""
    for elem in parent.iter():
        if _is_element(elem) and _local_name(elem) == tag:
            return elem
    return None


def find_all(parent: etree._Element, tag: str) -> list[etree._Element]:
    """Find all descendants matching tag by local name (namespace-agnostic)."""
    return [
        elem for elem in parent.iter() if _is_element(elem) and _local_name(elem) == tag
    ]


def find_child(parent: etree._Element, tag: str) -> etree._Element | None:
    """Find first direct child matching tag by local name."""
    for child in parent:
        if _is_element(child) and _local_name(child) == tag:
            return child
    return None


def find_children(parent: etree._Element, tag: str) -> list[etree._Element]:
    """Find all direct children matching tag by local name."""
    return [
        child for child in parent if _is_element(child) and _local_name(child) == tag
    ]


def text(elem: etree._Element | None, default: str | None = None) -> str | None:
    """Extract text content from an element."""
    if elem is None:
        return default
    t = elem.text
    if t is None:
        return default
    t = t.strip()
    return t if t else default


def text_int(elem: etree._Element | None) -> int | None:
    """Extract text as integer."""
    val = text(elem)
    if val is None:
        return None
    try:
        return int(val)
    except ValueError:
        return None


def text_decimal(elem: etree._Element | None) -> Decimal | None:
    """Extract text as Decimal."""
    val = text(elem)
    if val is None:
        return None
    try:
        return Decimal(val)
    except InvalidOperation:
        return None


def text_bool(elem: etree._Element | None) -> bool | None:
    """Extract text as boolean (true/false)."""
    val = text(elem)
    if val is None:
        return None
    return val.lower() == "true"


def text_date(elem: etree._Element | None) -> date | None:
    """Extract text as date (YYYY-MM-DD)."""
    val = text(elem)
    if val is None:
        return None
    try:
        return date.fromisoformat(val)
    except ValueError:
        return None


def text_time(elem: etree._Element | None) -> time | None:
    """Extract text as time (HH:MM:SS or HH:MM)."""
    val = text(elem)
    if val is None:
        return None
    try:
        return time.fromisoformat(val)
    except ValueError:
        return None


def attr(elem: etree._Element | None, name: str) -> str | None:
    """Extract attribute value from an element."""
    if elem is None:
        return None
    return str(elem.get(name)) if elem.get(name) is not None else None


def get_entries(root: etree._Element) -> list[etree._Element]:
    """Get all <entry> elements from an ATOM feed root."""
    return [
        child
        for child in root
        if _is_element(child)
        and _local_name(child) == "entry"
        and child.tag != f"{{{NS_TOMBSTONE}}}deleted-entry"
    ]


def get_deleted_entries(root: etree._Element) -> list[etree._Element]:
    """Get all <at:deleted-entry> elements from an ATOM feed root."""
    return [
        child
        for child in root
        if _is_element(child) and child.tag == f"{{{NS_TOMBSTONE}}}deleted-entry"
    ]


def extract_next_link(root: etree._Element) -> str | None:
    """Extract the rel='next' link URL from an ATOM feed root."""
    for child in root:
        if (
            _is_element(child)
            and _local_name(child) == "link"
            and child.get("rel") == "next"
        ):
            href = child.get("href")
            return str(href) if href is not None else None
    return None
