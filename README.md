# no-ip renewal

[noip.com](https://www.noip.com/) free hosts expire every month (every 30 days to be exact). This script checks the website to renew the hosts, using Python/Selenium with Chrome headless mode.

Based originally in [noip-renew](https://github.com/loblab/noip-renew) and made some minor improvements (improved logging, adding types, better docs).

## Prerequisites

- Have a no-ip account with DNS already setup (how you maintain the IPs pointing to the records is up to you).
- Your account must be secured with 2FA/TOTP, else no-ip will send a one-time code to your email and this script does not manage that.
- Python >= 3.10

## Usage

1. Clone this repository
2. Install the pip lib:

```shell
% pip install -r requirements.txt
```

3. Run the command:

```shell
% python3 noip-renew.py -h
usage: noip DDNS auto renewer [-h] -u USERNAME -p PASSWORD -s TOTP_SECRET [-t HTTPS_PROXY] [-d DEBUG]

Renews each of the no-ip DDNS hosts that are below 7 days to expire period

options:
  -h, --help            show this help message and exit
  -u USERNAME, --username USERNAME
  -p PASSWORD, --password PASSWORD
  -s TOTP_SECRET, --totp-secret TOTP_SECRET
  -t HTTPS_PROXY, --https-proxy HTTPS_PROXY
  -d DEBUG, --debug DEBUG
```

## Usage with Docker

1. First, build the container image:
```shell
% docker build -t noip-renewer:latest .
```

2. Then run it:

- Use `-v` to mount the screenshots path into your current directory.

```shell
% docker run -ti --rm -v ${PWD}/screenshots:/app/screenshots noip-renewer:latest -u "<YOUR_EMAIL>" -p "<YOUR_PASSWORD>" -s "<YOUR_TOTP_SECRET_KEY>"
```

## As a cronjob

Add the following to your crontab, e.g. everyday 1AM:

```shell
crontab -l | { cat; echo "0 1 * * * docker run -ti --rm -v ${PWD}/screenshots:/app/screenshots noip-renewer:latest -u '<YOUR_EMAIL>' -p '<YOUR_PASSWORD>' -s '<YOUR_TOTP_SECRET_KEY>'"; } | crontab -
```
