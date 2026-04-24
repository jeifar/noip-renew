import logging
import sys
from typing import Optional
import hvac
import pyotp

from constants import VAULT_ADDR

logger = logging.getLogger()


class VaultClient:
    def __init__(self, token: str, url: str = "http://127.0.0.1:8200"):
        self.client = hvac.Client(
            url=url,
            token=token,
        )
        logging.basicConfig(
            format="%(levelname)s: %(message)s", encoding="utf-8", level=logging.INFO
        )

    def _get_secret_from_path(self, path: str) -> dict:
        try:
            return self.client.secrets.kv.read_secret_version(path=path)["data"]["data"]
        except Exception as e:
            logger.error(f"Could not read secret: {e}")
            raise

    def get_password(self, path: str) -> str:
        return self._get_secret_from_path(path)["password"]

    def get_totp(self, path: str) -> str:
        return self._get_secret_from_path(path)["totp"]


class SecretStore:
    def __init__(
        self,
        password: Optional[str] = None,
        totp_secret: Optional[str] = None,
        vault_token: Optional[str] = None,
        vault_path: Optional[str] = None,
        vault_url: str = VAULT_ADDR,
    ):
        if not (password and totp_secret) and not (vault_token and vault_path):
            logger.error(
                "At least one of password and totp secret or vault token and path arguments need to be passed"
            )
            sys.exit(1)

        self.password = password
        self.totp_secret = totp_secret
        self.vault_client = VaultClient(vault_token, vault_url)
        self.vault_path = vault_path

    def get_password(self) -> str:
        return (
            self.password
            if self.password
            else self.vault_client.get_password(self.vault_path)
        )

    def get_token(self) -> str:
        otp_secret = (
            self.totp_secret
            if self.totp_secret
            else self.vault_client.get_totp(self.vault_path)
        )
        return pyotp.TOTP(otp_secret).now()
