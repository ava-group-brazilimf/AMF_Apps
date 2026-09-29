# SauceDemoE2E — Automated End‑to‑End Testing with Playwright (Python)

## Overview

**SauceDemoE2E** is an automated end‑to‑end (E2E) test suite built using **Playwright with Python** to validate critical user journeys of the SauceDemo web application.

The project was designed with a strong focus on **maintainability**, **traceability**, and **test evidence generation**, following modern QA engineering practices such as:

* Page Object Model (POM)
* Clean Code principles
* Separation of responsibilities
* Automated evidence collection
* Structured logging
* Scalable architecture for CI/CD integration

This repository demonstrates not only automated functional validation but also professional test engineering practices suitable for enterprise environments.

---

## Technology Stack

**Language**

* Python

**Frameworks and Tools**

* Playwright
* Pytest
* Allure Report
* python‑dotenv

**Testing Design Patterns**

* Page Object Model (POM)
* Clean Architecture concepts

**Evidence and Observability**

* Screenshot capture
* Video recording
* Execution logs
* Individual TXT evidence per test
* Allure test reporting

---

## Project Goals

The primary objective of this automation suite is to validate critical workflows of the SauceDemo application, including:

* User authentication
* Product selection
* Cart management
* Checkout process
* Order completion
* Checkout cancellation
* Error and edge‑case handling
* Inconsistent system behavior detection

The test suite was structured to provide reliable regression coverage while producing strong execution evidence for debugging, auditing, and reporting purposes.

---

## Project Structure

```
SauceDemoE2E/

artifacts/

  logs/

    execution.log

    tests/

  screenshots/

  videos/

pages/

  base_page.py

  login_page.py

  inventory_page.py

  cart_page.py

  checkout_page.py

tests/

  test_login.py

  test_purchase_flow.py

  test_checkout_complete.py

  test_cancel_checkout.py

  test_problem_user_checkout.py

utils/

  logger.py

  test_evidence.py

conftest.py

pytest.ini

requirements.txt

.env.example

README.md
```

---

## Architecture Design

### Page Object Model (POM)

Each page in the application is represented as a dedicated class responsible for its own elements and behaviors.

This ensures:

* Low coupling
* High readability
* Easy maintenance
* Reusable test logic

---

### BasePage

Provides shared functionality across all pages, including:

* Page navigation
* Element interaction helpers
* Assertions
* Logging integration

---

### LoginPage

Responsible for authentication workflows.

Capabilities:

* Navigate to login page
* Enter username
* Enter password
* Submit login
* Validate login success
* Validate login errors

---

### InventoryPage

Handles product listing and cart interaction.

Capabilities:

* Add products to cart
* Validate cart badge quantity
* Open cart

---

### CartPage

Represents the cart view.

Capabilities:

* Validate cart page visibility
* Initiate checkout process

---

### CheckoutPage

Handles checkout workflows.

Capabilities:

* Validate checkout step one
* Validate checkout step two
* Complete order
* Cancel checkout
* Validate confirmation message
* Handle inconsistent behavior scenarios

---

## Test Scenarios Implemented

### 1. User Login Validation

File:

```
tests/test_login.py
```

Validates authentication for multiple user types:

* standard_user
* locked_out_user
* problem_user
* performance_glitch_user
* error_user
* visual_user

Expected behavior:

Successful login redirects to:

```
https://www.saucedemo.com/inventory.html
```

---

### 2. Add Products and Start Checkout

File:

```
tests/test_purchase_flow.py
```

Flow:

* Login with standard_user
* Add multiple products
* Open cart
* Proceed to checkout

Expected result:

User reaches:

```
checkout-step-one.html
```

---

### 3. Complete Checkout Flow

File:

```
tests/test_checkout_complete.py
```

Flow:

* Login
* Add products
* Open cart
* Checkout
* Fill customer information
* Continue
* Finish order

Expected result:

```
checkout-complete.html
```

Confirmation message validation:

```
Your order has been dispatched, and will arrive just as fast as the pony can get there!
```

---

### 4. Cancel Checkout

File:

```
tests/test_cancel_checkout.py
```

Flow:

* Login
* Add products
* Open cart
* Start checkout
* Cancel checkout

Expected result:

User returns to:

```
cart.html
```

---

### 5. Problem User Behavior Validation

File:

```
tests/test_problem_user_checkout.py
```

Purpose:

Validate inconsistent behavior produced by the problem_user account.

Flow:

* Login with problem_user
* Add products
* Start checkout
* Attempt to fill form fields
* Observe system behavior

Outcome:

The test records anomalies and generates evidence for investigation.

---

## Test Evidence Generated

The framework automatically generates multiple evidence types during execution.

### Screenshots

Location:

```
artifacts/screenshots/
```

Captured automatically after each test.

---

### Video Recording

Location:

```
artifacts/videos/
```

Each test execution records a full session video.

---

### Execution Log

Location:

```
artifacts/logs/execution.log
```

Contains the consolidated execution history.

---

### Individual Test Evidence (TXT)

Location:

```
artifacts/logs/tests/
```

Each test produces its own structured log file containing:

* Test start time
* Test end time
* Execution status
* Final URL

Example:

```
2026-04-01 17:55:12 | TEST STARTED

2026-04-01 17:55:30 | TEST FINISHED

2026-04-01 17:55:30 | STATUS: PASSED

2026-04-01 17:55:30 | FINAL URL: checkout-complete.html
```

---

### Allure Report

All test evidence is automatically attached to Allure.

Includes:

* Screenshots
* Logs
* Test steps
* Execution status

---

## Installation

### Step 1 — Create virtual environment

```
python -m venv venv
```

Activate environment:

```
source venv/Scripts/activate
```

---

### Step 2 — Install dependencies

```
pip install -r requirements.txt
```

Install Playwright browsers:

```
python -m playwright install
```

---

### Step 3 — Configure environment variables

Copy the template file:

```
cp .env.example .env
```

---

## Running Tests

Run all tests:

```
pytest -v --headed
```

Run a specific test:

```
pytest tests/test_checkout_complete.py -v --headed
```

Run tests in headless mode:

```
pytest -v
```

---

## Generate Allure Report

```
allure serve allure-results
```

Alternative Windows path example:

```
C:/Users/<user>/tools/allure/allure/bin/allure.bat serve allure-results
```

---

## Design Principles Applied

Clean Code

* Readable test steps
* Explicit method naming
* Minimal duplication
* Clear responsibility boundaries

Page Object Model

* Encapsulation of UI logic
* Reusable components
* Stable selectors

Test Observability

* Structured logs
* Deterministic execution flow
* Reproducible results

Scalability

* CI/CD ready
* Extensible architecture
* Modular design

---

## Suggested Future Enhancements

* CI/CD pipeline integration
* Parallel execution
* API testing integration
* Test data management
* Network logging
* Performance testing
* Visual regression testing
* Test tagging strategy

---

## Git Commands — Push Project to Azure DevOps

Repository:

```
illinois-automation-project
```

Branch:

```
Gabriel-Tests
```

Folder destination:

```
SauceDemoE2E
```

---

### Clone repository

```
cd /c/projects


git clone -b Gabriel-Tests https://dev.azure.com/O2M-QA/Technical-Patterns/_git/illinois-automation-project
```

---

### Navigate to repository

```
cd illinois-automation-project
```

---

### Create project folder

```
mkdir SauceDemoE2E
```

---

### Copy project files

```
cp -r /c/projects/SaudeDemo-E2E/. ./SauceDemoE2E/
```

---

### Add files

```
git add SauceDemoE2E
```

---

### Commit

```
git commit -m "Add SauceDemoE2E Playwright Python automation project with POM and Allure reporting"
```

---

### Push to branch

```
git push origin Gabriel-Tests
```

---

## Recommended Commit Message

```
Add SauceDemoE2E automated end-to-end test suite using Playwright Python with POM architecture and Allure reporting
```

---

## Summary

The SauceDemoE2E project demonstrates professional-grade test automation practices using Playwright and Python, focusing on reliability, maintainability, and strong execution evidence.

It reflects a production-ready automation framework capable of supporting regression testing, defect investigation, and continuous delivery pipelines in enterprise environments.
