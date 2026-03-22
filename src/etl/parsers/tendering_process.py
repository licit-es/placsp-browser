"""Parser for TenderingProcess from ContractFolderStatus element."""

from dataclasses import dataclass
from datetime import date, time

from lxml import etree

from shared.codice.xml_helpers import (
    find_child,
    find_first,
    text,
    text_bool,
    text_date,
    text_int,
    text_time,
)


@dataclass
class TenderingProcessFields:
    """Fields extracted from TenderingProcess."""

    procedure_code: str | None = None
    urgency_code: str | None = None
    submission_method_code: str | None = None
    submission_deadline_date: date | None = None
    submission_deadline_time: time | None = None
    submission_deadline_description: str | None = None
    document_availability_end_date: date | None = None
    document_availability_end_time: time | None = None
    contracting_system_code: str | None = None
    part_presentation_code: str | None = None
    auction_constraint_indicator: bool | None = None
    max_lot_presentation_quantity: int | None = None
    max_tenderer_awarded_lots_qty: int | None = None
    lots_combination_rights: str | None = None
    over_threshold_indicator: bool | None = None
    participation_request_end_date: date | None = None
    participation_request_end_time: time | None = None
    short_list_limitation_description: str | None = None
    short_list_min_quantity: int | None = None
    short_list_expected_quantity: int | None = None
    short_list_max_quantity: int | None = None


class TenderingProcessParser:
    def parse(self, folder_elem: etree._Element) -> TenderingProcessFields:
        tp = find_child(folder_elem, "TenderingProcess")
        if tp is None:
            return TenderingProcessFields()

        submission = find_first(tp, "TenderSubmissionDeadlinePeriod")
        doc_avail = find_first(tp, "DocumentAvailabilityPeriod")
        auction = find_first(tp, "AuctionTerms")
        participation = find_first(tp, "ParticipationRequestReceptionPeriod")

        return TenderingProcessFields(
            procedure_code=text(find_child(tp, "ProcedureCode")),
            urgency_code=text(find_child(tp, "UrgencyCode")),
            submission_method_code=text(find_child(tp, "SubmissionMethodCode")),
            submission_deadline_date=text_date(find_first(submission, "EndDate"))
            if submission is not None
            else None,
            submission_deadline_time=text_time(find_first(submission, "EndTime"))
            if submission is not None
            else None,
            submission_deadline_description=text(find_first(submission, "Description"))
            if submission is not None
            else None,
            document_availability_end_date=text_date(find_first(doc_avail, "EndDate"))
            if doc_avail is not None
            else None,
            document_availability_end_time=text_time(find_first(doc_avail, "EndTime"))
            if doc_avail is not None
            else None,
            contracting_system_code=text(find_child(tp, "ContractingSystemCode")),
            part_presentation_code=text(find_child(tp, "PartPresentationCode")),
            auction_constraint_indicator=text_bool(
                find_first(auction, "AuctionConstraintIndicator")
            )
            if auction is not None
            else None,
            max_lot_presentation_quantity=text_int(
                find_child(tp, "MaximumLotPresentationQuantity")
            ),
            max_tenderer_awarded_lots_qty=text_int(
                find_child(tp, "MaximumTendererAwardedLotsQuantity")
            ),
            lots_combination_rights=text(
                find_child(tp, "LotsCombinationContractingAuthorityRights")
            ),
            over_threshold_indicator=text_bool(
                find_child(tp, "OverThresholdIndicator")
            ),
            participation_request_end_date=text_date(
                find_first(participation, "EndDate")
            )
            if participation is not None
            else None,
            participation_request_end_time=text_time(
                find_first(participation, "EndTime")
            )
            if participation is not None
            else None,
            short_list_limitation_description=text(
                find_first(tp, "ShortListLimitationDescription")
            ),
            short_list_min_quantity=text_int(
                find_first(tp, "ShortListMinimumQuantity")
            ),
            short_list_expected_quantity=text_int(
                find_first(tp, "ShortListExpectedQuantity")
            ),
            short_list_max_quantity=text_int(
                find_first(tp, "ShortListMaximumQuantity")
            ),
        )
