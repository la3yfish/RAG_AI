# Synthetic Data Schemas & Validity Rules (MVP)

This document defines minimal, implementation-ready schemas for the synthetic dataset used in **RAG_AI**.
It focuses on: **columns/types**, **keys/relations**, **validation rules**, and **generation rules**.

---

## 1) Canonical conventions (apply to all datasets)

### 1.1 Identifiers

- **Employee IDs**: `emp_\d{3}` (e.g., `emp_020`)
- **Project IDs**: `proj_\d{3}` (e.g., `proj_012`)
- **Document IDs**: file-like stable ids (e.g., `company_passport.md`, `sales_report_Q3_2025.pdf`) or UUIDs.

### 1.2 Dates

- ISO date: `YYYY-MM-DD`
- ISO timestamp (when needed): `YYYY-MM-DDTHH:MM:SSZ`

### 1.3 Currencies

Use 3-letter codes (as in the current synthetic set): `RUB`, `USD`, `EUR`, `CNY`, `KRW`.

### 1.4 Access level metadata (RAG governance)

Every ingested document must have `access_level ∈ {public, internal, confidential}` and (optionally) `department` metadata for retrieval filters. (See project Knowledge Base.)

---

## 2) Structured datasets (CSV)

### 2.1 `employees.csv`

**Purpose**: internal HR dataset (33 employees), used for analytics, permissions scoping, and assignment links.

#### Schema

| column              | type   | required | constraints / meaning                                                                              |
| ------------------- | ------:| --------:| -------------------------------------------------------------------------------------------------- |
| `employee_id`       | string | yes      | PK; pattern `emp_\d{3}`                                                                            |
| `first_name`        | string | yes      | Latin given name                                                                                   |
| `last_name`         | string | yes      | Latin family name                                                                                  |
| `full_name`         | string | yes      | `"{first_name} {last_name}"` (or equivalent)                                                       |
| `full_name_native`  | string | yes      | Name in native script                                                                              |
| `script`            | enum   | yes      | `latin` \| `cyrillic` (extendable)                                                                 |
| `department_code`   | enum   | yes      | `sales` \| `engineering` \| `procurement_logistics` \| `quality_claims` \| `finance_admin` \| `hr` |
| `position`          | string | yes      | Human-readable job title                                                                           |
| `role_code`         | enum   | null     | no                                                                                                 |
| `manager_id`        | string | null     | no                                                                                                 |
| `employment_status` | enum   | yes      | `active` \| `terminated`                                                                           |
| `hire_date`         | date   | yes      | `YYYY-MM-DD`                                                                                       |
| `termination_date`  | date   | null     | no                                                                                                 |

#### Validation (must-pass)

- `employee_id` unique.
- If `manager_id` is not null, it must exist as an `employee_id` and must not form cycles (basic acyclic org chart).
- `termination_date`:
  - required when `employment_status="terminated"`;
  - must be `>= hire_date`;
  - must be null when `employment_status="active"`.
- `script` consistent with `full_name_native` (soft check; warning-only in MVP).

#### Generation rules (when adding rows)

- Keep department headcount plausible (do not over-concentrate in one department).
- Ensure at least:
  - 1 CEO, 1 CFO
  - 1 department head for Sales / Engineering / Procurement&Logistics / Quality&Claims / HR
- Create a shallow management tree (depth 2–4), avoid cycles.

---

### 2.2 `client_projects.csv`

**Purpose**: portfolio of client projects (12), referenced by text reports and used for KPI queries.

#### Schema

| column              | type   | required | constraints / meaning                            |
| ------------------- | ------:| --------:| ------------------------------------------------ |
| `project_id`        | string | yes      | PK; pattern `proj_\d{3}`                         |
| `client_name`       | string | yes      | Client org name                                  |
| `start_date`        | date   | yes      | `YYYY-MM-DD`                                     |
| `end_date`          | date   | null     | no                                               |
| `status`            | enum   | yes      | `active` \| `completed` \| `on_hold`             |
| `budget`            | int    | yes      | Positive integer (minor units not used)          |
| `currency`          | enum   | yes      | `RUB` \| `USD` \| `EUR` \| `CNY` \| `KRW`        |
| `assigned_employee` | string | yes      | FK → `employees.employee_id` (responsible owner) |

#### Validation (must-pass)

- `project_id` unique.
- `start_date <= end_date` when `end_date` not null.
- Status/date consistency:
  - `completed` ⇒ `end_date` not null.
  - `active` ⇒ `end_date` may be null or future-dated.
  - `on_hold` ⇒ `end_date` usually null (warning if set).
- `assigned_employee` must exist in `employees.csv` (FK).
- `budget > 0`.

#### Generation rules (when adding projects)

- Ensure at least 3 statuses are represented across the dataset (active/completed/on_hold).
- Add multi-currency edge cases (rare currencies in the set: `CNY`, `KRW`) to test parsing and formatting.
- Keep client names consistent with other documents (reports/contracts) when linking.

---

## 3) Semi-structured / document datasets

### 3.1 `projects_report.md`

**Purpose**: narrative report that repeats project facts (id, dates, budget, owner) and adds unstructured fields (risks/success).

**Observed fields**: project blocks contain `proj_###`, client name, start/end dates, budget + currency, responsible employee id, status, description, and optional risks/success notes. (See file content.) 

#### Extracted table schema (for normalization)

Normalize each project block into a row:

| field                       | type   | required | notes                                                   |
| --------------------------- | ------:| --------:| ------------------------------------------------------- |
| `project_id`                | string | yes      | FK → `client_projects.project_id`                       |
| `client_name`               | string | yes      | should match `client_projects.client_name` (soft check) |
| `start_date`                | date   | yes      |                                                         |
| `end_date`                  | date   | null     | no                                                      |
| `budget_amount`             | int    | yes      | parse from text                                         |
| `budget_currency`           | enum   | yes      | `RUB                                                    |
| `responsible_employee_id`   | string | yes      | FK → `employees.employee_id`                            |
| `responsible_position_hint` | string | null     | no                                                      |
| `status_text`               | string | yes      | keep raw status phrase (map to enum in analytics)       |
| `description`               | string | null     | no                                                      |
| `risks`                     | string | null     | no                                                      |
| `success_notes`             | string | null     | no                                                      |

#### Validation (must-pass for extracted facts)

- Every `project_id` in this report must exist in `client_projects.csv`.
- Every `responsible_employee_id` must exist in `employees.csv`.
- Currency parsing must yield one of the allowed currency codes.

#### Generation rules (when extending report)

- Keep the report consistent with `client_projects.csv` (ids, dates, budgets).
- Include at least 2–3 "corner cases":
  - missing end date but status says "завершение планируется"
  - unusual currency mention
  - ambiguous status wording (to test mapping)

---

### 3.2 `company_passport.md`

**Purpose**: company reference doc (synthetic enterprise context). Includes company profile, business lines, import geography, departments, and KPI list.

#### Minimal normalized schema

Represent as a single JSON-like object (or `Document.content_text` with extracted metadata):

- `company_name`: string
- `legal_form`: string
- `hq_city`: string
- `employee_count`: int (expected: 33)
- `business_type`: enum (e.g., `B2B`)
- `contacts`: object { address, phone, email, site, telegram }
- `business_directions[]`: list of strings
- `import_countries[]`: list of strings (e.g., China/Taiwan/South Korea/Indonesia)
- `departments[]`: list of objects:
  - `department_name`: string (Russian)
  - `department_code`: enum aligned with `employees.department_code`
  - `functions[]`: list of strings
- `kpi_catalog`: object with keys:
  - `commercial[]`, `operational[]`, `financial[]`, `hr[]`

#### Validation (must-pass)

- Declared `employee_count` should match the number of rows in `employees.csv` (warning if mismatch in MVP).
- `departments[].department_code` must be within the known enum used by `employees.csv`.

#### Generation rules

- Keep department list aligned to HR dataset codes.
- Ensure KPIs cover at least: sales volume, lead time, complaints %, revenue, headcount.

---

### 3.3 `contract_sample.docx`

**Purpose**: legal/operations sample contract; used to test DOCX parsing and extraction of key business entities.

#### Extractable entities (minimal)

Normalize to:

| field                  | type   | required | notes                          |
| ---------------------- | ------:| --------:| ------------------------------ |
| `contract_number`      | string | yes      | e.g., `001/2025`               |
| `contract_type`        | string | yes      | e.g., `supply_contract`        |
| `signed_city`          | string | yes      |                                |
| `signed_date`          | date   | yes      |                                |
| `supplier_name`        | string | yes      | `ООО «ЮнитТек» (UnitTech LLC)` |
| `buyer_name`           | string | yes      | e.g., `Завод «Электроника»`    |
| `total_amount`         | int    | yes      | parse number                   |
| `currency`             | enum   | yes      | likely `RUB` here              |
| `delivery_deadline`    | date   | yes      |                                |
| `delivery_address`     | string | yes      |                                |
| `payment_terms`        | string | yes      | e.g., `30 days after delivery` |
| `warranty_months`      | int    | yes      | e.g., `12`                     |
| `penalty_rate_per_day` | float  | yes      | e.g., `0.1%`                   |

#### Validation (must-pass)

- Dates must parse; `delivery_deadline >= signed_date`.
- Amount positive.
- If buyer name matches a known client in other datasets, keep spelling consistent (soft check).

#### Generation rules

- Keep at least one contract that matches a client from `projects_report.md` for cross-document linking.

---

### 3.4 `sales_report_Q3_2025.pdf`

**Purpose**: sales KPI report; tests PDF parsing, table extraction, and chart-description handling.

#### Extracted table schema

From the report’s client table:

| field              | type   | required |
| ------------------ | ------:| --------:|
| `client_name`      | string | yes      |
| `sales_volume_rub` | int    | yes      |
| `orders_count`     | int    | yes      |
| `avg_check_rub`    | int    | yes      |

#### Extracted KPI schema

- `period`: string (e.g., `Q3 2025`)
- `total_sales_rub`: int
- `growth_qoq_pct`: float
- `customers_total`: int
- `customers_active`: int
- `avg_check_rub`: int
- `repeat_orders_pct`: float
- `complaints_pct`: float
- `monthly_sales_rub`: object { `jul`: int, `aug`: int, `sep`: int }
- `recommendations_text`: string

#### Validation (must-pass)

- Sum of monthly sales should equal (or be within rounding tolerance of) `total_sales_rub` (warning-level tolerance in MVP).
- Table client volumes should sum to `total_sales_rub` (warning-level; "Другие" aggregates).
- Percent fields in range `[0, 100]`.

#### Generation rules

- Keep "Другие" bucket for long-tail clients.
- Include at least one KPI that violates a target (e.g., complaints > target) to enable analytics recommendations.

---

## 4) Cross-dataset relationships (ERD-lite)

### 4.1 Core relations

- `client_projects.assigned_employee` → `employees.employee_id`
- `projects_report(project_id)` → `client_projects.project_id`
- `projects_report(responsible_employee_id)` → `employees.employee_id`

### 4.2 Consistency rules (recommended)

- Client names: maintain consistent spelling across:
  - `client_projects.csv`
  - `projects_report.md`
  - `sales_report_Q3_2025.pdf`
  - `contract_sample.docx`
- Department alignment:
  - employee department codes should map to `company_passport.md` departments list.

---

## 5) Corner cases to include intentionally (for robustness tests)

- CSV:
  - missing optional columns (simulate ingestion tolerance)
  - swapped column order
  - extra whitespace in ids/currency
- DOCX:
  - numbers with spaces as thousand separators (`10 000 000`)
  - different date formats (`15 июля 2025 г.` vs `2025-07-15`)
- PDF:
  - embedded tables vs plain text tables
  - chart-only page with caption text
- Text/MD:
  - status wording variants (to test mapping to enums)
  - missing end dates with "планируется"

---

## 6) Implementation notes (minimal)

- Ingestion should normalize all sources into the project `Document` schema; structured extracts (tables) are stored in `Document.tables`, and full text in `Document.content_text`.
- Analytics should rely on CSV + extracted tables; RAG should cite the original documents.


