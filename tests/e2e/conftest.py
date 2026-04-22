import os

import pytest
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait


DEFAULT_FRONTEND_URL = "http://localhost:3000"
DEFAULT_WAIT_SECONDS = 10


def pytest_addoption(parser):
    parser.addoption(
        "--e2e-base-url",
        action="store",
        default=os.getenv("ACCESS2_E2E_BASE_URL", DEFAULT_FRONTEND_URL),
        help="Base URL for the ACCESS2 frontend under test.",
    )
    parser.addoption(
        "--e2e-headed",
        action="store_true",
        default=os.getenv("ACCESS2_E2E_HEADED", "").lower() in {"1", "true", "yes"},
        help="Run Chrome with a visible browser window.",
    )
    parser.addoption(
        "--e2e-submit-bootstrap",
        action="store_true",
        default=os.getenv("ACCESS2_E2E_SUBMIT_BOOTSTRAP", "").lower() in {"1", "true", "yes"},
        help="Run the workflow bootstrap submit test. This creates application data.",
    )


@pytest.fixture(scope="session")
def base_url(pytestconfig):
    return pytestconfig.getoption("--e2e-base-url").rstrip("/")


@pytest.fixture(scope="session")
def submit_bootstrap_enabled(pytestconfig):
    return pytestconfig.getoption("--e2e-submit-bootstrap")


@pytest.fixture
def browser(pytestconfig):
    options = Options()
    if not pytestconfig.getoption("--e2e-headed"):
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,1000")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")

    try:
        driver = webdriver.Chrome(options=options)
    except WebDriverException as exc:
        pytest.skip(f"Chrome WebDriver is not available: {exc.msg}")

    driver.implicitly_wait(0)
    yield driver
    driver.quit()


@pytest.fixture
def wait(browser):
    return WebDriverWait(browser, DEFAULT_WAIT_SECONDS)
