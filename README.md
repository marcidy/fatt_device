## Repository
Each AMT FATT device has a branch on this repository.  'master' contains common code, but is not necessary a superset or a subset at this time.

## Installation
Clone this repo to the pi user's home directory and switch to the branch for the device.  If you deviate from this path, that's fine, it's assumed you know enough to change all the instances of that path in the repo.  This is a demo and not intended to be robust to changes.

Follow all the instructions in INSTALL.md on the raspberry pi.

## Please Note
Two separate sets of environment variables are required.  1 set is common to all devices which will connect back to AMT servers.  The other set is device specific information.  They are not stored in this repo as they are considered sensitive information.

## Control Flow
1) runs getrfids.py on a systemd timer
- This pulls all data available at the aformentioned undefined endpoint as a list of strings

2) runs main.py as a systemd service
- installs falling edge detection on a couple pins which are intended as a weigand interface. 
- when triggered, the pins will populate a string meant to be an ID
- if the ID authenticates against the aformnentioned list, sets a pin high for 1 second.

High level, it's an RFID reader implementing the weigand protocol which can unlock a thing if the RFID authenticates.
