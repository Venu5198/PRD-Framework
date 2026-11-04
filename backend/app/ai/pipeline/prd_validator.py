import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from app.models.prd import PRDVersion
from app.models.validation import ValidationIssue, ValidationReport
from app.services.validation_service import ValidationService

logger = logging.getLogger(__name__)

class PRDValidatorInput(BaseModel):
    version: PRDVersion

class PRDValidatorOutput(BaseModel):
    report: ValidationReport

class PRDValidator:
    """
    Component 10: PRD Validator.
    Performs deterministic quality analysis over generated or updated PRD versions.
    """
    def __init__(self, validation_service: ValidationService):
        self.validation_service = validation_service

    async def validate(self, input_data: PRDValidatorInput) -> PRDValidatorOutput:
        report = await self.validation_service.validate_version(input_data.version)
        return PRDValidatorOutput(report=report)

