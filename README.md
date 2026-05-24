# Labh Offset — Print Shop Management System

A full-stack, mobile-responsive web application that replaces a complex 9-sheet Microsoft Excel workbook for **Labh Offset** (Ahmedabad, India). The system automates and streamlines print job scheduling, live paper stock tracking, party/company stock ledger audits, job card routing, and inward/outward registers.

The system is optimized for local LAN access (so shop floor operators can update statuses on their phones) or seamless cloud hosting on platforms like Render.

---

## Current Build Status

| Layer | Status | Key Components |
|-------|--------|----------------|
| **Migration** | ✅ 100% Complete | [migrate.py](file:///c:/Users/asmit/Desktop/labhOffset/migrate.py) imports all historical client records, paper masters, job details, and stock registers. |
| **Database** | ✅ 100% Complete | SQLite locally ([labh_offset.db](file:///c:/Users/asmit/Desktop/labhOffset/labh_offset.db)) with seamless environment variable switch to PostgreSQL for server deployment. |
| **Backend** | ✅ 100% Complete | FastAPI application, strict schema verification, live computed stock logic, and automated stock pipelines. |
| **Frontend** | ✅ 100% Complete | Mobile-first vanilla HTML/CSS/JS with cohesive bottom nav, sticky section cards, toast alerts, dynamic color themes, and automatic formula calculations. |
| **PDF Generation** | ✅ 100% Complete | jinja2 templates compiled into high-resolution printable PDFs via **WeasyPrint** at `/api/jobs/{id}/pdf`. |
| **Web Slips Print** | ✅ 100% Complete | Custom web print layout ([print.html](file:///c:/Users/asmit/Desktop/labhOffset/static/print.html)) with print-media styling, perfectly optimized for browser A4 physical print. |
| **Caching & PWA** | ✅ 100% Complete | Strict `NO_CACHE` headers served by FastAPI for HTML routes, preventing sticky browser inputs and service-worker sync issues. |

---

## Project Directory Tree

```
labh-offset/
  ├── main.py                  ← FastAPI entry point & HTTP headers middleware
  ├── database.py              ← SQLAlchemy engine/session config (SQLite/PostgreSQL)
  ├── models.py                ← ORM mapping classes (Parties, Papers, Jobs, Inward, Outward, etc.)
  ├── schemas.py               ← Pydantic models for request validation and response contracts
  ├── migrate.py               ← Excel-to-SQLite bulk migrator (Latest_data.xlsx → SQLite)
  ├── requirements.txt         ← Python environment dependencies
  │
  ├── routers/                 ← Modular backend API endpoints
  │     ├── jobs.py            ← Job lifecycle, auto-outward pipelines, fuzzy search filters
  │     ├── jobcard.py         ← WeasyPrint PDF compiled output generator
  │     ├── stock.py           ← Live stock audits, ledger histories, dashboard stats
  │     ├── inward.py          ← Inward challan tracking and arrival logger
  │     ├── outward.py         ← Read-only outward register entries (auto-managed)
  │     ├── masters.py         ← Parties, paper codes, and operators CRUD
  │     ├── pending.py         ← Live shop floor queue queue filters
  │     └── backups.py         ← Automated & manual database archiving pipelines
  │
  ├── pdf/                     ← Server-side A4 slip generation
  │     ├── generator.py       ← Jinja2 layout rendering & WeasyPrint compilation
  │     └── templates/
  │           └── job_card.html ← A4 portrait paper template with cut-marks
  │
  └── static/                  ← Premium Vanilla HTML/CSS/JS frontend
        ├── index.html         ← Dashboard with analytics, low-stock metrics, and job states
        ├── entry.html         ← New job entry form with real-time stock-adequacy indicators
        ├── edit.html          ← Full job details editor featuring the auto-calc formula engine
        ├── jobcard.html       ← Job card search & visual block display
        ├── print.html         ← Dedicated browser print dialog template for A4 slips
        ├── inward.html        ← Log paper received (with arrived vs pending status)
        ├── stock.html         ← Stock balances, available catalog, and low stock thresholds
        ├── ledger.html        ← Party transactional ledger (chronological + running balance)
        ├── pending.html       ← Shop floor machine-queue and status cycler
        ├── masters.html       ← Manage clients, paper masters, and shop staff
        ├── settings.html      ← Color theme selector (Light vs Dark)
        ├── backups.html       ← Visual management interface for downloading system backups
        │
        ├── style.css          ← Core design system (DM Sans font, responsive variables, animations)
        ├── theme.js           ← Non-flash head script maintaining theme state
        ├── manifest.json      ← PWA installation profile
        └── sw.js              ← Service worker for local app installation
```

---

## Key Technical Mechanisms

### 1. Live Stock Engine (Live Auditing)
To ensure absolute accuracy, paper stock balances are **never stored as values**. Instead, they are calculated in real-time by querying the database's inward and outward records:
$$\text{Live Balance} = \sum(\text{Inward Received Sheets}) - \sum(\text{Outward Consumed Sheets})$$

*   **Party Stock**: Paper provided directly by clients (linked to `party_code`).
*   **Company Stock**: Paper purchased/owned by Labh Offset (`party_code` is `NULL`).
*   **Arrived vs. Pending Inwards**: Inward records can have a `status` of `'received'` or `'pending'`. Only `'received'` paper is counted toward available stock. When a pending shipment physically arrives, the operator clicks **Mark as Arrived**, instantly updating the stock balance.

### 2. Auto-Outward Pipeline
Operators never write or modify outward transactions manually. 
*   When a job is created and has sufficient paper, the system **auto-generates an outward record** with matching specifications (`used_sheets = total_sheets`).
*   When a job details form is modified (e.g., changes paper type, size, or reams), the matching outward record is **automatically synchronized** in the same database transaction.
*   When a job is soft-deleted, its associated outward entry is **permanently purged**, instantly releasing those sheets back into the available stock catalog.

### 3. Job Waiting & Activation Lifecycle
If a job is added but the required stock is insufficient, or if the client hasn't sent the paper yet:
*   The job is marked as `is_waiting_for_paper = True` and its status is set to `'pending'`.
*   An outward entry is created upon creation but is automatically updated/synchronized when the job is activated.
*   Once the paper arrives (logged via the Inward Register), the operator opens the Pending List and hits **Activate Job** (`POST /api/jobs/{id}/activate`). This clears the waiting flag, runs a real-time stock-adequacy check, updates the status to `'in_progress'`, and safely synchronizes the existing outward record (preventing duplicate outward entries and database unique constraint violations).

### 4. Advanced BI Search & Fuzzy Filters
The jobs listing endpoint (`GET /api/jobs`) integrates advanced querying:
*   **Time-Filters**: Quick scopes for `today`, `last_7`, `last_30`, `curr_month`, `prev_month`, `curr_year`, `prev_year`, and `custom` date ranges.
*   **Fuzzy Global Query**: Fuzzy searches across party names, party codes, job names, bill numbers, and remarks in a single search bar.
*   **Paper Query**: Directly isolate jobs using specific codes, sizes, or GSMs.
*   **Sub-Record Scopes**: Filters to locate jobs based on lamination status (`has_lam`) or punching status (`has_punch`).

### 5. Automated Database Archival
The system safeguards data via an integrated backup scheduler:
*   **Cron-based Automations**: Configured to run silently every night to dump the SQLite/PostgreSQL database into an encrypted snapshot.
*   **Background Jobs Threading**: Manual backups triggered via the API (`/api/backups/generate`) execute via Python's `threading.Thread`, preventing HTTP request timeouts during heavy snapshot operations.
*   **History Logs**: Complete audit trail of past successful database snapshots accessible through the frontend.

---

## Database Schema (SQLite / PostgreSQL)

### `parties` (Clients Master)
*   `party_code` (TEXT PRIMARY KEY) - e.g., `"amdatu"`
*   `party_name` (TEXT NOT NULL) - e.g., `"ATUL ENTERPRISE"`
*   `phone` / `email` / `address` (TEXT)
*   `is_active` (INTEGER, Default `1`)
*   `created_at` (TEXT)

### `paper_master` (Paper Types Master)
*   `paper_code` (TEXT PRIMARY KEY) - e.g., `"300gac"`
*   `description` (TEXT NOT NULL) - e.g., `"300 GSM ART CARD"`
*   `gsm` (INTEGER)
*   `category` (TEXT)
*   `is_active` (INTEGER, Default `1`)

### `operators` (Machine Operators)
*   `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
*   `name` (TEXT UNIQUE)
*   `role` / `is_active` (TEXT / INTEGER)

### `jobs` (Core Print Job Records)
*   `job_id` (INTEGER PRIMARY KEY)
*   `date` (TEXT NOT NULL) - `YYYY-MM-DD`
*   `year` / `month` (INTEGER) - Auto-extracted
*   `party_code` (TEXT FK `parties.party_code`)
*   `party_name` (TEXT NOT NULL) - Denormalized for rapid load
*   `job_name` (TEXT NOT NULL)
*   `bill_no` / `ctcp_bill_no` / `job_remark` (TEXT)
*   `paper_code` (TEXT FK `paper_master.paper_code`)
*   `paper_size` (TEXT) - e.g., `"28x40"`
*   `gsm_desc` (TEXT)
*   `ream` / `sheet_per_ream` / `loose_sheets` / `total_sheets` (INTEGER)
*   `cut_size` (TEXT) / `qty` (INTEGER) / `cut_part` (INTEGER)
*   `printing` (TEXT) - `'s/s'`, `'f/b'`, `'f+b'`, etc.
*   `pulling` (TEXT) - Impressions, e.g., `"3100+3100"`
*   `set_no` (INTEGER, Default `1`)
*   `plate_size` (TEXT) - e.g., `"635x775"`
*   `plate_process` (TEXT) - e.g., `"CTCP"`
*   `operator_name` / `pulling_charge` (TEXT)
*   `paper_source` (TEXT, Default `'party'`) - `'party'` vs `'company'`
*   `status` (TEXT, Default `'pending'`) - `'pending'`, `'in_progress'`, `'done'`, `'deleted'`
*   `is_waiting_for_paper` (INTEGER/Boolean, Default `0`)
*   `created_at` / `updated_at` (TEXT)

### `lam_jobs` (Lamination Sub-Records, 1-to-1 with Job)
*   `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
*   `job_id` (INTEGER FK `jobs.job_id`)
*   `process` (TEXT) - e.g., `"Matt"`, `"Gloss"`, `"UV"`
*   `size` / `agency_name` / `operator_name` / `side` (TEXT)
*   `pulling` (INTEGER)
*   `op_amount` / `op_pay` (REAL)

### `punch_jobs` (Punching / Die Sub-Records, 1-to-1 with Job)
*   `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
*   `job_id` (INTEGER FK `jobs.job_id`)
*   `dye` / `size` / `gsm` (TEXT)
*   `qty` (INTEGER)
*   `agency` (TEXT)
*   `pay` (REAL)

### `inward` (Inward Stock Register)
*   `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
*   `ch_no` / `sr_no` (INTEGER)
*   `date` (TEXT NOT NULL)
*   `dch_no` (TEXT) - Supplier Delivery Challan
*   `supplier_name` (TEXT)
*   `paper_code` (TEXT FK `paper_master.paper_code`)
*   `paper_desc` / `paper_size` (TEXT)
*   `ream` / `sheet_per_ream` / `loose_sheets` / `total_sheets` (INTEGER)
*   `party_code` (TEXT FK `parties.party_code`, NULL if Company stock)
*   `stock_type` (TEXT, Default `'party'`) - `'party'` vs `'company'`
*   `notes` (TEXT)
*   `status` (TEXT, Default `'received'`) - `'received'` vs `'pending'`
*   `created_at` (TEXT)

### `outward` (Outward Stock Register, Read-Only)
*   `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
*   `job_id` (INTEGER UNIQUE FK `jobs.job_id`)
*   `date` (TEXT NOT NULL)
*   `sr_no` (INTEGER)
*   `party_code` / `party_name` / `job_name` (TEXT)
*   `paper_code` / `paper_name` / `paper_size` (TEXT)
*   `used_sheets` (INTEGER)
*   `stock_type` (TEXT) - `'party'` vs `'company'`

---

## API Documentation

### Jobs Endpoint Router (`/api/jobs`)
*   `GET /api/jobs` - Fetches jobs with fuzzy keywords, dates, operators, and sub-record filters.
*   `POST /api/jobs` - Appends a job. Triggers stock audits. Generates an auto-outward record if paper is available.
*   `GET /api/jobs/{id}` - Retrieves complete job details, eagerly resolving lamination and punching details.
*   `PUT /api/jobs/{id}` - Performs structural edits on jobs. Instantly updates associated auto-outward sheets.
*   `DELETE /api/jobs/{id}` - Soft-deletes a job. **Hard-purges** the associated outward record to free up stock.
*   `PATCH /api/jobs/{id}/status` - Quick status cycler (`'pending'` → `'in_progress'` → `'done'`).
*   `POST /api/jobs/{id}/activate` - Validates stock, clears `is_waiting_for_paper`, spawns outward logs, and moves state to `'in_progress'`.
*   `GET /api/jobs/{id}/card` - Pulls job slips structured data for browser layouts.
*   `GET /api/jobs/{id}/pdf` - Returns an A4 portrait printable PDF of the job card generated via WeasyPrint.

### Stock & Audits Router (`/api`)
*   `GET /api/stock` - Compiles a complete live-computed register of both party and company paper stock balances.
*   `GET /api/stock/check` - Real-time stock calculator utilized during job form typing (returns available sheets and adequacy statements).
*   `GET /api/stock/available` - Catalogues paper codes and sizes containing positive balances (`sheets > 0`).
*   `GET /api/stock/party/{code}` - Party Ledger API. Generates chronological statements with dynamic running balances.
*   `GET /api/stock/pending` - Lists inward shipments marked as `'pending'`.
*   `PATCH /api/stock/inward/{id}/status` - Transitions a pending inward challan's state to `'received'`, releasing stock.
*   `GET /api/dashboard` - Analytics package returning queue statistics, active operator jobs, and low stock warnings.

### Inward Challans Router (`/api/inward`)
*   `GET /api/inward` - Paginated lists of logged stock deliveries.
*   `POST /api/inward` - Creates inward shipments. Supports starting them as `'pending'` or `'received'`.
*   `PUT /api/inward/{id}` - Updates delivery challan fields.
*   `DELETE /api/inward/{id}` - Deletes inward deliveries, recalculating affected paper codes.

### Backups Router (`/api/backups`)
*   `GET /api/backups/logs` - Fetches the history of all completed system backups.
*   `POST /api/backups/generate` - Triggers an asynchronous manual background backup snapshot.

---

## Frontend Design & UX Architecture

### 1. Typography & Colors (DM Sans Design System)
*   **Color Palette**: Curved Harmony Theme. Custom-tuned CSS variables for HSL values:
    *   `--primary`: Deep Blue (`#1A56A0`)
    *   `--bg`: Premium canvas color (`#08090D` in Dark Mode, `#F7F8FC` in Light Mode)
    *   `--surface`: White cards (`#FFFFFF` in Light Mode, `#12141C` in Dark Mode)
    *   `--accent-success` (`#16A34A`), `--accent-warning` (`#D97706`), `--accent-danger` (`#DC2626`)
*   **Typography**: dm sans (Google Fonts). Highly legible on low-resolution smartphones.
*   **Micro-animations**: Smooth `cubic-bezier` hover reactions on button rows, chip states, and cards.

### 2. Dual Themes (Light / Dark Switcher)
*   Integrated theme controller toggling `data-theme="dark"` or `data-theme="light"` on the `html` tag.
*   The selection is saved in `localStorage` and immediately initialized using an inline blocker script ([theme.js](file:///c:/Users/asmit/Desktop/labhOffset/static/theme.js)) in the `<head>` of all pages, avoiding white background flashes.

### 3. Client-Side Formula Engine
The New/Edit forms integrate real-time automation to speed up input:
*   **Paper Area Calculator**: Typing `Ream`, `Sheet per Ream`, and `Loose Sheets` instantly computes the `Total Sheets` ($(\text{Ream} \times \text{S/Ream}) + \text{Loose}$).
*   **Cutting Grid Resolver**: Selecting `Cut Part` (1, 2, 3, or 4) and entering the `Cut Size` automatically calculates the `Result Size` (e.g. cutting 28x40 into 2 parts gives result size 20x28) and populates `Result Qty` ($\text{Total Sheets} \times \text{Cut Part}$).
*   **Plates & Pulling Planner**: Select printing type (S/S, F/B, F+B) to auto-fill plate count (e.g., 2 plates for F+B) and compute impressions (`Pulling`) for printing.

### 4. Dynamic & Polish UX Enhancements (Job Card & Inward)
*   **Smart Inward Mismatch Warnings**: When logging inward deliveries with mismatching paper properties relative to a specific job card, a custom glassmorphic warning prompts the operator to automatically sync the job's paper profile or keep it separate.
*   **Adaptive Section Visibility**: On the Job Card viewing page, optional sub-sections (Lamination, Punching/Die) are dynamically hidden if no data is present, preventing clutter.
*   **Remarks Highlighting**: Moved the critical job Remarks section high up on the job card (directly below the paper specifications) and rendered it inside a styled amber alert box.
*   **Premium Bottom Action Bar**: Redesigned all action buttons into a cohesive, floating glassmorphic action row with highlighted actions like A4 Slip Printing.

### 5. Mobile-First Responsive Design
*   **Responsive Data Tables**: All complex tabular data dynamically pivots into stacked, card-style layouts on mobile devices using `data-label` attributes, ensuring full readability without horizontal scrolling.
*   **Touch-Friendly Navigation**: A dedicated sticky bottom navigation bar provides instant access to core routes (Dashboard, New Job, Pending, Stock), while a swipeable hamburger side-menu houses extended operations and logout functionality.
*   **Smart Modals & Forms**: Multi-column forms and modals intelligently collapse into single-column vertical stacks on mobile, complete with touch-optimized margins, padded target areas, and smooth bottom-sheet animations for overlays.

---

## Local Setup & System Requirements

### Installation Steps

1.  **Install Python 3.11+** from python.org. Make sure to check **Add to PATH** during setup.
2.  **Install WeasyPrint Dependencies (Required for Server-side PDFs)**:
    *   *Windows*: Download and run the **GTK3 Installer** (required for WeasyPrint to compile PDFs).
    *   *macOS*: `brew install shared-mime-info weasyprint`
    *   *Linux*: `sudo apt-get install build-essential python3-dev python3-pip python3-setuptools python3-wheel python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info`
3.  **Install Pip Packages**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run the excel migration script** (First time only, parses `Latest_data.xlsx` into the SQLite database):
    ```bash
    python migrate.py
    ```
5.  **Launch the FastAPI server**:
    ```bash
    python main.py
    ```
6.  **Access the application**:
    *   *Local Web Browser*: [http://localhost:8000](http://localhost:8000)
    *   *API Interactive Docs*: [http://localhost:8000/docs](http://localhost:8000/docs)
    *   *Local LAN Access*: Find your local IP (e.g. `ipconfig` on Windows) and navigate to `http://192.168.x.x:8000` on any phone/tablet connected to the same Wi-Fi.
