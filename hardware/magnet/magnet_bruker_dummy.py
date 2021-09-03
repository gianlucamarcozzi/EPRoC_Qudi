import visa
import time
import numpy as np

from core.module import Base
from core.configoption import ConfigOption
from interface.test_magnet_interface import EprocMagnetInterface


class MagnetBrukerDummy(Base, EprocMagnetInterface):
    """

    Example config for copy-paste:

    magnet_bruker:
        module.Class: 'magnet.test_magnet_bruker_esp300.MagnetBrukerESP300'
        gpib_address: 'GPIB0::12::INSTR'
        gpib_timeout: 10
    """

    def on_activate(self):
        """ Initialisation performed during activation of the module. """
        return

    def on_deactivate(self):
        """ Cleanup performed during deactivation of the module. """
        return

    def _command_wait(self, command_str):
        """
        Writes the command in command_str via ressource manager and waits until the device has finished
        processing it.
        @param command_str: The command to be written
        """
        return

    def off(self):
        return 0

    def set_central_field(self, field=None):
        return 3480
