# Architecture Document

## django-quickbooks-sync

**Version:** 0.1.0  
**Date:** August 2026  
**Author:** Md Mojno M.

---

## 1. Overview

This document describes the architecture of `django-quickbooks-sync`, a production-grade Django application for QuickBooks Online integration.

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Your Django Application                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    django-quickbooks-sync                             │   │
│  │                                                                       │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │   │
│  │  │   Models    │    │ Sync Engine │    │   Client    │              │   │
│  │  │             │    │             │    │             │              │   │
│  │  │ - Realm     │◄──►│ - Sync      │◄──►│ - OAuth     │              │   │
│  │  │ - SyncLog   │    │ - Conflict  │    │ - API Calls │              │   │
│  │  │ - Audit     │    │ - Audit     │    │ - Entities  │              │   │
│  │  │ - Webhook   │    │             │    │             │              │   │
│  │  └─────────────┘    └─────────────┘    └─────────────┘              │   │
│  │         │                  │                  │                       │   │
│  │         ▼                  ▼                  ▼                       │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │   │
│  │  │   Admin     │    │   Celery    │    │  Webhooks   │              │   │
│  │  │             │    │   Tasks     │    │  Handler    │              │   │
│  │  └─────────────┘    └─────────────┘    └─────────────┘              │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ HTTPS
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     QuickBooks Online API                                    │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │   OAuth 2.0     │  │  Accounting API  │  │   Webhooks      │            │
│  │   - Auth URL    │  │  - Entities      │  │   - Events      │            │
│  │   - Token Exchange│ │  - Queries       │  │   - Notifications│           │
│  │   - Refresh     │  │  - CRUD          │  │                 │            │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    django-quickbooks-sync                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Core Components                         │  │
│  │                                                            │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │  │
│  │  │   Client    │  │ Sync Engine │  │ Rate Limiter│      │  │
│  │  │  (wrapper)  │  │             │  │             │      │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘      │  │
│  │                                                            │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │  │
│  │  │Idempotency │  │  Webhook    │  │  Settings   │      │  │
│  │  │  Manager    │  │  Handler    │  │             │      │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘      │  │
│  │                                                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Data Layer                              │  │
│  │                                                            │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │  │
│  │  │   Models    │  │   Admin     │  │   Migrations│      │  │
│  │  │             │  │             │  │             │      │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘      │  │
│  │                                                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Integration Layer                       │  │
│  │                                                            │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │  │
│  │  │   Celery    │  │  Webhook    │  │  Management │      │  │
│  │  │   Tasks     │  │  Endpoint   │  │  Commands   │      │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘      │  │
│  │                                                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Flow

### 3.1 OAuth Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    User      │     │    Django    │     │  QuickBooks  │
│              │     │   (Client)   │     │     API      │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       │  1. Click "Connect"│                    │
       │───────────────────►│                    │
       │                    │                    │
       │  2. Redirect to QBO│                    │
       │◄───────────────────│                    │
       │                    │                    │
       │  3. Authorize App  │                    │
       │────────────────────────────────────────►│
       │                    │                    │
       │  4. Authorization  │                    │
       │     Code           │                    │
       │◄────────────────────────────────────────│
       │                    │                    │
       │  5. Send Code      │                    │
       │───────────────────►│                    │
       │                    │  6. Exchange Code  │
       │                    │───────────────────►│
       │                    │                    │
       │                    │  7. Access Token   │
       │                    │◄───────────────────│
       │                    │                    │
       │                    │  8. Store Tokens   │
       │                    │     (Encrypted)    │
       │                    │                    │
       │  9. Success        │                    │
       │◄───────────────────│                    │
```

### 3.2 Sync Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Django     │     │ Sync Engine  │     │  QuickBooks  │
│    (Local)   │     │              │     │     API      │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       │  1. Sync Request   │                    │
       │───────────────────►│                    │
       │                    │                    │
       │  2. Generate       │                    │
       │     Idempotency Key│                    │
       │                    │                    │
       │  3. Check Rate     │                    │
       │     Limits         │                    │
       │                    │                    │
       │  4. Acquire Slot   │                    │
       │                    │                    │
       │  5. Call QBO API   │                    │
       │────────────────────────────────────────►│
       │                    │                    │
       │  6. Response       │                    │
       │◄────────────────────────────────────────│
       │                    │                    │
       │  7. Update Sync    │                    │
       │     Log            │                    │
       │                    │                    │
       │  8. Create Audit   │                    │
       │     Entry          │                    │
       │                    │                    │
       │  9. Release Slot   │                    │
       │                    │                    │
       │  10. Return Result │                    │
       │◄───────────────────│                    │
```

### 3.3 Webhook Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  QuickBooks  │     │    Django    │     │   Celery     │
│     API      │     │  (Webhook)   │     │    Worker    │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       │  1. Event Occurs   │                    │
       │     (Invoice       │                    │
       │      Created)      │                    │
       │                    │                    │
       │  2. Send Webhook   │                    │
       │───────────────────►│                    │
       │                    │                    │
       │  3. Verify         │                    │
       │     Signature      │                    │
       │                    │                    │
       │  4. Parse Payload  │                    │
       │                    │                    │
       │  5. Queue Event    │                    │
       │────────────────────────────────────────►│
       │                    │                    │
       │  6. Return 200 OK  │                    │
       │◄───────────────────│                    │
       │                    │                    │
       │                    │  7. Process Event  │
       │                    │                    │
       │                    │  8. Sync Entity    │
       │                    │───────────────────►│
       │                    │                    │
       │                    │  9. Update Status  │
       │                    │◄───────────────────│
```

---

## 4. Component Details

### 4.1 Client Wrapper

**Purpose:** Wraps the `python-quickbooks` library with Django-specific features.

**Responsibilities:**
- OAuth 2.0 authentication
- Token management
- API call abstraction
- Error handling

**Dependencies:**
- `python-quickbooks`
- `intuit-oauth`

### 4.2 Sync Engine

**Purpose:** Core bidirectional synchronization logic.

**Responsibilities:**
- Coordinate sync operations
- Handle conflicts
- Create audit entries
- Manage sync state

**Dependencies:**
- Client Wrapper
- Rate Limiter
- Idempotency Manager

### 4.3 Rate Limiter

**Purpose:** Comply with QuickBooks API rate limits.

**Responsibilities:**
- Track requests per minute
- Track concurrent requests
- Enforce limits
- Provide retry timing

**Algorithm:** Token Bucket

### 4.4 Idempotency Manager

**Purpose:** Prevent duplicate operations.

**Responsibilities:**
- Generate deterministic keys
- Check for existing operations
- Track operation status
- Clean up expired keys

**Validity:** 24 hours

### 4.5 Webhook Handler

**Purpose:** Process incoming webhook events.

**Responsibilities:**
- Verify signatures
- Parse payloads
- Queue events
- Track processing status

**Security:** HMAC-SHA256 verification

---

## 5. Data Models

### 5.1 Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    QuickBooksRealm                               │
├─────────────────────────────────────────────────────────────────┤
│  - id (PK)                                                      │
│  - realm_id (unique)                                            │
│  - company_name                                                 │
│  - access_token (encrypted)                                     │
│  - refresh_token (encrypted)                                    │
│  - token_expires_at                                             │
│  - is_active                                                    │
│  - sync_enabled                                                 │
│  - last_sync_at                                                 │
│  - created_at                                                   │
│  - updated_at                                                   │
└─────────────────────────────────────────────────────────────────┘
                               │
       ┌───────────────────────┼───────────────────────┐
       │                       │                       │
       ▼                       ▼                       ▼
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│      SyncLog        │ │    AuditEntry       │ │   WebhookEvent      │
├─────────────────────┤ ├─────────────────────┤ ├─────────────────────┤
│  - id (PK)          │ │  - id (PK)          │ │  - id (PK)          │
│  - realm_id (FK)    │ │  - realm_id (FK)    │ │  - realm_id (FK)    │
│  - entity_type      │ │  - entity_type      │ │  - event_id (unique)│
│  - entity_id        │ │  - entity_id        │ │  - entity_type      │
│  - direction        │ │  - action           │ │  - entity_id        │
│  - status           │ │  - payload          │ │  - operation        │
│  - error_message    │ │  - outcome          │ │  - last_updated     │
│  - idempotency_key  │ │  - error_details    │ │  - payload          │
│  - payload          │ │  - user_id (FK)     │ │  - status           │
│  - response         │ │  - ip_address       │ │  - error_message    │
│  - retry_count      │ │  - timestamp        │ │  - processed_at     │
│  - created_at       │ │                     │ │  - created_at       │
│  - updated_at       │ │                     │ │                     │
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘
```

### 5.2 SyncLog States

```
┌─────────────┐
│   PENDING   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ IN_PROGRESS │
└──────┬──────┘
       │
       ├──────────────┐
       │              │
       ▼              ▼
┌─────────────┐ ┌─────────────┐
│   SUCCESS   │ │   FAILED    │
└─────────────┘ └──────┬──────┘
                       │
                       ▼
                ┌─────────────┐
                │  RETRYING   │
                └─────────────┘
```

---

## 6. Security Architecture

### 6.1 Token Security

```
┌─────────────────────────────────────────────────────────────────┐
│                    Token Security Flow                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Token Received                                              │
│     └─► 2. Encrypt with Django SECRET_KEY                       │
│         └─► 3. Store in Database                                │
│             └─► 4. Decrypt on Use                               │
│                 └─► 5. Refresh Before Expiry                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Webhook Security

```
┌─────────────────────────────────────────────────────────────────┐
│                    Webhook Security Flow                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Request Received                                            │
│     └─► 2. Extract Signature Header                            │
│         └─► 3. Compute HMAC-SHA256                             │
│             └─► 4. Compare Signatures                          │
│                 └─► 5. Reject if Invalid                       │
│                     └─► 6. Process Event                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Deployment Architecture

### 7.1 Production Deployment

```
┌─────────────────────────────────────────────────────────────────┐
│                    Production Environment                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Load Balancer                         │   │
│  │                    (nginx/HAProxy)                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Django Application                    │   │
│  │                    (Gunicorn/uWSGI)                      │   │
│  │                                                          │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │   Web       │  │   Admin     │  │  Webhook    │    │   │
│  │  │   Requests  │  │   Interface │  │  Endpoint   │    │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘    │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Celery Workers                        │   │
│  │                    (Multiple Processes)                   │   │
│  │                                                          │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │   Sync      │  │   Webhook   │  │   Token     │    │   │
│  │  │   Tasks     │  │   Processing│  │   Refresh   │    │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘    │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Message Broker                        │   │
│  │                    (RabbitMQ/Redis)                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Database                              │   │
│  │                    (PostgreSQL)                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Scaling Considerations

### 8.1 Horizontal Scaling

- **Celery Workers:** Add more workers to handle increased sync load
- **Database:** Use read replicas for reporting
- **Cache:** Use Redis cluster for rate limiting

### 8.2 Vertical Scaling

- **Database Connection Pooling:** Use PgBouncer
- **Worker Concurrency:** Increase Celery worker concurrency
- **Memory:** Increase RAM for large sync operations

---

## 9. Monitoring and Observability

### 9.1 Metrics

- Sync operations per minute
- API response times
- Rate limit hits
- Error rates
- Queue depth

### 9.2 Logging

- Structured JSON logging
- Correlation IDs for request tracing
- Audit trail for compliance

### 9.3 Alerting

- High error rates
- Rate limit violations
- Queue backlog
- Token expiry warnings

---

## 10. Future Considerations

### 10.1 Planned Features

- Xero integration
- Multi-accounting system support
- Real-time sync with WebSockets
- GraphQL API

### 10.2 Technical Debt

- Encrypted field support
- Connection pooling
- Query optimization
