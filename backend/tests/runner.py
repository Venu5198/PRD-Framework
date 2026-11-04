import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_auth import test_password_hashing, test_jwt_token_flow
from tests.test_pipeline import test_input_analyzer, test_clarification_engine, test_requirement_engineer_and_prd_assembly
from tests.test_validation import test_validation_missing_sections, test_validation_duplicate_and_unmapped_fr
from tests.test_export import test_export_all_formats
from tests.test_api import test_full_user_workflow
from app.core.database import db_manager

async def run_all():
    print("--- Running Test Suite ---")
    
    print("1. Running Auth Tests...")
    test_password_hashing()
    test_jwt_token_flow()
    print("   [PASS] Auth tests passed.")

    print("2. Running Pipeline Tests...")
    await test_input_analyzer()
    await test_clarification_engine()
    await test_requirement_engineer_and_prd_assembly()
    print("   [PASS] Pipeline tests passed.")

    print("3. Running Validation Tests...")
    await test_validation_missing_sections()
    await test_validation_duplicate_and_unmapped_fr()
    print("   [PASS] Validation tests passed.")

    print("4. Running Export Tests...")
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        test_export_all_formats(Path(tmpdir))
    print("   [PASS] Export tests passed.")

    print("5. Running Full API Workflow Test...")
    await db_manager.connect()
    try:
        await test_full_user_workflow()
    finally:
        await db_manager.close()
    print("   [PASS] Full API Workflow tests passed.")

    print("\n===============================")
    print("ALL TEST SUITES PASSED (5/5)!")
    print("===============================")

if __name__ == "__main__":
    asyncio.run(run_all())
