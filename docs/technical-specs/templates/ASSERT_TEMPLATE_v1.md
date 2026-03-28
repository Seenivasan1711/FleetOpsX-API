# [Feature Name] – Test Specification

> **Template Purpose:** This template provides a comprehensive, structured approach to testing that enables both automated test execution and AI-assisted test implementation. Tests are organized by type (unit, integration, API) and severity (P0, P1, P2, P3) to prioritize testing efforts. Each test case is specific, measurable, and executable.

---

## Document Information

| Field | Value |
|-------|-------|
| **Feature Name** | [Short feature name] |
| **Status** | Draft / In Review / Approved / Executed |
| **Version** | X.Y |
| **Date** | YYYY-MM-DD |
| **Author** | [Name or Team] |
| **Reference** | [Link to technical spec] |
| **Test Environment** | Dev / Staging / Production |
| **Last Test Run** | [Date] |
| **Pass Rate** | [X / Y tests passing] |

---

## Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | YYYY-MM-DD | [Name] | Initial test spec |

---

## Test Severity Levels

| Severity | Description | Examples | Required for Release |
|----------|-------------|----------|---------------------|
| **P0** | Critical - Blocks release, security risk | Auth bypass, data loss, wrong permission grant | 100% passing |
| **P1** | High - Major functionality broken | Core feature fails, incorrect calculations | 100% passing |
| **P2** | Medium - Feature degraded but workaround exists | Cache issues, slow performance, logging failures | 95% passing |
| **P3** | Low - Minor issues, cosmetic | Error message text, response format, documentation | Not blocking |

---

## Test Coverage Summary

| Category | Total Tests | P0 | P1 | P2 | P3 | Pass | Fail | Skip |
|----------|-------------|----|----|----|----|------|------|------|
| Unit Tests | [X] | [X] | [X] | [X] | [X] | [X] | [X] | [X] |
| Integration Tests | [X] | [X] | [X] | [X] | [X] | [X] | [X] | [X] |
| API Tests | [X] | [X] | [X] | [X] | [X] | [X] | [X] | [X] |
| Security Tests | [X] | [X] | [X] | [X] | [X] | [X] | [X] | [X] |
| Performance Tests | [X] | [X] | [X] | [X] | [X] | [X] | [X] | [X] |
| **TOTAL** | **[X]** | **[X]** | **[X]** | **[X]** | **[X]** | **[X]** | **[X]** | **[X]** |

---

## Table of Contents

1. [Unit Tests](#1-unit-tests)
2. [Integration Tests](#2-integration-tests)
3. [API Endpoint Tests](#3-api-endpoint-tests)
4. [Business Logic Tests](#4-business-logic-tests)
5. [Authorization & Security Tests](#5-authorization--security-tests)
6. [Edge Cases & Error Handling Tests](#6-edge-cases--error-handling-tests)
7. [Data Migration Tests](#7-data-migration-tests-if-applicable)
8. [Performance Tests](#8-performance-tests)
9. [Frontend Tests](#9-frontend-tests)
10. [End-to-End Tests](#10-end-to-end-tests)

---

## 1. Unit Tests

<details>
<summary><strong>1.1 [Component/Class Name] Tests</strong></summary>

### Test Class

**File:** `src/test/java/com/company/ComponentNameTest.java`

**Setup:**
```java
@ExtendWith(MockitoExtension.class)
class ComponentNameTest {
    
    @Mock
    private DependencyService dependencyService;
    
    @InjectMocks
    private ComponentName componentName;
    
    @BeforeEach
    void setUp() {
        // Common setup for all tests
    }
}
```

### Test Cases

| ID | Test Case | Severity | Input | Expected Output | Implementation |
|----|-----------|----------|-------|-----------------|----------------|
| UT-COMP-001 | Method returns correct value for valid input | P0 | `validInput` | `expectedValue` | `@Test void testMethodName_ValidInput_ReturnsExpectedValue()` |
| UT-COMP-002 | Method throws exception for null input | P0 | `null` | `IllegalArgumentException` | `@Test void testMethodName_NullInput_ThrowsException()` |
| UT-COMP-003 | Method handles empty collection correctly | P1 | `emptyList()` | `empty result` | `@Test void testMethodName_EmptyList_ReturnsEmpty()` |

### Example Test Implementation

```java
@Test
void testMethodName_ValidInput_ReturnsExpectedValue() {
    // Given
    InputType input = new InputType("value");
    when(dependencyService.getData()).thenReturn(expectedData);
    
    // When
    ResultType result = componentName.methodName(input);
    
    // Then
    assertNotNull(result);
    assertEquals(expectedValue, result.getValue());
    verify(dependencyService, times(1)).getData();
}

@Test
void testMethodName_NullInput_ThrowsException() {
    // When & Then
    assertThrows(IllegalArgumentException.class, () -> {
        componentName.methodName(null);
    });
}
```

**Test Data:**
```java
// Fixture data used across tests
private static final InputType VALID_INPUT = new InputType("value");
private static final InputType INVALID_INPUT = new InputType("");
```

</details>

<details>
<summary><strong>1.2 [Next Component] Tests</strong></summary>

[Follow same structure as 1.1]

</details>

---

## 2. Integration Tests

<details>
<summary><strong>2.1 Database Integration Tests</strong></summary>

### Test Class

**File:** `src/test/java/com/company/repository/RepositoryNameIntegrationTest.java`

**Setup:**
```java
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Sql(scripts = "/test-data.sql", executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
class RepositoryNameIntegrationTest {
    
    @Autowired
    private RepositoryName repository;
    
    @Autowired
    private TestEntityManager entityManager;
}
```

### Test Cases

| ID | Test Case | Severity | Setup | Action | Expected Result |
|----|-----------|----------|-------|--------|-----------------|
| IT-DB-001 | Save entity persists all fields correctly | P0 | Empty DB | Save entity | Entity retrievable with correct values |
| IT-DB-002 | Find by ID returns correct entity | P0 | Entity exists | findById(id) | Entity returned |
| IT-DB-003 | Find by ID returns empty for non-existent | P1 | Empty DB | findById(999) | Optional.empty() |
| IT-DB-004 | Custom query returns filtered results | P1 | Multiple entities | findByStatus("active") | Only active entities |
| IT-DB-005 | Foreign key constraint prevents orphans | P0 | Related entity deleted | Save with FK | ConstraintViolationException |
| IT-DB-006 | Index is used for query | P2 | 1000 entities | Query with indexed field | Query < 50ms |

### Example Test Implementation

```java
@Test
void testSaveEntity_ValidData_PersistsCorrectly() {
    // Given
    Entity entity = new Entity();
    entity.setField1("value1");
    entity.setField2("value2");
    
    // When
    Entity saved = repository.save(entity);
    entityManager.flush();
    entityManager.clear();
    
    // Then
    Entity retrieved = repository.findById(saved.getId()).orElse(null);
    assertNotNull(retrieved);
    assertEquals("value1", retrieved.getField1());
    assertEquals("value2", retrieved.getField2());
}

@Test
void testForeignKeyConstraint_DeleteParent_ThrowsException() {
    // Given
    Parent parent = createParent();
    Child child = createChildWithParent(parent);
    
    // When & Then
    assertThrows(DataIntegrityViolationException.class, () -> {
        parentRepository.delete(parent);
        entityManager.flush();
    });
}
```

**Test Data:**
```sql
-- test-data.sql
INSERT INTO parent (id, name) VALUES (1, 'Test Parent');
INSERT INTO child (id, parent_id, name) VALUES (1, 1, 'Test Child');
```

</details>

<details>
<summary><strong>2.2 Service Integration Tests</strong></summary>

### Test Class

**File:** `src/test/java/com/company/service/ServiceNameIntegrationTest.java`

**Setup:**
```java
@SpringBootTest
@Transactional
class ServiceNameIntegrationTest {
    
    @Autowired
    private ServiceName service;
    
    @Autowired
    private RepositoryName repository;
    
    @BeforeEach
    void setUp() {
        repository.deleteAll();
    }
}
```

### Test Cases

| ID | Test Case | Severity | Scenario | Expected Behavior |
|----|-----------|----------|----------|-------------------|
| IT-SVC-001 | Service integrates with repository correctly | P0 | Call service method | Data persisted to DB |
| IT-SVC-002 | Service handles transaction rollback | P0 | Exception during save | No data committed |
| IT-SVC-003 | Service integrates with external API | P1 | Call external service | Correct data returned |
| IT-SVC-004 | Service handles cache correctly | P2 | Multiple calls | Second call from cache |

### Example Test Implementation

```java
@Test
void testServiceMethod_ValidInput_PersistsData() {
    // Given
    InputDto input = new InputDto("value");
    
    // When
    ResultDto result = service.processInput(input);
    
    // Then
    assertNotNull(result);
    assertEquals(1, repository.count());
    
    Entity entity = repository.findAll().get(0);
    assertEquals("value", entity.getField());
}

@Test
void testServiceMethod_ExceptionDuringProcess_RollsBack() {
    // Given
    InputDto input = new InputDto("invalid");
    long initialCount = repository.count();
    
    // When & Then
    assertThrows(BusinessException.class, () -> {
        service.processInput(input);
    });
    
    assertEquals(initialCount, repository.count());
}
```

</details>

---

## 3. API Endpoint Tests

<details>
<summary><strong>3.1 [Endpoint Path] Tests</strong></summary>

### Test Class

**File:** `src/test/java/com/company/controller/ControllerNameTest.java`

**Setup:**
```java
@WebMvcTest(ControllerName.class)
class ControllerNameTest {
    
    @Autowired
    private MockMvc mockMvc;
    
    @MockBean
    private ServiceName service;
    
    private ObjectMapper objectMapper = new ObjectMapper();
}
```

### Test Cases

| ID | Test Case | Severity | Request | Expected Status | Expected Response |
|----|-----------|----------|---------|-----------------|-------------------|
| API-EP-001 | GET endpoint returns data for valid ID | P0 | `GET /api/v1/resource/1` | 200 OK | Resource JSON |
| API-EP-002 | GET endpoint returns 404 for non-existent | P0 | `GET /api/v1/resource/999` | 404 NOT_FOUND | Error JSON |
| API-EP-003 | POST endpoint creates resource | P0 | `POST /api/v1/resource` + body | 201 CREATED | Created resource |
| API-EP-004 | POST endpoint validates required fields | P0 | `POST /api/v1/resource` (missing field) | 400 BAD_REQUEST | Validation errors |
| API-EP-005 | PUT endpoint updates resource | P0 | `PUT /api/v1/resource/1` + body | 200 OK | Updated resource |
| API-EP-006 | DELETE endpoint removes resource | P1 | `DELETE /api/v1/resource/1` | 204 NO_CONTENT | Empty |
| API-EP-007 | Unauthorized request returns 401 | P0 | No auth header | 401 UNAUTHORIZED | Error JSON |
| API-EP-008 | Forbidden request returns 403 | P0 | Wrong permission | 403 FORBIDDEN | Error JSON |

### Example Test Implementation

```java
@Test
void testGetResource_ValidId_Returns200() throws Exception {
    // Given
    Long resourceId = 1L;
    ResourceDto resource = new ResourceDto(resourceId, "value");
    when(service.getResource(resourceId)).thenReturn(resource);
    
    // When & Then
    mockMvc.perform(get("/api/v1/resource/{id}", resourceId)
            .header("X-USER-ID", "user123")
            .contentType(MediaType.APPLICATION_JSON))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.id").value(resourceId))
        .andExpect(jsonPath("$.field").value("value"));
    
    verify(service, times(1)).getResource(resourceId);
}

@Test
void testGetResource_NonExistent_Returns404() throws Exception {
    // Given
    Long resourceId = 999L;
    when(service.getResource(resourceId))
        .thenThrow(new ResourceNotFoundException("Resource not found"));
    
    // When & Then
    mockMvc.perform(get("/api/v1/resource/{id}", resourceId)
            .header("X-USER-ID", "user123")
            .contentType(MediaType.APPLICATION_JSON))
        .andExpect(status().isNotFound())
        .andExpect(jsonPath("$.code").value("NOT_FOUND"))
        .andExpect(jsonPath("$.message").exists());
}

@Test
void testCreateResource_ValidData_Returns201() throws Exception {
    // Given
    CreateResourceDto createDto = new CreateResourceDto("value");
    ResourceDto created = new ResourceDto(1L, "value");
    when(service.createResource(any())).thenReturn(created);
    
    String requestBody = objectMapper.writeValueAsString(createDto);
    
    // When & Then
    mockMvc.perform(post("/api/v1/resource")
            .header("X-USER-ID", "user123")
            .contentType(MediaType.APPLICATION_JSON)
            .content(requestBody))
        .andExpect(status().isCreated())
        .andExpect(jsonPath("$.id").value(1))
        .andExpect(jsonPath("$.field").value("value"));
}

@Test
void testCreateResource_MissingField_Returns400() throws Exception {
    // Given
    String invalidRequest = "{\"field\": \"\"}"; // Empty required field
    
    // When & Then
    mockMvc.perform(post("/api/v1/resource")
            .header("X-USER-ID", "user123")
            .contentType(MediaType.APPLICATION_JSON)
            .content(invalidRequest))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.code").value("BAD_REQUEST"))
        .andExpect(jsonPath("$.errors").isArray());
}
```

**Request/Response Examples:**

```json
// Valid POST request
{
  "field": "value",
  "nestedField": {
    "subField": "value"
  }
}

// Valid response
{
  "id": 1,
  "field": "value",
  "nestedField": {
    "subField": "value"
  },
  "createdAt": "2025-12-03T10:00:00Z"
}

// Error response
{
  "code": "BAD_REQUEST",
  "message": "Validation failed",
  "errors": [
    {
      "field": "field",
      "message": "must not be blank"
    }
  ]
}
```

</details>

---

## 4. Business Logic Tests

<details>
<summary><strong>4.1 [Business Rule] Tests</strong></summary>

### Test Cases

| ID | Test Case | Severity | Scenario | Input | Expected Output | Business Rule Verified |
|----|-----------|----------|----------|-------|-----------------|------------------------|
| BL-001 | Rule A is enforced | P0 | Condition X | Data Y | Result Z | Rule A specification |
| BL-002 | Rule B exception handling | P0 | Invalid condition | Invalid data | Exception thrown | Rule B specification |
| BL-003 | Rule C calculation correct | P1 | Standard case | Valid numbers | Correct calculation | Rule C formula |

### Example Test Implementation

```java
@Test
void testBusinessRule_StandardCase_CalculatesCorrectly() {
    // Given
    InputData input = new InputData(100, 0.15);
    
    // When
    Result result = service.applyBusinessRule(input);
    
    // Then
    assertEquals(85.0, result.getCalculatedValue(), 0.01);
    assertEquals("APPROVED", result.getStatus());
}

@Test
void testBusinessRule_EdgeCase_HandlesCorrectly() {
    // Given
    InputData input = new InputData(0, 0.0);
    
    // When
    Result result = service.applyBusinessRule(input);
    
    // Then
    assertEquals(0.0, result.getCalculatedValue());
    assertEquals("PENDING", result.getStatus());
}
```

</details>

---

## 5. Authorization & Security Tests

<details>
<summary><strong>5.1 Permission Tests</strong></summary>

### Test Cases

| ID | Test Case | Severity | User Role | Action | Resource | Expected Result |
|----|-----------|----------|-----------|--------|----------|-----------------|
| SEC-PERM-001 | Admin can access admin endpoint | P0 | ADMIN | GET | /api/v1/admin | 200 OK |
| SEC-PERM-002 | Non-admin cannot access admin endpoint | P0 | USER | GET | /api/v1/admin | 403 FORBIDDEN |
| SEC-PERM-003 | User can access own resources | P0 | USER | GET | /api/v1/users/me | 200 OK |
| SEC-PERM-004 | User cannot access other users' resources | P0 | USER | GET | /api/v1/users/other | 403 FORBIDDEN |

### Example Test Implementation

```java
@Test
@WithMockUser(roles = "ADMIN")
void testAdminEndpoint_AdminUser_Returns200() throws Exception {
    mockMvc.perform(get("/api/v1/admin/resource"))
        .andExpect(status().isOk());
}

@Test
@WithMockUser(roles = "USER")
void testAdminEndpoint_RegularUser_Returns403() throws Exception {
    mockMvc.perform(get("/api/v1/admin/resource"))
        .andExpect(status().isForbidden());
}
```

</details>

<details>
<summary><strong>5.2 Security Vulnerability Tests</strong></summary>

### Test Cases

| ID | Test Case | Severity | Attack Vector | Expected Behavior |
|----|-----------|----------|---------------|-------------------|
| SEC-VUL-001 | SQL injection prevention | P0 | SQL in input field | Query sanitized, no injection |
| SEC-VUL-002 | XSS prevention | P0 | Script tag in input | Content escaped |
| SEC-VUL-003 | CSRF protection | P0 | Request without CSRF token | Request rejected |
| SEC-VUL-004 | Rate limiting | P1 | 100 requests in 1 second | Rate limit enforced |
| SEC-VUL-005 | Information disclosure | P1 | Error message | No stack trace exposed |

### Example Test Implementation

```java
@Test
void testSqlInjection_MaliciousInput_Sanitized() {
    // Given
    String maliciousInput = "'; DROP TABLE users; --";
    
    // When
    List<Entity> result = service.searchByName(maliciousInput);
    
    // Then
    // Should return empty or normal results, not execute SQL
    assertNotNull(result);
    assertTrue(tableStillExists("users")); // Verify table wasn't dropped
}
```

</details>

---

## 6. Edge Cases & Error Handling Tests

<details>
<summary><strong>6.1 Edge Case Tests</strong></summary>

### Test Cases

| ID | Test Case | Severity | Edge Case | Expected Handling |
|----|-----------|----------|-----------|-------------------|
| EDGE-001 | Null input handling | P0 | null | Exception or default value |
| EDGE-002 | Empty string handling | P1 | "" | Validation error or empty result |
| EDGE-003 | Empty collection handling | P1 | emptyList() | Empty result, no exception |
| EDGE-004 | Maximum value handling | P2 | Integer.MAX_VALUE | Correct handling or overflow check |
| EDGE-005 | Concurrent modifications | P1 | Two simultaneous updates | Optimistic locking or last-write-wins |
| EDGE-006 | Missing related data | P1 | FK reference missing | Null check and graceful handling |

### Example Test Implementation

```java
@Test
void testMethod_NullInput_ThrowsException() {
    assertThrows(IllegalArgumentException.class, () -> {
        service.process(null);
    });
}

@Test
void testMethod_EmptyList_ReturnsEmpty() {
    List<Entity> result = service.processMultiple(Collections.emptyList());
    assertTrue(result.isEmpty());
}

@Test
void testMethod_ConcurrentUpdate_HandlesCorrectly() {
    // Given
    Entity entity = repository.save(new Entity("value"));
    Entity entity1 = repository.findById(entity.getId()).get();
    Entity entity2 = repository.findById(entity.getId()).get();
    
    // When
    entity1.setValue("new1");
    repository.save(entity1);
    
    entity2.setValue("new2");
    
    // Then
    assertThrows(OptimisticLockingFailureException.class, () -> {
        repository.save(entity2);
    });
}
```

</details>

---

## 7. Data Migration Tests (if applicable)

<details>
<summary><strong>7.1 Migration Execution Tests</strong></summary>

### Test Cases

| ID | Test Case | Severity | Scenario | Expected Result |
|----|-----------|----------|----------|-----------------|
| MIG-001 | Migration creates tables correctly | P0 | Run migration | Tables exist with correct schema |
| MIG-002 | Migration migrates data correctly | P0 | Run with existing data | Data transferred correctly |
| MIG-003 | Migration is idempotent | P0 | Run twice | Second run has no effect |
| MIG-004 | Migration preserves existing data | P0 | Run with data | No data loss |
| MIG-005 | Rollback works correctly | P0 | Run then rollback | Original state restored |

### Example Test Implementation

```java
@Test
@Sql(scripts = "/migration-test-data.sql")
void testMigration_ExistingData_MigratesCorrectly() {
    // Given - test data loaded from SQL script
    long countBefore = legacyRepository.count();
    
    // When
    migrationService.runMigration();
    
    // Then
    long countAfter = newRepository.count();
    assertEquals(countBefore, countAfter);
    
    // Verify data integrity
    List<NewEntity> migrated = newRepository.findAll();
    assertFalse(migrated.isEmpty());
    migrated.forEach(entity -> {
        assertNotNull(entity.getId());
        assertNotNull(entity.getMigratedField());
    });
}
```

</details>

---

## 8. Performance Tests

<details>
<summary><strong>8.1 Response Time Tests</strong></summary>

### Test Cases

| ID | Test Case | Severity | Scenario | Threshold | Expected Result |
|----|-----------|----------|----------|-----------|-----------------|
| PERF-001 | Single query response time | P2 | Query with index | < 50ms | Meets threshold |
| PERF-002 | API endpoint response time | P2 | Standard request | < 200ms | Meets threshold |
| PERF-003 | Batch operation performance | P2 | Process 1000 items | < 5 seconds | Meets threshold |
| PERF-004 | Cache hit rate | P2 | 100 requests | > 90% hit rate | Meets threshold |

### Example Test Implementation

```java
@Test
void testQueryPerformance_IndexedQuery_MeetsThreshold() {
    // Given
    create1000TestEntities();
    
    // When
    long startTime = System.currentTimeMillis();
    List<Entity> results = repository.findByIndexedField("value");
    long duration = System.currentTimeMillis() - startTime;
    
    // Then
    assertTrue(duration < 50, "Query took " + duration + "ms, expected < 50ms");
    assertFalse(results.isEmpty());
}
```

</details>

---

## 9. Frontend Tests

<details>
<summary><strong>9.1 Component Tests</strong></summary>

### Test File

**File:** `src/components/__tests__/ComponentName.test.tsx`

### Test Cases

| ID | Test Case | Severity | Scenario | Expected Behavior |
|----|-----------|----------|----------|-------------------|
| FE-COMP-001 | Component renders correctly | P0 | Mount component | All elements visible |
| FE-COMP-002 | Component handles loading state | P1 | Data loading | Loading indicator shown |
| FE-COMP-003 | Component handles error state | P1 | API error | Error message displayed |
| FE-COMP-004 | Component handles user interaction | P0 | Button click | Callback fired |

### Example Test Implementation

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ComponentName } from './ComponentName';

describe('ComponentName', () => {
  it('renders correctly with valid props', () => {
    // Given
    const props = { field: 'value' };
    
    // When
    render(<ComponentName {...props} />);
    
    // Then
    expect(screen.getByText('Expected Text')).toBeInTheDocument();
  });
  
  it('handles button click correctly', async () => {
    // Given
    const onAction = jest.fn();
    render(<ComponentName onAction={onAction} />);
    
    // When
    fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
    
    // Then
    await waitFor(() => {
      expect(onAction).toHaveBeenCalledTimes(1);
    });
  });
  
  it('displays loading state while fetching data', () => {
    // Given - API is slow
    const { rerender } = render(<ComponentName loading={true} />);
    
    // Then
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    
    // When - loading completes
    rerender(<ComponentName loading={false} data={mockData} />);
    
    // Then
    expect(screen.queryByTestId('loading-spinner')).not.toBeInTheDocument();
    expect(screen.getByText(mockData.title)).toBeInTheDocument();
  });
});
```

</details>

---

## 10. End-to-End Tests

<details>
<summary><strong>10.1 User Flow Tests</strong></summary>

### Test Cases

| ID | Test Case | Severity | User Flow | Steps | Expected Result |
|----|-----------|----------|-----------|-------|-----------------|
| E2E-001 | Complete happy path flow | P0 | User creates resource | 1. Login 2. Navigate 3. Create 4. Verify | Resource created successfully |
| E2E-002 | Error recovery flow | P1 | User encounters error and recovers | 1. Trigger error 2. See error message 3. Retry | Successful on retry |

### Example Test Implementation

```typescript
// Cypress or Playwright test
describe('Resource Creation Flow', () => {
  it('allows user to create a resource end-to-end', () => {
    // Given - logged in user
    cy.login('testuser', 'password');
    
    // When
    cy.visit('/resources');
    cy.get('[data-testid="create-button"]').click();
    cy.get('[data-testid="name-input"]').type('Test Resource');
    cy.get('[data-testid="description-input"]').type('Test Description');
    cy.get('[data-testid="submit-button"]').click();
    
    // Then
    cy.url().should('include', '/resources/');
    cy.contains('Test Resource').should('be.visible');
    cy.contains('Resource created successfully').should('be.visible');
  });
});
```

</details>

---

## Test Data Setup

<details>
<summary><strong>Fixtures & Test Data</strong></summary>

### Database Test Data

**File:** `src/test/resources/test-data.sql`

```sql
-- Users
INSERT INTO users (id, username, email, role) VALUES 
  (1, 'testadmin', 'admin@test.com', 'ADMIN'),
  (2, 'testuser', 'user@test.com', 'USER');

-- Resources
INSERT INTO resources (id, name, user_id, status) VALUES
  (100, 'Test Resource 1', 1, 'ACTIVE'),
  (101, 'Test Resource 2', 2, 'ACTIVE'),
  (102, 'Test Resource 3', 2, 'INACTIVE');
```

### Java Test Fixtures

**File:** `src/test/java/com/company/fixtures/EntityFixtures.java`

```java
public class EntityFixtures {
    
    public static Entity createValidEntity() {
        return Entity.builder()
            .field1("value1")
            .field2("value2")
            .status("ACTIVE")
            .build();
    }
    
    public static Entity createInvalidEntity() {
        return Entity.builder()
            .field1(null) // Invalid - required field
            .build();
    }
}
```

### TypeScript Test Data

**File:** `src/test/fixtures/entities.ts`

```typescript
export const mockEntity: EntityType = {
  id: 1,
  field: 'value',
  status: 'active',
  createdAt: '2025-12-03T10:00:00Z',
};

export const mockEntityList: EntityType[] = [
  mockEntity,
  { ...mockEntity, id: 2, field: 'value2' },
];
```

</details>

---

## Test Execution Instructions

<details>
<summary><strong>How to Run Tests</strong></summary>

### Run All Tests

```bash
# Backend (Maven)
mvn clean test

# Backend (Gradle)
./gradlew test

# Frontend (npm)
npm test

# Frontend (specific test file)
npm test -- ComponentName.test.tsx
```

### Run Tests by Category

```bash
# Unit tests only
mvn test -Dtest=**/*Test

# Integration tests only
mvn test -Dtest=**/*IntegrationTest

# API tests only
mvn test -Dtest=**/*ApiTest
```

### Run Tests by Severity

```bash
# P0 tests only (using JUnit 5 tags)
mvn test -Dgroups=P0

# P0 and P1 tests
mvn test -Dgroups="P0 | P1"
```

### Generate Test Coverage Report

```bash
# Backend (JaCoCo)
mvn clean test jacoco:report
# Report at: target/site/jacoco/index.html

# Frontend (Jest)
npm test -- --coverage
# Report at: coverage/lcov-report/index.html
```

### CI/CD Integration

```yaml
# Example GitHub Actions workflow
name: Run Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Backend Tests
        run: mvn clean test
      - name: Run Frontend Tests
        run: npm test
      - name: Upload Coverage
        uses: codecov/codecov-action@v2
```

</details>

---

## Test Metrics & Reporting

<details>
<summary><strong>Coverage & Quality Metrics</strong></summary>

### Coverage Goals

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Line Coverage | 80% | [X%] | 🟢 / 🟡 / 🔴 |
| Branch Coverage | 75% | [X%] | 🟢 / 🟡 / 🔴 |
| Method Coverage | 85% | [X%] | 🟢 / 🟡 / 🔴 |
| Class Coverage | 90% | [X%] | 🟢 / 🟡 / 🔴 |

### Test Execution Metrics

| Metric | Value |
|--------|-------|
| Total Tests | [X] |
| Passing | [X] |
| Failing | [X] |
| Skipped | [X] |
| Average Duration | [X]s |
| Slowest Test | [Test Name] ([X]s) |

### Known Issues

| Issue | Severity | Test ID | Status | Workaround |
|-------|----------|---------|--------|------------|
| [Description] | P2 | UT-XXX-001 | Open | [Workaround] |

</details>

---

## AI Test Implementation Notes

> **For AI Coding Assistants:** When implementing tests from this specification:
> 
> 1. **Start with P0 tests** - These are critical and must pass
> 2. **Follow the naming convention** - Use test IDs and descriptive names
> 3. **Include all test phases** - Given, When, Then (Arrange, Act, Assert)
> 4. **Use fixtures** - Create reusable test data
> 5. **Mock external dependencies** - Don't test external services
> 6. **Test both success and failure paths** - Include error cases
> 7. **Make tests independent** - Each test should run standalone
> 8. **Clean up after tests** - Reset state in @AfterEach or teardown
> 9. **Use meaningful assertions** - Assert specific values, not just "not null"
> 10. **Document complex test logic** - Add comments for non-obvious tests
> 11. **Run tests frequently** - After each implementation phase
> 12. **Update test counts** - Keep coverage summary current

---

**Document Status:** [Status]  
**Last Updated:** [Date]  
**Test Execution Status:** [X / Y tests passing]

