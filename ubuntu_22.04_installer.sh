#!/bin/bash

echo "Executing install script!"

sudo apt update && sudo apt upgrade -y
sudo apt-get install ssh curl motion ffmpeg v4l-utils -y
sudo apt-get install libmariadb3 libpq5 libmicrohttpd12 -y

sudo apt-get install python2 -y
curl https://bootstrap.pypa.io/pip/2.7/get-pip.py --output get-pip.py
sudo python2 get-pip.py
sudo apt-get install libffi-dev libzbar-dev libzbar0 -y
sudo apt-get install python2-dev libssl-dev libcurl4-openssl-dev libjpeg-dev -y

sudo python2 -m pip install motioneye
sudo mkdir -p /etc/motioneye
sudo cp /usr/local/share/motioneye/extra/motioneye.conf.sample /etc/motioneye/motioneye.conf
sudo mkdir -p /var/lib/motioneye
sudo cp /usr/local/share/motioneye/extra/motioneye.systemd-unit-local /etc/systemd/system/motioneye.service

sudo systemctl daemon-reload
sudo systemctl enable motioneye
sudo systemctl start motioneye

sudo apt-get install python3-pip -y

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

echo "Completed install script!"