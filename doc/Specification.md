# Multi-Channel Amplifier Control Daemon - Technical Specification

## Version: 1.0.0

## Overview
A Python daemon for Raspberry Pi 5 that controls a multi-channel amplifier system with three 8-channel USB sound cards and a main power supply. The daemon monitors Squeezelite instances and manages power states based on playback activity.

## System Architecture

### Hardware Components
- **Raspberry Pi 5** running the daemon
- **Main Power Supply** controlled via GPIO 13
  - GPIO HIGH (1) = Power OFF
  - GPIO LOW (0) = Power ON
- **Three 8-channel USB Sound Cards** (KAB9_1, KAB9_2, KAB9_3)
  - Each controlled via 3 GPIO pins: SUSPEND, MUTE, LED
- **Error LED** on GPIO 26

### Sound Card Configuration

#### KAB9_1
- ALSA Card: 4
- USB Device: 1-2
- GPIO SUSPEND: 12
- GPIO MUTE: 16
- GPIO LED: 17
- Players: wohnzimmer, tvzimmer, kueche, gaestezimmer

#### KAB9_2
- ALSA Card: 3
- USB Device: 3-1
- GPIO SUSPEND: 6
- GPIO MUTE: 25
- GPIO LED: 27
- Players: schlafzimmer, terrasse, gwc, elternbad, balkon, sauna

#### KAB9_3
- ALSA Card: 0
- USB Device: 1-1
- GPIO SUSPEND: 23
- GPIO MUTE: 24
- GPIO LED: 22
- Players: kian, sarina, hobbyraum

## Functional Requirements

### Core Behavior

1. **Initial State**
   - All sound cards: SUSPENDED (GPIO SUSPEND=HIGH, MUTE=HIGH, LED=LOW)
   - Power supply: OFF (GPIO=HIGH)
   - Error LED: OFF (GPIO=LOW)

2. **Player Activation (Squeezelite starts playback)**
   - Activate main power supply immediately
   - Activate associated sound card with sequence:
     1. Set SUSPEND GPIO to LOW
     2. Wait 1 second (configurable constant GPIO_DELAY)
     3. Set MUTE GPIO to LOW
     4. Set LED GPIO to HIGH
   - Cancel any pending deactivation timers for power supply

3. **Player Deactivation (Squeezelite stops playback)**
   - Remove player from active list
   - If no players on that sound card are active:
     - Schedule sound card deactivation after 15 minutes (configurable SOUNDCARD_TIMEOUT)
   - Check if power supply can be deactivated

4. **Sound Card Deactivation (after timeout)**
   - Sequence:
     1. Set MUTE GPIO to HIGH
     2. Wait 1 second (GPIO_DELAY)
     3. Set SUSPEND GPIO to HIGH
     4. Set LED GPIO to LOW
   - After deactivation, trigger power supply deactivation check

5. **Power Supply Deactivation**
   - Only if ALL sound cards are inactive
   - Schedule deactivation after 30 minutes (configurable POWER_SUPPLY_TIMEOUT)
   - Set GPIO to HIGH (OFF)

### Timeout Configuration
- **Normal Mode:**
  - SOUNDCARD_TIMEOUT: 15 minutes (900 seconds)
  - POWER_SUPPLY_TIMEOUT: 30 minutes (1800 seconds)
- **Debug Mode (--debug flag):**
  - SOUNDCARD_TIMEOUT: 1 minute (60 seconds)
  - POWER_SUPPLY_TIMEOUT: 2 minutes (120 seconds)

### Communication Protocol

#### Unix Socket Interface
- **Socket Path:** `/var/run/amp_control.sock`
- **Permissions:** 0666 (readable/writable by all)
- **Protocol:** Text-based, line-delimited
- **Message Format:** `playername:state\n`
  - playername: Name of the Squeezelite player
  - state: `1` for play, `0` for stop
- **Response:** `OK\n`

#### Squeezelite Integration
- Each Squeezelite instance uses `-S` parameter to call callback script
- Callback script sends events via Unix socket
- Example: `squeezelite -n wohnzimmer -S "/usr/local/bin/amp_callback.py wohnzimmer" -o hw:4,0`

## Error Handling

### Critical Error Response
When a critical error occurs, execute in this order:
1. Log critical error message
2. Turn ON error LED (GPIO 26 = HIGH)
3. Deactivate all sound cards (force immediate shutdown)
4. Deactivate power supply (GPIO 13 = HIGH)

### Normal Shutdown
When daemon stops normally (SIGTERM, SIGINT):
1. Turn ON error LED (indicates daemon not running)
2. Close Unix socket
3. Remove PID file
4. Remove status file
5. Exit

### Daemon Instance Protection
- Use PID file at `/var/run/amp_control.pid`
- Check if daemon already running on startup
- Verify process exists with `os.kill(pid, 0)`
- Remove stale PID files if process doesn't exist
- Exit with error if daemon already running

## Threading and Concurrency

### Thread Safety
- **SoundcardController:** Uses threading.Lock for state modifications
- **PowerSupplyController:** Uses threading.Lock for state modifications
- **isActive() methods:** Do NOT use locks to prevent deadlock
  - Reading enum state is atomic and thread-safe
- **Timer threads:** All timer threads are daemon threads

### Socket Server Threading
- Main socket server thread accepts connections
- Each client connection handled in separate daemon thread
- Non-blocking socket operations with proper exception handling

## File Structure

### Two Separate Python Files Required

The system consists of two executable Python scripts that work together:

#### 1. MultiChannelAmpDaemon.py (Main Daemon)
**Purpose:** Background daemon that manages power supply and sound card states

**Key Components:**
- **Version Constant:** `VERSION = "1.0.0"` at top of file
- **Configuration Constants:** SOUNDCARD_TIMEOUT, POWER_SUPPLY_TIMEOUT, GPIO pins, file paths
- **Enums:** DeviceState (OFF, ON)
- **Data Classes:** SoundcardConfig (id, name, gpioSuspend, gpioMute, gpioLed, alsaCard, usbDevice, players)
- **Classes:**
  - `SoundcardController`: Manages individual sound card via GPIO
  - `PowerSupplyController`: Manages main power supply via GPIO
  - `AmpControlDaemon`: Main daemon orchestrating the system
- **Utility Functions:**
  - `checkAlreadyRunning()`: Verifies no other daemon instance is running
  - `writePidFile()`: Creates PID file with current process ID
  - `main()`: Entry point with argument parsing
- **Command-line Interface:**
  - `--debug`: Enable debug mode (1min/2min timeouts, DEBUG logging)
  - `--version`: Display version number

**Execution:** Runs as background daemon, listens on Unix socket for events

#### 2. amp_callback.py (Callback Script)
**Purpose:** Lightweight script invoked by Squeezelite to notify daemon of playback events

**Key Components:**
- **Socket Communication:** Connects to `/var/run/amp_control.sock`
- **Message Protocol:** Sends `playername:state\n` format
- **Timeout Handling:** 5-second connection timeout
- **Error Handling:** Proper error messages for connection failures
- **Exit Codes:** 0 on success, 1 on failure

**Execution:** Called by Squeezelite via `-S` parameter, sends message and exits immediately

**Integration Example:**
```bash
squeezelite -n wohnzimmer \
  -S "/usr/local/bin/amp_callback.py wohnzimmer" \
  -o hw:4,0 &
```

## Logging

### Log Configuration
- **Default Level:** INFO
- **Debug Mode Level:** DEBUG
- **Log File:** `/var/log/amp_control.log`
- **Console Output:** Yes (StreamHandler)
- **Format:** `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

### Startup Banner
```
================================================================================
=                                                                              =
=  AMP CONTROL DAEMON STARTING                                                =
=  Version: 1.0.0                                                             =
=                                                                              =
================================================================================
```

In debug mode, also show timeouts:
```
================================================================================
=                                                                              =
=  AMP CONTROL DAEMON STARTING (DEBUG MODE)                                   =
=  Version: 1.0.0                                                             =
=  Soundcard timeout: 60s, Power supply timeout: 120s                         =
=                                                                              =
================================================================================
```

### Key Log Messages
- INFO: Player events, state changes, timer scheduling
- DEBUG: GPIO state changes (SUSPEND, MUTE, LED values)
- WARNING: Unknown players
- ERROR: GPIO failures, socket errors
- CRITICAL: Fatal errors triggering emergency shutdown

## Code Style Requirements

### Naming Conventions
- **Functions and Methods:** camelCase (e.g., `activatePlayer()`, `setupGpio()`)
- **Variables:** camelCase (e.g., `playerName`, `soundcardId`)
- **Constants:** UPPER_SNAKE_CASE (e.g., `SOUNDCARD_TIMEOUT`, `GPIO_DELAY`)
- **Classes:** PascalCase (e.g., `SoundcardController`, `AmpControlDaemon`)

### Language
- All code, comments, and docstrings in English
- Clear, descriptive variable names
- Comprehensive docstrings for all classes and methods

## Version Management

### Version Format
- Semantic versioning: MAJOR.MINOR.PATCH
- Current version: 1.0.0
- Version constant at top of file
- Version in docstring header
- Version displayed in startup banner
- Version accessible via `--version` command-line flag

### Version Update Rules
- PATCH: Bug fixes, small changes (increment on each code change)
- MINOR: New features, no breaking changes
- MAJOR: Breaking changes, major restructuring

## File Paths and Permissions

### Required Files
- `/var/run/amp_control.pid` - PID file (created by daemon)
- `/var/run/amp_control.status` - Status file (created by daemon)
- `/var/run/amp_control.sock` - Unix socket (created by daemon, mode 0666)
- `/var/log/amp_control.log` - Log file (must be writable)

### Installation Paths
- `/usr/local/bin/MultiChannelAmpDaemon.py` - Main daemon (executable)
- `/usr/local/bin/amp_callback.py` - Callback script (executable)

## Dependencies

### Python Modules
- Standard library only:
  - sys, time, threading, logging, signal, socket, os, argparse, pathlib, typing, dataclasses, enum
- Platform-specific:
  - RPi.GPIO (Raspberry Pi GPIO control)

### System Requirements
- Raspberry Pi 5
- Python 3.7+ (for dataclasses)
- Root/sudo access for GPIO operations
- Write access to /var/run and /var/log

## Critical Implementation Details

### Deadlock Prevention
The `isActive()` methods in SoundcardController and PowerSupplyController must NOT use locks because:
- They are called from within locked sections of other methods
- Reading an enum value is atomic in Python
- Using locks here causes deadlock when `deactivate()` (which holds a lock) calls `daemon.checkPowerSupplyDeactivation()` which calls `isActive()`

### Power Supply Timer Cancellation
The power supply activation must ALWAYS be called when a player starts, not only when power supply is OFF:
- `handlePlayerEvent()` must call `powerSupply.activate()` unconditionally
- `activate()` must cancel pending timer BEFORE checking if already active
- This ensures pending shutdown timers are cancelled when new playback starts

### Soundcard Controller Reference
SoundcardController needs a reference to the parent daemon:
- Constructor takes `daemon` parameter
- After deactivation, calls `self.daemon.checkPowerSupplyDeactivation()`
- This ensures power supply timeout starts after sound card deactivates

## Expected Behavior Examples

### Example 1: Single Player Session
1. Daemon starts, all OFF
2. Player "wohnzimmer" starts playback → Power ON, KAB9_1 activates
3. Player "wohnzimmer" stops → KAB9_1 schedules deactivation (15 min)
4. After 15 min → KAB9_1 deactivates, power supply schedules deactivation (30 min)
5. After 30 min → Power supply turns OFF

### Example 2: Multiple Sound Cards
1. Player "wohnzimmer" (KAB9_1) starts → Power ON, KAB9_1 ON
2. Player "schlafzimmer" (KAB9_2) starts → KAB9_2 ON (power already on)
3. Player "wohnzimmer" stops → KAB9_1 schedules deactivation
4. After 15 min → KAB9_1 OFF, but power stays ON (KAB9_2 still active)
5. Player "schlafzimmer" stops → KAB9_2 schedules deactivation
6. After 15 min → KAB9_2 OFF, power schedules deactivation
7. After 30 min → Power OFF

### Example 3: Timer Cancellation
1. Player "kian" starts → Power ON, KAB9_3 ON
2. Player "kian" stops → KAB9_3 schedules deactivation (15 min)
3. After 15 min → KAB9_3 OFF, power schedules deactivation (30 min)
4. After 20 min → Player "sarina" starts (same card KAB9_3)
5. Power activation cancels power timer, KAB9_3 activates
6. System continues running normally

## Installation and Deployment

### File Installation
```bash
# Install daemon
sudo cp MultiChannelAmpDaemon.py /usr/local/bin/
sudo chmod +x /usr/local/bin/MultiChannelAmpDaemon.py

# Install callback script
sudo cp amp_callback.py /usr/local/bin/
sudo chmod +x /usr/local/bin/amp_callback.py
```

### Starting the Daemon
```bash
# Normal mode
sudo /usr/local/bin/MultiChannelAmpDaemon.py &

# Debug mode (shorter timeouts, verbose logging)
sudo /usr/local/bin/MultiChannelAmpDaemon.py --debug &

# Check version
/usr/local/bin/MultiChannelAmpDaemon.py --version
```

### Squeezelite Configuration
Each Squeezelite instance must be started with the `-S` callback parameter:

```bash
# Example for room "wohnzimmer" on soundcard KAB9_1 (hw:4,0)
squeezelite -n wohnzimmer \
  -S "/usr/local/bin/amp_callback.py wohnzimmer" \
  -o hw:4,0 &

# Example for room "schlafzimmer" on soundcard KAB9_2 (hw:3,0)
squeezelite -n schlafzimmer \
  -S "/usr/local/bin/amp_callback.py schlafzimmer" \
  -o hw:3,0 &

# Example for room "kian" on soundcard KAB9_3 (hw:0,0)
squeezelite -n kian \
  -S "/usr/local/bin/amp_callback.py kian" \
  -o hw:0,0 &
```

### Systemd Service (Optional)
For automatic startup on boot, create `/etc/systemd/system/amp-control.service`:

```ini
[Unit]
Description=Multi-Channel Amplifier Control Daemon
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/MultiChannelAmpDaemon.py
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Then enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable amp-control.service
sudo systemctl start amp-control.service
sudo systemctl status amp-control.service
```

### Debug Mode
Use `--debug` flag for faster testing:
- 1-minute sound card timeout instead of 15 minutes
- 2-minute power supply timeout instead of 30 minutes
- DEBUG level logging for detailed GPIO state information

### Manual Testing Commands
```bash
# Start daemon in debug mode
sudo /usr/local/bin/MultiChannelAmpDaemon.py --debug

# Simulate player events
echo "wohnzimmer:1" | nc -U /var/run/amp_control.sock  # Start playback
echo "wohnzimmer:0" | nc -U /var/run/amp_control.sock  # Stop playback

# Check daemon status
cat /var/run/amp_control.pid
cat /var/run/amp_control.status
tail -f /var/log/amp_control.log
```

## Troubleshooting

### Common Issues

#### Daemon won't start - "already running"
```bash
# Check if daemon is actually running
ps aux | grep MultiChannelAmpDaemon
# If not running, remove stale PID file
sudo rm /var/run/amp_control.pid
```

#### Socket connection failed
```bash
# Check if socket exists
ls -l /var/run/amp_control.sock
# Check socket permissions (should be 0666)
# Restart daemon if socket missing
```

#### GPIO permissions denied
```bash
# Daemon must run as root for GPIO access
sudo /usr/local/bin/MultiChannelAmpDaemon.py
```

#### Player events not working
```bash
# Test socket directly
echo "wohnzimmer:1" | nc -U /var/run/amp_control.sock
# Check logs for errors
tail -f /var/log/amp_control.log
# Verify player name matches configuration
```

#### Soundcard not activating
```bash
# Check GPIO states in debug mode logs
sudo /usr/local/bin/MultiChannelAmpDaemon.py --debug
# Verify GPIO pin numbers match hardware
# Check for GPIO initialization errors in logs
```

### Log Analysis

#### Normal startup sequence
```
================================================================================
=  AMP CONTROL DAEMON STARTING                                                =
=  Version: 1.0.0                                                             =
================================================================================
GPIO initialized for KAB9_1: SUSPEND=12, MUTE=16, LED=17
GPIO initialized for KAB9_2: SUSPEND=6, MUTE=25, LED=27
GPIO initialized for KAB9_3: SUSPEND=23, MUTE=24, LED=22
Initialized with 3 sound cards
GPIO pin 13 initialized for power supply (HIGH=OFF, LOW=ON)
Error LED initialized on GPIO 26
Socket server listening on /var/run/amp_control.sock
```

#### Normal playback sequence
```
Player wohnzimmer starting playback
Activating main power supply
Main power supply activated (GPIO=LOW)
Activating sound card KAB9_1
KAB9_1: SUSPEND set to LOW
KAB9_1: MUTE set to LOW
KAB9_1: LED set to HIGH
Sound card KAB9_1 activated
```

#### Error indicators
```
Critical error: <error message>
Error LED activated on GPIO 26
Emergency shutdown: Deactivating all sound cards
Emergency shutdown: Power supply deactivated
```

- Socket permissions (0666) allow any user to send events
- Daemon must run as root for GPIO access
- PID file prevents multiple daemon instances
- No authentication on socket (assumes trusted local system)
- Input validation on socket messages (format: "name:0/1")

## Future Extension Points

The specification includes placeholder values for ALSA and USB device paths (alsaCard, usbDevice in SoundcardConfig) for potential future USB/ALSA suspend functionality, though this is not currently implemented in the GPIO-based control system.
