"""
Automated Zerodha Login Module
Handles automated login to Zerodha using Selenium and TOTP
"""
import logging
import time
from typing import Optional, Tuple, TYPE_CHECKING
from urllib.parse import urlparse, parse_qs

import pyotp

# Lazy imports for selenium - only imported when actually needed
# This allows the module to load even if selenium is not installed
SELENIUM_AVAILABLE = False
WEBDRIVER_MANAGER_AVAILABLE = False

if TYPE_CHECKING:
    from selenium import webdriver

from config.credentials import Credentials


def _check_selenium_available():
    """Check if selenium is available and import it lazily"""
    global SELENIUM_AVAILABLE, WEBDRIVER_MANAGER_AVAILABLE

    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.common.exceptions import TimeoutException, WebDriverException
        SELENIUM_AVAILABLE = True
    except ImportError:
        raise ImportError(
            "Selenium is required for auto-login but is not installed. "
            "Please install it with: pip install selenium"
        )

    try:
        from webdriver_manager.chrome import ChromeDriverManager
        WEBDRIVER_MANAGER_AVAILABLE = True
    except ImportError:
        WEBDRIVER_MANAGER_AVAILABLE = False

    return {
        'webdriver': webdriver,
        'By': By,
        'WebDriverWait': WebDriverWait,
        'EC': EC,
        'Service': Service,
        'Options': Options,
        'TimeoutException': TimeoutException,
        'WebDriverException': WebDriverException,
        'ChromeDriverManager': ChromeDriverManager if WEBDRIVER_MANAGER_AVAILABLE else None,
    }

logger = logging.getLogger(__name__)

# Zerodha login page elements
ZERODHA_LOGIN_URL = "https://kite.zerodha.com/connect/login"
USER_ID_INPUT = "input#userid"
PASSWORD_INPUT = "input#password"
TOTP_INPUT = "input[type='number']"
LOGIN_BUTTON = "button[type='submit']"


class ZerodhaAutoLogin:
    """Automated Zerodha login handler"""

    def __init__(self, headless: bool = True, timeout: int = 60, page_load_timeout: int = 30, max_retries: int = 2):
        """
        Initialize auto login handler

        Args:
            headless: Run browser in headless mode (no GUI)
            timeout: Maximum wait time for page elements (seconds)
            page_load_timeout: Maximum wait time for page to load (seconds)
            max_retries: Maximum number of retry attempts for transient failures
        """
        self.headless = headless
        self.timeout = timeout
        self.page_load_timeout = page_load_timeout
        self.max_retries = max_retries
        self.driver = None
        self.totp = None
        self._selenium_modules = None
        self._current_step = ""

        # Initialize TOTP generator if secret is available
        if Credentials.ZERODHA_TOTP_SECRET:
            self.totp = pyotp.TOTP(Credentials.ZERODHA_TOTP_SECRET)

    def _get_selenium_modules(self):
        """Lazily load selenium modules"""
        if self._selenium_modules is None:
            self._selenium_modules = _check_selenium_available()
        return self._selenium_modules

    def _setup_driver(self):
        """Setup Chrome WebDriver"""
        modules = self._get_selenium_modules()
        webdriver = modules['webdriver']
        Options = modules['Options']
        Service = modules['Service']
        WebDriverException = modules['WebDriverException']
        ChromeDriverManager = modules['ChromeDriverManager']

        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument("--headless=new")

        # Common options for stability
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")

        # Avoid detection
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        try:
            if ChromeDriverManager is not None:
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                driver = webdriver.Chrome(options=chrome_options)

            # Additional anti-detection measures
            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        })
                    """
                },
            )

            # Set page load timeout
            driver.set_page_load_timeout(self.page_load_timeout)
            driver.implicitly_wait(5)  # Brief implicit wait for elements

            return driver

        except WebDriverException as e:
            logger.error(f"Failed to setup Chrome WebDriver: {e}")
            raise

    def generate_totp(self) -> str:
        """Generate current TOTP code"""
        if not self.totp:
            raise ValueError("TOTP secret not configured")
        return self.totp.now()

    def _wait_for_element(self, wait, condition, selector: str, step_name: str):
        """
        Wait for an element with better error handling

        Args:
            wait: WebDriverWait instance
            condition: Expected condition to wait for
            selector: CSS selector for the element
            step_name: Human-readable step name for error messages

        Returns:
            The found element

        Raises:
            TimeoutException: With detailed step information
        """
        modules = self._get_selenium_modules()
        TimeoutException = modules['TimeoutException']

        self._current_step = step_name
        logger.info(f"[Step: {step_name}] Waiting for element: {selector}")

        try:
            element = wait.until(condition)
            logger.info(f"[Step: {step_name}] Element found successfully")
            return element
        except TimeoutException:
            # Try to capture page state for debugging
            page_title = "unknown"
            current_url = "unknown"
            try:
                if self.driver:
                    page_title = self.driver.title
                    current_url = self.driver.current_url
            except Exception:
                pass

            error_msg = (
                f"Timeout at step '{step_name}' waiting for element '{selector}'. "
                f"Page title: '{page_title}', URL: '{current_url}'"
            )
            logger.error(error_msg)
            raise TimeoutException(error_msg)

    def login(self, login_url: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Perform automated login to Zerodha with retry logic

        Args:
            login_url: The Kite Connect login URL with API key

        Returns:
            Tuple of (success, request_token, error_message)
        """
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            logger.info(f"Login attempt {attempt}/{self.max_retries}")

            success, request_token, error_message = self._attempt_login(login_url)

            if success:
                return True, request_token, None

            last_error = error_message
            logger.warning(f"Attempt {attempt} failed: {error_message}")

            # Cleanup before retry
            self.cleanup()

            if attempt < self.max_retries:
                wait_time = 2 ** attempt  # Exponential backoff: 2, 4 seconds
                logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)

        return False, None, f"Auto-login failed after {self.max_retries} attempts. Last error: {last_error}"

    def _attempt_login(self, login_url: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Single login attempt to Zerodha

        Args:
            login_url: The Kite Connect login URL with API key

        Returns:
            Tuple of (success, request_token, error_message)
        """
        request_token = None
        error_message = None

        # Get selenium modules (will raise ImportError if selenium not installed)
        modules = self._get_selenium_modules()
        By = modules['By']
        WebDriverWait = modules['WebDriverWait']
        EC = modules['EC']
        TimeoutException = modules['TimeoutException']

        try:
            logger.info("Starting automated Zerodha login...")

            # Validate credentials
            if not all([
                Credentials.ZERODHA_USER_ID,
                Credentials.ZERODHA_PASSWORD,
                Credentials.ZERODHA_TOTP_SECRET,
            ]):
                return False, None, "Auto-login credentials not configured"

            # Setup browser
            logger.info("Setting up browser...")
            self.driver = self._setup_driver()

            # Navigate to login URL
            logger.info("Navigating to Zerodha login page...")
            self.driver.get(login_url)

            # Wait for page to be fully loaded
            logger.info("Waiting for page to load...")
            time.sleep(2)  # Initial page load wait

            wait = WebDriverWait(self.driver, self.timeout)

            # Step 1: Enter User ID
            user_id_field = self._wait_for_element(
                wait,
                EC.visibility_of_element_located((By.CSS_SELECTOR, USER_ID_INPUT)),
                USER_ID_INPUT,
                "Enter User ID"
            )
            user_id_field.clear()
            user_id_field.send_keys(Credentials.ZERODHA_USER_ID)

            # Step 2: Enter Password
            password_field = self._wait_for_element(
                wait,
                EC.visibility_of_element_located((By.CSS_SELECTOR, PASSWORD_INPUT)),
                PASSWORD_INPUT,
                "Enter Password"
            )
            password_field.clear()
            password_field.send_keys(Credentials.ZERODHA_PASSWORD)

            # Step 3: Click Login button
            login_button = self._wait_for_element(
                wait,
                EC.element_to_be_clickable((By.CSS_SELECTOR, LOGIN_BUTTON)),
                LOGIN_BUTTON,
                "Click Login Button"
            )
            login_button.click()

            # Step 4: Wait for TOTP page and enter TOTP
            logger.info("Waiting for TOTP page to load...")
            time.sleep(3)  # Wait for page transition after login

            totp_field = self._wait_for_element(
                wait,
                EC.visibility_of_element_located((By.CSS_SELECTOR, TOTP_INPUT)),
                TOTP_INPUT,
                "Enter TOTP"
            )

            # Generate and enter TOTP
            totp_code = self.generate_totp()
            logger.info("Entering TOTP code...")
            totp_field.clear()
            totp_field.send_keys(totp_code)

            # Step 5: Click continue/submit for TOTP
            submit_button = self._wait_for_element(
                wait,
                EC.element_to_be_clickable((By.CSS_SELECTOR, LOGIN_BUTTON)),
                LOGIN_BUTTON,
                "Submit TOTP"
            )
            submit_button.click()

            # Step 6: Wait for redirect and extract request token
            logger.info("Waiting for redirect...")
            time.sleep(5)  # Increased wait for redirect

            # Check for successful redirect with request_token
            current_url = self.driver.current_url
            logger.info(f"Current URL after login: {current_url}")

            # Extract request token from URL
            request_token = self._extract_request_token(current_url)

            if request_token:
                logger.info("Successfully obtained request token!")
                return True, request_token, None
            else:
                # Check if there's an error message on page
                error_message = self._check_for_error()
                if not error_message:
                    error_message = f"Failed to obtain request token from redirect URL: {current_url}"
                return False, None, error_message

        except TimeoutException as e:
            error_message = f"Timeout at step '{self._current_step}': {e}"
            logger.error(error_message)
            return False, None, error_message

        except Exception as e:
            error_message = f"Auto-login failed at step '{self._current_step}': {e}"
            logger.error(error_message, exc_info=True)
            return False, None, error_message

        finally:
            # Only cleanup on failure; success cleanup is handled by the caller
            if not request_token:
                self.cleanup()

    def _extract_request_token(self, url: str) -> Optional[str]:
        """Extract request token from redirect URL"""
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)

            # Check for request_token parameter
            if "request_token" in params:
                return params["request_token"][0]

            # Check fragment for single-page app redirects
            if parsed.fragment:
                fragment_params = parse_qs(parsed.fragment)
                if "request_token" in fragment_params:
                    return fragment_params["request_token"][0]

            return None

        except Exception as e:
            logger.error(f"Error extracting request token: {e}")
            return None

    def _check_for_error(self) -> Optional[str]:
        """Check if there's an error message on the page"""
        try:
            if self.driver:
                modules = self._get_selenium_modules()
                By = modules['By']

                # Look for common error elements
                error_selectors = [
                    ".error-message",
                    ".alert-error",
                    ".error",
                    "[class*='error']",
                ]

                for selector in error_selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if element.text:
                            return element.text
                    except Exception:
                        continue

            return None

        except Exception:
            return None

    def cleanup(self):
        """Cleanup browser resources"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
            finally:
                self.driver = None


def perform_auto_login(
    login_url: str,
    headless: bool = True,
    timeout: int = 60,
    page_load_timeout: int = 30,
    max_retries: int = 2
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Convenience function to perform automated login

    Args:
        login_url: The Kite Connect login URL
        headless: Run browser in headless mode
        timeout: Maximum wait time for page elements (seconds)
        page_load_timeout: Maximum wait time for page to load (seconds)
        max_retries: Maximum number of retry attempts for transient failures

    Returns:
        Tuple of (success, request_token, error_message)
    """
    auto_login = ZerodhaAutoLogin(
        headless=headless,
        timeout=timeout,
        page_load_timeout=page_load_timeout,
        max_retries=max_retries
    )
    return auto_login.login(login_url)
