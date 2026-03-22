"""Parser for ValidNoticeInfo elements including publication statuses and docs."""

from dataclasses import dataclass, field
from datetime import date

from lxml import etree

from etl.parsers.document import DocumentData
from shared.codice.xml_helpers import (
    find_all,
    find_children,
    find_first,
    text,
    text_date,
)


@dataclass
class PublicationStatusData:
    """Raw publication status data before FK assignment."""

    publication_media_name: str | None = None
    documents: list[DocumentData] = field(default_factory=list)


@dataclass
class NoticeData:
    """Raw notice data before FK assignment."""

    notice_type_code: str | None = None
    notice_issue_date: date | None = None
    publication_statuses: list[PublicationStatusData] = field(default_factory=list)


@dataclass
class NoticeBundle:
    """Complete parsed output from ValidNoticeInfo elements."""

    notices: list[NoticeData] = field(default_factory=list)


class ValidNoticeInfoParser:
    def parse(self, folder_elem: etree._Element) -> NoticeBundle:
        notices: list[NoticeData] = []

        for vni in find_children(folder_elem, "ValidNoticeInfo"):
            notice_type = text(find_first(vni, "NoticeTypeCode"))
            notice_date = text_date(find_first(vni, "NoticeIssueDate"))

            statuses = self._parse_statuses(vni)

            notices.append(
                NoticeData(
                    notice_type_code=notice_type,
                    notice_issue_date=notice_date,
                    publication_statuses=statuses,
                )
            )

        return NoticeBundle(notices=notices)

    def _parse_statuses(self, vni: etree._Element) -> list[PublicationStatusData]:
        statuses: list[PublicationStatusData] = []

        for aps in find_all(vni, "AdditionalPublicationStatus"):
            media_name = text(find_first(aps, "PublicationMediaName"))

            documents = self._parse_pub_documents(aps)

            statuses.append(
                PublicationStatusData(
                    publication_media_name=media_name,
                    documents=documents,
                )
            )

        return statuses

    def _parse_pub_documents(self, aps: etree._Element) -> list[DocumentData]:
        docs: list[DocumentData] = []

        for ref in find_all(aps, "AdditionalPublicationDocumentReference"):
            ext_ref = find_first(ref, "ExternalReference")
            uri = text(find_first(ext_ref, "URI")) if ext_ref is not None else None
            filename_elem = (
                find_first(ext_ref, "FileName") if ext_ref is not None else None
            )
            filename = text(filename_elem) or text(find_first(ref, "ID"))

            docs.append(
                DocumentData(
                    source_type="PUBLICATION",
                    filename=filename,
                    uri=uri,
                    document_type_code=text(find_first(ref, "DocumentTypeCode")),
                )
            )

        return docs
