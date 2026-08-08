import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.db import get_supabase_client
from app.security.audit import log_security_event

async def run_db_test():
    client = get_supabase_client()
    if client is None:
        print("Supabase client is not configured")
        return
    try:
        # Test audit log
        await log_security_event(
            action="test_audit",
            user="test_runner",
            status="success",
            target_urn="urn:li:dataset:(urn:li:dataPlatform:snowflake,prod.sales.fct_revenue,PROD)",
            details={"test_key": "test_value"}
        )
        print("Audit log write finished (check console above to see if insert raised exception)")
    except Exception as e:
        print("Audit log test failed:", e)

if __name__ == "__main__":
    asyncio.run(run_db_test())
