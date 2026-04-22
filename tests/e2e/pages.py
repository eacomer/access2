from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support import expected_conditions as EC


ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin123!"


def by_test_id(test_id):
    return (By.CSS_SELECTOR, f'[data-testid="{test_id}"]')


def wait_for_test_id(wait, test_id):
    return wait.until(EC.presence_of_element_located(by_test_id(test_id)))


def login_as_admin(browser, wait, base_url):
    browser.get(f"{base_url}/login")
    wait_for_test_id(wait, "login-page")
    browser.find_element(*by_test_id("login-email")).send_keys(ADMIN_EMAIL)
    browser.find_element(*by_test_id("login-password")).send_keys(ADMIN_PASSWORD)
    browser.find_element(*by_test_id("login-submit")).click()
    try:
        wait.until(EC.url_contains("/patients"))
        wait_for_test_id(wait, "patients-page")
    except TimeoutException as exc:
        try:
            alert_text = browser.find_element(By.CSS_SELECTOR, '[role="alert"]').text
        except NoSuchElementException:
            alert_text = "No login error message was rendered."
        raise AssertionError(
            f"Admin login did not reach /patients. Current URL: {browser.current_url}. "
            f"Page feedback: {alert_text}"
        ) from exc
