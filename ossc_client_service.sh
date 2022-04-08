#!/bin/bash

### BEGIN INIT INFO
# Provides:          ossc_client
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: ossc_client
# Description:       Open Source Security Camera Client
### END INIT INFO

source /lib/lsb/init-functions

do_start () {
  log_daemon_msg "Starting system ossc_client daemon"
  start-stop-daemon --start --background --pidfile /var/run/ossc_client.pid --make-pidfile --user root --chuid root --startas /usr/bin/python3 /var/lib/ossc_client/ossc_client.py
  log_end_msg $?
}
do_stop () {
  log_daemon_msg "Stopping system ossc_client daemon"
  start-stop-daemon --stop --pidfile /var/run/ossc_client.pid --retry 10
  log_end_msg $?
}

case "$1" in
  start|stop)
    do_${1}
    ;;
  restart|reload|force-reload)
    do_stop
      do_start
      ;;
  status)
    status_of_proc "ossc_client" "DAEMON" && exit 0 || exit $?
    ;;
  *)
    echo "Usage: ossc_client {start|stop|restart|reload|force-reload|status}"
        ;;

esac
exit 0