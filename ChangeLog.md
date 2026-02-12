# Change Log - Multi-Channel Amplifier Control Daemon

## Version 1.3.1 (2026-02-08)

### Bug Fixes & Cleanup
1. **Removed SOUNDCARD_MUTE_DELAY:** Unnecessary delay removed from suspend sequence
   - Sound cards are already in MUTED state when `suspend()` is called
   - Suspend now happens immediately after timeout expires
   - Simplified suspend logic - no waiting period before SUSPEND GPIO
   - Configuration parameter `soundcard_mute_delay` is now ignored (deprecated)

### Implementation Details
- Removed `SOUNDCARD_MUTE_DELAY` constant and all references
- `suspend()` no longer waits 5 seconds before suspending
- `suspend()` adds defensive check: warns if not in MUTED state
- Config loading no longer reads `soundcard_mute_delay` parameter
- Simplified log messages in `setupSoundcards()`

### Documentation Improvements
- Added explicit "Daemon Shutdown" section to Core Behavior
- Removed all references to deprecated `muteImmediately()` method
- Extracted changelog to separate `ChangeLog.md` file
- Updated all method references to use new naming (v1.3.0)

### Backward Compatibility
- **Fully compatible** with existing configuration files
- Config files can still include `soundcard_mute_delay` (will be ignored)
- No external behavior changes
- Status JSON format unchanged
- Socket protocol unchanged

---

## Version 1.3.0 (2026-02-08)

### Major Refactoring - Cleaner State Machine
This is a **MINOR version bump** due to significant internal refactoring, though the external API remains compatible.

### 1. New State Machine with Three States
**DeviceState Enum:**
- `SUSPENDED = 0`: Fully off (SUSPEND=HIGH, MUTE=HIGH, LED=LOW)
- `MUTED = 1`: Active but muted (SUSPEND=LOW, MUTE=HIGH, LED=HIGH)
- `ON = 2`: Active and unmuted (SUSPEND=LOW, MUTE=LOW, LED=HIGH)

**PowerState Enum** (separate for power supply):
- `OFF = 0`
- `ON = 1`

**Previous State Model (v1.2.2):**
- Only two states: OFF and ON
- MUTED state was implicit (not tracked)

### 2. Cleaner Method Names
**Before (v1.2.2) → After (v1.3.0):**
- `activate()` → `resume()` (from suspended) + `unmute()` (from muted)
- `deactivate()` → `suspend()` (to suspended)
- `muteImmediately()` → `mute()` (to muted state)
- `scheduleDeactivation()` → `scheduleSuspend()`

**New Helper Methods:**
- `isActive()`: Returns True if not suspended
- `isMuted()`: Returns True if muted
- `isSuspended()`: Returns True if suspended

### 3. Fixed Bug: Unmuting When Player Restarts
**Problem in v1.2.2:**
When a player restarted while soundcard was MUTED (waiting for suspend), the soundcard was not unmuted, causing no audio.

**Solution in v1.3.0:**
`activatePlayer()` now checks current state:
- If `SUSPENDED`: calls `resume()` (full resume sequence)
- If `MUTED`: calls `unmute()` (just clear mute)  ← **This fixes the bug!**
- If `ON`: no action needed

### 4. State Transitions
```
SUSPENDED  ──resume()──→  ON
    ↑                      ↓
    │                   mute()
    │                      ↓
    └────suspend()────  MUTED
                           ↑
                      unmute()
                           ↓
                          ON
```

### Implementation Details
- All GPIO operations now update the `state` field correctly
- `getStatus()` uses actual state enum instead of inferring from active players
- Separate `PowerState` enum for power supply (simpler ON/OFF model)
- Consistent naming: `resume()`/`suspend()` for major transitions, `mute()`/`unmute()` for quick toggles
- All internal references to `DeviceState.OFF` changed to `DeviceState.SUSPENDED`
- `suspend()` verifies state is MUTED before suspending (defensive check)
- `unmute()` checks if suspended and warns (prevents invalid state transitions)

### Backward Compatibility
- **Fully compatible** with existing configuration files
- **Fully compatible** with Squeezelite callback protocol
- Status JSON format unchanged (same state strings: "on", "muted", "suspended")
- Socket protocol unchanged
- Externally visible behavior identical (except bug fix)
- No changes required to monitoring tools

### Benefits
1. **Bug Fix:** Unmute works correctly when player restarts from MUTED state
2. **Clearer Code:** Method names clearly indicate what they do
3. **Better State Tracking:** State enum always reflects actual GPIO state
4. **Easier Debugging:** State is explicit in logs and status
5. **More Maintainable:** State machine logic is clearer and easier to extend

---

## Version 1.2.2 (2026-02-08)

### Improvements
1. **Proper Shutdown Sequence:** Hardware is now shut down before error LED activation
   - **Before (1.2.1):** Error LED turned on first, then cleanup
   - **After (1.2.2):** Soundcards muted/suspended → Power supply off → Error LED on
   - **Reason:** Ensures clean hardware shutdown even during daemon termination
   - Prevents amplifiers staying powered if daemon crashes during shutdown

2. **Human-Readable Player Names in Status:** Status JSON now uses player description in name field
   - **Before (1.2.1):** `"name": "wohnzimmer"` (technical ID)
   - **After (1.2.2):** `"name": "Wohnzimmer"` (description from config with umlauts)
   - **Applies to:** Players section only, soundcard names remain technical IDs
   - **Reason:** Better readability in logs and monitoring dashboards (Grafana, etc.)
   - Umlauts and special characters now properly displayed for players

### Implementation Details
- `SoundcardConfig` dataclass: Changed `players` from `Set[str]` to `Dict[str, str]` (name → description mapping)
- `setupSoundcards()`: Loads player descriptions from YAML config (falls back to name if not present)
- `getStatus()`: Uses player description in `name` field of players section
- `stop()`: Reordered shutdown sequence:
  1. Mute all active soundcards (MUTE HIGH)
  2. Suspend all soundcards (SUSPEND HIGH, LED LOW)
  3. Deactivate power supply (GPIO LOW)
  4. Activate error LED (GPIO HIGH)
  5. Write final status and cleanup files

### Configuration File
- Player `description` field now used in status output
- Example:
  ```yaml
  soundcards:
    - id: 1
      name: KAB9_1
      players:
        - name: wohnzimmer          # Technical ID (used as key)
          description: "Wohnzimmer" # Human-readable (used in status JSON name field)
        - name: kueche
          description: "Küche"      # With umlauts
  ```
- If player `description` not provided, `name` is used as fallback (backward compatible)

### Backward Compatibility
- **Fully backward compatible** with configuration files from v1.2.1
- Existing configs without player `description` field continue to work (uses `name` as fallback)
- Status JSON format unchanged (same structure, different values in players.name)
- Socket protocol unchanged
- Monitoring tools may need adjustment if they rely on exact player name matching in displays

---

## Version 1.2.1 (2026-02-08)

### Safety Enhancement
1. **Inverted Power Supply Logic:** Power supply GPIO control inverted for safety
   - **Before (1.2.0):** GPIO HIGH = OFF, GPIO LOW = ON
   - **After (1.2.1):** GPIO LOW = OFF, GPIO HIGH = ON
   - **Reason:** If Raspberry Pi crashes, shuts down, or loses power, GPIO pins default to LOW, automatically turning OFF the power supply
   - This prevents the amplifier power supply from staying on indefinitely in case of system failure

### Implementation Details
- `PowerSupplyController.setupGpio()`: Initializes GPIO to LOW (OFF)
- `PowerSupplyController.activate()`: Sets GPIO to HIGH (ON)
- `PowerSupplyController.deactivate()`: Sets GPIO to LOW (OFF)
- `handleError()`: Emergency shutdown sets GPIO to LOW (OFF)
- Updated all log messages to reflect inverted logic
- Class docstring updated: "Controls the main power supply via GPIO (inverted logic for safety)"

### Hardware Impact
- **BREAKING CHANGE:** External circuit must be inverted to match new logic
- Requires hardware modification: relay or transistor circuit must respond to HIGH=ON instead of LOW=ON
- Significantly improves system safety in case of Raspberry Pi failure

### Backward Compatibility
- **NOT backward compatible** with hardware designed for v1.2.0
- Configuration file format unchanged
- Socket protocol unchanged
- Status file format unchanged
- Monitoring tools unaffected

---

## Version 1.2.0 (2026-02-08)

### Major Changes
1. **Immediate Mute on Stop:** When a player stops, MUTE is now set HIGH immediately (in `muteImmediately()`), not after SOUNDCARD_TIMEOUT
2. **Players Section in Status:** Added dedicated `players` section in JSON status with individual player status
3. **Enhanced Error Handling:** `handleError()` method properly activates error LED and performs emergency shutdown
4. **Improved Timer Cancellation:** Power supply `activate()` always cancels pending timers first
5. **Configuration Loading:** GPIO pins now configurable via YAML (gpio_power_supply, gpio_error_led)

### Implementation Details
- `deactivatePlayer()` now calls `muteImmediately()` when last player stops
- `deactivate()` verifies MUTE is already HIGH before mute delay
- `getStatus()` builds players section from all configured soundcard players
- Error LED state tracked with `errorLedActive` boolean flag
- Enhanced logging for mute operations and timer cancellations

### Backward Compatibility
- Configuration file format unchanged
- Socket protocol unchanged
- Status file adds new `players` section (additive change)
- All existing monitoring tools continue to work

---

## Version 1.1.0 (Initial documented version)

Initial release with basic functionality:
- Multi-soundcard control via GPIO
- Power supply management with timeouts
- Squeezelite callback integration
- Unix socket communication
- JSON status file export
- Temperature sensor support (DS18B20)
