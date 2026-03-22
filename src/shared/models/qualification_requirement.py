import uuid
from decimal import Decimal

from pydantic import BaseModel


class QualificationRequirementWrite(BaseModel):
    contract_folder_status_id: uuid.UUID
    lot_id: uuid.UUID | None = None
    origin_type: str
    evaluation_criteria_type_code: str | None = None
    description: str | None = None
    threshold_quantity: Decimal | None = None
    personal_situation: str | None = None
    operating_years_quantity: int | None = None
    employee_quantity: int | None = None


class QualificationRequirementRead(QualificationRequirementWrite):
    id: uuid.UUID
