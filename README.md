# N9OH Rig Control Panel

[![Tests](https://github.com/sjwoodr/RigControlPanel/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/sjwoodr/RigControlPanel/actions/workflows/tests.yml)

A comprehensive GUI application for controlling an Icom IC-7300 radio with advanced features including voice keying, QSO recording, and text-to-speech transmission via PulseAudio.

**Author**: Steve Woodruff, N9OH  
**License**: MIT

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Technical Details](#technical-details)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [License](#license)

---

## Features

### VFO Control
- **Copy VFO A → B**: Duplicate frequency/mode from VFO A to VFO B
- **VFO A/B Toggle**: Switch between VFO A and B with synchronized display
- **Split Mode**: Enable/disable split operation with real-time visual indicator
- **Real-time Status Display**: Shows current frequency, mode, VFO, and split status
- **VFO B Status**: Displays secondary VFO information when split mode is active

### Band Selection
- **CW Mode**: Quick access to 10m, 12m, 15m, 20m, and 40m CW frequencies
- **SSB Mode**: Band buttons with automatic sideband selection based on band
  - 10m, 12m, 15m, 20m: USB (upper sideband)
  - 40m: LSB (lower sideband)
  - Proper restoration to original mode after other transmit operations

### QSO Recording
Record, playback, and manage QSO audio files with combined radio and microphone input.

- **Record**: Captures both radio audio (USB audio interface) and microphone input (USB webcam) simultaneously
- **Play**: Review recorded QSOs with VLC media player
- **Save**: Export recordings to `~/Documents/QSO Recordings/` with custom naming
- **Delete**: Remove unwanted recordings with confirmation for previously saved files

### Voice Keyer - Memory Playback
Transmit pre-recorded voice messages stored in the radio's internal voice memory via CI-V commands over serial port.

#### Voice Memory Buttons
- **N9OH**: Transmits voice memory slot T1 (callsign announcement)
- **59 FL**: Transmits voice memory slot T2 (signal report response)
- **T3, T4**: Placeholder buttons (disabled for future expansion)

**How it works:**
1. Raises RTS (Request To Send) signal on the serial port to key the radio's PTT
2. Sends CI-V command to play the specified voice memory slot (01-08)
3. Monitors radio's power meter to detect transmission completion
4. Automatically lowers RTS when transmission ends
5. No mode changes required - transmits in current mode

### Voice Keyer - Piper TTS
Generate and transmit speech-synthesized messages using the Piper text-to-speech engine with automatic mode switching and RTS control.

#### TTS Buttons
- **N9OH**: Generates "November Nine Oscar HOTEL" at normal speed (length-scale 0.72)
- **TU 59**: Generates "Thanks, also FIVE NINE" at normal speed (length-scale 0.72)
- **73**: Generates "Seventy-Three" at slower speed (length-scale 0.55) with enhanced pitch for clarity

**How it works:**
1. Pre-generates WAV files at startup (cached for instant playback)
2. Saves current radio mode before proceeding
3. Switches radio to [UL]SB-D (data mode) for optimal audio quality and levels
4. Raises RTS to key the radio for transmission
5. Streams audio via PulseAudio using `paplay` command
6. Automatically restores original radio mode when audio finishes
7. Lowers RTS after mode restoration

**Audio Processing:**
- TTS files generated using Piper with `en_US-hfc_male-medium` voice model
- Variable length scale controls speech rate for clarity
- 73 button applies sox pitch shift (+150 cents) for enhanced intelligibility
- Pre-generation at startup eliminates real-time processing delays
- Audio played through default PulseAudio device

### Debug Output
- Collapsible debug panel shows real-time system messages and state changes
- Logs voice keyer operations, mode changes, RTS control, TTS generation, and errors
- Clear button to reset debug output between sessions
- All messages timestamped with HH:MM:SS format for troubleshooting
- Serial port and CI-V command logging for development

---

## Requirements

### Platform Support

⚠️ **This application is tested and supported on Linux (Ubuntu 24.04) only.**

The application is not compatible with Windows or macOS due to:
- Heavy reliance on Linux-specific tools (PulseAudio, ffmpeg, sox)
- Serial port handling specific to Linux
- Filesystem paths and permissions that differ on other platforms

### Support & Disclaimer

⚠️ **No official support is provided for this tool.** This is a personal project developed for amateur radio use. Users are responsible for:
- Installation and configuration of all dependencies
- Troubleshooting hardware/software compatibility issues
- Modifying code to suit their specific radio setup and environment

For assistance, refer to the [Troubleshooting](#troubleshooting) section or consult relevant documentation for the tools used (flrig, PulseAudio, Piper, ffmpeg, etc.).

### Hardware
- **Radio**: Icom IC-7300 (or other Icom model with CI-V support - adjust address in code)
- **Serial Interface**: USB-to-serial cable or radio's native USB port (for CI-V control via RTS/DTR)
- **Audio Interface**: USB audio interface (for QSO recording and TTS playback)
- **Microphone**: USB microphone or webcam with mic (optional, for recording)

### Software Dependencies

#### Core Requirements
- **Python 3.8+** with tkinter
- **flrig**: Icom radio control via XML-RPC (must be running)
- **pyserial**: Python serial port library for RTS/DTR control

#### Voice Keyer - Memory
- **socat**: (built-in, used for serial communication if needed)

#### Voice Keyer - TTS
- **piper**: Text-to-speech engine
- **paplay**: PulseAudio playback utility (part of `pulseaudio-utils`)
- **sox**: Audio processing (for pitch shifting)

#### QSO Recording & Playback
- **ffmpeg**: Audio/video recording and conversion
- **vlc**: Recording playback
- **PulseAudio**: Audio routing and device management

---

## Installation

### System Requirements

- **Operating System**: Ubuntu 24.04 (tested and verified)
- **Other Linux distributions**: May work but not officially tested
- **Windows/macOS**: Not supported

### 1. System Dependencies (Ubuntu 24.04)

```bash
# Install base requirements
sudo apt-get update
sudo apt-get install python3 python3-tk

# Install radio control and audio tools
sudo apt-get install flrig sox ffmpeg vlc pavucontrol pulseaudio-utils piper

# Install pyserial for serial port communication
sudo apt-get install python3-serial
```

**Dependency Summary:**
- `flrig` - Radio control daemon
- `sox` - Audio processing (pitch shifting)
- `ffmpeg` - QSO recording
- `vlc` - Recording playback
- `pavucontrol` - PulseAudio mixer
- `pulseaudio-utils` - Contains `paplay` for TTS audio playback
- `piper` - Text-to-speech synthesis engine
- `python3-serial` - Serial port control

### 2. Piper Voice Model

```bash
# Download the voice model used by default
python3 -m piper.download_voices en_US-hfc_male-medium
```

### 3. Serial Port Permissions

```bash
# Add your user to dialout group for USB serial access
sudo usermod -a -G dialout $USER

# Apply group changes (log out and back in, or use newgrp)
newgrp dialout
```

### 4. Clone or Copy Repository

```bash
# If you have this in a git repository
git clone <repository-url> ~/src/other/RigControlPanel
cd ~/src/other/RigControlPanel
```

---

## Configuration

### 1. Voice Keyer & TTS Settings (rig-macros.conf)

The application reads customizable voice keyer and TTS settings from `rig-macros.conf`. This file allows you to personalize button labels and text without editing Python code.

#### Voice Keyer Memory Buttons (T1-T4)

Edit the `[Voice Keyer Memory]` section to customize labels:

```ini
[Voice Keyer Memory]
t1_label = N9OH
t2_label = 59 FL
t3_label = T3
t4_label = T4
```

These labels appear on the buttons in the GUI. T3 and T4 are disabled by default but you can customize their labels for future use.

#### Piper TTS Buttons

Edit the `[Piper TTS]` section to customize button labels, text, speech rate, and pitch:

```ini
[Piper TTS]
# Button 1
button1_label = N9OH
button1_text = ,, November Nine Oscar HOTEL
button1_length_scale = 0.72
button1_pitch = 0

# Button 2
button2_label = TU 59
button2_text = Thanks, also FIVE NINE
button2_length_scale = 0.72
button2_pitch = 0

# Button 3
button3_label = 73
button3_text = Seventy-Three
button3_length_scale = 0.55
button3_pitch = 150
```

**Configuration Parameters:**

- **button_label**: Text displayed on the button in the GUI
- **button_text**: Text to be synthesized by Piper TTS
- **button_length_scale**: Speech speed (0.5-1.0)
  - `0.55` = slower (better for important messages)
  - `0.72` = normal (recommended)
  - `1.0` = faster
- **button_pitch**: Pitch shift in cents (0=normal)
  - `0` = no pitch change
  - `150` = raised pitch (better intelligibility on radio)
  - `-150` = lowered pitch

**Example - Custom Button:**

To change Button 1 to your call sign with different speech rate:
```ini
button1_label = MYCALL
button1_text = ,, Mike Yankee Charlie Alpha Lima Lima
button1_length_scale = 0.60
button1_pitch = 100
```

Changes take effect when you restart the application.

### 2. Serial Port Configuration

Edit `rig-macros.py` to match your setup:

```python
# Line ~40: Change device path if not /dev/ttyUSB0
serial_port = serial.Serial('/dev/ttyUSB0', 19200, timeout=0.1)
```

Find your USB device:
```bash
ls -la /dev/ttyUSB*
dmesg | grep -i "usb\|serial"
```

### 3. flrig Configuration

#### Option A: Automatic (via startup script)
```bash
bash rig-macros.sh
```
This automatically starts flrig with default settings.

#### Option B: Manual Configuration
1. Launch flrig separately: `flrig &`
2. Configure for your radio model (IC-7300)
3. Verify XML-RPC port (default: 12345)
4. Ensure radio is powered on and USB is connected

Check flrig's XML-RPC port:
```bash
grep -i "xmlport\|xmlrig" ~/.flrig/IC-7300.prefs
```

### 4. Radio Voice Memory Setup

Record voice messages in your radio's voice memory slots:

1. **IC-7300 Voice Keyer Setup**:
   - Press MENU → VFO/MEM → Voice Keyer
   - Select slot (T1, T2, etc.)
   - Press PTT and speak your message
   - Release PTT when done
   - Test playback by pressing T1, T2 button on radio

2. **Recommended Messages**:
   - **T1 (N9OH)**: Your callsign ("November Nine Oscar Hotel")
   - **T2 (59 FL)**: Signal report ("Five Nine, Florida")
   - **T3-T8**: Custom messages for your use

### 5. PulseAudio Configuration

#### View Available Devices
```bash
pactl list short sources      # Audio inputs
pactl list short sinks        # Audio outputs
```

#### Set Default Output (for TTS)
```bash
# Launch PulseAudio control
pavucontrol &

# In the Playback tab, set default device for paplay
# In the Recording tab, set devices for ffmpeg recording
```

#### Or use CLI
```bash
# Find device index
pactl list short sinks | grep -i "usb"

# Set as default
pactl set-default-sink <index>
```

### 6. Window Position Customization

Edit `rig-macros.sh` to adjust window positions for your monitor:

```bash
# Geometry format: 0,x,y,width,height
move_window "N9OH Rig Control Panel" "0,43,456,492,502"
move_window "Volume Control" "0,21,920,382,680"
move_window "flrig IC-7300" "0,50,80,425,322"
```

Get window manager info:
```bash
wmctrl -l  # List all windows with IDs
xdotool search --name "N9OH"  # Find window ID
```

---

## Usage

### Starting the Application

#### Option 1: Using the Startup Script (Recommended)
```bash
bash rig-macros.sh
```

This automatically:
- Kills any previous instances (flrig, pavucontrol, rig-macros.py)
- Starts pavucontrol (PulseAudio volume control)
- Starts flrig (radio control daemon)
- Waits for flrig to be ready
- Launches the Rig Control Panel GUI
- Positions all windows for optimal layout

#### Option 2: Manual Launch
```bash
# Ensure flrig is already running
ps aux | grep flrig

# Launch the panel
python3 rig-macros.py
```

### Basic Operations

#### Band Selection
1. Click any **SSB** button (10m, 12m, 15m, 20m, 40m)
   - Frequency and mode update instantly
   - Correct sideband selected automatically
2. Click any **CW** button
   - Switches to CW mode at selected frequency

#### VFO Management
1. **Copy A → B**: Copies current VFO A to VFO B
2. **A/B Toggle**: Switches between VFO A and B
3. **Split**: Enables/disables split mode (two frequencies active)

#### Voice Keyer - Memory
1. Click **N9OH** button
   - Radio keys down automatically
   - Plays voice memory T1 from radio
   - Returns to receive when done
2. Click **59 FL** button
   - Similar process for voice memory T2
3. **STOP** button
   - Immediately unkeys the radio

#### Voice Keyer - TTS
1. Click any TTS button (N9OH, TU 59, 73)
   - Automatically switches to USB-D mode
   - Radio keys down (RTS raised)
   - Audio plays through radio
   - Automatically returns to original mode
2. **STOP** button
   - Stops playback and unkeys radio
   - Restores original mode

#### QSO Recording
1. **REC** button: Start recording from both radio and microphone
2. **REC** again: Stop recording (stored in `/tmp/`)
3. **Play**: Open recording in VLC media player
4. **Save**: Export to `~/Documents/QSO Recordings/` with custom name
5. **Delete**: Remove recording (confirms before deleting saved files)

#### Debug Panel
1. Click **▶ Show Debug** to expand debug output
2. Watch real-time messages for troubleshooting
3. Click **Clear** to reset debug output
4. Messages include:
   - Startup messages
   - Band/mode changes
   - Voice keyer operations
   - RTS control signals
   - TTS generation details
   - Error messages

---

## Technical Details

### CI-V Voice Memory Command Format

**Command Structure:**
```
FE FE <address> E0 28 00 <slot> FD
```

**Parameters:**
- `FE FE`: CI-V frame header
- `<address>`: Radio address (94 = IC-7300, A4 = IC-7610, etc.)
- `E0`: Transceiver subcommand
- `28`: Voice keyer subcommand
- `00`: Voice keyer play subcommand
- `<slot>`: Memory slot (01-08 for T1-T8)
- `FD`: Frame terminator

**Examples:**
```
FE FE 94 E0 28 00 01 FD  → Play T1
FE FE 94 E0 28 00 02 FD  → Play T2
FE FE 94 E0 28 00 00 FD  → Stop transmission
```

### Serial Port Control

**RTS (Request To Send):**
- **HIGH (1)**: Radio key is down - PTT active
- **LOW (0)**: Radio key is up - PTT inactive
- Used for: Voice memory playback, TTS playback, general PTT control

**DTR (Data Terminal Ready):**
- **Always LOW (0)** in this application
- Reserved for CW keying (not implemented in this version)
- Must be kept LOW to prevent accidental CW keying

**Serial Port Settings:**
```
Device: /dev/ttyUSB0 (or your USB-to-serial device)
Baud Rate: 19200
Data Bits: 8
Stop Bits: 1
Parity: None
Flow Control: None
```

### Mode Switching for TTS

TTS buttons automatically manage radio mode to ensure proper audio routing:

**Mode Switching Logic:**
```
Original Mode → Data Mode Variant → TTS Playback → Original Mode
USB            → USB-D
LSB            → LSB-D
CW             → (not supported, stays CW)
```

**Why Mode Switching?**
- Data modes (USB-D, LSB-D) route audio through USB input
- SSB modes (USB, LSB) route audio through microphone input
- Ensures TTS audio is properly received and transmitted

**Implementation:**
1. Save current mode at button press
2. Switch to `-D` variant before raising RTS
3. Play audio while in data mode
4. Wait for audio completion
5. Restore original mode
6. Lower RTS

### Audio Level Management

**Piper TTS Output:**
- Generated at 16-bit, 8000 Hz (mono) to match radio voice keyer format
- Length scale varies per button (controls speech rate)
- Pitch adjustment applied to 73 button via sox

**PulseAudio Routing:**
- Default playback device (typically PCM2901 or USB audio codec)
- User can select device via pavucontrol
- Volume controlled via system mixer

**Radio USB Input:**
- IC-7300: USB MOD LEVEL (menu setting) controls input gain
- Recommend starting at 50-75% and adjust based on power meter
- Excessive gain causes distortion; insufficient gain requires more RTS hold time

**sox Audio Processing (73 Button):**
```bash
sox in.wav out.wav pitch +150  # Raise pitch by 150 cents
```

### Startup Process

1. **Script Start** (`rig-macros.sh`):
   - Kill previous instances
   - Start pavucontrol
   - Start flrig
   - Wait for flrig XML-RPC to be ready
   - Start Python application

2. **Python Initialization**:
   - Open serial port
   - Connect to flrig XML-RPC
   - Load TTS files (or pre-generate if missing)
   - Initialize GUI
   - Enter main loop

3. **TTS Pre-generation** (startup):
   - Generate N9OH, TU 59 normal speed files
   - Generate 73 slow/pitch file
   - Cache in `/tmp/tts_*.wav`
   - Makes button clicks instant (no generation delay)

---

## Troubleshooting

### Voice Memories Not Transmitting

**Problem:** Click N9OH/59 FL but nothing transmits

**Diagnosis:**
1. Check debug output for RTS status
2. Verify radio receives PTT:
   - Listen for radio's PTT beep
   - Check if power meter moves
3. Test CI-V command manually:
   ```bash
   # Monitor serial port
   cat /dev/ttyUSB0 &
   # Then click button and check output
   ```

**Solutions:**
- Verify radio is on and properly connected
- Check serial port permissions: `ls -la /dev/ttyUSB0`
- Confirm correct radio address (94 for IC-7300)
- Verify voice memories are recorded in radio (T1, T2, etc.)
- Check power meter shows transmission
- Try different USB-to-serial cable

### TTS Audio Quality Issues

**Problem:** TTS audio sounds muffled, low volume, or harsh

**Diagnosis Steps:**
1. Check audio output device:
   ```bash
   pactl list short sinks
   pavucontrol  # Verify correct device selected
   ```
2. Check radio's USB input level:
   - Radio MENU → Connectors → Data Mode → USB MOD Level
   - Adjust 0-100%
3. Monitor power meter while transmitting
4. Test with manual paplay:
   ```bash
   paplay /tmp/tts_n9oh.wav
   ```

**Solutions:**
- Adjust radio's USB MOD LEVEL (try 50%, 75%, 100%)
- Lower PulseAudio output volume in pavucontrol (prevent distortion)
- Ensure USB audio device is correctly selected in pavucontrol
- Check that rig-macros.py is using correct audio device
- Verify sox is installed for pitch processing: `which sox`
- Try different TTS buttons to compare quality

### Mode Doesn't Restore After TTS

**Problem:** Radio stays in USB-D after TTS playback

**Diagnosis:**
1. Check debug output for mode restoration messages
2. Manually check current mode on radio or flrig

**Solutions:**
- Ensure flrig is running and responding: `ps aux | grep flrig`
- Check XML-RPC connection in debug output
- Try clicking a band button to manually restore mode
- Restart application if mode gets stuck
- Monitor flrig logs: `tail /tmp/flrig.log`

### flrig Connection Errors

**Problem:** "Could not connect to flrig" or XML-RPC errors

**Diagnosis:**
```bash
# Check if flrig is running
ps aux | grep flrig

# Check if XML-RPC port is listening
ss -ltn | grep 12345
netstat -ln | grep 12345

# Test XML-RPC connection
python3 -c "import xmlrpc.client; s = xmlrpc.client.ServerProxy('http://localhost:12345'); print(s.rig.get_frequency())"
```

**Solutions:**
- Ensure flrig is running: `flrig &`
- Check XML-RPC port setting: `grep xmlport ~/.flrig/IC-7300.prefs`
- Verify port matches in rig-macros.py (line ~49)
- Check firewall isn't blocking localhost:12345
- Restart flrig: `killall flrig; sleep 1; flrig &`
- Ensure radio is powered on and connected

### QSO Recording Issues

**Problem:** Recording fails or has missing audio

**Diagnosis:**
```bash
# List available audio sources
pactl list short sources

# Check ffmpeg command works
ffmpeg -f pulse -i default -f pulse -i 1 -t 5 -q:a 9 /tmp/test.wav
```

**Solutions:**
- Verify audio devices in recording code match your system
- Update device names in `record_qso()` function
- Ensure PulseAudio is running: `pulseaudio --check -v`
- Check microphone is selected in pavucontrol Recording tab
- Test individual devices with ffmpeg before debugging

### Serial Port Permission Denied

**Problem:** `PermissionError: [Errno 13] Permission denied: '/dev/ttyUSB0'`

**Solution:**
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER

# Apply changes immediately
newgrp dialout

# Or log out and back in
logout
```

**Verify:**
```bash
groups  # Should include 'dialout'
ls -l /dev/ttyUSB0  # Should have 'crw-rw----'
```

### UI Doesn't Display or Freezes

**Problem:** Window doesn't appear or becomes unresponsive

**Solutions:**
- Check debug output for errors: `cat /tmp/rig-macros-error.log`
- Ensure tkinter is installed: `sudo apt-get install python3-tk`
- Try with DISPLAY set: `DISPLAY=:0 python3 rig-macros.py`
- Kill and restart: `pkill -f rig-macros.py`
- Check system resources: `free -h; top -b -n 1 | head -10`

### TTS Playback Blocks UI

**Problem:** Clicking TTS button freezes interface until done

**Note:** This is expected behavior in current implementation. TTS playback runs in background thread but UI may appear unresponsive during long transmissions. This is acceptable for hobby use where TTS messages are short (3-10 seconds).

**Workaround:** You can still click STOP button to interrupt playback.

---

## Development

### Adding New Voice Memory Buttons

To add a T3 or T4 button:

1. **Find the Voice Memory section** (search for "Voice Keyer - Memory")

2. **Create the button:**
```python
btn_t3 = tk.Button(voice_frame, text="T3", width=6, command=play_voice_memory_t3)
btn_t3.grid(row=0, column=2)
```

3. **Implement the handler function:**
```python
def play_voice_memory_t3():
    play_voice_memory("T3", "FEFE94E3280003FD")
```

4. **Update CI-V command:**
   - T1 = 01, T2 = 02, T3 = 03, etc.
   - Format: `FEFE94E028 00[nn]FD` where [nn] is slot

### Adding New TTS Phrases

To add a new TTS button:

1. **Add to pre-generation** (search for `pre_generate_tts()`):
```python
phrases = {
    'n9oh': (',, November Nine Oscar HOTEL', 0.72, False),
    'tu59': (',, Thanks, also FIVE NINE', 0.72, False),
    '73': (',, Seventy-Three', 0.55, True),  # True = apply pitch
    'new': (',, Your text here', 0.72, False),  # Add this
}
```

2. **Create button:**
```python
btn_new = tk.Button(tts_frame, text="NEW", width=6, command=play_tts_new)
btn_new.grid(row=1, column=3)
```

3. **Implement handler:**
```python
def play_tts_new():
    play_tts_phrase('new', '/tmp/tts_new.wav')
```

4. **Test:**
   - Restart application to regenerate TTS files
   - Click button and verify audio

### Modifying CI-V Address for Different Radios

If using an IC-7610 or other Icom radio:

1. **Find correct address:**
   - IC-7300: 94
   - IC-7610: A4
   - IC-705: A0
   - Consult Icom CI-V documentation

2. **Update in code:**
```python
# Search for "FEFE94E0" (94 is address)
# Replace all instances with your address
# E.g., for IC-7610: "FEFEA4E0"
```

3. **Update comment:**
```python
# Address 94 = IC-7300; adjust for other Icom models
```

### Performance Considerations

- **TTS Pre-generation**: 1-2 second startup delay is normal
- **Voice Memory Playback**: Synchronous - blocks UI briefly while checking power meter
- **TTS Playback**: Asynchronous - runs in background thread
- **PulseAudio Mixing**: Multiple audio sources handled by PulseAudio daemon
- **Serial Port**: Keep port open throughout session to avoid reconnect delays

### Code Style

- Use snake_case for functions and variables
- Use CamelCase for classes
- Keep functions focused on single responsibility
- Add debug logging for all user actions
- Include timestamps in debug output

---

## File Structure

```
RigControlPanel/
├── rig-macros.py          # Main Python GUI application
│                          # ~1000 lines
│                          # VFO control, band selection, voice keyer,
│                          # QSO recording, TTS generation and playback
│
├── rig-macros.sh          # Startup script
│                          # Kills previous instances
│                          # Starts flrig and pavucontrol
│                          # Positions windows
│                          # Launches main application
│
├── rig-macros.conf        # Configuration file (USER-EDITABLE)
│                          # Customize voice keyer labels and TTS buttons
│                          # Change text, speech rate, and pitch
│                          # No restart required for config changes
│
├── README.md              # This file
│
├── LICENSE                # MIT License
│
└── /tmp/                  # Generated files (cleaned on restart)
    ├── rig-macros-error.log     # Application logs
    ├── tts_n9oh.wav             # Pre-generated TTS audio
    ├── tts_tu59.wav
    ├── tts_73.wav
    ├── flrig.log                # flrig daemon logs
    └── pavucontrol.log          # PulseAudio control logs
```

### Output Locations

- **Configuration**: `rig-macros.conf`
  - User-editable settings for voice keyer and TTS
  - Changes take effect on application restart
  
- **Application Log**: `/tmp/rig-macros-error.log`
  - Check for errors and debug messages
  - Truncated on each restart
  
- **QSO Recordings**: `~/Documents/QSO Recordings/`
  - Final saved recordings
  - Named by user with custom prefix
  
- **TTS Cache**: `/tmp/tts_*.wav`
  - Pre-generated at startup
  - Regenerated if deleted
  
- **flrig Log**: `/tmp/flrig.log`
  - Radio control daemon messages
  - Useful for debugging XML-RPC issues
  
- **PulseAudio Log**: `/tmp/pavucontrol.log`
  - Audio control interface messages

---

## License

MIT License

Copyright (c) 2026 Steve Woodruff, N9OH

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## Support & Feedback

For issues, feature requests, or feedback, contact **Steve Woodruff, N9OH**.

### Useful Resources

- **Icom IC-7300 CI-V Command Reference**: Consult official Icom documentation
- **flrig Documentation**: http://www.w5xj.net/flrig/
- **Piper TTS GitHub**: https://github.com/rhasspy/piper
- **PulseAudio Documentation**: https://www.freedesktop.org/wiki/Software/PulseAudio/
- **IC-7300 Voice Keyer Setup**: Refer to IC-7300 User Manual, Section 2-36

### Related Projects

- **WriteLog**: Professional contest logging with radio integration
- **flrig**: XML-RPC interface used in this project

---

**Last Updated**: January 4, 2026  
**Version**: 1.0
