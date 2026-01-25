#!/usr/bin/env python3
"""
Callback script for Squeezelite
Sends player events to the amp control daemon via Unix socket

Usage from Squeezelite:
  squeezelite -n wohnzimmer -S "/usr/local/bin/amp_callback.py wohnzimmer"
"""

import socket
import sys
import os
import logging

SOCKET_PATH = "/var/run/MultiChannelAmpDaemon.sock"
TIMEOUT = 5  # seconds

# Logging setup
logging.basicConfig(
    level=logging.DEBUG,  # Default level, will be changed to DEBUG if --debug is used
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/MultiChannelAmpCallback.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('squeezelite-launcher')


def sendEvent(playerName: str, state: int) -> bool:
    """
    Sends a player event to the daemon

    Args:
        playerName: Name of the player
        state: 1 for play, 0 for stop, 2 for init

    Returns:
        True if successful, False otherwise
    """
    try:
        # Create socket
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)

        # Connect to daemon
        sock.connect(SOCKET_PATH)

        # Send message in format "playername:state"
        message = f"{playerName}:{state}\n"
        sock.send(message.encode('utf-8'))

        # Wait for acknowledgment
        response = sock.recv(1024).decode('utf-8').strip()

        sock.close()

        if response == "OK":
            return True
        else:
            logger.error(f"Unexpected response: {response}")
            return False

    except socket.timeout:
        logger.error(f"Timeout connecting to daemon at {SOCKET_PATH}")
        return False
    except FileNotFoundError:
        logger.error(f"Daemon socket not found at {SOCKET_PATH}")
        logger.error("Is the amp_control daemon running?")
        return False
    except ConnectionRefusedError:
        logger.error(f"Connection refused to {SOCKET_PATH}")
        logger.error("Is the amp_control daemon running?")
        return False
    except Exception as e:
        logger.error(f"Error sending event: {e}")
        return False


def main():
    """Main entry point"""
    # Check arguments
    if len(sys.argv) != 3:
        print("Usage: MultiChannelAmpCallback.py <player_name> <state>", file=sys.stderr)
        print("  player_name: Name of the Squeezelite player", file=sys.stderr)
        print("  state: 1 for play, 0 for stop, 2 for initilization (ignored)", file=sys.stderr)
        sys.exit(1)

    playerName = sys.argv[1]

    # Validate state
    try:
        state = int(sys.argv[2])
        if state not in [0, 1, 2]:
            raise ValueError("State must be 0, 1 or 2")
    except ValueError as e:
        logger.error(f"Invalid state argument: {sys.argv[2]} - {e}")
        sys.exit(1)

    logger.debug(f"Received command: {state}")

    # Send event to daemon
    if state in [0, 1]:
        success = sendEvent(playerName, state)

        if not success:
            sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
