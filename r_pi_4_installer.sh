#!/bin/bash

sudo apt-get update -y
sudo apt-get install ffmpeg libmariadb3 libpq5 libmicrohttpd12 -y
wget https://github.com/Motion-Project/motion/releases/download/release-4.4.0/pi_buster_motion_4.4.0-1_armhf.deb
sudo dpkg -i pi_buster_motion_4.4.0-1_armhf.deb
sudo rm pi_buster_motion_4.4.0-1_armhf.deb

sudo systemctl stop motion
sudo systemctl disable motion

sudo apt-get install python2 python-dev-is-python2 -y
sudo curl https://bootstrap.pypa.io/pip/2.7/get-pip.py --output get-pip.py
sudo python2 get-pip.py
sudo apt-get install libssl-dev libcurl4-openssl-dev libjpeg-dev zlib1g-dev -y
sudo python2 -m pip install motioneye

sudo mkdir -p /etc/motioneye
sudo cp /usr/local/share/motioneye/extra/motioneye.conf.sample /etc/motioneye/motioneye.conf
sudo mkdir -p /var/lib/motioneye

sudo cp /usr/local/share/motioneye/extra/motioneye.systemd-unit-local /etc/systemd/system/motioneye.service
sudo systemctl daemon-reload
sudo systemctl enable motioneye
sudo systemctl start motioneye

sudo apt-get -y install python3-pip
sudo apt-get install libzbar-dev libzbar0 -y
sudo apt install libolm3 libolm-dev -y
sudo python3 -m pip install python-olm

sudo pip3 install matrix-nio
sudo pip3 install "matrix-nio[e2e]"

sudo python3 -m pip install --upgrade Pillow
sudo python3 -m pip install python-magic

sudo python3 -m pip install watchdog

sudo mkdir /var/lib/ossc_client
sudo mkdir /var/lib/ossc_client/log
sudo mkdir /var/lib/ossc_client/credentials


sudo mv ./ossc_client.py /var/lib/ossc_client
sudo mv ./config.cfg /var/lib/ossc_client
sudo mv ./ossc_client_service.sh /var/lib/ossc_client

sudo ln -s /var/lib/ossc_client/ossc_client_service.sh /etc/init.d
sudo update-rc.d ossc_client_service.sh defaults