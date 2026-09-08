# Software Requirements Specification (SRS)

## django-quickbooks-sync

**Version:** 0.1.0  
**Date:** August 2026  
**Author:** Md Mojno M.

---

## 1. Introduction

### 1.1 Purpose

This document specifies the requirements for `django-quickbooks-sync`, a production-grade Django application that provides bidirectional synchronization between Django applications and QuickBooks Online.

### 1.2 Scope

The system enables Django developers to:
- Integrate QuickBooks Online accounting data into their applications
- Synchronize entities bidirectionally (Django ↔ QuickBooks)
- Handle OAuth 2.0 authentication and token management
- Process webhook events for real-time synchronization
- Maintain audit trails for all synchronization operations

### 1.3 Definitions

| Term | Definition |
|------|------------|
| QBO | QuickBooks Online |
| OAuth | Open Authorization protocol |
| Sync | Synchronization of data between systems |
| Realm | QuickBooks company/account identifier |
| Entity | A QuickBooks object (Customer, Invoice, etc.) |

---

## 2. Overall Description

### 2.1 Product Perspective

`django-quickbooks-sync` is a reusable Django application that extends existing Django projects with QuickBooks Online integration capabilities. It builds upon the `python-quickbooks` library to provide Django-specific features including models, admin interface, Celery tasks, and management commands.

### 2.2 Product Functions

1. **OAuth 2.0 Management**
   - Secure token storage
   - Automatic token refresh
   - Multi-realm support

2. **Bidirectional Sync**
   - Push local changes to QuickBooks
   - Pull changes from QuickBooks
   - Change Data Capture (CDC) support

3. **Async Processing**
   - Celery task queue integration
   - Background synchronization
   - Retry logic with exponential backoff

4. **Rate Limiting**
   - Token bucket algorithm
   - Per-realm rate tracking
   - Automatic retry on limits

5. **Idempotency**
   - Duplicate operation prevention
   - Deterministic key generation
   - Configurable key validity

6. **Audit Logging**
   - Complete operation history
   - User attribution
   - Export capability

7. **Webhook Processing**
   - Real-time event handling
   - Signature verification
   - Event queuing and processing

### 2.3 User Classes

| User | Description |
|------|-------------|
| Developer | Integrates the package into Django projects |
| End User | Uses the integrated application |
| Administrator | Manages QuickBooks connections and sync operations |

### 2.4 Operating Environment

- Python 3.10+
- Django 4.2+ LTS
- PostgreSQL (recommended) or SQLite (development)
- Redis (for Celery)
- RabbitMQ or Redis (as Celery broker)

---

## 3. Functional Requirements

### 3.1 OAuth Management

#### FR-01: Token Storage
- **Description:** Store OAuth tokens securely for each QuickBooks realm
- **Priority:** High
- **Input:** Access token, refresh token, realm ID
- **Output:** Stored token record
- **Constraints:** Tokens must be encrypted at rest

#### FR-02: Token Refresh
- **Description:** Automatically refresh expired access tokens
- **Priority:** High
- **Input:** Refresh token
- **Output:** New access token
- **Constraints:** Must handle token rotation

#### FR-03: Multi-Realm Support
- **Description:** Support multiple QuickBooks companies
- **Priority:** High
- **Input:** Realm-specific credentials
- **Output:** Isolated realm configurations
- **Constraints:** Each realm must have independent tokens

### 3.2 Synchronization

#### FR-04: Bidirectional Sync
- **Description:** Synchronize data in both directions
- **Priority:** High
- **Input:** Entity type, entity data
- **Output:** Synchronized entity
- **Constraints:** Must handle conflicts

#### FR-05: Incremental Sync
- **Description:** Only sync changed data
- **Priority:** Medium
- **Input:** Last sync timestamp
- **Output:** Changed entities
- **Constraints:** Must use CDC or timestamps

#### FR-06: Full Sync
- **Description:** Complete synchronization of all entities
- **Priority:** Medium
- **Input:** Entity types to sync
- **Output:** All entities
- **Constraints:** Must respect rate limits

### 3.3 Entity Support

#### FR-07: Account Sync
- **Description:** Synchronize Chart of Accounts
- **Priority:** High
- **Input:** Account data
- **Output:** Synchronized account
- **Constraints:** Must maintain account hierarchy

#### FR-08: Customer Sync
- **Description:** Synchronize customer records
- **Priority:** High
- **Input:** Customer data
- **Output:** Synchronized customer
- **Constraints:** Must handle duplicates

#### FR-09: Vendor Sync
- **Description:** Synchronize vendor records
- **Priority:** High
- **Input:** Vendor data
- **Output:** Synchronized vendor
- **Constraints:** Must handle duplicates

#### FR-10: Invoice Sync
- **Description:** Synchronize invoices
- **Priority:** High
- **Input:** Invoice data
- **Output:** Synchronized invoice
- **Constraints:** Must maintain line items

#### FR-11: Bill Sync
- **Description:** Synchronize bills
- **Priority:** High
- **Input:** Bill data
- **Output:** Synchronized bill
- **Constraints:** Must maintain line items

#### FR-12: Payment Sync
- **Description:** Synchronize payments
- **Priority:** High
- **Input:** Payment data
- **Output:** Synchronized payment
- **Constraints:** Must link to invoices/bills

#### FR-13: Item Sync
- **Description:** Synchronize inventory and service items
- **Priority:** Medium
- **Input:** Item data
- **Output:** Synchronized item
- **Constraints:** Must maintain inventory counts

#### FR-14: Employee Sync
- **Description:** Synchronize employee records
- **Priority:** Medium
- **Input:** Employee data
- **Output:** Synchronized employee
- **Constraints:** Must handle sensitive data

### 3.4 Rate Limiting

#### FR-15: Request Rate Limiting
- **Description:** Limit API requests to comply with QBO limits
- **Priority:** High
- **Input:** API request
- **Output:** Allowed/denied
- **Constraints:** 500 requests per minute per realm

#### FR-16: Concurrent Request Limiting
- **Description:** Limit concurrent API requests
- **Priority:** High
- **Input:** API request
- **Output:** Allowed/denied
- **Constraints:** 10 concurrent requests per second

#### FR-17: Retry Logic
- **Description:** Retry failed requests with backoff
- **Priority:** High
- **Input:** Failed request
- **Output:** Retried request
- **Constraints:** Exponential backoff required

### 3.5 Idempotency

#### FR-18: Idempotency Key Generation
- **Description:** Generate unique keys for operations
- **Priority:** High
- **Input:** Operation parameters
- **Output:** Deterministic key
- **Constraints:** Same input must produce same key

#### FR-19: Duplicate Detection
- **Description:** Prevent duplicate operations
- **Priority:** High
- **Input:** Idempotency key
- **Output:** Skip/execute
- **Constraints:** Keys valid for 24 hours

### 3.6 Audit Logging

#### FR-20: Operation Logging
- **Description:** Log all sync operations
- **Priority:** High
- **Input:** Operation details
- **Output:** Audit entry
- **Constraints:** Must be tamper-proof

#### FR-21: User Attribution
- **Description:** Track which user initiated operations
- **Priority:** Medium
- **Input:** User context
- **Output:** User-attributed log
- **Constraints:** Must handle anonymous operations

#### FR-22: Audit Export
- **Description:** Export audit logs
- **Priority:** Low
- **Input:** Export parameters
- **Output:** Exported data
- **Constraints:** Must support CSV and JSON

### 3.7 Webhooks

#### FR-23: Webhook Reception
- **Description:** Receive webhook events from QBO
- **Priority:** Medium
- **Input:** Webhook payload
- **Output:** Processed event
- **Constraints:** Must verify signature

#### FR-24: Event Processing
- **Description:** Process webhook events asynchronously
- **Priority:** Medium
- **Input:** Webhook event
- **Output:** Updated data
- **Constraints:** Must be idempotent

#### FR-25: Event Queuing
- **Description:** Queue events for processing
- **Priority:** Medium
- **Input:** Incoming event
- **Output:** Queued event
- **Constraints:** Must handle duplicates

---

## 4. Non-Functional Requirements

### 4.1 Performance

#### NFR-01: Response Time
- **Description:** Sync operations must complete within acceptable time
- **Target:** <100ms overhead per operation
- **Measurement:** Average response time

#### NFR-02: Throughput
- **Description:** System must handle expected load
- **Target:** 1000 sync operations per minute
- **Measurement:** Requests per second

### 4.2 Reliability

#### NFR-03: Availability
- **Description:** System must be available when needed
- **Target:** 99.9% uptime
- **Measurement:** Monthly uptime percentage

#### NFR-04: Data Integrity
- **Description:** Synced data must be accurate
- **Target:** 100% data integrity
- **Measurement:** Checksum verification

### 4.3 Security

#### NFR-05: Token Security
- **Description:** OAuth tokens must be protected
- **Target:** Encrypted at rest
- **Measurement:** Security audit

#### NFR-06: Webhook Security
- **Description:** Webhooks must be verified
- **Target:** HMAC-SHA256 verification
- **Measurement:** Security testing

### 4.4 Maintainability

#### NFR-07: Code Quality
- **Description:** Code must be maintainable
- **Target:** 90% test coverage
- **Measurement:** Coverage reports

#### NFR-08: Documentation
- **Description:** Code must be documented
- **Target:** Complete API documentation
- **Measurement:** Documentation review

### 4.5 Compatibility

#### NFR-09: Django Compatibility
- **Description:** Must work with Django 4.2+
- **Target:** LTS versions
- **Measurement:** Test matrix

#### NFR-10: Python Compatibility
- **Description:** Must work with Python 3.10+
- **Target:** Modern Python versions
- **Measurement:** Test matrix

---

## 5. External Interface Requirements

### 5.1 User Interface

#### UI-01: Admin Interface
- **Description:** Django admin interface for managing realms and viewing logs
- **Priority:** High
- **Interface:** Django Admin

#### UI-02: Management Commands
- **Description:** CLI commands for setup and operations
- **Priority:** High
- **Interface:** Django management commands

### 5.2 API Interface

#### API-01: QuickBooks API
- **Description:** Integration with QuickBooks Online API
- **Priority:** High
- **Interface:** REST API via python-quickbooks

#### API-02: Webhook Interface
- **Description:** Endpoint for receiving webhooks
- **Priority:** Medium
- **Interface:** HTTP POST endpoint

### 5.3 Data Interface

#### DATA-01: Database
- **Description:** Storage for tokens, logs, and audit entries
- **Priority:** High
- **Interface:** Django ORM

#### DATA-02: Cache
- **Description:** Optional caching for rate limiting
- **Priority:** Low
- **Interface:** Redis

---

## 6. System Features

### 6.1 Feature: OAuth Management

**Description:** Secure OAuth 2.0 token management with automatic refresh.

**Functional Requirements:**
- Store tokens encrypted per realm
- Auto-refresh before expiry
- Handle token rotation
- Support multiple realms

**Use Case: UC-01 - Connect New Realm**
1. User initiates connection
2. System redirects to QuickBooks
3. User authorizes application
4. System receives authorization code
5. System exchanges code for tokens
6. System stores tokens securely
7. System confirms connection

### 6.2 Feature: Bidirectional Sync

**Description:** Synchronize data between Django and QuickBooks.

**Functional Requirements:**
- Push local changes to QuickBooks
- Pull changes from QuickBooks
- Handle conflicts
- Maintain sync state

**Use Case: UC-02 - Sync Customer**
1. User creates customer locally
2. System generates idempotency key
3. System acquires rate limit slot
4. System calls QuickBooks API
5. System logs operation
6. System updates sync state
7. System releases rate limit slot

### 6.3 Feature: Rate Limiting

**Description:** Comply with QuickBooks API rate limits.

**Functional Requirements:**
- Track requests per minute
- Track concurrent requests
- Retry on limits
- Exponential backoff

**Use Case: UC-03 - Handle Rate Limit**
1. System attempts API call
2. QuickBooks returns 429
3. System extracts retry-after
4. System waits specified time
5. System retries request
6. System succeeds or fails

---

## 7. Data Requirements

### 7.1 Data Models

#### QuickBooksRealm
- realm_id (string, unique)
- company_name (string)
- access_token (text, encrypted)
- refresh_token (text, encrypted)
- token_expires_at (datetime)
- is_active (boolean)
- sync_enabled (boolean)
- last_sync_at (datetime)

#### SyncLog
- realm (foreign key)
- entity_type (string)
- entity_id (string)
- direction (enum)
- status (enum)
- error_message (text)
- idempotency_key (string, unique)
- payload (json)
- response (json)
- retry_count (integer)

#### AuditEntry
- realm (foreign key)
- entity_type (string)
- entity_id (string)
- action (enum)
- payload (json)
- outcome (enum)
- error_details (json)
- user (foreign key)
- ip_address (string)
- timestamp (datetime)

#### WebhookEvent
- realm (foreign key)
- event_id (string, unique)
- entity_type (string)
- entity_id (string)
- operation (enum)
- last_updated (datetime)
- payload (json)
- status (enum)
- error_message (text)
- processed_at (datetime)

### 7.2 Data Storage

- **Tokens:** Encrypted in database
- **Logs:** Standard database storage
- **Audit:** Append-only logging
- **Events:** Queued in Redis/Celery

---

## 8. Security Requirements

### 8.1 Authentication

- OAuth 2.0 for QuickBooks API
- Django authentication for admin

### 8.2 Authorization

- Realm-based access control
- User-attributed operations

### 8.3 Data Protection

- Tokens encrypted at rest
- Sensitive data masked in logs
- HTTPS required for webhooks

### 8.4 Audit

- Complete operation history
- User attribution
- Tamper-proof logging

---

## 9. Quality Attributes

### 9.1 Usability

- Simple setup process
- Clear error messages
- Comprehensive documentation

### 9.2 Reliability

- Graceful error handling
- Automatic retry logic
- Data integrity checks

### 9.3 Performance

- Minimal overhead
- Efficient rate limiting
- Async processing

### 9.4 Scalability

- Multi-realm support
- Horizontal scaling with Celery
- Database optimization

---

## 10. Constraints

### 10.1 Technical

- Must use Python 3.10+
- Must use Django 4.2+
- Must be compatible with Celery

### 10.2 Regulatory

- Must comply with QuickBooks API terms
- Must handle data privacy requirements

### 10.3 Business

- Must be open source (MIT license)
- Must be maintainable by community

---

## 11. Appendices

### Appendix A: QuickBooks API Limits

- 500 requests per minute per realm
- 10 concurrent requests per second per realm
- 40 batch requests per minute per realm
- 30 payloads per batch request

### Appendix B: Token Lifetimes

- Access token: 1 hour
- Refresh token: 100 days
- Refresh token rotation: 24-26 hours

### Appendix C: Supported Entities

- Account
- Customer
- Vendor
- Employee
- Invoice
- Bill
- Payment
- BillPayment
- Item
