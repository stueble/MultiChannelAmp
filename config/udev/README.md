# Description
The USB subsystem does not guarantee that the USB sound cards will have the same id after a reboot. Therefore, I use udev rules to assign unique identifiers to them based on the USB port. Keep in mind that the identifer will change if you change the used USB ports!

# Installation
Copy the udev rules file to /etc/udev/rules.d/

