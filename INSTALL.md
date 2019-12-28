# Image preparation
The base image for these devices is currently 2019-09-26-raspbian-buster-lite.img

Download the rasbian image from raspberrypi.org, extract it, and write to an SD card.

Re-insert the card and mount the root filesystem (1st partition)
Enable ssh by creating a file 'ssh' in the root of the boot partition
$ touch /mnt/ssh

Mount the root filesystem (2nd partition)

Create /home/pi/.ssh
$ mkdir /home/pi/.ssh

Add ssh public keys to /home/pi/.ssh/authorized_keys

Restrict permissions to authorized_keys file
$ chmod 400 /home/pi/.ssh/authorized_keys

Restrict permissions to .ssh directory
$ chmod 700 /home/pi/.ssh

Eject the SD card and insert it into a raspberry pi
Connect the device to an accessible network
Log into the device to contine with the rest of the steps.

# Expand the filesystem
$ sudo raspi-config 

Select Advanced, Expand the filesystem

Let the system reboot when asked.

# Install system libraries using apt
$ sudo apt-get update
$ sudo apt-get install python3-pip python3-venv git

# Configure python with virtual environment
$ python3 -m pip install --user --upgrade pip
$ python3 -m venv venv 
$ source venv/bin/activate
$ pip install requests
$ pip install RPi.GPIO

If you have a customized wpa_supplicant.conf, add it to /etc/wpa_supplicant/ folder and restart

# configure deploy keys
Acquire the fatt device deployment key and put in the .ssh directory.  This key is read only on the fatt device repo.  Write keys should not be useed.

# clone repo
$ git clone <this repo> amt_door

# link systemd files to /etc/systemd/system
$ sudo ln -s /home/pi/amt_door/systemd/amt_door.service /etc/systemd/system/amt_door.service
$ sudo ln -s /home/pi/amt_door/systemd/getrfids.service /etc/systemd/system/getrfids.service
$ sudo ln -s /home/pi/amt_door/systemd/getrfids.timer /etc/systemd/system/getrfids.timer

# Environment Files
Two environment files are required, fatt.env and device.env.  fatt.env is application wide variables and device.env are device specific.  It'd be nice to automate the generation of these files at somme point.

## fatt.env
This file configures the URL to get a list of RFIDs and where to send log data
```
FATT_URL=https://some.url.tld:port/rfid_source
FATT_SECRET=SOMETOKEN
AMTGC_REPORTING_URL=https://some.url.tld:port/reporting_endpoint
```
## device.env
This file is configuration specific to this hardware, ie, it's unique ID and unique django token
```
AMTGC_ASSET_ID=<Asset ID in Grand Central>
AMTGC_ASSET_TOKEN=DJANGO_USER_TOKEN
```
# reload systemd services
$ sudo systemctl daemon-reload

# install systemd services
$ sudo systemctl enable getrfids.timer
$ sudo systemctl start getrfids.timer
$ sudo systemctl enable amt_door.service
$ sudo systemctl start amt_door.service

# Check rfid download 
rfid shoulds be downloaded to ~/amt_door/authorized.txt, check timestamp and file integrity

# Update hostname
update the device hostname in /etc/hostname. The hostname should be 'amt<door number>' where <door number> is like '113' for the acl device controlling the door to room 113.  This is not a FQDN, it's just the host name.

# reboot the system
Check that everything comes back up as expected over a reboot, and scan a known good fob to see if it logs properly
