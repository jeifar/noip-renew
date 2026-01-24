# no-ip renewal

[noip.com](https://www.noip.com/) free hosts expire every month (every 30 days to be exact). This script checks the website to renew the hosts, using Python/Selenium with Chrome headless mode.

Based originally in [noip-renew](https://github.com/loblab/noip-renew) and made some minor improvements (improved logging, stronger typing, better docs) and updated to fit NO-IP latest UI changes.

## Prerequisites

- Have a no-ip account with DNS already setup (how you maintain the IPs pointing to the records is up to you).
- Your account must be secured with 2FA/TOTP, else no-ip will send a one-time code to your email and this script does not manage that (nor it is its intention)
- Python >= 3.12

## Usage

1. Clone this repository
2. Install the libs:

```shell
% pip install -r requirements.txt
```

3. Run the command:

```shell
python noip-renew.py  -h
usage: noip DDNS auto renewer [-h] -u USERNAME -p PASSWORD -s TOTP_SECRET [-t HTTPS_PROXY] [-d DEBUG]

options:
  -h, --help            show this help message and exit
  -u, --username USERNAME
  -p, --password PASSWORD
  -s, --totp-secret TOTP_SECRET
  -t, --https-proxy HTTPS_PROXY
  -d, --debug DEBUG
```

### Note

You can use either a TOTP secret (6-digit number) or the PRIV Key from the 2FA

## Usage with Docker

1. Build the container image:

```shell
% docker build -t noip-renewer:latest .
```

2. Run it:

- Use `-v` to mount the screenshots path into your current directory.

```shell
% docker run -ti --rm -v ${PWD}/screenshots:/app/screenshots noip-renewer:latest -u "<YOUR_EMAIL>" -p "<YOUR_PASSWORD>" -s "<YOUR_TOTP_SECRET>"
```

## As a cronjob

Add the following to your crontab, e.g. everyday 1AM:

```shell
crontab -l | { cat; echo "0 1 * * * docker run -ti --rm -v ${PWD}/screenshots:/app/screenshots noip-renewer:latest -u '<YOUR_EMAIL>' -p '<YOUR_PASSWORD>' -s '<YOUR_TOTP_SECRET>'"; } | crontab -
```
