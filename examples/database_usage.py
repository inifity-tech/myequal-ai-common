"""Example usage of the database module.

This example demonstrates:
- Basic CRUD operations with BaseDBManager
- Custom query methods using execute_query()
- Raw SQL execution with execute_raw_sql()
- Bulk operations (create/update)
- Transaction management
- Exception handling
- Database-session-manager-transaction flow
- Both synchronous and asynchronous patterns

Architecture Flow:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Your Service  │    │  Database       │    │  Session        │
│                 │───▶│  Manager        │───▶│  (get_sync_db)  │
│  (FastAPI/etc)  │    │  (TaskManager)  │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │  Transaction    │    │  SQLAlchemy     │
                       │  Context Mgr    │    │  Engine/Pool    │
                       │  (auto commit)  │    │                 │
                       └─────────────────┘    └─────────────────┘
"""

import asyncio
import os

from sqlalchemy import select
from sqlmodel import Field, SQLModel

from myequal_ai_common.database import (
    AsyncBaseDBManager,
    BaseDBManager,
    async_check_database_health,
    check_database_health,
    get_async_db,
    get_sync_db,
)


# Example model
class Task(SQLModel, table=True):
    """Example task model."""

    __tablename__ = "tasks"

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    description: str | None = None
    completed: bool = Field(default=False)
    priority: int = Field(default=0)


# Sync manager
class TaskManager(BaseDBManager[Task]):
    """Task manager for sync operations."""

    @property
    def model_class(self):
        return Task

    def get_incomplete_tasks(self):
        """Get all incomplete tasks."""
        return self.list(filters={"completed": False}, order_by="-priority")

    def complete_task(self, task_id: int) -> Task | None:
        """Mark a task as completed."""
        return self.update(task_id, completed=True)

    def get_tasks_by_priority_range(
        self, min_priority: int, max_priority: int
    ) -> list[Task]:
        """Get tasks within a priority range using custom query."""
        query = (
            select(Task)
            .where(Task.priority >= min_priority, Task.priority <= max_priority)
            .order_by(Task.priority.desc())
        )
        result = self.execute_query(query, operation="get_by_priority_range")
        return list(result.scalars().all())

    def bulk_create_tasks(self, tasks_data: list[dict]) -> list[Task]:
        """Create multiple tasks at once."""
        tasks = [Task(**data) for data in tasks_data]
        return self.bulk_create(tasks)

    def get_task_stats(self) -> dict:
        """Get task statistics using raw SQL."""
        sql = """
            SELECT
                COUNT(*) as total_tasks,
                COUNT(*) FILTER (WHERE completed = true) as completed_tasks,
                AVG(priority) as avg_priority,
                MAX(priority) as max_priority
            FROM tasks
        """
        result = self.execute_raw_sql(sql, operation="task_stats")
        row = result.fetchone()
        return {
            "total_tasks": row[0] or 0,
            "completed_tasks": row[1] or 0,
            "avg_priority": float(row[2] or 0),
            "max_priority": row[3] or 0,
        }


# Async manager
class AsyncTaskManager(AsyncBaseDBManager[Task]):
    """Task manager for async operations."""

    @property
    def model_class(self):
        return Task

    async def get_high_priority_tasks(self, min_priority: int = 5):
        """Get high priority tasks using custom query."""
        query = (
            select(Task)
            .where(Task.priority >= min_priority)
            .order_by(Task.priority.desc())
        )
        result = await self.execute_query(query, operation="get_high_priority")
        return list(result.scalars().all())

    async def bulk_update_completion(self, task_ids: list[int], completed: bool) -> int:
        """Bulk update task completion status using raw SQL."""
        sql = """
            UPDATE tasks
            SET completed = :completed
            WHERE id = ANY(:task_ids)
        """
        result = await self.execute_raw_sql(
            sql,
            {"completed": completed, "task_ids": task_ids},
            operation="bulk_update_completion",
        )
        return result.rowcount

    async def get_task_stats(self) -> dict:
        """Get task statistics using raw SQL."""
        sql = """
            SELECT
                COUNT(*) as total_tasks,
                COUNT(*) FILTER (WHERE completed = true) as completed_tasks,
                AVG(priority) as avg_priority,
                MAX(priority) as max_priority
            FROM tasks
        """
        result = await self.execute_raw_sql(sql, operation="task_stats")
        row = result.fetchone()
        return {
            "total_tasks": row[0] or 0,
            "completed_tasks": row[1] or 0,
            "avg_priority": float(row[2] or 0),
            "max_priority": row[3] or 0,
        }


def sync_example():
    """Example of synchronous database usage with exception handling."""
    print("\n=== Synchronous Example ===")

    # Check database health
    try:
        health = check_database_health()
        print(f"Database health: {health}")
    except Exception as e:
        print(f"Database health check failed: {e}")
        return

    # Use the database with exception handling
    try:
        with get_sync_db() as db:
            manager = TaskManager(db)

            # Create tasks
            task1 = manager.create(
                title="Write documentation",
                description="Create comprehensive docs",
                priority=8,
            )
            print(f"Created task: {task1.title} (ID: {task1.id})")

            task2 = manager.create(
                title="Add tests",
                description="Write unit tests",
                priority=9,
            )
            print(f"Created task: {task2.title} (ID: {task2.id})")

            # List tasks
            all_tasks = manager.list()
            print(f"\nTotal tasks: {len(all_tasks)}")

            # Get incomplete tasks
            incomplete = manager.get_incomplete_tasks()
            print(f"Incomplete tasks: {len(incomplete)}")

            # Complete a task
            if incomplete:
                completed = manager.complete_task(incomplete[0].id)
                print(f"\nCompleted task: {completed.title}")

            # Transaction example - demonstrates automatic rollback on error
            try:
                with manager.transaction():
                    manager.create(title="Task in transaction", priority=10)
                    manager.create(title="Another transaction task", priority=7)
                    print("\nCreated 2 tasks in transaction")
                    # If an error occurred here, both creates would be rolled back
            except Exception as e:
                print(f"Transaction failed and was rolled back: {e}")

            # Count tasks
            total = manager.count()
            completed_count = manager.count(filters={"completed": True})
            print(f"\nTotal tasks: {total}, Completed: {completed_count}")

            # Custom query example - get tasks by priority range
            try:
                mid_priority_tasks = manager.get_tasks_by_priority_range(5, 8)
                print(f"\nTasks with priority 5-8: {len(mid_priority_tasks)}")
                for task in mid_priority_tasks:
                    print(f"  - {task.title} (priority: {task.priority})")
            except Exception as e:
                print(f"Custom query failed: {e}")

            # Bulk create example with error handling
            try:
                bulk_tasks_data = [
                    {"title": f"Bulk task {i}", "priority": i * 2} for i in range(1, 4)
                ]
                bulk_tasks = manager.bulk_create_tasks(bulk_tasks_data)
                print(f"\nCreated {len(bulk_tasks)} tasks in bulk")
            except Exception as e:
                print(f"Bulk create failed: {e}")

            # NEW: Update by field example - update task by title
            try:
                updated_task = manager.update_by(
                    {"title": "Write documentation"},
                    description="Updated: Create comprehensive documentation with examples",
                    priority=10
                )
                if updated_task:
                    print(f"\nUpdated task by title: {updated_task.title} (priority: {updated_task.priority})")
            except Exception as e:
                print(f"Update by title failed: {e}")

            # NEW: Update all by field example - mark all high priority tasks as completed
            try:
                updated_count = manager.update_all_by(
                    {"priority": 9},
                    completed=True
                )
                print(f"Marked {updated_count} high priority tasks as completed")
            except Exception as e:
                print(f"Update all by priority failed: {e}")

            # NEW: Delete by field example - delete a specific task by title
            try:
                deleted = manager.delete_by(title="Bulk task 1")
                print(f"Deleted task by title: {deleted}")
            except Exception as e:
                print(f"Delete by title failed: {e}")

            # NEW: Delete all by field example - delete all completed low priority tasks
            try:
                deleted_count = manager.delete_all_by(completed=True, priority=2)
                print(f"Deleted {deleted_count} completed low priority tasks")
            except Exception as e:
                print(f"Delete all by filters failed: {e}")

            # Get statistics using raw SQL with error handling
            try:
                stats = manager.get_task_stats()
                print("\nTask Statistics:")
                print(f"  Total: {stats['total_tasks']}")
                print(f"  Completed: {stats['completed_tasks']}")
                print(f"  Average Priority: {stats['avg_priority']:.2f}")
                print(f"  Max Priority: {stats['max_priority']}")
            except Exception as e:
                print(f"Statistics query failed: {e}")

    except Exception as e:
        print(f"Database operation failed: {e}")
        print(
            "This could be due to connection issues, query errors, or constraint violations"
        )


async def async_example():
    """Example of asynchronous database usage."""
    print("\n=== Asynchronous Example ===")

    # Check database health
    health = await async_check_database_health()
    print(f"Database health: {health}")

    # Use the database
    async with get_async_db() as db:
        manager = AsyncTaskManager(db)

        # Create tasks
        task1 = await manager.create(
            title="Async task 1",
            description="First async task",
            priority=6,
        )
        print(f"Created async task: {task1.title}")

        task2 = await manager.create(
            title="Async task 2",
            description="Second async task",
            priority=10,
        )
        print(f"Created async task: {task2.title}")

        # Get high priority tasks
        high_priority = await manager.get_high_priority_tasks(min_priority=8)
        print(f"\nHigh priority tasks: {len(high_priority)}")
        for task in high_priority:
            print(f"  - {task.title} (priority: {task.priority})")

        # Bulk operations
        async with manager.transaction():
            tasks = []
            for i in range(5):
                task = await manager.create(
                    title=f"Bulk task {i}",
                    priority=i,
                )
                tasks.append(task)
            print(f"\nCreated {len(tasks)} tasks in bulk")

        # Bulk update example
        task_ids = [t.id for t in tasks[:3]]
        updated_count = await manager.bulk_update_completion(task_ids, completed=True)
        print(f"\nBulk updated {updated_count} tasks to completed")

        # NEW: Async update by field example - update task by title
        updated_task = await manager.update_by(
            {"title": "Async task 1"},
            description="Updated async description",
            priority=8
        )
        if updated_task:
            print(f"\nAsync: Updated task by title: {updated_task.title}")

        # NEW: Async update all by field example
        updated_count = await manager.update_all_by(
            {"completed": False, "priority": 0},
            priority=1
        )
        print(f"Async: Updated {updated_count} tasks to priority 1")

        # NEW: Async delete by field example
        deleted = await manager.delete_by(title="Bulk task 4")
        print(f"Async: Deleted task by title: {deleted}")

        # NEW: Async delete all by field example
        deleted_count = await manager.delete_all_by(priority=0)
        print(f"Async: Deleted {deleted_count} tasks with priority 0")

        # Get statistics using raw SQL
        stats = await manager.get_task_stats()
        print("\nAsync Task Statistics:")
        print(f"  Total: {stats['total_tasks']}")
        print(f"  Completed: {stats['completed_tasks']}")
        print(f"  Average Priority: {stats['avg_priority']:.2f}")
        print(f"  Max Priority: {stats['max_priority']}")


def main():
    """Run examples."""
    # Set up environment (in real usage, these come from .env or environment)
    os.environ["DATABASE_URL"] = (
        "postgresql://postgres:postgres@localhost:5432/example_db"
    )
    os.environ["DATABASE_SERVICE_NAME"] = "example-service"
    os.environ["DATABASE_ENVIRONMENT"] = "development"

    print("MyEqual AI Common - Database Module Example")
    print("=" * 50)

    # Note: In a real application, you would need to ensure the database
    # and tables exist before running these examples

    try:
        # Run sync example
        sync_example()

        # Run async example
        asyncio.run(async_example())

    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure PostgreSQL is running and the database exists.")
        print("You may need to create the tables first using Alembic migrations.")
    print("\nCommon database exception types:")
    print("- DatabaseError: Base database exception")
    print("- ConnectionError: Database connection issues")
    print("- RecordNotFoundError: Entity not found")
    print("- DuplicateRecordError: Unique constraint violations")
    print("- TransactionError: Transaction management issues")
    print("- ValidationError: Data validation failures")


if __name__ == "__main__":
    main()
