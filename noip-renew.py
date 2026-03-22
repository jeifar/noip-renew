import argparse
import os
import sys
import logging

from constants import LOGIN_URL, SCREENSHOTS_PATH, USER_AGENT
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

debug_enabled = False
logger = logging.getLogger()


class NoIPRobot:
    def __init__(
        self,
        username: str,
        password: str,
        totp_secret: str,
        https_proxy: str = None,
    ):
        self.username = username
        self.password = password
        self.totp_secret = totp_secret
        self.https_proxy = https_proxy
        self.browser = self.init_browser()

    def init_browser(self, timeout: int = 90):
        options = webdriver.ChromeOptions()
        options.add_argument("disable-features=VizDisplayCompositor")
        options.add_argument("headless")
        options.add_argument("no-sandbox")
        options.add_argument("window-size=1920x1080")
        options.add_argument("start-maximized")
        options.add_argument(f"user-agent={USER_AGENT}")
        if self.https_proxy:
            options.add_argument("proxy-server=" + self.https_proxy)

        # Fixing weird issue with linux/arm64 distros
        IS_DOCKER = os.environ.get("IS_DOCKER", False)
        if not IS_DOCKER:
            browser = webdriver.Chrome(options=options)
        else:
            options.binary_location = "/usr/bin/chromium"
            service = webdriver.ChromeService(executable_path="/usr/bin/chromedriver")
            browser = webdriver.Chrome(service=service, options=options)

        browser.set_page_load_timeout(timeout)
        return browser

    def login(self):
        logger.info(f"Opening {LOGIN_URL}...")
        self.browser.get(LOGIN_URL)
        if debug_enabled:
            self.browser.save_screenshot(f"{SCREENSHOTS_PATH}/debug1.png")

        logger.info("Logging in...")

        # Fill in the user form
        ele_usr = self.browser.find_element("name", "username")
        try:
            ele_usr.send_keys(self.username)
        except Exception as e:
            logger.error(
                f"An error has occurred while inserting the username/email: {e}"
            )
            raise Exception("Failed while inserting the username")

        # Fill in the password form
        ele_pwd = self.browser.find_element("name", "password")
        try:
            ele_pwd.send_keys(self.password)
        except Exception as e:
            logger.error(f"An error has occurred while inserting the password: {e}")
            raise Exception("Failed while inserting the password")

        login_button = WebDriverWait(self.browser, 10).until(
            EC.element_to_be_clickable((By.ID, "clogs-captcha-button"))
        )

        try:
            # Hack since NO-IP folks are not stupid and triggers some JS on headless mode
            self.browser.execute_script("arguments[0].click();", login_button)
        except Exception as e:
            logger.error(f"Error while logging in: {e}")
            raise Exception("Failed while trying to logging in")

        # Use Priv Key to generate the TOTP Secret
        if not self.totp_secret.isdigit():
            import pyotp

            otp = pyotp.TOTP(self.totp_secret).now()
        # Passing the 6-digit TOTP
        else:
            if not len(self.totp_secret) == 6:
                logger.error("The TOTP Secret must be a 6-digit number!")
                sys.exit(1)
            otp = self.totp_secret

        # Fills in 6 pin OTP code
        WebDriverWait(self.browser, 10).until(
            EC.presence_of_all_elements_located(
                (By.XPATH, '//*[@id="totp-input"]/input')
            )
        )
        try:
            for pos in range(6):
                otp_elem = self.browser.find_element(
                    By.XPATH,
                    '//*[@id="totp-input"]/input' + str([pos + 1]),
                )
                otp_elem.send_keys(otp[pos])
        except Exception as e:
            logger.error(f"Error while filling the 6-digit OTP code: {e}")
            raise Exception("Failed while trying to logging in")

        totp_button = WebDriverWait(self.browser, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@value='Verify']"))
        )
        try:
            totp_button.click()
        except Exception as e:
            logger.error(f"Error while verifying 6-digit OTP code: {e}")
            raise Exception("Failed while trying to logging in")

        if debug_enabled:
            self.browser.save_screenshot(f"{SCREENSHOTS_PATH}/debug2.png")

    def look_for_warn_msg_and_confirm(self) -> None:
        logger.info("Checking for expired hosts..")
        expire_elem = None
        # TODO: This clicks on the first host marked to expire
        # If you have > 1 host you'd have to run the script again
        # Maybe add a loop or something, anyways you only have 3 free-hosts per account so no big deal
        try:
            expire_elem = self.browser.find_element(
                By.XPATH, "//div[contains(@id, 'expiration-banner-hostname-')]"
            )
        # This is expected. No hosts are marked for renewal
        except NoSuchElementException:
            logger.info("No expiring hosts found. You are all set!")
            return

        if debug_enabled:
            self.browser.save_screenshot(f"{SCREENSHOTS_PATH}/hosts-to-expire.png")
        try:
            host_name = expire_elem.get_attribute("id").split("-")[-1]
            logger.info(f"Expiring host {host_name} found. Proceeding to renewal")
            confirmation_button = self.browser.find_element(
                By.XPATH,
                "//button[contains(@hx-get, 'https://my.noip.com/ajax/host/')]",
            )
            confirmation_button.click()
            logger.info(f"Host {host_name} successfully renewed!")
        except Exception as e:
            logger.error(f"Error while trying to renew host {host_name}: {e}")

    def update_hosts(self):
        try:
            logger.info("Looking for expired DNS Records")
            WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//ul/li/a[@href='#']//span[text()='DDNS & Remote Access']",
                    )
                )
            ).click()
            dynamic_dns_list = WebDriverWait(self.browser, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//a[@href='/dns/records']//span[text()='DNS Records']")
                )
            )
            dynamic_dns_list.click()
            self.browser.save_screenshot(f"{SCREENSHOTS_PATH}/hosts-to-expire.png")
            self.look_for_warn_msg_and_confirm()
        except Exception as e:
            logger.error(f"Error while looking up DNS records: {e}")
            raise

    def run(self) -> int:
        return_code = 0
        try:
            self.login()
            self.update_hosts()
        except Exception as e:
            logger.error(f"An error has ocurred while running: {e}")
            self.browser.save_screenshot(f"{SCREENSHOTS_PATH}/exception.png")
            return_code = 1
        finally:
            self.browser.quit()
        return return_code


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="noip DDNS auto renewer",
    )
    parser.add_argument(
        "-u",
        "--username",
        required=True,
    )
    parser.add_argument("-p", "--password", required=True)
    parser.add_argument(
        "-s",
        "--totp-secret",
        required=True,
    )
    parser.add_argument(
        "-t",
        "--https-proxy",
        required=False,
    )
    parser.add_argument("-d", "--debug", type=bool, default=False, required=False)
    args = vars(parser.parse_args())

    logging.basicConfig(
        format="%(levelname)s: %(message)s",
        encoding="utf-8",
        level=logging.DEBUG if args["debug"] else logging.INFO,
    )

    NoIPRobot(
        args["username"],
        args["password"],
        args["totp_secret"],
        args["https_proxy"],
    ).run()
