import uuid

from pydantic import BaseModel


class ExecutionConditionWrite(BaseModel):
    contract_folder_status_id: uuid.UUID
    name: str | None = None
    execution_requirement_code: str | None = None
    description: str | None = None


class ExecutionConditionRead(ExecutionConditionWrite):
    id: uuid.UUID
