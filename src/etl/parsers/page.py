"""PageParser — top-level parser that converts raw ATOM bytes to ParsedPage."""

from datetime import datetime

from shared.codice.xml_helpers import (
    extract_next_link,
    get_deleted_entries,
    get_entries,
    parse_xml,
)
from shared.models.parsed_page import DeletedEntry, ParsedPage
from etl.parsers.entry import EntryParser

NS_TOMBSTONE = "http://purl.org/atompub/tombstones/1.0"


class PageParser:
    def __init__(self) -> None:
        self._entry_parser = EntryParser()

    def parse(self, content: bytes, feed_type: str) -> ParsedPage:
        root = parse_xml(content)

        entries = []
        for entry_elem in get_entries(root):
            parsed = self._entry_parser.parse(entry_elem, feed_type)
            entries.append(parsed)

        deleted_entries = []
        for del_elem in get_deleted_entries(root):
            ref = del_elem.get("ref", "")
            when_str = del_elem.get("when")
            when = datetime.fromisoformat(when_str) if when_str else None
            deleted_entries.append(DeletedEntry(ref=ref, when=when))

        next_link = extract_next_link(root)

        return ParsedPage(
            entries=entries,
            deleted_entries=deleted_entries,
            next_link=next_link,
        )
