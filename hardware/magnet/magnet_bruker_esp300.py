import visa
import time
import numpy as np

from core.module import Base
from core.configoption import ConfigOption
from interface.test_magnet_interface import EprocMagnetInterface


class MagnetBrukerESP300(Base, EprocMagnetInterface):
    """

    Example config for copy-paste:

    magnet_bruker:
        module.Class: 'magnet.test_magnet_bruker_esp300.MagnetBrukerESP300'
        gpib_address: 'GPIB0::12::INSTR'
        gpib_timeout: 10
    """

    # visa address of the hardware : this can be over ethernet, the name is here for
    # backward compatibility
    _address = ConfigOption('gpib_address', missing='error')
    _timeout = ConfigOption('gpib_timeout', 10, missing='warn')

    def on_activate(self):
        """ Initialisation performed during activation of the module. """
        self._timeout = self._timeout * 1000
        self.SETTLING_TIME = 0.05  # For small steps of magnetic field
        self.SETTLING_TIME_LARGE = 20 * self.SETTLING_TIME  # For big steps of magnetic field (reset_sweeppos)

        # Lists for field sweep
        self.sweep_list = []
        self.remaining_fields = []

        self.rm = visa.ResourceManager()
        try:
            self._connection = self.rm.open_resource(self._address,
                                                     timeout=self._timeout)
        except:
            self.log.error('Could not connect to the address >>{}<<.'.format(self._address))
            raise

        self.log.info('Magnet initialised and connected.')
        return

    def on_deactivate(self):
        """ Cleanup performed during deactivation of the module. """
        self.rm.close()
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
        field = np.round(field, 2)
        self._connection.write('CF{}'.format(field))
        time.sleep(self.SETTLING_TIME)  # is this enough?
        # self._connection.write('LE')
        # led_status = self._connection.read()
        # while led_status == 1:
        #     time.sleep(0.01)
        #     led_status = self._connection.query('LE')
        return field

    def set_sweep(self, start, stop, step):
        start = np.round(start, 2)
        stop = np.round(stop, 2)
        step = np.round(step, 2)
        self.sweep_list = np.arange(start, stop + step, step)
        self.remaining_fields = self.sweep_list
        self.set_central_field(start - step)
        time.sleep(self.SETTLING_TIME)
        return start, stop, step

    def trigger(self):
        new_field, self.remaining_fields = self.remaining_fields[0], self.remaining_fields[1:]
        self.set_central_field(new_field)
        return 0

    def reset_sweeppos(self):
        self.remaining_fields = self.sweep_list
        start = self.sweep_list[0]
        step = self.sweep_list[1] - self.sweep_list[0]
        self.set_central_field(start - step)
        time.sleep(self.SETTLING_TIME_LARGE)   # Additional waiting time because of large field value change
        return 0
