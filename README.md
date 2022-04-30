# Installation Notes
This guide is for installing on a Raspberry Pi 4. However, you can use any version of linux where you're able to get the dependencies working. The details of installing on anything else will be left up to you, but this guide will most likely be a good starting point anyway. 

Note that the Raspberry Pi foundation broke their old camera support in Nov of 2021, and Motion and MotionEye don't work Raspberry Pi integrated cameras anymore. However, it still works with networked cameras, usb cameras or other types that are supported by Motion. The nice thing about this is that you can still use MotionEyeOS on a Raspberry Pi with an integrated camera, set it up as a network cam, then have this installed on a hub that handles the recording and remote communications. If this situation changes, you will likely be able to install this matrix-chat based security cam setup directly on a Raspberry Pi with an integrated camera following the same setup, only differing in the install of MotionEye.

Why can't we just use Raspian Buster? Well, the problem with this is that Buster used an older version of python3, and some of the other dependencies for Matrix NIO aren't compatible with Buster. So we'll need to stick with Bullseye. Plus, hitching our cart to the legacy version of Raspian isn't a recipe for long term success.

# Raspberry Pi setup. This specifically is for the Raspberry Pi 4. 

## 1: Install raspian lite - 32bit (Bullseye)
Use Raspberry Pi Imager - https://www.raspberrypi.com/software/
In the Raspberry Pi Imager select the appropriate operating system from the menu. Press ctrl-x (or press the gear icon) to bring up config menu. Enable SSH, select a password, username will be 'pi' by default. Make sure to enable wifi and configure too, and setup region details.

write your image to your micro SD Card.

SSH into the raspberry... Look up the IP it got on your local router if needed.

## 2: Install ffmpeg: 
```
sudo apt-get install ffmpeg libmariadb3 libpq5 libmicrohttpd12 -y
```

## 3: Install motion:
I recommend going and getting the latest version of motion manually. This one labeled as buster works just fine with my setup on Bullseye 32 bit.
```
wget https://github.com/Motion-Project/motion/releases/download/release-4.4.0/pi_buster_motion_4.4.0-1_armhf.deb
sudo dpkg -i pi_buster_motion_4.4.0-1_armhf.deb
```
These steps only needed if there is an error starting motion
```
sudo mkdir /tmp/motion
sudo chown motion:motion /tmp/motion
sudo nano /etc/motion/motion.conf
```
--Edit the file to point the logs at our new file... The "logfile" line:
```
logfile /tmp/motion/motion.log
```
		
			
## 4: Stop motion:

```
sudo systemctl stop motion
sudo systemctl disable motion
```

## 5: Install pip, motioneye and dependencies:

```
sudo apt-get update
sudo apt-get install python2 python-dev-is-python2 -y
curl https://bootstrap.pypa.io/pip/2.7/get-pip.py --output get-pip.py
sudo python2 get-pip.py
sudo apt-get install libssl-dev libcurl4-openssl-dev libjpeg-dev zlib1g-dev -y
sudo python2 -m pip install motioneye
```

## 6: Prep config directory:
```
sudo mkdir -p /etc/motioneye
```
Copy the motioneye.conf.sample file to the directory as below... you might have to change the source directory.\
```
sudo cp /usr/local/share/motioneye/extra/motioneye.conf.sample /etc/motioneye/motioneye.conf
```
		
## 7: Prep the media directory:

```
sudo mkdir -p /var/lib/motioneye
```

## 8: Add an init script, configure it to run at startup and start the motionEye server:
```
sudo cp /usr/local/share/motioneye/extra/motioneye.systemd-unit-local /etc/systemd/system/motioneye.service
sudo systemctl daemon-reload
sudo systemctl enable motioneye
sudo systemctl start motioneye
```

## 9: Add to MotionEye:
This is something you will need to work out with your particular setup, as you can use basically anything compatible with MotionEye.
Again, this won't work with the integrated Raspberry Pi camera yet, as MotionEye hasn't been updated (at this time) to use the new Raspberry Pi camera stack. You can use other types of cameras as specified in their documentation.
You can however, use a raspberry pi camera setup to be a network cam. For example I setup my pi zero using "MotionEyeOS", then in its settings under "expert settings" enabled "Fast Network Cam" which just streams the camera output to an address which can be found under stream settings. Mine for example was located at http://192.168.0.198:8081/ Then on my controller Raspberry Pi 4 I added this camera as a network cam. I couldn't get MotionEye recording to work correctly with the cam setup as a remote MotionEye camera, this is because the remote camera will record on the remote device, and not the camera hub. So use a Fast Network Cam Setup.

## 10: Configure MotionEye
Setup movies and motion detection. You will want to experiment to see what is right for you, as motion has plenty of options for masking areas, and thresholds for recording. One setting that you might want to tweak right away is the frame rate on the video device, as by default its set to 2. Bumping it up to 10 seems pretty good for my purposes, and should help keep video sizes down.

All done. MotionEye should be installed and running. Next we need to install the Matrix Communication Dependencies.

# Installing Matrix NIO on a Raspberry Pi 4
Your needs and setup my be different if not using a Raspberry Pi 4. You will need Raspian Bullseye for this next portion to work though, as many of the dependencies don't exist for earlier versions of Raspian (buster for example).

### === Additional things to add to cam maybe. Testing stuff ===
```
sudo apt-get -y install python3-pip
```

#### Install Matrix dependencies.

```
sudo apt install python3 python3-pip
sudo apt-get install libzbar-dev libzbar0 -y
sudo apt install libolm3 libolm-dev -y
sudo python3 -m pip install python-olm
```

#### Matrix nio, and encrypted client.
```
sudo pip3 install matrix-nio
sudo pip3 install "matrix-nio[e2e]"
```

#### Pillow for the client scripts
```
sudo python3 -m pip install --upgrade Pillow
sudo python3 -m pip install python-magic
```


# Install Camera Client Software

Our dependencies:
MotionEye
MatrixNio
Watchdog

sudo python3 -m pip install watchdog

Install procedure pending finishing up of client alpha software.

Create directories for the client
sudo mkdir /var/lib/ossc_client
sudo mkdir /var/lib/ossc_client/log
sudo mkdir /var/lib/ossc_client/credentials

Move files to their correct locations - This assumes you've copied them to the device and are in their current directory.
sudo mv ./ossc_client.py /var/lib/ossc_client
sudo mv ./config.cfg /var/lib/ossc_client
sudo mv ./ossc_client_service.sh /var/lib/ossc_client

Setup the service
sudo ln -s /var/lib/ossc_client/ossc_client_service.sh /etc/init.d
sudo update-rc.d ossc_client_service.sh defaults

How to uninstall service:
update-rc.d ossc_client_service.sh remove 



# Notes for things to do

DONE - ADD functionality for monitoring camera configs.
DONE - ADD Functionality so client keeps track of camera config too
DONE - Eliminate Hachiko dependency.
DONE - NEEDS CHECKING POSSIBLE REFACTOR - ADD ID to messages / requests
DONE - For Raspberry PI 4 - Create install / setup script
DONE - Create video on demand service.
DONE - Replace "is_for" with "requestor_id"
DONE - Synch keys on every message send.
DONE - Refactor send_image function to allow for custom "content" in JSON for send.


TODO - Encrypted Key Backup
TODO - Network loss tolerance check
TODO - Unit tests
TODO - QR setup maybe?
TODO - History video request.


## For QR reader we will need extra tools:

[sudo] python3 -m pip install qrtools
[sudo] python3 -m pip install pypng
[sudo] python3 -m pip install pyzbar

