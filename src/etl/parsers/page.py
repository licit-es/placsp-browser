"""PageParser — top-level parser that converts raw ATOM bytes to ParsedPage."""

from datetime import datetime

from etl.parsers.entry import EntryParser
from shared.codice.xml_helpers import (
    extract_next_link,
    find_first,
    get_deleted_entries,
    get_entries,
    parse_xml,
    text,
)
from shared.logger import get_logger
from shared.models.parsed_page import DeletedEntry, ParsedPage, ParseFailure

logger = get_logger(__name__)

NS_TOMBSTONE = "http://purl.org/atompub/tombstones/1.0"


class PageParser:
    def __init__(self) -> None:
        self._entry_parser = EntryParser()

    def parse(self, content: bytes, feed_type: str) -> ParsedPage:
        root = parse_xml(content)

        entries = []
        parse_failures: list[ParseFailure] = []
        for entry_elem in get_entries(root):
            try:
                parsed = self._entry_parser.parse(entry_elem, feed_type)
                entries.append(parsed)
            except (ValueError, KeyError, TypeError, AttributeError) as exc:
                entry_id = text(find_first(entry_elem, "id"))
                logger.warning(
                    "Entry parse failed entry_id=%s error=%s",
                    entry_id,
                    exc,
                )
                parse_failures.append(
                    ParseFailure(
                        entry_id=entry_id,
                        error_message=str(exc),
                    )
                )

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
            parse_failures=parse_failures,
            next_link=next_link,
        )
