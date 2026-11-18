# 🤝 Contributing Guidelines

Thank you for your interest in contributing to the **EmpowerED API — Institutional OBE & ABET Analytics Middleware (Technological Institute of the Philippines)**! This document provides guidelines and best practices for submitting bug fixes, new features, and documentation improvements.

---

## 📋 Table of Contents

- [Code of Conduct](#-code-of-conduct)
- [Getting Started](#-getting-started)
- [Development Workflow](#-development-workflow)
- [Coding Standards](#-coding-standards)
- [Submitting Pull Requests](#-submitting-pull-requests)

---

## 📜 Code of Conduct

We are committed to providing a welcoming, respectful, and collaborative environment for everyone. Please review our [Contributor Code of Conduct](CODE_OF_CONDUCT.md) and ensure all interactions across issues, pull requests, and discussions remain professional and constructive.

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.12+**
- **Git**
- **pip**

### Local Development Setup

1. **Fork & Clone the Repository**:
   ```powershell
   git clone https://github.com/TheUnshackled1/empowered-analytics-v2.git
   cd Tip-API
   ```

2. **Create & Activate Virtual Environment**:
   ```powershell
   python -m venv env
   .\env\Scripts\Activate
   ```

3. **Install Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

4. **Apply Migrations**:
   ```powershell
   python manage.py migrate
   ```

5. **Run the Test Suite**:
   ```powershell
   python manage.py test analytics --verbosity 2
   ```

6. **Start the Server**:
   ```powershell
   python manage.py runserver
   ```

---

## 🔄 Development Workflow

```mermaid
flowchart LR
    A["Fork & Clone<br/>Repository"] --> B["Create Feature/Fix<br/>Branch"]
    B --> C["Implement Changes<br/>(Models / Views / UI)"]
    C --> D["Run 22-Test Suite<br/>& System Check"]
    D --> E["Commit & Push<br/>to Fork"]
    E --> F["Open Pull Request<br/>Against main"]
```

1. **Create a Feature Branch**:
   ```powershell
   git checkout -b feature/your-feature-name
   # or for bug fixes:
   git checkout -b fix/issue-description
   ```

2. **Make Your Changes**: Keep commits focused, modular, and easy to review.

3. **Run Automated Tests**:
   Ensure all unit and API integration tests pass cleanly before committing:
   ```powershell
   python manage.py test analytics --verbosity 2
   python manage.py check
   ```

---

## 📐 Coding Standards

- **Python & DRF**: Follow [PEP 8](https://peps.python.org/pep-0008/) style conventions. Write clean Django views, DRF serializers, and service functions with explicit transaction boundaries and RBAC clearance validation (`Level 1 · Read`, `Level 2 · Write`, `Level 3 · Admin`).
- **HTML / Templates**: Use standard Django template inheritance (`{% extends 'base.html' %}`) and keep interactive elements accessible with descriptive IDs and centered workspace alignment.
- **RA 10173 Data Privacy & Security**: Always anonymize student identifiers via SHA-256 tokenization before database persistence, record state-changing operations in `DPAAuditLog`, and preserve the 15-minute expiring session guard (`_empowered_login_required`).
- **Frontend / Styling**: Maintain the dedicated per-template CSS (`analytics/static/css/`) and JavaScript (`analytics/static/javascript/`) architecture using design system tokens from `base.css`. Avoid `<style>` blocks inside HTML templates.

---

## 📤 Submitting Pull Requests

```mermaid
sequenceDiagram
    participant Dev as Contributor
    participant Fork as Forked Repo
    participant Main as Official Repository (main)
    participant CI as Automated Test Suite
    Dev->>Fork: git push origin feature/your-feature-name
    Dev->>Main: Open Pull Request (Title & Summary)
    Main->>CI: Run manage.py test analytics (22 tests)
    CI-->>Main: All Tests Pass + RBAC & DPA Verified
    Main-->>Dev: Maintainer Review & Merge into main
```

1. Push your feature branch to your fork:
   ```powershell
   git push origin feature/your-feature-name
   ```
2. Open a **Pull Request (PR)** against the `main` branch of the official repository.
3. Provide a clear title and description explaining what your PR changes or fixes.
4. Ensure all automated tests (`python manage.py test analytics --verbosity 2`) pass `OK` on your branch.

Thank you for contributing to the **Technological Institute of the Philippines (T.I.P.) — EmpowerED API** analytics platform!
