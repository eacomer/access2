import pytest
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support import expected_conditions as EC

from .pages import by_test_id, login_as_admin, wait_for_test_id


def wait_for_bootstrap_success(browser, wait):
    try:
        return wait.until(EC.visibility_of_element_located(by_test_id("workflow-bootstrap-success")))
    except TimeoutException as exc:
        feedback = [
            element.text.strip()
            for element in browser.find_elements(By.CSS_SELECTOR, ".form-feedback")
            if element.text.strip()
        ]
        try:
            submit = browser.find_element(
                By.CSS_SELECTOR,
                '[data-testid="workflow-bootstrap-form"] button[type="submit"]',
            )
            submit_state = f"submit_enabled={submit.is_enabled()} submit_text={submit.text!r}"
        except NoSuchElementException:
            submit_state = "submit button not found"
        field_state = {}
        for test_id in (
            "workflow-bootstrap-scenario",
            "workflow-bootstrap-first-name",
            "workflow-bootstrap-last-name",
            "workflow-bootstrap-date-of-birth",
            "workflow-bootstrap-task-title",
        ):
            try:
                field_state[test_id] = browser.find_element(*by_test_id(test_id)).get_attribute("value")
            except NoSuchElementException:
                field_state[test_id] = "<missing>"
        raise AssertionError(
            "Workflow bootstrap did not render success feedback. "
            f"URL={browser.current_url}. {submit_state}. "
            f"Feedback={feedback or ['no visible form feedback']}. "
            f"Fields={field_state}"
        ) from exc


def set_input_value(browser, test_id, value):
    element = browser.find_element(*by_test_id(test_id))
    browser.execute_script(
        """
        const [element, value] = arguments;
        const setter = Object.getOwnPropertyDescriptor(
          window.HTMLInputElement.prototype,
          "value",
        ).set;
        setter.call(element, value);
        element.dispatchEvent(new Event("input", { bubbles: true }));
        element.dispatchEvent(new Event("change", { bubbles: true }));
        """,
        element,
        value,
    )


def find_by_test_id_or_id(browser, wait, test_id, element_id):
    return wait.until(
        lambda driver: (
            driver.find_elements(*by_test_id(test_id))
            or driver.find_elements(By.ID, element_id)
            or False
        )[0]
    )


def wait_for_action_feedback(browser, wait):
    def find_feedback(driver):
        elements = (
            driver.find_elements(*by_test_id("patient-action-feedback"))
            or driver.find_elements(By.CSS_SELECTOR, ".action-feedback")
        )
        return elements[0] if elements else False

    try:
        return wait.until(find_feedback)
    except TimeoutException as exc:
        feedback = [
            element.text.strip()
            for element in browser.find_elements(By.CSS_SELECTOR, ".form-feedback")
            if element.text.strip()
        ]
        task_panel_text = ""
        panels = browser.find_elements(*by_test_id("patient-task-action-panel"))
        if panels:
            task_panel_text = panels[0].text
        raise AssertionError(
            "Patient action feedback did not render. "
            f"URL={browser.current_url}. "
            f"Feedback={feedback or ['no visible form feedback']}. "
            f"Task panel={task_panel_text!r}"
        ) from exc


def create_workflow_bootstrap(
    browser,
    wait,
    base_url,
    *,
    scenario,
    task_title,
    first_name="Selenium",
    last_name="OverdueTask",
):
    browser.get(f"{base_url}/admin/workflow-bootstrap")
    wait_for_test_id(wait, "workflow-bootstrap-form")

    scenario_select = wait_for_test_id(wait, "workflow-bootstrap-scenario")
    Select(scenario_select).select_by_value(scenario)
    browser.find_element(*by_test_id("workflow-bootstrap-first-name")).send_keys(first_name)
    browser.find_element(*by_test_id("workflow-bootstrap-last-name")).send_keys(last_name)
    set_input_value(browser, "workflow-bootstrap-date-of-birth", "1975-01-15")
    browser.find_element(*by_test_id("workflow-bootstrap-signal-notes")).send_keys(
        f"Selenium {scenario} scenario signal note."
    )
    task_title_input = browser.find_element(*by_test_id("workflow-bootstrap-task-title"))
    task_title_input.clear()
    task_title_input.send_keys(task_title)
    browser.find_element(*by_test_id("workflow-bootstrap-task-description")).send_keys(
        "Verify overdue task workflow content on patient detail."
    )
    submit = browser.find_element(
        By.CSS_SELECTOR,
        '[data-testid="workflow-bootstrap-form"] button[type="submit"]',
    )
    assert submit.is_enabled()
    submit.click()

    success = wait_for_bootstrap_success(browser, wait)
    assert f"Workflow bootstrap created for {first_name} {last_name}" in success.text

    patient_link = wait.until(
        EC.element_to_be_clickable(by_test_id("workflow-bootstrap-patient-link"))
    )
    patient_href = patient_link.get_attribute("href")
    assert patient_href
    browser.get(patient_href)

    wait.until(EC.url_contains("/patients/"))
    wait_for_test_id(wait, "patient-detail-page")

    return {
        "scenario": scenario,
        "first_name": first_name,
        "last_name": last_name,
        "task_title": task_title,
    }


def create_overdue_task_bootstrap(browser, wait, base_url, task_title):
    return create_workflow_bootstrap(
        browser,
        wait,
        base_url,
        scenario="overdue_task",
        task_title=task_title,
    )


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
    task_title = "Selenium overdue task validation"
    created = create_overdue_task_bootstrap(browser, wait, base_url, task_title)

    scenario_marker = wait_for_test_id(wait, "patient-validation-scenario")
    assert f"Validation scenario: {created['scenario']}" in scenario_marker.text

    workflow_header = wait_for_test_id(wait, "patient-workflow-header")
    assert f"{created['first_name']} {created['last_name']}" in workflow_header.text
    assert task_title in workflow_header.text

    why_now = wait_for_test_id(wait, "patient-why-now-summary")
    assert "task is overdue" in why_now.text.lower()
    assert "Update or close the task" in why_now.text

    intervention_summary = wait_for_test_id(wait, "patient-intervention-summary")
    assert "1 open task" in intervention_summary.text
    assert task_title in intervention_summary.text

    task_panel = wait_for_test_id(wait, "patient-task-action-panel")
    assert task_title in task_panel.text
    assert "Current status: Open" in task_panel.text


def test_admin_can_complete_patient_detail_task(
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
    task_title = "Selenium complete task mutation"
    create_overdue_task_bootstrap(browser, wait, base_url, task_title)

    task_panel = wait_for_test_id(wait, "patient-task-action-panel")
    assert task_title in task_panel.text
    assert "Current status: Open" in task_panel.text

    browser.find_element(*by_test_id("patient-task-completion-note")).send_keys(
        "Completed by Selenium mutation E2E."
    )
    browser.find_element(*by_test_id("patient-task-complete")).click()

    feedback = wait_for_action_feedback(browser, wait)
    assert "Task completed and documented." in feedback.text

    wait.until(
        lambda driver: "No active task is available"
        in driver.find_element(*by_test_id("patient-task-action-panel")).text
    )
    refreshed_task_panel = browser.find_element(*by_test_id("patient-task-action-panel"))
    assert task_title not in refreshed_task_panel.text

    wait.until(
        lambda driver: "1 completed task"
        in driver.find_element(*by_test_id("patient-intervention-summary")).text
    )
    intervention_summary = browser.find_element(*by_test_id("patient-intervention-summary"))
    assert "1 completed task" in intervention_summary.text


def test_admin_can_create_patient_detail_task(
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
    created_task_title = "Selenium created detail task"
    create_workflow_bootstrap(
        browser,
        wait,
        base_url,
        scenario="open_escalation_no_task",
        task_title="Unused bootstrap task title",
        last_name="CreateTask",
    )

    task_panel = wait_for_test_id(wait, "patient-task-action-panel")
    assert "No active task is available" in task_panel.text

    title_input = find_by_test_id_or_id(browser, wait, "patient-create-task-title", "task-title")
    create_form = title_input.find_element(By.XPATH, "./ancestor::form")
    assert "New intervention task" in create_form.text
    title_input.send_keys(created_task_title)
    find_by_test_id_or_id(
        browser,
        wait,
        "patient-create-task-description",
        "task-description",
    ).send_keys(
        "Created by Selenium from patient detail."
    )
    create_submit = create_form.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
    assert create_submit.is_enabled()
    create_submit.click()

    feedback = wait_for_action_feedback(browser, wait)
    assert "Task created successfully." in feedback.text

    wait.until(
        lambda driver: created_task_title
        in driver.find_element(*by_test_id("patient-task-action-panel")).text
    )
    refreshed_task_panel = browser.find_element(*by_test_id("patient-task-action-panel"))
    assert "Current status: Open" in refreshed_task_panel.text

    wait.until(
        lambda driver: "1 open task"
        in driver.find_element(*by_test_id("patient-intervention-summary")).text
    )
    intervention_summary = browser.find_element(*by_test_id("patient-intervention-summary"))
    assert created_task_title in intervention_summary.text
