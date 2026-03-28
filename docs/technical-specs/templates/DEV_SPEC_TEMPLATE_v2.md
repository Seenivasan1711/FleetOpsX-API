# [Feature Name] – Technical Specification

> **Template Purpose:** This template provides a standardized structure for technical specifications that enable AI-assisted implementation. Engineers should be able to read, review, and execute implementation from this document alone. This document focuses on WHAT to build and HOW to build it, with sufficient context and direction for both human engineers and AI coding assistants.

---

## Document Information

| Field | Value |
|-------|-------|
| **Feature Name** | [Short feature name] |
| **Status** | Draft / In Review / Approved / Implemented |
| **Version** | X.Y |
| **Date** | YYYY-MM-DD |
| **Author** | [Name or Team] |
| **Reviewer** | [Name or Team] |
| **Reference** | [Related product requirements, previous specs] |
| **Implementation Branch** | [Git branch name] |
| **QA Document** | [Link to QA/questions document] |
| **Test Specification** | [Link to separate test spec document] |

---

## Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | YYYY-MM-DD | [Name] | Initial draft |

---

## Executive Summary

**Purpose:** One-paragraph description of what this feature accomplishes and why it's important.

### Key Deliverables

| Component | Description | Priority | Estimate |
|-----------|-------------|----------|----------|
| Component A | Brief description | P0/P1/P2 | X hours/days |
| Component B | Brief description | P0/P1/P2 | X hours/days |

### Success Criteria

- [ ] Criterion 1 (measurable)
- [ ] Criterion 2 (measurable)
- [ ] Criterion 3 (measurable)

### Dependencies

| Dependency | Type | Status | Impact |
|------------|------|--------|--------|
| External API | External | Ready | Blocks component A |
| Database migration | Internal | In progress | Blocks component B |

---

## 1. Goals & Objectives

<details>
<summary><strong>Click to expand</strong></summary>

### Primary Goals

1. **Goal 1:** Clear, specific goal
2. **Goal 2:** Clear, specific goal
3. **Goal 3:** Clear, specific goal

### Non-Goals

- What this feature will NOT do
- Out of scope items
- Future considerations

### What This Replaces

| Before (Current) | After (New) |
|------------------|-------------|
| Current behavior | New behavior |

</details>

---

## 2. Functional Requirements

<details>
<summary><strong>Click to expand</strong></summary>

### FR-1: [Requirement Name]

**Description:** [Clear description of the requirement]

**Requirement:**
```
[Technical description or pseudocode]
```

**Acceptance Criteria:**
- [ ] Specific, testable criterion
- [ ] Specific, testable criterion
- [ ] Specific, testable criterion

**Example:**
```
[Code example, API call, or user flow example]
```

---

### FR-2: [Next Requirement]

[Follow same structure as FR-1]

</details>

---

## 3. Architecture & Design

<details>
<summary><strong>Click to expand</strong></summary>

### 3.1 System Architecture

```
[ASCII diagram showing high-level architecture]

Example:
┌─────────────────────────────────────────────────────────────┐
│                       COMPONENT A                            │
│                   Description of layer                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       COMPONENT B                            │
│                   Description of layer                       │
└─────────────────────────────────────────────────────────────┘
```

**Components:**
- **Component A:** Responsibility description
- **Component B:** Responsibility description

### 3.2 Data Flow

```
1. Entry point (User action, API call, event trigger)
           ↓
2. Processing step 1
           ↓
3. Processing step 2
           ↓
4. Final output/state change
```

### 3.3 Component Interactions

```
[Sequence diagram or component interaction diagram]

Example:
1. Client Request (e.g., GET /resource)
           │
           ▼
2. Controller validates request
           │
           ▼
3. Service processes business logic
           │
    ┌──────┴──────┐
    │  Success?   │
    └──────┬──────┘
     Yes/    \No
       │      │
       ▼      ▼
   200 OK   Error Response
```

</details>

---

## 4. Data Model

<details>
<summary><strong>Click to expand</strong></summary>

### 4.1 Entity Relationships

```
[ERD diagram or relationship description]

Example:
ENTITY_A (1) ──────< ENTITY_B (many)
                         │
ENTITY_C (many) >────────┘
```

### 4.2 Table: `table_name`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BIGSERIAL | PRIMARY KEY | Unique identifier |
| `column_name` | VARCHAR(255) | NOT NULL | Description |
| `foreign_id` | BIGINT | FK to other_table(id) | Reference to other entity |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | Last update timestamp |

**Indexes:**
- `idx_table_column` on `column_name`
- `idx_table_foreign` on `foreign_id`

**Constraints:**
- `fk_table_foreign` - Foreign key to other_table(id)
- `chk_table_status` - CHECK constraint for valid status values
- `uq_table_unique` - Unique constraint

### 4.3 Database Migrations

**Migration File:** `db.changelog-setXX_description.xml`

```sql
-- Create new table
CREATE TABLE table_name (
    id BIGSERIAL PRIMARY KEY,
    column_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add indexes
CREATE INDEX idx_table_column ON table_name(column_name);
```

**Rollback Strategy:**
```sql
-- Rollback commands
DROP TABLE IF EXISTS table_name;
```

</details>

---

## 5. API Specifications

<details>
<summary><strong>Click to expand</strong></summary>

### 5.1 Endpoint: [Method] [Path]

**Purpose:** [Brief description]

**Authentication:** Required / Optional / None

**Authorization:** [Required permission or role]

**Path Parameters:**
- `{paramName}` - Type - Description

**Query Parameters:**
- `paramName` - Type - Optional/Required - Description

**Request Body:**
```json
{
  "field": "value",
  "nestedField": {
    "subField": "value"
  }
}
```

**Request Schema (TypeScript):**
```typescript
interface RequestType {
  field: string;
  nestedField: {
    subField: string;
  };
}
```

**Request Schema (Java):**
```java
public record RequestDto(
    String field,
    NestedDto nestedField
) {}
```

**Response (200 OK):**
```json
{
  "data": {...},
  "meta": {...}
}
```

**Response Schema (TypeScript):**
```typescript
interface ResponseType {
  data: DataType;
  meta?: MetaType;
}
```

**Error Responses:**
| Status | Code | Message | Cause |
|--------|------|---------|-------|
| 400 | BAD_REQUEST | "Invalid input" | Validation failure |
| 401 | UNAUTHORIZED | "Authentication required" | No valid token |
| 403 | FORBIDDEN | "No permission" | Authorization failure |
| 404 | NOT_FOUND | "Resource not found" | Resource doesn't exist |

**Example Request:**
```bash
curl -X POST https://api.example.com/endpoint \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"field": "value"}'
```

---

### 5.2 [Next Endpoint]

[Follow same structure]

</details>

---

## 6. Backend Implementation

<details>
<summary><strong>Click to expand</strong></summary>

### 6.1 DTOs & Request/Response Models

> Define all DTOs with validation annotations for AI to implement correctly.

**Request DTO Example:**
```java
// Request: Create Entity
public record CreateEntityRequest(
    @NotBlank(message = "Name is required")
    @Size(max = 255, message = "Name must be less than 255 characters")
    String name,
    
    @NotBlank(message = "Type is required")
    @Pattern(regexp = "TYPE_A|TYPE_B|TYPE_C", message = "Invalid type")
    String type,
    
    @Email(message = "Invalid email format")
    String email,
    
    @Min(value = 0, message = "Value must be positive")
    Integer count
) {}
```

**Response DTO Example:**
```java
// Response: Entity
public record EntityResponse(
    Long id,
    String name,
    String type,
    String status,
    LocalDateTime createdAt,
    LocalDateTime updatedAt
) {}

// Response: List with pagination
public record EntityListResponse(
    List<EntityResponse> data,
    PaginationMeta meta
) {}

public record PaginationMeta(
    int page,
    int size,
    long total,
    int totalPages
) {}
```

---

### 6.2 Service Layer

**File:** `src/main/java/com/company/service/ServiceName.java`

**Purpose:** [What this service does]

**Methods with Pseudocode:**

```java
@Service
@Slf4j
public class ServiceName {
    
    private final EntityRepository entityRepository;
    private final HelperService helperService;
    
    /**
     * Creates a new entity
     * @param request The creation request with validated fields
     * @param userId The user performing the action
     * @return Created entity response
     * @throws ValidationException if business rules violated
     * @throws ConflictException if entity already exists
     */
    public EntityResponse createEntity(CreateEntityRequest request, String userId) {
        // PSEUDOCODE:
        // 1. Log operation start
        log.info("[CREATE_ENTITY] Starting for userId: {}, name: {}", userId, request.name());
        
        // 2. Check for duplicates
        if (entityRepository.existsByName(request.name())) {
            log.warn("[CREATE_ENTITY] Duplicate name: {}", request.name());
            throw new ConflictException("Entity already exists");
        }
        
        // 3. Create entity
        Entity entity = new Entity();
        entity.setName(request.name());
        entity.setType(request.type());
        entity.setCreatedAt(LocalDateTime.now());
        
        // 4. Save and return
        Entity saved = entityRepository.save(entity);
        log.info("[CREATE_ENTITY] Success for userId: {}, entityId: {}", userId, saved.getId());
        
        return mapToResponse(saved);
    }
    
    /**
     * Gets entity by ID with permission check
     */
    public EntityResponse getEntity(Long id, String userId) {
        // PSEUDOCODE:
        log.info("[GET_ENTITY] userId: {}, entityId: {}", userId, id);
        
        Entity entity = entityRepository.findById(id)
            .orElseThrow(() -> {
                log.warn("[GET_ENTITY] Not found: entityId: {}", id);
                return new NotFoundException("Entity not found");
            });
        
        return mapToResponse(entity);
    }
}
```

**Dependencies:**
- `EntityRepository` - For data access
- `HelperService` - For auxiliary operations

**Error Handling Pattern:**
```java
// Specific error handling patterns to implement
try {
    // operation
} catch (DataIntegrityViolationException e) {
    log.error("[OPERATION_NAME] Data integrity error for userId: {}", userId, e);
    throw new ConflictException("Resource conflict", e);
} catch (Exception e) {
    log.error("[OPERATION_NAME] Unexpected error for userId: {}", userId, e);
    throw new InternalException("Internal error", e);
}
```

---

### 6.3 Repository Layer

**File:** `src/main/java/com/company/repository/RepositoryName.java`

```java
public interface RepositoryName extends JpaRepository<Entity, Long> {
    
    /**
     * Find entities by specific criteria
     * Query should use index: idx_entity_field
     */
    List<Entity> findByField(String field);
    
    /**
     * Check if entity exists by name (for duplicate check)
     */
    boolean existsByName(String name);
    
    /**
     * Custom query for complex operations
     */
    @Query("SELECT e FROM Entity e WHERE e.field = :param")
    Optional<Entity> findComplexCase(@Param("param") String param);
}
```

---

### 6.4 Controller Layer

**File:** `src/main/java/com/company/controller/ControllerName.java`

```java
@RestController
@RequestMapping("/api/v1/resource")
@Slf4j
public class ControllerName {
    
    @GetMapping("/{id}")
    @PreAuthorize("hasPermission(#id, 'RESOURCE', 'PERMISSION_NAME')")
    public ResponseEntity<ResponseType> getResource(
        @PathVariable Long id,
        @RequestHeader("X-USER-ID") String userId
    ) {
        log.info("[GET_RESOURCE] userId: {}, resourceId: {}", userId, id);
        
        // 1. Validate input
        // 2. Call service layer
        // 3. Transform response
        // 4. Return result
        
        return ResponseEntity.ok(result);
    }
}
```

**Validation:**
- Input validation rules
- Business logic validation
- Authorization checks

---

### 6.5 Model/Entity Layer

**File:** `src/main/java/com/company/model/EntityName.java`

```java
@Entity
@Table(name = "table_name", indexes = {
    @Index(name = "idx_field", columnList = "field_name")
})
@Getter @Setter
public class EntityName {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(name = "field_name", nullable = false)
    private String fieldName;
    
    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;
    
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
    
    // Relationships
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "parent_id")
    private ParentEntity parent;
}
```

---

### 6.6 Configuration

**Required Configuration:**
- Environment variables needed
- Application properties to add
- Spring Bean configurations

**Example:**
```yaml
# application.yml
feature:
  enabled: true
  config:
    timeout: 5000

# Cache configuration (if needed)
spring:
  cache:
    type: caffeine
    caffeine:
      spec: maximumSize=1000,expireAfterWrite=300s
```

</details>

---

## 7. Frontend Implementation

<details>
<summary><strong>Click to expand</strong></summary>

### 7.1 Types & Interfaces

**File:** `src/types/featureName.ts`

```typescript
export interface EntityType {
  id: number;
  field: string;
  nestedObject?: {
    subField: string;
  };
  createdAt: string;
  updatedAt: string;
}

export type StatusType = 'active' | 'inactive' | 'pending';

export interface ApiResponse<T> {
  data: T;
  meta?: {
    total: number;
    page: number;
  };
}

// Request DTOs
export interface CreateEntityRequest {
  field: string;
  nestedObject?: {
    subField: string;
  };
}

export interface UpdateEntityRequest extends Partial<CreateEntityRequest> {
  id: number;
}
```

---

### 7.2 API Client

**File:** `src/api/featureNameApi.ts`

```typescript
export const featureApi = {
  async getEntity(id: number): Promise<EntityType> {
    const response = await apiClient.get<ApiResponse<EntityType>>(
      `/api/v1/entities/${id}`
    );
    return response.data.data;
  },
  
  async createEntity(data: CreateEntityRequest): Promise<EntityType> {
    const response = await apiClient.post<ApiResponse<EntityType>>(
      '/api/v1/entities',
      data
    );
    return response.data.data;
  },
  
  async updateEntity(id: number, data: UpdateEntityRequest): Promise<EntityType> {
    const response = await apiClient.put<ApiResponse<EntityType>>(
      `/api/v1/entities/${id}`,
      data
    );
    return response.data.data;
  },
  
  async deleteEntity(id: number): Promise<void> {
    await apiClient.delete(`/api/v1/entities/${id}`);
  },
};
```

---

### 7.3 Hooks

**File:** `src/hooks/useFeatureName.ts`

```typescript
export function useEntity(id: number) {
  const [data, setData] = useState<EntityType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  
  useEffect(() => {
    // Implementation notes:
    // 1. Fetch data
    // 2. Handle loading state
    // 3. Handle errors
    // 4. Cache if appropriate
    
    const fetchData = async () => {
      try {
        setLoading(true);
        const result = await featureApi.getEntity(id);
        setData(result);
      } catch (err) {
        setError(err as Error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [id]);
  
  return { data, loading, error };
}
```

---

### 7.4 Components

**File:** `src/components/ComponentName.tsx`

```typescript
interface ComponentNameProps {
  propName: string;
  optionalProp?: number;
  onAction?: (data: DataType) => void;
}

export function ComponentName({ 
  propName, 
  optionalProp, 
  onAction 
}: ComponentNameProps) {
  // Implementation notes:
  // 1. State management
  // 2. Event handlers
  // 3. Conditional rendering
  // 4. Permission checks (if applicable)
  
  return (
    <div>
      {/* Component JSX */}
    </div>
  );
}
```

**Usage Example:**
```typescript
<ComponentName 
  propName="value" 
  onAction={(data) => console.log(data)} 
/>
```

</details>

---

## 8. Security & Authorization

<details>
<summary><strong>Click to expand</strong></summary>

### 8.1 Authentication Requirements

- JWT token validation
- Session management
- Token refresh logic
- User identification via `X-USER-ID` header

### 8.2 Authorization Rules

| Resource | Action | Required Permission | Scope |
|----------|--------|-------------------|-------|
| Resource A | Read | PERMISSION_NAME | Scope level |
| Resource A | Write | PERMISSION_NAME | Scope level |
| Resource A | Delete | PERMISSION_NAME | Scope level |

### 8.3 Security Considerations

1. **Input Validation:** All inputs must be validated and sanitized
2. **SQL Injection Prevention:** Use parameterized queries
3. **XSS Prevention:** Escape all user-generated content
4. **CSRF Protection:** Include CSRF tokens for state-changing operations
5. **Rate Limiting:** [Specify limits per endpoint]

### 8.4 Sensitive Data Handling

- PII fields requiring encryption
- Logging restrictions (no sensitive data in logs)
- Data retention policies

</details>

---

## 9. Error Handling & Edge Cases

<details>
<summary><strong>Click to expand</strong></summary>

### 9.1 Error Responses

| Status | Code | Message | Cause |
|--------|------|---------|-------|
| 400 | `INVALID_INPUT` | "Validation failed" | Validation failure |
| 401 | `UNAUTHORIZED` | "Authentication required" | No valid token |
| 403 | `FORBIDDEN` | "No permission" | Authorization failure |
| 404 | `NOT_FOUND` | "Resource not found" | Resource doesn't exist |
| 409 | `CONFLICT` | "Resource already exists" | Duplicate entry |
| 500 | `INTERNAL_ERROR` | "Internal server error" | Unexpected error |

### 9.2 Error Response JSON Examples

**400 Validation Error:**
```json
{
  "timestamp": "2025-12-04T10:30:00Z",
  "status": 400,
  "error": "INVALID_INPUT",
  "message": "Validation failed",
  "path": "/api/v1/entities",
  "details": {
    "errors": [
      { "field": "name", "message": "Name is required" },
      { "field": "type", "message": "Invalid type" }
    ]
  }
}
```

**401 Unauthorized:**
```json
{
  "timestamp": "2025-12-04T10:30:00Z",
  "status": 401,
  "error": "UNAUTHORIZED",
  "message": "Authentication required",
  "path": "/api/v1/entities"
}
```

**403 Forbidden:**
```json
{
  "timestamp": "2025-12-04T10:30:00Z",
  "status": 403,
  "error": "FORBIDDEN",
  "message": "Missing permission: ENTITY_CREATE",
  "path": "/api/v1/entities",
  "details": {
    "requiredPermission": "ENTITY_CREATE"
  }
}
```

**404 Not Found:**
```json
{
  "timestamp": "2025-12-04T10:30:00Z",
  "status": 404,
  "error": "NOT_FOUND",
  "message": "Entity not found",
  "path": "/api/v1/entities/999"
}
```

**409 Conflict:**
```json
{
  "timestamp": "2025-12-04T10:30:00Z",
  "status": 409,
  "error": "CONFLICT",
  "message": "Entity with this name already exists",
  "path": "/api/v1/entities"
}
```

### 9.3 Edge Cases

| Case | Expected Behavior | Handling |
|------|-------------------|----------|
| Null/empty input | Return validation error | Input validation layer |
| Concurrent modifications | Use optimistic locking | Database constraint |
| Missing related data | Fail gracefully | Null checks and defaults |
| Network timeout | Retry with exponential backoff | API client layer |
| User with no roles | Deny all access | Authorization layer |

### 9.4 Fail-Safe Defaults

- Default to deny on authorization errors
- Default to returning empty results on data errors
- Never expose internal error details to users
- Log all errors with correlation IDs

</details>

---

## 10. Observability & Monitoring

<details>
<summary><strong>Click to expand</strong></summary>

### 10.1 Logging Requirements

**Log Levels:**
- **INFO:** Normal operations, state transitions
- **WARN:** Recoverable errors, unusual conditions
- **ERROR:** Failures requiring investigation

**Structured Logging Format:**
```json
{
  "timestamp": "2025-12-04T10:00:00Z",
  "level": "INFO",
  "service": "service-name",
  "operation": "operation-name",
  "userId": "user123",
  "resourceId": "resource456",
  "duration_ms": 45,
  "status": "success"
}
```

**Log Examples:**
```java
log.info("[OPERATION_NAME] Starting operation for user: {}, resource: {}", userId, resourceId);
log.warn("[OPERATION_NAME] Unusual condition: {} for user: {}", condition, userId);
log.error("[OPERATION_NAME] Operation failed for user: {}", userId, exception);
```

### 10.2 Metrics

| Metric | Type | Description | Threshold |
|--------|------|-------------|-----------|
| `operation.count` | Counter | Total operations | - |
| `operation.duration_ms` | Histogram | Operation duration | p95 < 100ms |
| `operation.errors` | Counter | Failed operations | < 1% |
| `cache.hit_rate` | Gauge | Cache hit percentage | > 90% |

### 10.3 Alerts

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| High error rate | > 5% errors in 5 min | CRITICAL | Page on-call |
| Slow performance | p95 > 500ms | WARNING | Investigate |
| Low cache hit rate | < 80% in 10 min | WARNING | Investigate |

</details>

---

## 11. Deployment Plan

<details>
<summary><strong>Click to expand</strong></summary>

### 11.1 Pre-Deployment Checklist

- [ ] All tests passing (reference test spec)
- [ ] Code review approved
- [ ] Database migrations reviewed
- [ ] Monitoring dashboards ready
- [ ] Rollback plan documented

### 11.2 Deployment Steps

| Step | Action | Verification | Rollback |
|------|--------|--------------|----------|
| 1 | Run DB migrations | Tables/columns exist | Drop tables/revert schema |
| 2 | Deploy backend | Health check passes | Redeploy previous version |
| 3 | Deploy frontend | UI loads correctly | Redeploy previous version |
| 4 | Enable feature flag | Feature accessible | Disable flag |

### 11.3 Feature Flag Strategy

```java
if (featureFlagService.isEnabled("feature-name")) {
    // New implementation
} else {
    // Legacy implementation (if applicable)
}
```

### 11.4 Rollback Criteria

- Error rate > 5%
- Critical bug discovered
- Performance degradation > 50%

</details>

---

## 12. Migration Strategy (if applicable)

<details>
<summary><strong>Click to expand</strong></summary>

### 12.1 Current State

[Description of existing system/data]

### 12.2 Target State

[Description of desired system/data]

### 12.3 Migration Phases

```
Phase 1: DEPLOY
┌─────────────────────────────────────┐
│ • Deploy new components             │
│ • Run database migrations           │
│ • Old system still serving          │
└─────────────────────────────────────┘
                 │
                 ▼
Phase 2: TEST
┌─────────────────────────────────────┐
│ • QA tests new endpoints            │
│ • Validate data integrity           │
│ • Old system still serving          │
└─────────────────────────────────────┘
                 │
                 ▼
Phase 3: MIGRATE (Gradual)
┌─────────────────────────────────────┐
│ • Switch traffic gradually          │
│ • Monitor for issues                │
│ • Feature flags for rollback        │
└─────────────────────────────────────┘
                 │
                 ▼
Phase 4: COMPLETE
┌─────────────────────────────────────┐
│ • All traffic on new system         │
│ • Deprecate old endpoints           │
│ • Remove old code (later)           │
└─────────────────────────────────────┘
```

### 12.4 Data Migration

```sql
-- Migration script
-- Should be idempotent (can run multiple times safely)
INSERT INTO new_table (columns)
SELECT columns FROM old_table
WHERE NOT EXISTS (SELECT 1 FROM new_table WHERE new_table.id = old_table.id);
```

### 12.5 Backward Compatibility

[How old and new systems coexist during migration]

</details>

---

## 13. AI Implementation Guide

<details open>
<summary><strong>Step-by-Step Implementation for AI Coding Assistants</strong></summary>

> **Purpose:** This section provides a structured, checkpoint-based implementation guide designed for AI coding assistants (Cursor, GitHub Copilot, etc.). Each checkpoint is reversible and can be implemented independently.

### Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    IMPLEMENTATION CHECKPOINTS                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  CP-1: Core Types ──► CP-2: Database Schema ──► CP-3: Entity Models     │
│                                                                         │
│  CP-4: Repositories ──► CP-5: Services ──► CP-6: Controllers            │
│                                                                         │
│  CP-7: Frontend Types ──► CP-8: API Client ──► CP-9: Components         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### Checkpoint 1 (CP-1): Core Types & Enums

**Goal:** Define all static types that other components depend on.

**Revertible:** Yes - Delete files to revert.

**Depends On:** None

**Files to Create:**

| File Path | Purpose |
|-----------|---------|
| `src/main/java/com/company/[feature]/TypeName.java` | Enum/Type definition |

**Tasks:**

```
Task 1.1: Create [TypeName] Enum/Class
File: src/main/java/com/company/[feature]/TypeName.java

Create enum/class with:
- Values: VALUE_A, VALUE_B, VALUE_C
- Methods: getCode(), fromCode(String)
```

**Verification:**
- [ ] All types compile without errors
- [ ] Unit tests pass for type conversions

---

### Checkpoint 2 (CP-2): Database Schema

**Goal:** Create database migrations for new tables.

**Revertible:** Yes - Run rollback migrations.

**Depends On:** None (independent)

**Files to Create:**

| File Path | Purpose |
|-----------|---------|
| `src/main/resources/db/changelog/db.changelog-setXX_[name].xml` | Migration file |

**Tasks:**

```
Task 2.1: Create [TableName] Table Migration
File: db.changelog-setXX_[name].xml

Table: [table_name]
Columns:
- id: BIGSERIAL PRIMARY KEY
- [columns from Section 4]

Indexes:
- [indexes from Section 4]

Constraints:
- [constraints from Section 4]
```

**Verification:**
- [ ] Run `./gradlew bootRun` - no migration errors
- [ ] Tables exist with correct schema
- [ ] Constraints and indexes are created

---

### Checkpoint 3 (CP-3): Entity Models

**Goal:** Create JPA entities for new tables.

**Revertible:** Yes - Delete entity files.

**Depends On:** CP-2 (Database Schema)

**Files to Create:**

| File Path | Purpose |
|-----------|---------|
| `src/main/java/com/company/model/EntityName.java` | JPA entity |

**Tasks:**

```
Task 3.1: Create [EntityName] Entity
File: src/main/java/com/company/model/EntityName.java

@Entity
@Table(name = "[table_name]")
Fields: [from Section 4]
Relationships: [from Section 4]
```

**Verification:**
- [ ] Entities compile without errors
- [ ] Run application - Hibernate validates schema

---

### Checkpoint 4 (CP-4): Repository Layer

**Goal:** Create data access repositories.

**Revertible:** Yes - Delete repository files.

**Depends On:** CP-3 (Entity Models)

**Files to Create:**

| File Path | Purpose |
|-----------|---------|
| `src/main/java/com/company/repository/EntityRepository.java` | Data access |

**Tasks:**

```
Task 4.1: Create [Entity]Repository
File: src/main/java/com/company/repository/[Entity]Repository.java

Methods: [from Section 6.2]
```

**Verification:**
- [ ] Repositories compile
- [ ] Can perform CRUD operations

---

### Checkpoint 5 (CP-5): Service Layer

**Goal:** Implement business logic services.

**Revertible:** Yes - Delete service files.

**Depends On:** CP-1, CP-4

**Files to Create:**

| File Path | Purpose |
|-----------|---------|
| `src/main/java/com/company/service/ServiceName.java` | Business logic |

**Tasks:**

```
Task 5.1: Create [ServiceName]
File: src/main/java/com/company/service/[ServiceName].java

@Service
Dependencies: [from Section 6.1]
Methods: [from Section 6.1]
```

**Verification:**
- [ ] Services compile without errors
- [ ] Unit tests pass for all methods

---

### Checkpoint 6 (CP-6): Controller Layer

**Goal:** Create API endpoints.

**Revertible:** Yes - Delete controller files.

**Depends On:** CP-5

**Files to Create:**

| File Path | Purpose |
|-----------|---------|
| `src/main/java/com/company/controller/ControllerName.java` | API endpoints |

**Tasks:**

```
Task 6.1: Create [ControllerName]
File: src/main/java/com/company/controller/[ControllerName].java

@RestController
@RequestMapping("[base-path]")
Endpoints: [from Section 5]
```

**Verification:**
- [ ] All endpoints return correct responses
- [ ] Authorization annotations work
- [ ] API integration tests pass

---

### Checkpoint 7 (CP-7): Frontend Types

**Goal:** Create TypeScript types/interfaces.

**Revertible:** Yes - Delete type files.

**Depends On:** None (can parallel with backend)

**Files to Create:**

| File Path | Purpose |
|-----------|---------|
| `src/types/featureName.ts` | TypeScript interfaces |

**Tasks:**

```
Task 7.1: Create TypeScript Types
File: src/types/featureName.ts

Interfaces: [from Section 7.1]
```

**Verification:**
- [ ] Types compile without errors
- [ ] Types match API response shapes

---

### Checkpoint 8 (CP-8): Frontend API Client

**Goal:** Create API client functions.

**Revertible:** Yes - Delete API client files.

**Depends On:** CP-7

**Files to Create:**

| File Path | Purpose |
|-----------|---------|
| `src/api/featureNameApi.ts` | API client functions |

**Tasks:**

```
Task 8.1: Create API Client
File: src/api/featureNameApi.ts

Methods: [from Section 7.2]
```

**Verification:**
- [ ] API calls work correctly
- [ ] Error handling works

---

### Checkpoint 9 (CP-9): Frontend Components

**Goal:** Create UI components.

**Revertible:** Yes - Delete component files.

**Depends On:** CP-7, CP-8

**Files to Create:**

| File Path | Purpose |
|-----------|---------|
| `src/components/ComponentName.tsx` | React component |
| `src/hooks/useFeatureName.ts` | Custom hooks |

**Tasks:**

```
Task 9.1: Create Components
Files: [from Section 7.3, 7.4]
```

**Verification:**
- [ ] Components render correctly
- [ ] User interactions work
- [ ] Component tests pass

---

### Implementation Order Summary

| Order | Checkpoint | Depends On | Est. Time | Reversible |
|-------|------------|------------|-----------|------------|
| 1 | CP-1: Core Types | None | X hours | Yes |
| 2 | CP-2: Database Schema | None | X hours | Yes |
| 3 | CP-3: Entity Models | CP-2 | X hours | Yes |
| 4 | CP-4: Repository Layer | CP-3 | X hours | Yes |
| 5 | CP-5: Service Layer | CP-1, CP-4 | X hours | Yes |
| 6 | CP-6: Controller Layer | CP-5 | X hours | Yes |
| 7 | CP-7: Frontend Types | None | X hours | Yes |
| 8 | CP-8: API Client | CP-7 | X hours | Yes |
| 9 | CP-9: Components | CP-7, CP-8 | X hours | Yes |

**Total Estimated Time:** ~X hours

</details>

---

## 14. Documentation

<details>
<summary><strong>Click to expand</strong></summary>

> **Purpose:** This section provides links to all related documentation artifacts produced during the feature lifecycle. Maintain these links to ensure traceability from requirements to release.

### 14.1 Product Requirements (PRD/BRD)

**Description:** Links to Jira epics/stories and Confluence PRDs. Captures the **"WHY"** - business context, user stories, and acceptance criteria that drive this feature.

**What to Include:**
- Product Requirements Document (PRD)
- Business Requirements Document (BRD)
- Jira Epic/Story links
- Confluence requirement pages
- Stakeholder sign-off documents

**Links:**
| Document | Link | Status |
|----------|------|--------|
| Jira Epic | [PROJ-XXX](link) | Active |
| PRD - Confluence | [Feature PRD](link) | Approved |
| User Stories | [PROJ-XXX](link) | Completed |

---

### 14.2 Technical Specifications (Generation & Assertion Specs)

**Description:** Developer specifications for AI-assisted development workflow. Captures the **"HOW"** - implementation decisions, API contracts, data models, and validation criteria.

**What to Include:**
- **GENSPEC** - Generation Specification: Detailed specs used as AI/Cursor prompts for code generation
- **ASSERT** - Assertion Specification: Test criteria for AI-driven validation of generated code
- API Specifications
- Database Schema Design
- QA Documentation
- Implementation Notes

**Links:**
| Document | Link | Version |
|----------|------|---------|
| Generation Spec | `docs/technical-specs/[feature]/GENSPEC_[feature]_v1.md` | v1.0 |
| Assertion Spec | `docs/technical-specs/[feature]/ASSERT_[feature]_v1.md` | v1.0 |
| QA Document | `docs/technical-specs/[feature]/QA_[feature]_v1.md` | v1.0 |

---

### 14.3 Architecture Decision Records (ADR/HLD/LLD)

**Description:** Architecture decisions made during implementation. Captures **"WHY this design"** - how this feature fits into the existing architecture, integration points, trade-offs, and alternatives considered.

**What to Include:**
- Architecture Decision Records (ADR)
- High-Level Design (HLD)
- Low-Level Design (LLD)
- System integration diagrams
- Component interaction flows
- Design trade-off analysis

**Links:**
| Document | Link | Decision Date |
|----------|------|---------------|
| ADR - [Decision Title] | `docs/architecture/ADR_XXX_[title].md` | YYYY-MM-DD |
| HLD - System Overview | `docs/architecture/HLD_[feature].md` | YYYY-MM-DD |
| LLD - Component Design | `docs/architecture/LLD_[component].md` | YYYY-MM-DD |

---

### 14.4 Release Notes & User Guides

**Description:** Release documentation and user-facing guides. Captures **"WHAT's new"** - release notes, feature guides, and user manuals for end-users and administrators.

**What to Include:**
- Release Notes (What's New, Fixed, Changed)
- User Guides / Feature Walkthroughs
- Admin Configuration Guides
- Migration Guides (if applicable)
- FAQ / Troubleshooting

**Links:**
| Document | Link | Version |
|----------|------|---------|
| Release Notes | `docs/user-manuals/RELEASE_vX.X_notes.md` | vX.X |
| User Guide | `docs/user-manuals/USER_[feature]_guide.md` | v1.0 |
| Admin Guide | `docs/user-manuals/GUIDE_admin_[feature].md` | v1.0 |

---

### 14.5 Knowledge Base & Runbooks

**Description:** Developer notes, lessons learned, and operational procedures. Captures **"LESSONS"** - issues encountered, solutions, and operational runbooks.

**What to Include:**
- Development notes and issues faced
- Troubleshooting guides
- Deployment runbooks
- Incident response playbooks
- Performance tuning notes

**Links:**
| Document | Link | Last Updated |
|----------|------|--------------|
| Dev Notes | `docs/knowledge-base/NOTES_[feature]_issues.md` | YYYY-MM-DD |
| Runbook | `docs/knowledge-base/PLAYBOOK_[process].md` | YYYY-MM-DD |

---

### Documentation Folder Structure Reference

```
docs/
├── requirements/                      # Product Requirements (PRD/BRD)
│   └── [feature]/
│       ├── REQ_[feature]_v1.md
│       └── PRD_[feature]_v1.md
│
├── technical-specs/                   # Technical Specifications (TDD)
│   ├── [feature]/
│   │   ├── GENSPEC_[feature]_v1.md    # Generation Spec (AI code generation)
│   │   ├── GENSPEC_[feature]_v2.md    # Version iterations
│   │   ├── ASSERT_[feature]_v1.md     # Assertion Spec (AI-driven validation)
│   │   ├── QA_[feature]_v1.md         # QA questions & decisions
│   │   └── NOTES_[feature]_issues.md  # Implementation notes
│   └── templates/
│       ├── GENSPEC_TEMPLATE_v1.md
│       └── ASSERT_TEMPLATE_v1.md
│
├── architecture/                      # Architecture Decision Records
│   ├── ADR_001_[decision_title].md    # Individual ADRs
│   ├── HLD_system_overview.md         # High-level design
│   ├── LLD_[component].md             # Low-level design
│   └── [feature]/
│       └── ARCH_[feature]_design.md
│
├── user-manuals/                      # Release Notes & User Guides
│   ├── RELEASE_vX.X_notes.md          # Release notes per version
│   ├── USER_[feature]_guide.md        # End-user guides
│   └── GUIDE_admin_[feature].md       # Admin/config guides
│
└── knowledge-base/                    # Dev Notes & Runbooks
    ├── NOTES_dev_issues_encountered.md
    ├── NOTES_[feature]_lessons.md
    ├── PLAYBOOK_deployment_v1.md
    └── PLAYBOOK_incident_response.md
```

### File Naming Convention

| Prefix | Category | Purpose | Example |
|--------|----------|---------|---------|
| `REQ_` | Requirements | Business/Product requirements | `REQ_rbac_v1.md` |
| `PRD_` | Product Requirements Doc | Detailed PRD from PM | `PRD_user_auth_v1.md` |
| `GENSPEC_` | Generation Specification | AI code generation prompts | `GENSPEC_db_refactor_v1.md` |
| `ASSERT_` | Assertion Specification | AI-driven test validation | `ASSERT_rbac_v1.md` |
| `QA_` | QA Questions/Decisions | QA clarifications | `QA_rbac_v1.md` |
| `ADR_` | Architecture Decision Record | Design decisions | `ADR_001_use_postgres.md` |
| `HLD_` | High-Level Design | System architecture | `HLD_system_overview.md` |
| `LLD_` | Low-Level Design | Component design | `LLD_auth_service.md` |
| `ARCH_` | Architecture Document | Feature architecture | `ARCH_rbac_design.md` |
| `RELEASE_` | Release Notes | What's new/fixed/changed | `RELEASE_v2.1_notes.md` |
| `USER_` | User Guide | End-user documentation | `USER_admin_portal.md` |
| `GUIDE_` | Admin/Config Guide | Setup/config guides | `GUIDE_setup_v1.md` |
| `NOTES_` | Development Notes | Lessons learned | `NOTES_migration_issues.md` |
| `PLAYBOOK_` | Operational Runbook | Deployment/ops procedures | `PLAYBOOK_deploy_v1.md` |

</details>

---

## 15. Open Questions & Decisions

<details open>
<summary><strong>Click to expand</strong></summary>

> **Note:** For extensive Q&A, create a separate document: `QA/[feature]_questions.md`

### Q1: [Question Title]

| Field | Details |
|-------|---------|
| **Status** | 🟡 Pending / 🟢 Decided / 🔴 Blocked |
| **Priority** | P0/P1/P2 |
| **Impact** | [What this affects] |
| **Blocking** | [What this blocks] |

**Question:** [Clear question statement]

**Options:**
| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A | [Description] | [Pros] | [Cons] |
| B | [Description] | [Pros] | [Cons] |

**Recommendation:** [Recommended option with reasoning]

**Decision:** [Chosen option] - Decided by [Name] on [Date]

---

### Q2: [Next Question]

[Follow same structure]

</details>

---

## 16. Future Considerations

<details>
<summary><strong>Click to expand</strong></summary>

### 16.1 Potential Enhancements

- Enhancement 1
- Enhancement 2

### 16.2 Technical Debt

- Known limitation 1
- Known limitation 2

### 16.3 Follow-up Work

- [ ] Task 1 (link to future ticket)
- [ ] Task 2 (link to future ticket)

</details>

---

## 17. Developer Checklist

<details>
<summary><strong>Click to expand</strong></summary>

### 17.1 Backend Tasks

- [ ] Create core types/enums
- [ ] Create database migrations
- [ ] Create entity models
- [ ] Create repositories
- [ ] Create services
- [ ] Create controllers
- [ ] Add logging
- [ ] Add metrics

### 17.2 Frontend Tasks

- [ ] Create TypeScript types
- [ ] Create API client
- [ ] Create custom hooks
- [ ] Create components
- [ ] Add error handling
- [ ] Add loading states

### 17.3 DevOps Tasks

- [ ] Set up monitoring dashboards
- [ ] Configure alerts
- [ ] Prepare rollback scripts
- [ ] Document deployment runbook

</details>

---

## 18. Appendices

<details>
<summary><strong>Click to expand</strong></summary>

### 18.1 Glossary

| Term | Definition |
|------|------------|
| Term 1 | Definition |
| Term 2 | Definition |

### 18.2 Related Documents

| Document | Purpose |
|----------|---------|
| [Product Requirements](link) | Business requirements |
| [QA Document](link) | Open questions & decisions |
| [Test Specification](link) | Test cases and scenarios |
| [API Documentation](link) | Full API reference |

### 18.3 References

- External documentation links
- Library/framework documentation
- Related RFCs or design docs

</details>

---

## AI Implementation Notes

> **For AI Coding Assistants:** When implementing this specification:
> 
> 1. **Start with core types** - Create enums, constants, and interfaces first
> 2. **Build data layer** - Create migrations, entities, repositories
> 3. **Implement business logic** - Build services with proper error handling
> 4. **Add API endpoints** - Controllers with validation and authorization
> 5. **Implement frontend** - Types, API clients, hooks, components
> 6. **Follow checkpoint order** - Each checkpoint builds on previous ones
> 7. **Verify at each checkpoint** - Run verification steps before moving on
> 8. **Use structured logging** - Include operation name, user ID, resource ID
> 9. **Preserve existing functionality** - Don't break legacy code
> 10. **Ask for clarification** - Flag any ambiguous requirements

---

## AI Readiness Checklist

> **Use this checklist to verify the spec is ready for AI implementation**

| Category | Criterion | Status |
|----------|-----------|:------:|
| **Completeness** | All sections have content (not just placeholders) | ⬜ |
| **Completeness** | Data model fully defined with all columns | ⬜ |
| **Completeness** | All API endpoints documented | ⬜ |
| **Completeness** | Request/Response DTOs with validation annotations | ⬜ |
| **Completeness** | Dependencies section present | ⬜ |
| **Clarity** | No ambiguous requirements | ⬜ |
| **Clarity** | Technical terms defined in glossary | ⬜ |
| **Clarity** | Non-goals clearly stated | ⬜ |
| **Specificity** | File paths specified for all components | ⬜ |
| **Specificity** | Method signatures with JavaDoc | ⬜ |
| **Specificity** | Pseudocode for business logic | ⬜ |
| **Specificity** | Error codes and JSON examples defined | ⬜ |
| **Specificity** | Logging patterns defined | ⬜ |
| **Reversibility** | Each checkpoint has rollback instructions | ⬜ |
| **Testability** | Acceptance criteria are testable | ⬜ |
| **Testability** | Edge cases documented | ⬜ |

**Score:** ___ / 16 items checked = ___% AI Ready

---

**Document Status:** [Status]  
**Last Updated:** [Date]  
**Implementation Status:** [Not Started / In Progress / Completed]  
**Open Questions:** See `QA/[feature]_questions.md`