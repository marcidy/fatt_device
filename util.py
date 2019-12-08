from datetime import datetime
import os
import requests


DEBUG = True


def report_attempt(rfid, result):
    ASSET_ID = os.environ['AMTGC_ASSET_ID']
    GC_ASSET_TOKEN = os.environ['AMTGC_ASSET_TOKEN']
    REPORTING_URL = os.environ['AMTGC_REPORTING_URL']

    data = {
        'access_point': ASSET_ID,
        'activity_date': datetime.now(),
        'credential': rfid,
        'success': result,
    }

    headers = {'Authorization': "Token {}".format(GC_ASSET_TOKEN)}
    resp = requests.post(REPORTING_URL, data, headers=headers)
    print(resp.content)
    return resp


def load_whitelist():
    with open("authorized.txt", 'r') as f:
        authorized_rfids = f.read().split("\n")
        return authorized_rfids
