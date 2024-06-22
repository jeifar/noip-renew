import argparse
import logging
import re
import time
from sys import stdout

import pyotp
from constants import HOST_URL, LOGIN_URL, SCREENSHOTS_PATH, USER_AGENT
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By

# Set up logging
debug_enabled = False
logger = logging.getLogger(__name__)

logFormatter = logging.Formatter(
    "%(name)-12s %(asctime)s %(levelname)-8s %(filename)s:%(funcName)s %(message)s"
)
consoleHandler = logging.StreamHandler(stdout)
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)


class Robot:
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
        # Setup browser options
        options = webdriver.ChromeOptions()
        options.add_argument("disable-features=VizDisplayCompositor")
        options.add_argument("headless")
        options.add_argument("no-sandbox")
        options.add_argument("window-size=1200x800")
        options.add_argument(f"user-agent={USER_AGENT}")
        if self.https_proxy:
            options.add_argument("proxy-server=" + self.https_proxy)
        browser = webdriver.Chrome(options=options)
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

        try:
            self.browser.find_element(By.ID, "clogs-captcha-button").click()
        except Exception as e:
            logger.error(f"Error while logging in: {e}")
            raise Exception("Failed while trying to logging in")

        otp = pyotp.TOTP(self.totp_secret).now()

        # Fills in 6 pin OTP code
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

        try:
            self.browser.find_element(By.XPATH, "//input[@value='Verify']").click()
        except Exception as e:
            logger.error(f"Error while verifying 6-digit OTP code: {e}")
            raise Exception("Failed while trying to logging in")

        if debug_enabled:
            time.sleep(1)
            self.browser.save_screenshot(f"{SCREENSHOTS_PATH}/debug2.png")

    def open_hosts_page(self):
        logger.info(f"Opening {HOST_URL}...")
        try:
            self.browser.get(HOST_URL)
        except TimeoutException as e:
            logger.error(f"The process has timed out: {e}")
            self.browser.save_screenshot(f"{SCREENSHOTS_PATH}/timeout.png")

    def update_hosts(self):
        self.open_hosts_page()
        time.sleep(1)

        hosts = self.get_hosts()
        for host in hosts:
            host_name = self.get_host_link(host).text
            expiration_days = self.get_host_expiration_days(host)
            logger.info(f"expiration days: {expiration_days}")
            if expiration_days < 7:
                logger.info(f"Host {host_name} is about to expire, confirming host..")
                host_button = self.get_host_button(host)
                self.update_host(host_button, host_name)
                logger.info(f"Host confirmed: {host_name}")
            else:
                logger.info(
                    f"Host {host_name} is yet not due, remaining days to expire: {expiration_days}"
                )
            self.browser.save_screenshot(f"{SCREENSHOTS_PATH}/{host_name}-results.png")

    def update_host(self, host_button, host_name):
        logger.info(f"Updating {host_name}")
        host_button.click()
        time.sleep(1)
        intervention = False
        try:
            intervention = (
                self.browser.find_element(By.XPATH, "//h2[@class='big']")[0].text
                == "Upgrade Now"
            )
        except Exception as e:
            logger.error(f"An error has occurred: {e}")
            pass

        if intervention:
            raise Exception("Manual intervention required. Upgrade text detected.")
        self.browser.save_screenshot(f"{SCREENSHOTS_PATH}/{host_name}_success.png")

    @staticmethod
    def get_host_expiration_days(host):
        try:
            host_remaining_days = host.find_element(
                By.XPATH,
                ".//a[@class='no-link-style popover-info popover-colorful popover-dark']",
            ).get_attribute("data-original-title")
        except Exception:
            logger.info("Seems like the host has already expired")
            # Host is expired: Return 0 (remaining days)
            return 0
        regex_match = re.search("\\d+", host_remaining_days)
        if regex_match is None:
            raise Exception("Expiration days label does not match the expected pattern")
        expiration_days = int(regex_match.group(0))
        return expiration_days

    @staticmethod
    def get_host_link(host):
        return host.find_element(By.XPATH, ".//a[@class='link-info cursor-pointer']")

    @staticmethod
    def get_host_button(host):
        return host.find_element(
            By.XPATH, ".//following-sibling::td[4]/button[contains(@class, 'btn')]"
        )

    def get_hosts(self) -> list:
        host_tds = self.browser.find_elements(By.XPATH, '//td[@data-title="Host"]')
        if len(host_tds) == 0:
            raise Exception("No hosts or host table rows not found")
        return host_tds

    def run(self) -> int:
        return_code = 0
        try:
            self.login()
            self.update_hosts()
        except Exception as e:
            logger.error(f"An error has ocurred while Robot was running: {e}")
            self.browser.save_screenshot(f"{SCREENSHOTS_PATH}/exception.png")
            return_code = 1
        finally:
            self.browser.quit()
        return return_code


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="noip DDNS auto renewer",
        description="Renews each of the no-ip DDNS hosts that are below 7 days to expire period",
    )
    parser.add_argument("-u", "--username", required=True)
    parser.add_argument("-p", "--password", required=True)
    parser.add_argument("-s", "--totp-secret", required=True)
    parser.add_argument("-t", "--https-proxy", required=False)
    parser.add_argument("-d", "--debug", type=bool, default=False, required=False)
    args = vars(parser.parse_args())

    # Set debug level
    logger.setLevel(logging.DEBUG if args["debug"] else logging.ERROR)

    Robot(
        args["username"],
        args["password"],
        args["totp_secret"],
        args["https_proxy"],
    ).run()
