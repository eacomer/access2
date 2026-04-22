import time

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .pages import by_test_id, login_as_admin, wait_for_test_id


def test_login_page_loads(browser, wait, base_url):
    browser.get(f"{base_url}/login")

    wait_for_test_id(wait, "login-page")
    assert browser.find_element(*by_test_id("login-email")).is_displayed()
    assert browser.find_element(*by_test_id("login-password")).is_displayed()
    assert browser.find_element(*by_test_id("login-submit")).is_enabled()


def test_admin_login_reaches_patients(browser, wait, base_url):
    login_as_admin(browser, wait, base_url)

    assert "/patients" in browser.current_url


def test_admin_workflow_bootstrap_page_loads(browser, wait, base_url):
    login_as_admin(browser, wait, base_url)

    browser.get(f"{base_url}/admin/workflow-bootstrap")
    wait_for_test_id(wait, "workflow-bootstrap-page")

    assert browser.find_element(*by_test_id("workflow-bootstrap-form")).is_displayed()
    assert browser.find_element(*by_test_id("workflow-bootstrap-first-name")).is_displayed()
    assert browser.find_element(*by_test_id("workflow-bootstrap-last-name")).is_displayed()
    assert browser.find_element(*by_test_id("workflow-bootstrap-date-of-birth")).is_displayed()


def test_admin_can_submit_workflow_bootstrap(
    browser,
    wait,
    base_url,
    submit_bootstrap_enabled,
):
    if not submit_bootstrap_enabled:
        pytest.skip(
            "Set ACCESS2_E2E_SUBMIT_BOOTSTRAP=1 or pass --e2e-submit-bootstrap "
            "to run this data-creating browser test."
        )

    login_as_admin(browser, wait, base_url)
    browser.get(f"{base_url}/admin/workflow-bootstrap")
    wait_for_test_id(wait, "workflow-bootstrap-form")

    unique_suffix = str(int(time.time()))
    browser.find_element(*by_test_id("workflow-bootstrap-first-name")).send_keys("Selenium")
    browser.find_element(*by_test_id("workflow-bootstrap-last-name")).send_keys(f"Bootstrap{unique_suffix}")
    browser.find_element(*by_test_id("workflow-bootstrap-date-of-birth")).send_keys("01/15/1975")
    browser.find_element(*by_test_id("workflow-bootstrap-signal-notes")).send_keys(
        "Created by Selenium E2E smoke coverage."
    )
    browser.find_element(*by_test_id("workflow-bootstrap-task-description")).send_keys(
        "Verify generated workflow case in browser."
    )
    browser.find_element(By.CSS_SELECTOR, '[data-testid="workflow-bootstrap-form"] button[type="submit"]').click()

    success = wait.until(EC.visibility_of_element_located(by_test_id("workflow-bootstrap-success")))
    assert "Workflow bootstrap created" in success.text
