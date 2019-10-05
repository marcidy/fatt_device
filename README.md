## What is this
This is just a demo.  IT's meant to be installed and run on a raspberry pi.  It will not work otherwise.

## Installation
clone this repo or unzip the download into a directory '/home/pi/amt_door'.  IF you deviate from this path, that's fine, I assume you know enough to change all the directories in the repo.  This is a demo and not intended to be robust to changes.

Follow all the instructions in doc/customizations on the raspberry pi.

## Please Note
This is confgured to pull from an API endpoint which is not defined in this repo, and would normally be set in a file 'rfids' which is referenced in the systemd configuration in systemd/getrfids.service.

## What is this doing
1) runs getrfids.py on a systemd timer
- This pulls all data available at the aformentioned undefined endpoint as a list of strings

2) running main.py as a systemd service
- installs falling edge detection on a couple pins which are intended as a weigand interface. 
- when triggered, the pins will populate a string meant to be an ID
- if the ID authenticates against the aformnentioned list, sets a pin high for 1 second.

High level, it's an RFID reader implementing the weigand protocol which can unlock a thing if the RFID authenticates.
