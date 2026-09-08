"""Tests for quickbooks_sync rate limiter."""

from django.test import TestCase

from quickbooks_sync.exceptions import RateLimitError
from quickbooks_sync.rate_limiter import PerRealmRateLimiter, RateLimiter


class RateLimiterTest(TestCase):
    """Tests for RateLimiter."""

    def setUp(self):
        self.limiter = RateLimiter(
            max_requests_per_minute=10,
            max_concurrent_requests=5,
        )

    def test_initial_status(self):
        """Test initial rate limiter status."""
        status = self.limiter.get_status()
        self.assertEqual(status["requests_in_window"], 0)
        self.assertEqual(status["concurrent_requests"], 0)

    def test_acquire_success(self):
        """Test successful acquisition."""
        self.limiter.acquire()
        status = self.limiter.get_status()
        self.assertEqual(status["requests_in_window"], 1)

    def test_acquire_concurrent_success(self):
        """Test successful concurrent acquisition."""
        self.limiter.acquire_concurrent()
        status = self.limiter.get_status()
        self.assertEqual(status["concurrent_requests"], 1)

    def test_release_concurrent(self):
        """Test releasing concurrent slot."""
        self.limiter.acquire_concurrent()
        self.limiter.release()
        status = self.limiter.get_status()
        self.assertEqual(status["concurrent_requests"], 0)

    def test_acquire_rate_limit_exceeded(self):
        """Test rate limit exceeded."""
        for _ in range(10):
            self.limiter.acquire()
        with self.assertRaises(RateLimitError):
            self.limiter.acquire()

    def test_acquire_concurrent_limit_exceeded(self):
        """Test concurrent limit exceeded."""
        for _ in range(5):
            self.limiter.acquire_concurrent()
        with self.assertRaises(RateLimitError):
            self.limiter.acquire_concurrent()

    def test_reset(self):
        """Test resetting rate limiter."""
        for _ in range(5):
            self.limiter.acquire()
        self.limiter.reset()
        status = self.limiter.get_status()
        self.assertEqual(status["requests_in_window"], 0)

    def test_wait_for_slot_success(self):
        """Test waiting for slot."""
        self.limiter.wait_for_slot()
        status = self.limiter.get_status()
        self.assertEqual(status["requests_in_window"], 1)

    def test_wait_for_slot_timeout(self):
        """Test waiting for slot with timeout."""
        for _ in range(10):
            self.limiter.acquire()
        with self.assertRaises(RateLimitError):
            self.limiter.wait_for_slot(timeout=0.1)


class PerRealmRateLimiterTest(TestCase):
    """Tests for PerRealmRateLimiter."""

    def setUp(self):
        self.limiter = PerRealmRateLimiter(
            max_requests_per_minute=10,
            max_concurrent_requests=5,
        )

    def test_get_limiter_creates_new(self):
        """Test getting limiter creates new instance."""
        limiter = self.limiter.get_limiter("realm1")
        self.assertIsNotNone(limiter)

    def test_get_limiter_returns_same(self):
        """Test getting limiter returns same instance."""
        limiter1 = self.limiter.get_limiter("realm1")
        limiter2 = self.limiter.get_limiter("realm1")
        self.assertEqual(limiter1, limiter2)

    def test_acquire_per_realm(self):
        """Test acquiring per realm."""
        self.limiter.acquire("realm1")
        status = self.limiter.get_status("realm1")
        self.assertEqual(status["requests_in_window"], 1)

    def test_separate_realms(self):
        """Test separate realms have separate limits."""
        self.limiter.acquire("realm1")
        self.limiter.acquire("realm2")
        status1 = self.limiter.get_status("realm1")
        status2 = self.limiter.get_status("realm2")
        self.assertEqual(status1["requests_in_window"], 1)
        self.assertEqual(status2["requests_in_window"], 1)

    def test_get_all_status(self):
        """Test getting all realms status."""
        self.limiter.acquire("realm1")
        self.limiter.acquire("realm2")
        status = self.limiter.get_status()
        self.assertIn("realms", status)
        self.assertEqual(len(status["realms"]), 2)
