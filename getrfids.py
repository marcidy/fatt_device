#!/usr/bin/env python
####
#
# FYI, this is god awful.  I wish it hadn't been implemented this way
# fortunately Elijah is re-writing the backend so we can burn this garbage
# down for the tire-fire it is.
#
###
import os
import sys

import requests

secret = os.getenv("FATT_SECRET")
URL = os.getenv("FATT_URL")


def getrfids():
    """
    """
    payload = None
    headers = {'User-Agent': 'Wget/1.20.1 (linux-gnu)'}
    # response = requests.get(URL, params=payload, verify=False)
    try:
        response = requests.get(URL, params=payload, headers=headers)
    except requests.exceptions.Timeout:
        # Maybe set up for a retry, or continue in a retry loop
        print("Timeout connecting to URL")
        sys.exit(1)
    except requests.exceptions.TooManyRedirects:
        # Tell the user their URL was bad and try a different one
        print("Invalid URL, exiting")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(e)
        sys.exit(1)
    rfids = response.content.decode("utf-8").split('\n')
    return rfids


def cacheRFIDs(rfids, filename="authorized.txt"):
    file = open(filename, "w+")
    for token in rfids:
        # short_token = token[-6:]
        short_token = token[-8:]
        file.write(short_token + "\n")


def main():
    r = getrfids()

    print("Total of {} RFID fobs".format(len(r)))
    cacheRFIDs(r)


if __name__ == '__main__':
    main()

# vim: ts=4 sw=4 et
