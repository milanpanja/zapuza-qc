<div align="center">

---

## 📑 Table of Contents

1. [Features](#-features)
2. [Quick Start](#-quick-start)
3. [Login Accounts](#-login-accounts)
4. [What Each Role Can Do](#-what-each-role-can-do)
5. [Main Pages](#-main-pages)
6. [Business Rules (The Locks)](#-business-rules-the-locks)
7. [Project Structure](#-project-structure)
8. [Typical Workflow](#-typical-workflow)
9. [Configuration](#-configuration)
10. [Testing](#-testing)
11. [Troubleshooting](#-troubleshooting)
12. [Roadmap](#-roadmap)

---

## ✨ Features

|          | Feature                                 | What it does                                                                                                  |
| -------- | --------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| 📦       | **Raw material intake**           | Heat number, supplier, PO and mandatory Mill Test Certificate (MTC). Rejected lots go to Supplier Quarantine. |
| 📋       | **Inspection templates**          | Versioned checklists (Rev A, B...) with tolerances, CTQ flags, and read-only after release.                   |
| 📱       | **Tablet inspection**             | Two QR scans, locked step-by-step entry, green/red feedback, mandatory defect photos.                         |
| ✅       | **Supervisor review**             | Approve, conditional concession (non-CTQ only), or quarantine.                                                |
| 🧑‍⚖️ | **MRB disposition**               | Rework, scrap, return to vendor, or customer special concession.                                              |
| 🔗       | **Digital traveler**              | Operations must run in order. Full forward and backward traceability by heat number.                          |
| ⏱️     | **Hold timers**                   | Cooling or curing time is enforced before the next operation can start.                                       |
| 🥇       | **First-piece & periodic checks** | Machine stays in Setup Mode until QA approves the first piece.                                                |
| 🔄       | **Shift handover**                | The incoming worker must acknowledge the log before starting.                                                 |
| 🚚       | **Shipping interlock**            | Gate pass, packing slip and invoice stay locked until all conditions are green.                               |
| 🔏       | **Customer certificate**          | Signed QR on the crate opens a public certified inspection report.                                            |
| 🧾       | **Immutable audit trail**         | Every action is logged with user, time, IP, old and new value. Nothing can be edited or deleted.              |

---

## 🚀 Quick Start

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create the database
python manage.py migrate

# 4. Load demo data (users, machine, gauge, material, template, job)
python manage.py seed_demo

# 5. Create your own admin account
python manage.py createsuperuser

# 6. Start the server
python manage.py runserver
```

Open **http://127.0.0.1:8000/** and log in with any account below.

> 💡 `seed_demo` also prints the **machine QR text** and **job QR text**. Copy them to paste into the scan fields while testing without a camera.

---

## 🔑 Login Accounts

### Demo accounts (created by `python manage.py seed_demo`)

**Password for all demo users: `demo12345`**

| # | Username      | Password      | Role               | Email                  |
| - | ------------- | ------------- | ------------------ | ---------------------- |
| 1 | `plantmgr`  | `demo12345` | Plant Manager      | plantmgr@zapuza.local  |
| 2 | `qeng`      | `demo12345` | Quality Engineer   | qeng@zapuza.local      |
| 3 | `qmgr`      | `demo12345` | Quality Manager    | qmgr@zapuza.local      |
| 4 | `super`     | `demo12345` | Shift Supervisor   | super@zapuza.local     |
| 5 | `inspector` | `demo12345` | QA Floor Inspector | inspector@zapuza.local |
| 6 | `operator`  | `demo12345` | Machine Operator   | operator@zapuza.local  |
| 7 | `dock`      | `demo12345` | Dock Clerk         | dock@zapuza.local      |
| 8 | `ware`      | `demo12345` | Warehouse Clerk    | ware@zapuza.local      |

### Admin account (you create it)

| Username  | Password                               | Role      | Created by                           |
| --------- | -------------------------------------- | --------- | ------------------------------------ |
| `admin` | `123` *(example, choose your own)* | Superuser | `python manage.py createsuperuser` |

The admin panel is at **http://127.0.0.1:8000/admin/**. Only superusers (or users with *Staff status* ticked) can open it. Use it to add machines, gauges, parts, templates and job travelers.

### Step-by-step practice accounts (if you follow the hands-on walkthrough)

If you create the users yourself in the admin instead of using `seed_demo`:

| Username        | Password       | Role                                    |
| --------------- | -------------- | --------------------------------------- |
| `inspector1`  | `Test@12345` | QA Floor Inspector                      |
| `operator1`   | `Test@12345` | Machine Operator                        |
| `supervisor1` | `Test@12345` | Shift Supervisor                        |
| `qmanager1`   | `Test@12345` | Quality Manager (email `qm@test.com`) |
| `dock1`       | `Test@12345` | Dock Clerk                              |
| `ware1`       | `Test@12345` | Warehouse Clerk                         |

> ⚠️ **Security:** these passwords are for demo and training only. Before real use, delete the demo users or change every password, and set a strong `SECRET_KEY` with `DEBUG=0`.

---

## 👥 What Each Role Can Do

| Role                         | Main tasks                                                                                                                      |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| **Plant Manager**      | View machines, materials, templates, travelers and bottlenecks. Take MRB decisions. Read the audit trail. Mark machine PM done. |
| **Quality Engineer**   | Build inspection templates in the admin (needs *Staff status*). Clear lab-tested lots.                                        |
| **Quality Manager**    | Release templates, approve or concede inspections, take MRB decisions, clear lab lots, read the audit trail.                    |
| **Shift Supervisor**   | Mark daily machine PM done, review the approval queue (approve, concede, quarantine), acknowledge handovers, view bottlenecks.  |
| **QA Floor Inspector** | Scan QR codes, run inspections, upload defect photos, approve first piece.                                                      |
| **Machine Operator**   | Start and finish operations, count parts, create shift handovers.                                                               |
| **Dock Clerk**         | Receive raw material, upload the MTC, reject lots.                                                                              |
| **Warehouse Clerk**    | Open the gate pass, create shipping manifests, print the customer QR.                                                           |

Any page opened by the wrong role returns **403 Forbidden**.

---

## 🧭 Main Pages

| URL                          | Page                                   | Used by                        |
| ---------------------------- | -------------------------------------- | ------------------------------ |
| `/`                        | Dashboard                              | Everyone                       |
| `/plant/machines/`         | Machines and today's PM status         | Supervisor, Plant Manager      |
| `/materials/`              | Raw material lots                      | Dock, Quality                  |
| `/quality/templates/`      | Template list and release              | Quality Manager                |
| `/quality/scan/`           | Start an inspection (scan 2 QR codes)  | Inspector                      |
| `/quality/queue/`          | Supervisor approval queue              | Supervisor, Quality Manager    |
| `/quality/mrb/`            | Rejection holding area (MRB)           | Plant Manager, Quality Manager |
| `/production/`             | Job travelers                          | Everyone                       |
| `/production/handover/`    | Shift handover log                     | Operator, Supervisor           |
| `/production/bottlenecks/` | Queue and cycle times                  | Supervisor, Managers           |
| `/dispatch/gate/<id>/`     | Gate pass and shipping interlock       | Warehouse                      |
| `/dispatch/cert/<token>/`  | Public customer certificate (no login) | Customer                       |
| `/audit/`                  | Read-only audit trail                  | Plant Manager, Quality Manager |
| `/admin/`                  | Master data setup                      | Admin                          |

---

## 🔒 Business Rules (The Locks)

| #  | Lock                            | What happens                                                              |
| -- | ------------------------------- | ------------------------------------------------------------------------- |
| 1  | Missing MTC                     | Raw material intake cannot be saved.                                      |
| 2  | Quarantined or lab lot          | A job cannot be created from it.                                          |
| 3  | Machine PM not done today       | No operation can start on that machine.                                   |
| 4  | Operation order                 | Op 30 cannot start before Op 20 is finished.                              |
| 5  | Hold timer active               | Next operation is blocked with a countdown message.                       |
| 6  | Shift handover not acknowledged | Machine cannot start new work.                                            |
| 7  | Fake or edited QR code          | Rejected as invalid (digitally signed).                                   |
| 8  | Expired gauge calibration       | Measurement is refused.                                                   |
| 9  | Skipping a field                | Fields must be measured in order.                                         |
| 10 | Out-of-tolerance value          | Turns red and needs at least 2 defect photos.                             |
| 11 | CTQ failure                     | Checklist freezes, Quality Manager is emailed, concession is blocked.     |
| 12 | Concession                      | Non-CTQ only, with reason code and written justification.                 |
| 13 | Released template               | Read-only. Changes need a new revision.                                   |
| 14 | Submitted measurement           | Cannot be edited or deleted.                                              |
| 15 | First piece not approved        | Machine stays in Setup Mode, counter locked.                              |
| 16 | Quarantined job                 | All work stops until the MRB decides.                                     |
| 17 | Shipping interlock              | Gate pass locked until all operations, holds and the final PDI are green. |
| 18 | Audit log                       | Append-only. Update and delete are blocked.                               |

> **Golden rule:** business rules live **only** in each app's `services.py`. Views just call them, so no page can bypass a lock.

---

## 🗂️ Project Structure

```
zapuza_qc/
├── manage.py
├── requirements.txt
├── README.md
│
├── zapuza/                 ⚙️  settings.py, urls.py
├── accounts/               👤  User model with roles, @role_required
├── core/                   🧾  AuditLog, notifications, tests.py, seed_demo command
├── plant/                  🏗️  Site, Machine, Part, Gauge, PM checks      (services.py)
├── materials/              📦  Raw material lots, MTC, SNCR               (services.py)
├── quality/                📋  Templates, inspections, concessions, MRB   (services.py)
├── production/             🔗  Travelers, operations, holds, handover     (services.py)
├── dispatch/               🚚  Shipping interlock, manifest, certificate  (services.py)
└── templates/              🖥️  All HTML pages
```

Every app follows the same pattern: `models.py` → `services.py` → `views.py` → `urls.py` → `admin.py`.

---

## 🔄 Typical Workflow

```
 Raw steel arrives        Job traveler            Shop floor
 ┌─────────────────┐     ┌────────────────┐      ┌──────────────────────────┐
 │ Dock: log heat  │────▶│ Create job from│─────▶│ Op 10 → Op 20 (1st piece)│
 │ + upload MTC    │     │ a CLEARED lot  │      │ → Op 30 (hold timer)     │
 └─────────────────┘     └────────────────┘      └────────────┬─────────────┘
                                                              ▼
 ┌─────────────────┐     ┌────────────────┐      ┌──────────────────────────┐
 │ Customer scans  │◀────│ Warehouse:     │◀─────│ Inspector measures,      │
 │ QR certificate  │     │ gate pass +    │      │ Supervisor approves,     │
 └─────────────────┘     │ manifest       │      │ Final PDI approved       │
                         └────────────────┘      └──────────────────────────┘

   Failed part ─▶ Quarantine ─▶ MRB: Rework / Scrap / Return to vendor / Customer concession
```

---

## ⚙️ Configuration

Set these as environment variables (all optional for local use):

| Variable              | Default                | Purpose                                                              |
| --------------------- | ---------------------- | -------------------------------------------------------------------- |
| `SECRET_KEY`        | `dev-only-change-me` | **Change in production.** Also signs all QR codes.             |
| `DEBUG`             | `1`                  | Set `0` in production. Scan fields become read-only (camera only). |
| `ALLOWED_HOSTS`     | `*`                  | Comma-separated host names.                                          |
| `POSTGRES_DB`       | *(unset)*            | Set to switch from SQLite to PostgreSQL.                             |
| `POSTGRES_USER`     | `postgres`           | PostgreSQL user.                                                     |
| `POSTGRES_PASSWORD` | *(empty)*            | PostgreSQL password.                                                 |
| `POSTGRES_HOST`     | `localhost`          | PostgreSQL host.                                                     |
| `EMAIL_BACKEND`     | console                | Use an SMTP backend to send real alert emails.                       |

Uploaded files (MTC, drawings, defect photos) are stored in the `media/` folder.

---

## 🧪 Testing

```bash
python manage.py test
```

13 tests prove the main locks: expired gauge, field order, two-photo rule, CTQ freeze, concession rules, operation sequence, hold timer, PM lock, quarantine, first piece, shipping interlock, template read-only and audit immutability.

---

## 🛠️ Troubleshooting

| Problem                               | Fix                                                                                     |
| ------------------------------------- | --------------------------------------------------------------------------------------- |
| `Invalid machine QR code`           | Paste the full text printed by `seed_demo` or the Django shell, with no extra spaces. |
| `403 Forbidden`                     | Your role is not allowed on that page. Log in with the right user.                      |
| Cannot open `/admin/`               | Use a superuser, or tick *Staff status* on the user.                                  |
| `Machine daily PM check is pending` | Log in as a supervisor and click **Mark PM done** on the Machines page.           |
| `Acknowledge the shift handover`    | A different user must click **Acknowledge** on the handover list.                 |
| Gate pass shows a red lockout         | Read the list. It names exactly which operation, hold or PDI is missing.                |
| Uploaded files give 404               | Run with `DEBUG=1`, or serve `/media/` with Nginx in production.                    |
| Start over with clean data            | Delete `db.sqlite3`, then run `migrate` again.                                      |

---

## 🗺️ Roadmap

- [ ] Celery background jobs for automatic alerts and hourly-check timers
- [ ] Offline service worker for tablets (the `/quality/api/sync/` endpoint is ready)
- [ ] Click-to-place blueprint pins on drawings
- [ ] SMS alerts and PDF export of certificates
- [ ] Static files moved out of inline CSS

---

<div align="center">

<div align="center">

---

## 📑 Table of Contents

1. [Features](#-features)
2. [Quick Start](#-quick-start)
3. [Login Accounts](#-login-accounts)
4. [What Each Role Can Do](#-what-each-role-can-do)
5. [Main Pages](#-main-pages)
6. [Business Rules (The Locks)](#-business-rules-the-locks)
7. [Project Structure](#-project-structure)
8. [Typical Workflow](#-typical-workflow)
9. [Configuration](#-configuration)
10. [Testing](#-testing)
11. [Troubleshooting](#-troubleshooting)
12. [Roadmap](#-roadmap)

---

## ✨ Features

|          | Feature                                 | What it does                                                                                                  |
| -------- | --------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| 📦       | **Raw material intake**           | Heat number, supplier, PO and mandatory Mill Test Certificate (MTC). Rejected lots go to Supplier Quarantine. |
| 📋       | **Inspection templates**          | Versioned checklists (Rev A, B...) with tolerances, CTQ flags, and read-only after release.                   |
| 📱       | **Tablet inspection**             | Two QR scans, locked step-by-step entry, green/red feedback, mandatory defect photos.                         |
| ✅       | **Supervisor review**             | Approve, conditional concession (non-CTQ only), or quarantine.                                                |
| 🧑‍⚖️ | **MRB disposition**               | Rework, scrap, return to vendor, or customer special concession.                                              |
| 🔗       | **Digital traveler**              | Operations must run in order. Full forward and backward traceability by heat number.                          |
| ⏱️     | **Hold timers**                   | Cooling or curing time is enforced before the next operation can start.                                       |
| 🥇       | **First-piece & periodic checks** | Machine stays in Setup Mode until QA approves the first piece.                                                |
| 🔄       | **Shift handover**                | The incoming worker must acknowledge the log before starting.                                                 |
| 🚚       | **Shipping interlock**            | Gate pass, packing slip and invoice stay locked until all conditions are green.                               |
| 🔏       | **Customer certificate**          | Signed QR on the crate opens a public certified inspection report.                                            |
| 🧾       | **Immutable audit trail**         | Every action is logged with user, time, IP, old and new value. Nothing can be edited or deleted.              |

---

## 🚀 Quick Start

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create the database
python manage.py migrate

# 4. Load demo data (users, machine, gauge, material, template, job)
python manage.py seed_demo

# 5. Create your own admin account
python manage.py createsuperuser

# 6. Start the server
python manage.py runserver
```

Open **http://127.0.0.1:8000/** and log in with any account below.

> 💡 `seed_demo` also prints the **machine QR text** and **job QR text**. Copy them to paste into the scan fields while testing without a camera.

---

## 🔑 Login Accounts

### Demo accounts (created by `python manage.py seed_demo`)

**Password for all demo users: `demo12345`**

| # | Username      | Password      | Role               | Email                  |
| - | ------------- | ------------- | ------------------ | ---------------------- |
| 1 | `plantmgr`  | `demo12345` | Plant Manager      | plantmgr@zapuza.local  |
| 2 | `qeng`      | `demo12345` | Quality Engineer   | qeng@zapuza.local      |
| 3 | `qmgr`      | `demo12345` | Quality Manager    | qmgr@zapuza.local      |
| 4 | `super`     | `demo12345` | Shift Supervisor   | super@zapuza.local     |
| 5 | `inspector` | `demo12345` | QA Floor Inspector | inspector@zapuza.local |
| 6 | `operator`  | `demo12345` | Machine Operator   | operator@zapuza.local  |
| 7 | `dock`      | `demo12345` | Dock Clerk         | dock@zapuza.local      |
| 8 | `ware`      | `demo12345` | Warehouse Clerk    | ware@zapuza.local      |

### Admin account (you create it)

| Username  | Password                               | Role      | Created by                           |
| --------- | -------------------------------------- | --------- | ------------------------------------ |
| `admin` | `123` *(example, choose your own)* | Superuser | `python manage.py createsuperuser` |

The admin panel is at **http://127.0.0.1:8000/admin/**. Only superusers (or users with *Staff status* ticked) can open it. Use it to add machines, gauges, parts, templates and job travelers.

### Step-by-step practice accounts (if you follow the hands-on walkthrough)

If you create the users yourself in the admin instead of using `seed_demo`:

| Username        | Password       | Role                                    |
| --------------- | -------------- | --------------------------------------- |
| `inspector1`  | `Test@12345` | QA Floor Inspector                      |
| `operator1`   | `Test@12345` | Machine Operator                        |
| `supervisor1` | `Test@12345` | Shift Supervisor                        |
| `qmanager1`   | `Test@12345` | Quality Manager (email `qm@test.com`) |
| `dock1`       | `Test@12345` | Dock Clerk                              |
| `ware1`       | `Test@12345` | Warehouse Clerk                         |

> ⚠️ **Security:** these passwords are for demo and training only. Before real use, delete the demo users or change every password, and set a strong `SECRET_KEY` with `DEBUG=0`.

---

## 👥 What Each Role Can Do

| Role                         | Main tasks                                                                                                                      |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| **Plant Manager**      | View machines, materials, templates, travelers and bottlenecks. Take MRB decisions. Read the audit trail. Mark machine PM done. |
| **Quality Engineer**   | Build inspection templates in the admin (needs *Staff status*). Clear lab-tested lots.                                        |
| **Quality Manager**    | Release templates, approve or concede inspections, take MRB decisions, clear lab lots, read the audit trail.                    |
| **Shift Supervisor**   | Mark daily machine PM done, review the approval queue (approve, concede, quarantine), acknowledge handovers, view bottlenecks.  |
| **QA Floor Inspector** | Scan QR codes, run inspections, upload defect photos, approve first piece.                                                      |
| **Machine Operator**   | Start and finish operations, count parts, create shift handovers.                                                               |
| **Dock Clerk**         | Receive raw material, upload the MTC, reject lots.                                                                              |
| **Warehouse Clerk**    | Open the gate pass, create shipping manifests, print the customer QR.                                                           |

Any page opened by the wrong role returns **403 Forbidden**.

---

## 🧭 Main Pages

| URL                          | Page                                   | Used by                        |
| ---------------------------- | -------------------------------------- | ------------------------------ |
| `/`                        | Dashboard                              | Everyone                       |
| `/plant/machines/`         | Machines and today's PM status         | Supervisor, Plant Manager      |
| `/materials/`              | Raw material lots                      | Dock, Quality                  |
| `/quality/templates/`      | Template list and release              | Quality Manager                |
| `/quality/scan/`           | Start an inspection (scan 2 QR codes)  | Inspector                      |
| `/quality/queue/`          | Supervisor approval queue              | Supervisor, Quality Manager    |
| `/quality/mrb/`            | Rejection holding area (MRB)           | Plant Manager, Quality Manager |
| `/production/`             | Job travelers                          | Everyone                       |
| `/production/handover/`    | Shift handover log                     | Operator, Supervisor           |
| `/production/bottlenecks/` | Queue and cycle times                  | Supervisor, Managers           |
| `/dispatch/gate/<id>/`     | Gate pass and shipping interlock       | Warehouse                      |
| `/dispatch/cert/<token>/`  | Public customer certificate (no login) | Customer                       |
| `/audit/`                  | Read-only audit trail                  | Plant Manager, Quality Manager |
| `/admin/`                  | Master data setup                      | Admin                          |

---

## 🔒 Business Rules (The Locks)

| #  | Lock                            | What happens                                                              |
| -- | ------------------------------- | ------------------------------------------------------------------------- |
| 1  | Missing MTC                     | Raw material intake cannot be saved.                                      |
| 2  | Quarantined or lab lot          | A job cannot be created from it.                                          |
| 3  | Machine PM not done today       | No operation can start on that machine.                                   |
| 4  | Operation order                 | Op 30 cannot start before Op 20 is finished.                              |
| 5  | Hold timer active               | Next operation is blocked with a countdown message.                       |
| 6  | Shift handover not acknowledged | Machine cannot start new work.                                            |
| 7  | Fake or edited QR code          | Rejected as invalid (digitally signed).                                   |
| 8  | Expired gauge calibration       | Measurement is refused.                                                   |
| 9  | Skipping a field                | Fields must be measured in order.                                         |
| 10 | Out-of-tolerance value          | Turns red and needs at least 2 defect photos.                             |
| 11 | CTQ failure                     | Checklist freezes, Quality Manager is emailed, concession is blocked.     |
| 12 | Concession                      | Non-CTQ only, with reason code and written justification.                 |
| 13 | Released template               | Read-only. Changes need a new revision.                                   |
| 14 | Submitted measurement           | Cannot be edited or deleted.                                              |
| 15 | First piece not approved        | Machine stays in Setup Mode, counter locked.                              |
| 16 | Quarantined job                 | All work stops until the MRB decides.                                     |
| 17 | Shipping interlock              | Gate pass locked until all operations, holds and the final PDI are green. |
| 18 | Audit log                       | Append-only. Update and delete are blocked.                               |

> **Golden rule:** business rules live **only** in each app's `services.py`. Views just call them, so no page can bypass a lock.

---

## 🗂️ Project Structure

```
zapuza_qc/
├── manage.py
├── requirements.txt
├── README.md
│
├── zapuza/                 ⚙️  settings.py, urls.py
├── accounts/               👤  User model with roles, @role_required
├── core/                   🧾  AuditLog, notifications, tests.py, seed_demo command
├── plant/                  🏗️  Site, Machine, Part, Gauge, PM checks      (services.py)
├── materials/              📦  Raw material lots, MTC, SNCR               (services.py)
├── quality/                📋  Templates, inspections, concessions, MRB   (services.py)
├── production/             🔗  Travelers, operations, holds, handover     (services.py)
├── dispatch/               🚚  Shipping interlock, manifest, certificate  (services.py)
└── templates/              🖥️  All HTML pages
```

Every app follows the same pattern: `models.py` → `services.py` → `views.py` → `urls.py` → `admin.py`.

---

## 🔄 Typical Workflow

```
 Raw steel arrives        Job traveler            Shop floor
 ┌─────────────────┐     ┌────────────────┐      ┌──────────────────────────┐
 │ Dock: log heat  │────▶│ Create job from│─────▶│ Op 10 → Op 20 (1st piece)│
 │ + upload MTC    │     │ a CLEARED lot  │      │ → Op 30 (hold timer)     │
 └─────────────────┘     └────────────────┘      └────────────┬─────────────┘
                                                              ▼
 ┌─────────────────┐     ┌────────────────┐      ┌──────────────────────────┐
 │ Customer scans  │◀────│ Warehouse:     │◀─────│ Inspector measures,      │
 │ QR certificate  │     │ gate pass +    │      │ Supervisor approves,     │
 └─────────────────┘     │ manifest       │      │ Final PDI approved       │
                         └────────────────┘      └──────────────────────────┘

   Failed part ─▶ Quarantine ─▶ MRB: Rework / Scrap / Return to vendor / Customer concession
```

---

## ⚙️ Configuration

Set these as environment variables (all optional for local use):

| Variable              | Default                | Purpose                                                              |
| --------------------- | ---------------------- | -------------------------------------------------------------------- |
| `SECRET_KEY`        | `dev-only-change-me` | **Change in production.** Also signs all QR codes.             |
| `DEBUG`             | `1`                  | Set `0` in production. Scan fields become read-only (camera only). |
| `ALLOWED_HOSTS`     | `*`                  | Comma-separated host names.                                          |
| `POSTGRES_DB`       | *(unset)*            | Set to switch from SQLite to PostgreSQL.                             |
| `POSTGRES_USER`     | `postgres`           | PostgreSQL user.                                                     |
| `POSTGRES_PASSWORD` | *(empty)*            | PostgreSQL password.                                                 |
| `POSTGRES_HOST`     | `localhost`          | PostgreSQL host.                                                     |
| `EMAIL_BACKEND`     | console                | Use an SMTP backend to send real alert emails.                       |

Uploaded files (MTC, drawings, defect photos) are stored in the `media/` folder.

---

## 🧪 Testing

```bash
python manage.py test
```

13 tests prove the main locks: expired gauge, field order, two-photo rule, CTQ freeze, concession rules, operation sequence, hold timer, PM lock, quarantine, first piece, shipping interlock, template read-only and audit immutability.

---

## 🛠️ Troubleshooting

| Problem                               | Fix                                                                                     |
| ------------------------------------- | --------------------------------------------------------------------------------------- |
| `Invalid machine QR code`           | Paste the full text printed by `seed_demo` or the Django shell, with no extra spaces. |
| `403 Forbidden`                     | Your role is not allowed on that page. Log in with the right user.                      |
| Cannot open `/admin/`               | Use a superuser, or tick *Staff status* on the user.                                  |
| `Machine daily PM check is pending` | Log in as a supervisor and click **Mark PM done** on the Machines page.           |
| `Acknowledge the shift handover`    | A different user must click **Acknowledge** on the handover list.                 |
| Gate pass shows a red lockout         | Read the list. It names exactly which operation, hold or PDI is missing.                |
| Uploaded files give 404               | Run with `DEBUG=1`, or serve `/media/` with Nginx in production.                    |
| Start over with clean data            | Delete `db.sqlite3`, then run `migrate` again.                                      |

---

## 🗺️ Roadmap

- [ ] Celery background jobs for automatic alerts and hourly-check timers
- [ ] Offline service worker for tablets (the `/quality/api/sync/` endpoint is ready)
- [ ] Click-to-place blueprint pins on drawings
- [ ] SMS alerts and PDF export of certificates
- [ ] Static files moved out of inline CSS

---

<div align="center">
