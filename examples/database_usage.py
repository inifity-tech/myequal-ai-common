"""Example usage of the database module."""

import asyncio
import os
from typing import Optional

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

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    description: Optional[str] = None
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

    def complete_task(self, task_id: int) -> Optional[Task]:
        """Mark a task as completed."""
        return self.update(task_id, completed=True)


# Async manager
class AsyncTaskManager(AsyncBaseDBManager[Task]):
    """Task manager for async operations."""

    @property
    def model_class(self):
        return Task

    async def get_high_priority_tasks(self, min_priority: int = 5):
        """Get high priority tasks."""
        tasks = await self.list(order_by="-priority")
        return [t for t in tasks if t.priority >= min_priority]


def sync_example():
    """Example of synchronous database usage."""
    print("\n=== Synchronous Example ===")

    # Check database health
    health = check_database_health()
    print(f"Database health: {health}")

    # Use the database
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

        # Transaction example
        with manager.transaction():
            task3 = manager.create(title="Task in transaction", priority=10)
            task4 = manager.create(title="Another transaction task", priority=7)
            print("\nCreated 2 tasks in transaction")

        # Count tasks
        total = manager.count()
        completed_count = manager.count(filters={"completed": True})
        print(f"\nTotal tasks: {total}, Completed: {completed_count}")


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


if __name__ == "__main__":
    main()