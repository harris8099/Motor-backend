"""
Test script for the fault management system.
Creates sample faults for testing the UI and resolution workflow.

Usage:
    python scripts/test_faults.py
    python scripts/test_faults.py --device esp32-001 --fault overtemp
    python scripts/test_faults.py --list-faults
    python scripts/test_faults.py --resolve 123 --technician "John Doe"


## Create a Single Fault
```bash
cd "c:\Users\TUF\Desktop\Main project\AI ml backend"
python scripts\test_faults.py --device esp32-001 --fault overtemp --severity critical
```

## Create Multiple Sample Faults
```bash
python scripts\test_faults.py --sample
```
This creates 5 faults across different devices (critical, warning, info).

## List Active Faults
```bash
python scripts\test_faults.py --list-faults
```

## Resolve a Fault
```bash
python scripts\test_faults.py --resolve 1 --technician "John Doe"
```

## Clear All Faults
```bash
python scripts\test_faults.py --clear
```

---

## Quick Test Workflow

1. **Create sample faults:**
   ```bash
   python scripts\test_faults.py --sample
   ```

2. **Open frontend** → See red banner + device indicators

3. **Click "View & Resolve"** → Test resolution form

4. **Resolve a fault:**
   ```bash
   python scripts\test_faults.py --resolve 1 --technician "Your Name"
   ```

5. **Check history** → Filter to "resolved" to see past faults
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import engine, settings


async def create_test_fault(device_id: str, fault_type: str, severity: str = "critical"):
    """Create a test fault for a device."""
    async with engine.begin() as conn:
        # Check if device exists, create if not
        await conn.execute(text("""
            INSERT INTO devices (id, name, is_active, created_at, updated_at, last_seen_at)
            VALUES (:device_id, :device_id, TRUE, NOW(), NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """), {"device_id": device_id})
        
        # Create the fault
        result = await conn.execute(text("""
            INSERT INTO fault_logs (device_id, fault_type, severity, status, message)
            VALUES (:device_id, :fault_type, :severity, 'active', :message)
            RETURNING id
        """), {
            "device_id": device_id,
            "fault_type": fault_type,
            "severity": severity,
            "message": f"Test fault: {fault_type} detected on {device_id}"
        })
        fault_id = result.scalar()
        print(f"✓ Created fault ID {fault_id}: {fault_type} ({severity}) on {device_id}")
        return fault_id


async def list_active_faults():
    """List all active faults."""
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT f.id, f.device_id, d.name as device_name, f.fault_type, 
                   f.severity, f.status, f.detected_at
            FROM fault_logs f
            LEFT JOIN devices d ON f.device_id = d.id
            WHERE f.status = 'active'
            ORDER BY 
                CASE f.severity WHEN 'critical' THEN 1 WHEN 'warning' THEN 2 ELSE 3 END,
                f.detected_at DESC
        """))
        rows = result.mappings().all()
        
        if not rows:
            print("No active faults found.")
            return
        
        print(f"\n{'ID':<6} {'Device':<15} {'Fault Type':<20} {'Severity':<10} {'Detected At'}")
        print("-" * 80)
        for row in rows:
            device = row["device_name"] or row["device_id"]
            print(f"{row['id']:<6} {device:<15} {row['fault_type']:<20} {row['severity']:<10} {row['detected_at']}")
        print(f"\nTotal active faults: {len(rows)}")


async def resolve_fault(fault_id: int, technician: str, actions: str = "Test resolution"):
    """Resolve a fault with test data."""
    async with engine.begin() as conn:
        # Check if fault exists and is active
        check = await conn.execute(text("""
            SELECT status FROM fault_logs WHERE id = :fault_id
        """), {"fault_id": fault_id})
        row = check.mappings().first()
        
        if not row:
            print(f"✗ Fault {fault_id} not found")
            return False
        if row["status"] == "resolved":
            print(f"✗ Fault {fault_id} is already resolved")
            return False
        
        # Resolve the fault
        await conn.execute(text("""
            UPDATE fault_logs SET
                status = 'resolved',
                resolved_at = NOW(),
                resolved_by = :technician,
                root_cause = 'mechanical_failure',
                actions_taken = :actions,
                parts_replaced = 'Test parts',
                resolution_notes = 'Resolved via test script'
            WHERE id = :fault_id
        """), {"fault_id": fault_id, "technician": technician, "actions": actions})
        
        print(f"✓ Resolved fault {fault_id} by {technician}")
        return True


async def clear_all_faults():
    """Delete all fault records (use with caution)."""
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            DELETE FROM fault_logs RETURNING id
        """))
        deleted = result.scalars().all()
        print(f"✓ Deleted {len(deleted)} fault records")


async def create_sample_faults():
    """Create a variety of test faults for demo purposes."""
    test_cases = [
        ("esp32-001", "overtemp", "critical"),
        ("esp32-001", "vibration", "warning"),
        ("esp32-002", "overcurrent", "critical"),
        ("esp32-003", "stall", "critical"),
        ("esp32-003", "maintenance_due", "info"),
    ]
    
    print("Creating sample faults...")
    for device_id, fault_type, severity in test_cases:
        await create_test_fault(device_id, fault_type, severity)
    print("\nDone! Check the UI for the fault banner and indicators.")


async def main():
    parser = argparse.ArgumentParser(description="Test fault management system")
    parser.add_argument("--device", default="esp32-001", help="Device ID")
    parser.add_argument("--fault", default="overtemp", 
                       choices=["overtemp", "overcurrent", "stall", "vibration", 
                               "overvoltage", "undervoltage", "maintenance_due"],
                       help="Fault type to create")
    parser.add_argument("--severity", default="critical",
                       choices=["critical", "warning", "info"],
                       help="Fault severity")
    parser.add_argument("--list-faults", action="store_true", help="List all active faults")
    parser.add_argument("--resolve", type=int, help="Resolve a fault by ID")
    parser.add_argument("--technician", default="Test Technician", help="Name of technician resolving")
    parser.add_argument("--sample", action="store_true", help="Create multiple sample faults")
    parser.add_argument("--clear", action="store_true", help="Delete all faults (DANGER)")
    
    args = parser.parse_args()
    
    if args.clear:
        confirm = input("Are you sure you want to delete ALL faults? Type 'yes': ")
        if confirm == "yes":
            await clear_all_faults()
        else:
            print("Cancelled")
    elif args.list_faults:
        await list_active_faults()
    elif args.resolve:
        await resolve_fault(args.resolve, args.technician)
    elif args.sample:
        await create_sample_faults()
    else:
        # Default: create single fault
        await create_test_fault(args.device, args.fault, args.severity)
        print("\nRefresh the frontend to see the fault banner and indicators!")


if __name__ == "__main__":
    asyncio.run(main())
