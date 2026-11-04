import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_auth import test_password_hashing, test_jwt_token_flow
from tests.test_pipeline import test_input_analyzer, test_clarification_engine, test_requirement_engineer_and_prd_assembly
from tests.test_components import (
    test_assignment_parser,
    test_problem_analyst,
    test_stakeholder_analyst,
    test_business_rules_analyst,
    test_risk_analyst
)
from tests.test_security import (
    test_security_auth_rejection,
    test_security_upload_restrictions,
    test_security_duplicate_username_enforcement
)
from tests.test_validation import test_validation_missing_sections, test_validation_duplicate_and_unmapped_fr
from tests.test_export import test_export_all_formats
from tests.test_api import test_full_user_workflow
from app.core.database import db_manager

async def run_all():
    print("--- Running Test Suite ---")
    await db_manager.connect()
    try:
        print("1. Running Auth Tests...")
        test_password_hashing()
        test_jwt_token_flow()
        print("   [PASS] Auth tests passed.")

        print("2. Running Pipeline & Component Tests (10 Stages)...")
        await test_input_analyzer()
        await test_clarification_engine()
        await test_requirement_engineer_and_prd_assembly()
        await test_assignment_parser()
        await test_problem_analyst()
        await test_stakeholder_analyst()
        await test_business_rules_analyst()
        await test_risk_analyst()
        print("   [PASS] All 10-stage pipeline component tests passed.")

        print("3. Running Security & Hardening Tests...")
        await test_security_auth_rejection()
        await test_security_upload_restrictions()
        await test_security_duplicate_username_enforcement()
        print("   [PASS] Security tests passed (Upload limits, Path traversal, Index uniqueness).")

        print("4. Running Validation Tests...")
        await test_validation_missing_sections()
        await test_validation_duplicate_and_unmapped_fr()
        print("   [PASS] Validation tests passed.")

        print("5. Running Export Tests...")
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            test_export_all_formats(Path(tmpdir))
        print("   [PASS] Export tests passed.")

        print("6. Running Full API Workflow Test...")
        await test_full_user_workflow()
        print("   [PASS] Full API Workflow tests passed.")

        print("\n========================================")
        print("ALL TEST SUITES PASSED (6/6 SUITES, 17 TESTS)!")
        print("========================================")
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(run_all())

