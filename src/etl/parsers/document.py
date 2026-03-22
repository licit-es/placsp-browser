"""Parser for document references from all 4 direct source types.

PUBLICATION documents are handled by ValidNoticeInfoParser instead.
"""

from dataclasses import dataclass

from lxml import etree

from shared.codice.xml_helpers import find_all, find_children, find_first, text


@dataclass
class DocumentData:
    """Raw document reference data before FK assignment."""

    source_type: str
    filename: str | None = None
    uri: str | None = None
    document_hash: str | None = None
    document_type_code: str | None = None


class DocumentParser:
    def parse(self, folder_elem: etree._Element) -> list[DocumentData]:
        docs: list[DocumentData] = []
        docs.extend(
            self._parse_typed_refs(folder_elem, "LegalDocumentReference", "LEGAL")
        )
        docs.extend(
            self._parse_typed_refs(
                folder_elem, "TechnicalDocumentReference", "TECHNICAL"
            )
        )
        docs.extend(
            self._parse_typed_refs(
                folder_elem, "AdditionalDocumentReference", "ADDITIONAL"
            )
        )
        docs.extend(self._parse_general_docs(folder_elem))
        return docs

    def _parse_typed_refs(
        self,
        folder_elem: etree._Element,
        tag: str,
        source_type: str,
    ) -> list[DocumentData]:
        results: list[DocumentData] = []
        for ref in find_children(folder_elem, tag):
            ext_ref = find_first(ref, "ExternalReference")
            uri = text(find_first(ext_ref, "URI")) if ext_ref is not None else None
            doc_hash = (
                text(find_first(ext_ref, "DocumentHash"))
                if ext_ref is not None
                else None
            )
            results.append(
                DocumentData(
                    source_type=source_type,
                    filename=text(find_first(ref, "ID")),
                    uri=uri,
                    document_hash=doc_hash,
                )
            )
        return results

    def _parse_general_docs(self, folder_elem: etree._Element) -> list[DocumentData]:
        results: list[DocumentData] = []
        for gd in find_children(folder_elem, "GeneralDocument"):
            for ref in find_all(gd, "GeneralDocumentDocumentReference"):
                ext_ref = find_first(ref, "ExternalReference")
                uri = text(find_first(ext_ref, "URI")) if ext_ref is not None else None
                filename_elem = (
                    find_first(ext_ref, "FileName") if ext_ref is not None else None
                )
                filename = text(filename_elem) or text(find_first(ref, "ID"))
                results.append(
                    DocumentData(
                        source_type="GENERAL",
                        filename=filename,
                        uri=uri,
                        document_type_code=text(find_first(ref, "DocumentTypeCode")),
                    )
                )
        return results
