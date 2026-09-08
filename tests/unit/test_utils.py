"""Tests for quickbooks_sync utils."""

from datetime import datetime, timezone

from django.test import TestCase
from django.utils import timezone as django_timezone

from quickbooks_sync.utils import (
    calculate_token_expiry,
    chunk_list,
    format_qbo_datetime,
    generate_idempotency_key,
    generate_request_id,
    is_token_expired,
    mask_sensitive_data,
    parse_qbo_datetime,
    safe_json_dumps,
    truncate_string,
    verify_webhook_signature,
)


class UtilsTest(TestCase):
    """Tests for utility functions."""

    def test_generate_idempotency_key(self):
        """Test idempotency key generation."""
        key = generate_idempotency_key("Customer", "123", "create")
        self.assertIsInstance(key, str)
        self.assertEqual(len(key), 64)

    def test_generate_idempotency_key_deterministic(self):
        """Test key generation is deterministic."""
        key1 = generate_idempotency_key("Customer", "123", "create")
        key2 = generate_idempotency_key("Customer", "123", "create")
        self.assertEqual(key1, key2)

    def test_generate_request_id(self):
        """Test request ID generation."""
        request_id = generate_request_id()
        self.assertIsInstance(request_id, str)
        self.assertEqual(len(request_id), 36)  # UUID format

    def test_parse_qbo_datetime(self):
        """Test QBO datetime parsing."""
        dt = parse_qbo_datetime("2024-01-15T10:30:00Z")
        self.assertEqual(dt.year, 2024)
        self.assertEqual(dt.month, 1)
        self.assertEqual(dt.day, 15)

    def test_parse_qbo_datetime_with_offset(self):
        """Test QBO datetime parsing with timezone offset."""
        dt = parse_qbo_datetime("2024-01-15T10:30:00+00:00")
        self.assertEqual(dt.year, 2024)

    def test_format_qbo_datetime(self):
        """Test QBO datetime formatting."""
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        formatted = format_qbo_datetime(dt)
        self.assertIn("2024", formatted)
        self.assertIn("01", formatted)

    def test_calculate_token_expiry(self):
        """Test token expiry calculation."""
        expiry = calculate_token_expiry(3600)
        self.assertIsNotNone(expiry)

    def test_is_token_expired_true(self):
        """Test token expiry check (expired)."""
        expired_time = django_timezone.now() - django_timezone.timedelta(hours=1)
        self.assertTrue(is_token_expired(expired_time))

    def test_is_token_expired_false(self):
        """Test token expiry check (not expired)."""
        future_time = django_timezone.now() + django_timezone.timedelta(hours=1)
        self.assertFalse(is_token_expired(future_time))

    def test_is_token_expired_none(self):
        """Test token expiry check with None."""
        self.assertTrue(is_token_expired(None))

    def test_verify_webhook_signature_valid(self):
        """Test valid webhook signature verification."""
        payload = "test_payload"
        secret = "test_secret"
        import hashlib
        import hmac

        expected = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        self.assertTrue(verify_webhook_signature(payload, expected, secret))

    def test_verify_webhook_signature_invalid(self):
        """Test invalid webhook signature verification."""
        self.assertFalse(
            verify_webhook_signature("test_payload", "invalid_signature", "test_secret")
        )

    def test_mask_sensitive_data(self):
        """Test sensitive data masking."""
        masked = mask_sensitive_data("1234567890", visible_chars=4)
        self.assertEqual(masked, "******7890")

    def test_mask_sensitive_data_short(self):
        """Test masking short data."""
        masked = mask_sensitive_data("1234", visible_chars=4)
        self.assertEqual(masked, "1234")

    def test_chunk_list(self):
        """Test list chunking."""
        lst = [1, 2, 3, 4, 5]
        chunks = chunk_list(lst, 2)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0], [1, 2])
        self.assertEqual(chunks[1], [3, 4])
        self.assertEqual(chunks[2], [5])

    def test_safe_json_dumps(self):
        """Test safe JSON dumps."""
        import json

        data = {"key": "value", "number": 123}
        result = safe_json_dumps(data)
        parsed = json.loads(result)
        self.assertEqual(parsed["key"], "value")

    def test_safe_json_dumps_with_datetime(self):
        """Test safe JSON dumps with datetime."""
        data = {"timestamp": datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)}
        result = safe_json_dumps(data)
        self.assertIn("2024", result)

    def test_truncate_string(self):
        """Test string truncation."""
        result = truncate_string("Hello World", max_length=5)
        self.assertEqual(result, "He...")

    def test_truncate_string_no_truncation(self):
        """Test string truncation when not needed."""
        result = truncate_string("Hi", max_length=10)
        self.assertEqual(result, "Hi")
