import threading
from typing import Dict, Optional
from .service import EntitlementService, QuotaDecision


class InMemoryQuotaService(EntitlementService):
    """Thread-safe in-memory quota tracking implementation.
    
    Enforces the freemium business rule:
    - Every user gets 3 free questions.
    - Subsequent questions require a paid subscription or are blocked with HTTP 402.
    """

    def __init__(self, free_questions_limit: int = 3, enforce: bool = True):
        self.free_questions_limit = free_questions_limit
        self.enforce = enforce
        self._usage: Dict[str, int] = {}
        self._active_reservations: Dict[str, int] = {}
        self._lock = threading.Lock()

    async def check_access(self, user_id: str, entitlement_token: Optional[str] = None) -> QuotaDecision:
        if not self.enforce:
            return QuotaDecision(
                allowed=True,
                remaining_free_questions=self.free_questions_limit,
                is_subscribed=True,
            )

        with self._lock:
            used = self._usage.get(user_id, 0)
            reserved = self._active_reservations.get(user_id, 0)
            remaining = max(0, self.free_questions_limit - (used + reserved))

            if remaining > 0:
                return QuotaDecision(
                    allowed=True,
                    remaining_free_questions=remaining,
                    is_subscribed=False,
                )
            else:
                return QuotaDecision(
                    allowed=False,
                    remaining_free_questions=0,
                    is_subscribed=False,
                    rejection_code="QUOTA_EXCEEDED",
                    rejection_message="თქვენ ამოწურეთ 3 უფასო შეკითხვა. მასხარასთან საუბრის გასაგრძელებლად საჭიროა წვდომის განახლება.",
                )

    async def reserve_quota(self, user_id: str, entitlement_token: Optional[str] = None) -> QuotaDecision:
        """Atomically reserves one question turn if quota is available."""
        if not self.enforce:
            return QuotaDecision(
                allowed=True,
                remaining_free_questions=self.free_questions_limit,
                is_subscribed=True,
            )

        with self._lock:
            used = self._usage.get(user_id, 0)
            reserved = self._active_reservations.get(user_id, 0)
            available = self.free_questions_limit - (used + reserved)

            if available > 0:
                self._active_reservations[user_id] = reserved + 1
                remaining_after = max(0, available - 1)
                return QuotaDecision(
                    allowed=True,
                    remaining_free_questions=remaining_after,
                    is_subscribed=False,
                )
            else:
                return QuotaDecision(
                    allowed=False,
                    remaining_free_questions=0,
                    is_subscribed=False,
                    rejection_code="QUOTA_EXCEEDED",
                    rejection_message="თქვენ ამოწურეთ 3 უფასო შეკითხვა. მასხარასთან საუბრის გასაგრძელებლად საჭიროა წვდომის განახლება.",
                )

    async def commit_quota(self, user_id: str) -> None:
        """Finalizes consumption: decrements active reservation and increments permanent usage."""
        if not self.enforce:
            return
        with self._lock:
            active = self._active_reservations.get(user_id, 0)
            if active > 0:
                self._active_reservations[user_id] = active - 1
            self._usage[user_id] = self._usage.get(user_id, 0) + 1

    async def release_quota(self, user_id: str) -> None:
        """Releases an active reservation on inference failure without consuming quota."""
        if not self.enforce:
            return
        with self._lock:
            active = self._active_reservations.get(user_id, 0)
            if active > 0:
                self._active_reservations[user_id] = active - 1

    async def consume_quota(self, user_id: str) -> None:
        """Directly records one consumed question turn (backward compatibility)."""
        if not self.enforce:
            return
        with self._lock:
            self._usage[user_id] = self._usage.get(user_id, 0) + 1

    def get_usage(self, user_id: str) -> int:
        with self._lock:
            return self._usage.get(user_id, 0)

    def get_active_reservations(self, user_id: str) -> int:
        with self._lock:
            return self._active_reservations.get(user_id, 0)

    def set_usage(self, user_id: str, count: int) -> None:
        """Utility for test setups."""
        with self._lock:
            self._usage[user_id] = count

    def reset(self, user_id: Optional[str] = None) -> None:
        """Resets quota and active reservations for a specific user or clears all users."""
        with self._lock:
            if user_id:
                self._usage.pop(user_id, None)
                self._active_reservations.pop(user_id, None)
            else:
                self._usage.clear()
                self._active_reservations.clear()
