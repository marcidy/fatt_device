# Install system libraries using apt
$ sudo apt-get update
$ sudo apt-get install python3-pip python3-venv git rclone

# Configure python with virtual environment
$ python3 -m pip install --user --upgrade pip
$ python3 -m venv venv 
$ source venv/bin/activate
$ pip install requests
$ pip install RPi.GPIO

If you have a customized wpa_supplicant.conf, add it to /etc/wpa_supplicant/ folder and restart

# clone repo
$ git clone <git location>

# link systemd files to /etc/systemd/system
$ sudo ln -s /home/pi/amt_door/systemd/amt_door.service /etc/systemd/system/amt_door.service
$ sudo ln -s /home/pi/amt_door/systemd/getrfids.service /etc/systemd/system/getrfids.service
$ sudo ln -s /home/pi/amt_door/systemd/getrfids.timer /etc/systemd/system/getrfids.timer

# Two environment files are required, fatt.env and device.env.  fatt.env is application wide variables and device.env are device specific.

## fatt.env
# configures the URL to get a list of RFIDs and where to send log data
FATT_URL=https://some.url.tld:port/rfid_source
FATT_SECRET=SOMETOKEN
AMTGC_REPORTING_URL=https://some.url.tld:port/reporting_endpoint

## device.env
# Configuration specific to this hardware, ie, it's unique ID and unique django token
AMTGC_ASSET_ID=1
AMTGC_ASSET_TOKEN=DJANGO_USER_TOKEN

# reload systemd services
$ sudo systemctl daemon-reload

# install systemd services
$ sudo systemctl enable getrfids.timer
$ sudo systemctl start getrfids.timer
$ sudo systemctl enable amt_door.service
$ sudo systemctl start amt_door.service

# rfid shoulds be downloaded to ~/new_door/authorized.txt, check timestamp and file integrity

