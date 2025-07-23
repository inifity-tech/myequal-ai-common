"""Example demonstrating session_id-based operations with the enhanced DB manager.

This example shows how to use the new update_by and delete_by methods
to work with records using fields other than the primary key ID.
"""

import asyncio
from datetime import datetime
from sqlmodel import Field, SQLModel

from myequal_ai_common.database import AsyncBaseDBManager, get_async_db


# Example model with session_id
class CallSession(SQLModel, table=True):
    """Call session model with session_id as a unique identifier."""

    __tablename__ = "call_sessions"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(index=True, unique=True)  # Unique session identifier
    user_id: int = Field(index=True)
    status: str = Field(default="pending")
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_seconds: int | None = None
    summary: str | None = None


class CallSessionManager(AsyncBaseDBManager[CallSession]):
    """Manager for call sessions with session_id operations."""

    @property
    def model_class(self):
        return CallSession

    async def start_session(self, session_id: str) -> CallSession | None:
        """Start a call session by updating its status and start time."""
        return await self.update_by(
            {"session_id": session_id},
            status="active",
            start_time=datetime.now()
        )

    async def complete_session(self, session_id: str, summary: str) -> CallSession | None:
        """Complete a call session with summary and duration calculation."""
        # First get the session to calculate duration
        session = await self.get_by(session_id=session_id)
        if not session or not session.start_time:
            return None

        end_time = datetime.now()
        duration = int((end_time - session.start_time).total_seconds())

        return await self.update_by(
            {"session_id": session_id},
            status="completed",
            end_time=end_time,
            duration_seconds=duration,
            summary=summary
        )

    async def fail_session(self, session_id: str, reason: str) -> CallSession | None:
        """Mark a session as failed."""
        return await self.update_by(
            {"session_id": session_id},
            status="failed",
            end_time=datetime.now(),
            summary=f"Failed: {reason}"
        )

    async def cleanup_abandoned_sessions(self, user_id: int) -> int:
        """Clean up all abandoned sessions for a user."""
        return await self.update_all_by(
            {"user_id": user_id, "status": "pending"},
            status="abandoned"
        )

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session by session_id."""
        return await self.delete_by(session_id=session_id)

    async def delete_user_sessions(self, user_id: int) -> int:
        """Delete all sessions for a user."""
        return await self.delete_all_by(user_id=user_id)


async def session_example():
    """Demonstrate session_id-based operations."""
    print("=== Session ID Example ===\n")

    async with get_async_db() as db:
        manager = CallSessionManager(db)

        # Create some sessions
        sessions = []
        for i in range(3):
            session = await manager.create(
                session_id=f"ses_{i}_{datetime.now().timestamp()}",
                user_id=100,
                status="pending"
            )
            sessions.append(session)
            print(f"Created session: {session.session_id}")

        # Start a session using session_id
        started = await manager.start_session(sessions[0].session_id)
        if started:
            print(f"\nStarted session: {started.session_id} at {started.start_time}")

        # Wait a bit to simulate call duration
        await asyncio.sleep(1)

        # Complete the session
        completed = await manager.complete_session(
            sessions[0].session_id,
            "Call completed successfully. Discussed product features."
        )
        if completed:
            print(f"Completed session: {completed.session_id}")
            print(f"  Duration: {completed.duration_seconds} seconds")
            print(f"  Summary: {completed.summary}")

        # Fail another session
        failed = await manager.fail_session(
            sessions[1].session_id,
            "Network connection lost"
        )
        if failed:
            print(f"\nFailed session: {failed.session_id}")
            print(f"  Reason: {failed.summary}")

        # Clean up abandoned sessions
        cleaned = await manager.cleanup_abandoned_sessions(user_id=100)
        print(f"\nCleaned up {cleaned} abandoned sessions")

        # Get session by session_id (using existing get_by)
        session = await manager.get_by(session_id=sessions[0].session_id)
        if session:
            print(f"\nRetrieved session: {session.session_id}")
            print(f"  Status: {session.status}")
            print(f"  Duration: {session.duration_seconds} seconds")

        # Delete a specific session
        deleted = await manager.delete_session(sessions[2].session_id)
        print(f"\nDeleted session by session_id: {deleted}")

        # Count remaining sessions
        remaining = await manager.count(filters={"user_id": 100})
        print(f"Remaining sessions for user 100: {remaining}")


if __name__ == "__main__":
    # This example requires a database with the call_sessions table
    # You would typically create this via Alembic migrations
    asyncio.run(session_example())