# Vectronyx AI Workbench — API Reference

This document provides the full API specification for **Vectronyx**, detailing both the Strawberry GraphQL endpoint and the REST authentication routes.

---

## 1. General API Conventions

- **Base URL**: `http://localhost:8000`
- **GraphQL Endpoint**: `http://localhost:8000/graphql`
- **REST Endpoints**: `http://localhost:8000/auth/*`
- **Authentication**: JWT tokens passed in the standard `Authorization` header:
  ```http
  Authorization: Bearer <token>
  ```
- **Content Type**: `application/json` (or `multipart/form-data` for file uploads).

---

## 2. REST Authentication Endpoints

### 2.1 User Registration (`POST /auth/signup`)

Registers a new user record in the database.

- **URL**: `/auth/signup`
- **Method**: `POST`
- **Content-Type**: `application/json`

**Request Payload**:
```json
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "password": "SecurePassword123!"
}
```

**Success Response (200 OK)**:
```json
{
  "message": "User created successfully"
}
```

**Error Responses**:
- `400 Bad Request`: `{"detail": "User already exists"}`
- `422 Unprocessable Entity`: Validation failure on missing or malformed fields.

---

### 2.2 User Login (`POST /auth/login`)

Authenticates an existing user and returns their profile details.

- **URL**: `/auth/login`
- **Method**: `POST`
- **Content-Type**: `application/json`

**Request Payload**:
```json
{
  "email": "jane@example.com",
  "password": "SecurePassword123!"
}
```

**Success Response (200 OK)**:
```json
{
  "message": "Login successful",
  "user": {
    "email": "jane@example.com",
    "name": "Jane Doe"
  }
}
```

**Error Responses**:
- `401 Unauthorized`: `{"detail": "User not found"}` or `{"detail": "Invalid password"}`

---

### 2.3 Health Check (`GET /`)

Simple liveness probe for load balancers and orchestrators.

- **URL**: `/`
- **Method**: `GET`

**Success Response (200 OK)**:
```json
{
  "message": "Backend running "
}
```

---

## 3. Strawberry GraphQL API (`POST /graphql`)

The core intelligence layer is exposed through a typed Strawberry GraphQL schema. An interactive GraphQL playground is accessible in your browser at `http://localhost:8000/graphql`.

### 3.1 Queries

#### `searchMemories`
Performs a semantic vector similarity search over previously indexed user memories.

```graphql
query SearchMemories($query: String!, $limit: Int) {
  searchMemories(query: $query, limit: $limit) {
    id
    content
    score
    createdAt
  }
}
```

**Variables**:
```json
{
  "query": "machine learning notes",
  "limit": 5
}
```

**Sample Response**:
```json
{
  "data": {
    "searchMemories": [
      {
        "id": 14,
        "content": "Prefers AdamW optimizer with cosine learning rate schedule",
        "score": 0.884,
        "createdAt": "2026-04-12T10:14:22Z"
      }
    ]
  }
}
```

---

#### `getResearchReport`
Fetches a previously completed research report by ID.

```graphql
query GetResearchReport($reportId: String!) {
  getResearchReport(reportId: $reportId) {
    id
    topic
    status
    summary
    sources {
      title
      url
      snippet
    }
    createdAt
  }
}
```

---

#### `analyzeQuery`
Queries an uploaded dataset using natural language.

```graphql
query AnalyzeQuery($datasetId: String!, $query: String!) {
  analyzeQuery(datasetId: $datasetId, query: $query) {
    insight
    pythonCode
    chartBase64
    summaryTable
  }
}
```

---

### 3.2 Mutations

#### `createMemory`
Ingests a new text memory, generates its 384d embedding, and stores it in FAISS and PostgreSQL.

```graphql
mutation CreateMemory($content: String!) {
  createMemory(content: $content) {
    id
    content
    createdAt
  }
}
```

**Variables**:
```json
{
  "content": "Working on Qwen2 and LLaMA 3.3 multi-agent architecture"
}
```

---

#### `startResearch`
Launches the autonomous ReAct research agent on a given topic.

```graphql
mutation StartResearch($topic: String!, $depth: Int) {
  startResearch(topic: $topic, depth: $depth) {
    id
    topic
    status
    reportMarkdown
    sourcesCount
    executionTimeMs
  }
}
```

**Variables**:
```json
{
  "topic": "Recent developments in vector databases 2026",
  "depth": 2
}
```

---

#### `uploadDataset`
Uploads a CSV dataset for analysis.

```graphql
mutation UploadDataset($file: Upload!) {
  uploadDataset(file: $file) {
    datasetId
    filename
    rowCount
    columnCount
    columns {
      name
      dtype
      nullCount
    }
  }
}
```

---

## 4. GraphQL Types Specification

```graphql
type MemoryItem {
  id: Int!
  content: String!
  userId: Int
  createdAt: String!
}

type MemorySearchResult {
  id: Int!
  content: String!
  score: Float!
  createdAt: String!
}

type ResearchSource {
  title: String!
  url: String!
  snippet: String!
}

type ResearchReport {
  id: String!
  topic: String!
  status: String!
  reportMarkdown: String!
  sources: [ResearchSource!]!
  sourcesCount: Int!
  executionTimeMs: Int!
}

type ColumnProfile {
  name: String!
  dtype: String!
  nullCount: Int!
  uniqueCount: Int
}

type DatasetProfile {
  datasetId: String!
  filename: String!
  rowCount: Int!
  columnCount: Int!
  columns: [ColumnProfile!]!
}

type AnalystResponse {
  insight: String!
  pythonCode: String
  chartBase64: String
  summaryTable: String
}
```

---

## 5. Error Envelope Specification

Vectronyx conforms to standard GraphQL error handling:

```json
{
  "errors": [
    {
      "message": "Resource not found or unauthorized",
      "locations": [{ "line": 2, "column": 3 }],
      "path": ["searchMemories"],
      "extensions": {
        "code": "UNAUTHORIZED",
        "timestamp": "2026-04-14T16:50:00Z"
      }
    }
  ],
  "data": null
}
```
