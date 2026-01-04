#!/bin/bash
#
# N9OH Rig Control Panel - IC-7300 Radio Control Startup Script
#
# Startup script that initializes the Rig Control Panel application.
# Manages process lifecycle for flrig, pavucontrol, and the main GUI application.
# Positions windows for optimal workspace layout.
#
# Author: Steve Woodruff, N9OH
# License: MIT
#
# Copyright (c) 2026 Steve Woodruff, N9OH
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

# Force native Wayland apps to use X11 backend
export QT_QPA_PLATFORM=xcb
export GDK_BACKEND=x11

# Kill running versions, if any
ps aux | grep rig-macros.py | grep -v grep | awk '{print $2}' | xargs kill > /dev/null 2>&1
killall flrig pavucontrol >/dev/null 2>&1

echo "Starting pavucontrol (pulse) ..."
pavucontrol > /tmp/pavucontrol.log 2>&1 &

echo "Starting flrig ..."
flrig > /tmp/flrig.log 2>&1 &

# Wait until flrig is listening on its configured XML-RPC port
# You can override this to a hard-coded port if you know what you bind to
FLRIG_PORT=$(grep -E 'xmlport|xmlrig_port' ~/.flrig/IC-7300.prefs | head -n1 | awk -F: '{print $2}')
until ss -ltn | grep -q ":$FLRIG_PORT"; do sleep 1; done

echo "Starting Rig Macros ..."
python3 rig-macros.py &

move_window() {
  local pattern="$1"
  local geom="$2"
  local attempts=5
  local delay=1
  local wid=""

  for ((i=0; i<attempts; i++)); do
    wid=$(wmctrl -l | grep "$pattern" | awk '{print $1}' | head -n1)
    if [ -n "$wid" ]; then
      wmctrl -i -r "$wid" -e "$geom"
      return
    fi
    sleep $delay
  done

  echo "Window not found for pattern: $pattern"
}

move_window "Volume Control" "0,21,920,680,382"
move_window "flrig IC-7300" "0,50,80,425,322"
move_window "N9OH Rig Control Panel" "0,43,456,492,502"
