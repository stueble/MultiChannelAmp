# MultiChannelAmp
Information and corresponding tools of my DIY 24-channel multi-room audio amp based on three KAB9 sound cards. The sound cards are connected to and controlled by a raspberry pi running several instances of squeezelite players driving some mono but mostly stereo channels.

This repository includes the following components:
- *src/MultiChannelAmpDaemon.py*: A daemon to control the sound cards of type KAB9 and the power supply of my 24 channel multi channel amp based on the states of the sqeezelite players. The suspends sound cards not in use and deactivated the main power supply if no sound card is active
- *example/MultiChannelAmpDaemon.yaml*: Example configuration file for the daemon
- *src/MultiChannelAmpCallback.py*: A small command line program to send squeezelite player status information (play/stop) to the daemon
- *src/fancontrol.py*: Another daemon to control the case fan based on temperature sensors connected to the KAB9 sound cards as well as the CPU and SOC temperatures
- *src/squeezelite-launcher*: Systemd init script to start all squeezelite instances configurured in MultiChannelAmpDaemon.yaml
- *src/amp_status_to_telegraf.py*: Another tool to collect amp-specific monitoring data and output it using influx format
- *config/alsa/asound.conf*: My configuration file for the three KAB9 sound cards

The code was interactively generated with https://claude.ai as a test case. Although some iterations had been necessary to get it finally working, I am so far happy with the result. To continue the development using AI, you can start with the current specification at [doc/Specification.md](doc/Specification.md)
```

