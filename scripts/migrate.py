import argparse
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from db.database import get_pool, close_db
from db import migrate

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def cmd_up(_args: argparse.Namespace) -> None:
    pool = await get_pool()
    await migrate.auto_baseline_if_needed(pool)
    versions = await migrate.run_all(pool)
    if versions:
        print(f"Applied {len(versions)} migration(s): {', '.join(f'{v:03d}' for v in versions)}")
    else:
        print("No pending migrations")


async def cmd_down(args: argparse.Namespace) -> None:
    pool = await get_pool()
    steps = args.steps
    versions = await migrate.rollback(pool, steps=steps)
    if versions:
        print(f"Rolled back {len(versions)} migration(s): {', '.join(f'{v:03d}' for v in versions)}")
    else:
        print("Nothing to rollback")


async def cmd_status(_args: argparse.Namespace) -> None:
    pool = await get_pool()
    rows = await migrate.status(pool)
    print(f"{'Version':<8} {'Applied':<8}  Name")
    print("-" * 50)
    for r in rows:
        status = "YES" if r["applied"] else "no"
        print(f"{r['version']:03d}      {status:<8}  {r['name']}")


async def cmd_new(args: argparse.Namespace) -> None:
    fpath = migrate.create_migration(args.description)
    print(f"Created: {fpath}")


async def cmd_baseline(_args: argparse.Namespace) -> None:
    pool = await get_pool()
    versions = await migrate.baseline(pool)
    if versions:
        print(f"Baselined {len(versions)} migration(s): {', '.join(f'{v:03d}' for v in versions)}")
    else:
        print("All migrations already baselined")


async def run(args: argparse.Namespace) -> None:
    try:
        if args.command == "up":
            await cmd_up(args)
        elif args.command in ("down", "rollback"):
            await cmd_down(args)
        elif args.command == "status":
            await cmd_status(args)
        elif args.command == "new":
            await cmd_new(args)
        elif args.command == "baseline":
            await cmd_baseline(args)
    finally:
        await close_db()


def main() -> None:
    parser = argparse.ArgumentParser(description="Migration management CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_up = sub.add_parser("up", help="Apply all pending migrations")
    p_up.set_defaults(func=cmd_up)

    p_down = sub.add_parser("down", aliases=["rollback"], help="Rollback last N migrations")
    p_down.add_argument("steps", nargs="?", type=int, default=1, help="Number of migrations to rollback (default: 1)")
    p_down.set_defaults(func=cmd_down)

    p_status = sub.add_parser("status", help="Show migration status")
    p_status.set_defaults(func=cmd_status)

    p_new = sub.add_parser("new", help="Create a new migration file")
    p_new.add_argument("description", help="Short description of the migration")
    p_new.set_defaults(func=cmd_new)

    p_baseline = sub.add_parser("baseline", help="Mark all migrations as applied without executing")
    p_baseline.set_defaults(func=cmd_baseline)

    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
