## Repository
Each AMT FATT device has a branch on this repository.  'master' contains common code, but is not necessary a superset or a subset at this time.

The laser branch contains code which runs the access control box on the AMT laser.  At this moment, the repo contains code which executes on a raspberry pi, which inturn communicates with a Teensy attached via USB.  The teensy firmware is located here:  https://github.com/acemonstertoys/laser-rfid/tree/master/teensy/laser_worker

Most FATT devices use the new standardized weigand reader, however the laser currently uses one attached to the Teensy.  This will evolve to standardization over time.

## Installation
Clone this repo to the pi user's home directory and switch to the branch for the device.  If you deviate from this path, that's fine, it's assumed you know enough to change all the instances of that path in the repo.  This is a demo and not intended to be robust to changes.

Follow all the instructions in INSTALL.md on the raspberry pi.

## Please Note
Two separate sets of environment variables are required.  1 set is common to all devices which will connect back to AMT servers.  The other set is device specific information.  They are not stored in this repo as they are considered sensitive information.

A file using dummy values is required to run the tests.

## Control Flow
1) runs getrfids.py on a systemd timer
- This pulls all data available at the aformentioned undefined endpoint as a list of strings

2) runs main.py as a systemd service
- communicates to Teensy to updates to the odoeter and checking for new rfid scans
- if scanned ID authenticates against the wihtelist, enables the laser
- resets odometer on a new session
- tracks change in odometer over a logged in session
- logs cuts times, costs, and access attemps via systemd

# Tests
## Runnning
pytest is used to run tests.  It will be installed as a requirement.  The following env vars are needed to executes tests, but have no consequence on the test results (with example values which work fine for testing).

```bash
AMTGC_ASSET_ID=9999
AMTGC_ASSET_TOKEN=d3adb33fc4f3f00d
AMTGC_LASER_COST=0.5
FATT_URL=https://notarealurl.com
FATT_SECRET=asdfasdfasdf
AMTGC_REPORTING_URL=http://notarealurl.com
```

## Coverage
Coverage is installed and calculated when running pytest as
```bash
$ pytest --cov
```
