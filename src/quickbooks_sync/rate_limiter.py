"""Rate limiter for QuickBooks API."""

import time
from collections import deque
from threading import Lock
from typing import Optional

from quickbooks_sync.exceptions import RateLimitError
from quickbooks_sync.settings import qbs_settings


class RateLimiter:
    """
    Rate limiter for QuickBooks Online API.

    QuickBooks has the following rate limits:
    - 500 requests per minute per realm
    - 10 concurrent requests per second per realm

    This class implements both limits using a token bucket algorithm.
    """

    def __init__(
        self,
        max_requests_per_minute: Optional[int] = None,
        max_concurrent_requests: Optional[int] = None,
    ):
        """
        Initialize the rate limiter.

        Args:
            max_requests_per_minute: Maximum requests per minute
            max_concurrent_requests: Maximum concurrent requests per second
        """
        self.max_requests_per_minute = (
            max_requests_per_minute or qbs_settings.MAX_REQUESTS_PER_MINUTE
        )
        self.max_concurrent_requests = (
            max_concurrent_requests or qbs_settings.MAX_CONCURRENT_REQUESTS
        )

        # Request timestamps for per-minute limiting
        self._request_times: deque = deque()
        self._lock = Lock()

        # Concurrent request tracking
        self._concurrent_requests: int = 0
        self._concurrent_lock = Lock()

    def _cleanup_old_requests(self) -> None:
        """Remove requests older than 1 minute from the queue."""
        now = time.time()
        cutoff = now - 60

        while self._request_times and self._request_times[0] < cutoff:
            self._request_times.popleft()

    def acquire(self) -> None:
        """
        Acquire permission to make a request.

        Raises:
            RateLimitError: If rate limit would be exceeded
        """
        with self._lock:
            self._cleanup_old_requests()

            if len(self._request_times) >= self.max_requests_per_minute:
                # Calculate wait time until oldest request expires
                oldest = self._request_times[0]
                wait_time = 60 - (time.time() - oldest)
                raise RateLimitError(
                    retry_after=int(wait_time) + 1,
                )

            self._request_times.append(time.time())

    def release(self) -> None:
        """Release a concurrent request slot."""
        with self._concurrent_lock:
            if self._concurrent_requests > 0:
                self._concurrent_requests -= 1

    def acquire_concurrent(self) -> None:
        """
        Acquire a concurrent request slot.

        Raises:
            RateLimitError: If concurrent limit would be exceeded
        """
        with self._concurrent_lock:
            if self._concurrent_requests >= self.max_concurrent_requests:
                raise RateLimitError(
                    retry_after=1,
                )
            self._concurrent_requests += 1

    def wait_for_slot(self, timeout: float = 30.0) -> None:
        """
        Wait for an available slot.

        Args:
            timeout: Maximum time to wait in seconds

        Raises:
            RateLimitError: If timeout exceeded
        """
        start_time = time.time()

        while True:
            try:
                self.acquire()
                self.acquire_concurrent()
                return
            except RateLimitError:
                if time.time() - start_time >= timeout:
                    raise RateLimitError(
                        retry_after=int(timeout),
                    )
                time.sleep(0.1)

    def get_status(self) -> dict:
        """
        Get current rate limiter status.

        Returns:
            Dictionary with current status
        """
        with self._lock:
            self._cleanup_old_requests()

        return {
            "requests_in_window": len(self._request_times),
            "max_requests_per_minute": self.max_requests_per_minute,
            "concurrent_requests": self._concurrent_requests,
            "max_concurrent_requests": self.max_concurrent_requests,
        }

    def reset(self) -> None:
        """Reset the rate limiter state."""
        with self._lock:
            self._request_times.clear()

        with self._concurrent_lock:
            self._concurrent_requests = 0


class PerRealmRateLimiter:
    """
    Rate limiter that tracks limits per realm.

    Useful when working with multiple QuickBooks companies.
    """

    def __init__(
        self,
        max_requests_per_minute: Optional[int] = None,
        max_concurrent_requests: Optional[int] = None,
    ):
        self.max_requests_per_minute = (
            max_requests_per_minute or qbs_settings.MAX_REQUESTS_PER_MINUTE
        )
        self.max_concurrent_requests = (
            max_concurrent_requests or qbs_settings.MAX_CONCURRENT_REQUESTS
        )
        self._limiters: dict[str, RateLimiter] = {}
        self._lock = Lock()

    def get_limiter(self, realm_id: str) -> RateLimiter:
        """Get or create a rate limiter for a specific realm."""
        with self._lock:
            if realm_id not in self._limiters:
                self._limiters[realm_id] = RateLimiter(
                    self.max_requests_per_minute,
                    self.max_concurrent_requests,
                )
            return self._limiters[realm_id]

    def acquire(self, realm_id: str) -> None:
        """Acquire permission for a specific realm."""
        limiter = self.get_limiter(realm_id)
        limiter.acquire()

    def release(self, realm_id: str) -> None:
        """Release a concurrent slot for a specific realm."""
        limiter = self.get_limiter(realm_id)
        limiter.release()

    def acquire_concurrent(self, realm_id: str) -> None:
        """Acquire a concurrent slot for a specific realm."""
        limiter = self.get_limiter(realm_id)
        limiter.acquire_concurrent()

    def get_status(self, realm_id: Optional[str] = None) -> dict:
        """
        Get rate limiter status.

        Args:
            realm_id: If provided, return status for specific realm

        Returns:
            Dictionary with status information
        """
        if realm_id:
            limiter = self.get_limiter(realm_id)
            return {"realm_id": realm_id, **limiter.get_status()}

        # Return status for all realms
        with self._lock:
            return {
                "realms": {
                    rid: limiter.get_status()
                    for rid, limiter in self._limiters.items()
                }
            }


# Global rate limiter instances
rate_limiter = RateLimiter()
per_realm_rate_limiter = PerRealmRateLimiter()
