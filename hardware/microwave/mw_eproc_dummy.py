# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware file to control R&S SMB100A or SMBV100A microwave device.
Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.
Parts of this file were developed from a PI3diamond module which is
Copyright (C) 2009 Helmut Rathgen <helmut.rathgen@gmail.com>
Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import visa
import time
import numpy as np

from core.module import Base
from core.configoption import ConfigOption
from interface.microwave_interface import MicrowaveInterface
from interface.microwave_interface import MicrowaveLimits
from interface.microwave_interface import MicrowaveMode
from interface.microwave_interface import TriggerEdge


class MicrowaveSmbv(Base, MicrowaveInterface):
    """ Hardware file to control a R&S SMBV100A microwave device.
    Example config for copy-paste:
    mw_source_smbv:
        module.Class: 'microwave.mw_source_smbv.MicrowaveSmbv'
        gpib_address: 'GPIB0::12::INSTR'
        gpib_address: 'GPIB0::12::INSTR'
        gpib_timeout: 10
    """

    # visa address of the hardware : this can be over ethernet, the name is here for
    # backward compatibility
    _address = ConfigOption('gpib_address', missing='error')
    _timeout = ConfigOption('gpib_timeout', 10, missing='warn')

    # to limit the power to a lower value that the hardware can provide
    _max_power = ConfigOption('max_power', None)

    # Indicate how fast frequencies within a list or sweep mode can be changed:
    _FREQ_SWITCH_SPEED = 0.003  # Frequency switching speed in s (acc. to specs)

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

    def get_limits(self):
        """ Create an object containing parameter limits for this microwave source.
            @return MicrowaveLimits: device-specific parameter limits
        """
        limits = MicrowaveLimits()
        limits.supported_modes = (MicrowaveMode.CW, MicrowaveMode.SWEEP)

        # values for SMBV100A
        limits.min_power = -145
        limits.max_power = 30

        limits.min_frequency = 9e3
        limits.max_frequency = 6e9

        limits.list_minstep = 0.1
        limits.list_maxstep = limits.max_frequency - limits.min_frequency
        limits.list_maxentries = 1

        limits.sweep_minstep = 0.1
        limits.sweep_maxstep = limits.max_frequency - limits.min_frequency
        limits.sweep_maxentries = 10001

        # in case a lower maximum is set in config file
        if self._max_power is not None and self._max_power < limits.max_power:
            limits.max_power = self._max_power

        return limits

    def off(self):
        """
        Switches off any microwave output.
        Must return AFTER the device is actually stopped.
        @return int: error code (0:OK, -1:error)
        """
        return 0

    def get_status(self):
        """
        Gets the current status of the MW source, i.e. the mode (cw, list or sweep) and
        the output state (stopped, running)
        @return str, bool: mode ['cw', 'list', 'sweep'], is_running [True, False]
        """
        return 'cw', True

    def get_power(self):
        """
        Gets the microwave output power.
        @return float: the power set at the device in dBm
        """
        # This case works for cw AND sweep mode
        return 10

    def get_frequency(self):
        """
        Gets the frequency of the microwave output.
        Returns single float value if the device is in cw mode.
        Returns list like [start, stop, step] if the device is in sweep mode.
        Returns list of frequencies if the device is in list mode.
        @return [float, list]: frequency(s) currently set for this device in Hz
        """
        return [1, 1, 1]

    def cw_on(self):
        """
        Switches on cw microwave output.
        Must return AFTER the device is actually running.
        @return int: error code (0:OK, -1:error)
        """
        return 0

    def set_cw(self, frequency=None, power=None):
        """
        Configures the device for cw-mode and optionally sets frequency and/or power
        @param float frequency: frequency to set in Hz
        @param float power: power to set in dBm
        @return tuple(float, float, str): with the relation
            current frequency in Hz,
            current power in dBm,
            current mode
        """
        return 1000, 10, 'cw'

    def list_on(self):
        """
        Switches on the list mode microwave output.
        Must return AFTER the device is actually running.
        @return int: error code (0:OK, -1:error)
        """
        self.log.error('List mode not available for this microwave hardware!')
        return -1

    def set_list(self, frequency=None, power=None):
        """
        Configures the device for list-mode and optionally sets frequencies and/or power
        @param list frequency: list of frequencies in Hz
        @param float power: MW power of the frequency list in dBm
        @return tuple(list, float, str):
            current frequencies in Hz,
            current power in dBm,
            current mode
        """
        return self.get_frequency(), self.get_power(), True

    def reset_listpos(self):
        """
        Reset of MW list mode position to start (first frequency step)
        @return int: error code (0:OK, -1:error)
        """
        self.log.error('List mode not available for this microwave hardware!')
        return -1

    def sweep_on(self):
        """ Switches on the sweep mode.
        @return int: error code (0:OK, -1:error)
        """
        return 0

    def set_sweep(self, start=None, stop=None, step=None, power=None):
        """
        Configures the device for sweep-mode and optionally sets frequency start/stop/step
        and/or power
        @return float, float, float, float, str: current start frequency in Hz,
                                                 current stop frequency in Hz,
                                                 current frequency step in Hz,
                                                 current power in dBm,
                                                 current mode
        """
        return 100, 100, 100, 10, 'cw'

    def reset_sweeppos(self):
        """
        Reset of MW sweep mode position to start (start frequency)
        @return int: error code (0:OK, -1:error)
        """
        return 0

    def set_ext_trigger(self, pol, timing):
        """ Set the external trigger for this device with proper polarization.
        @param TriggerEdge pol: polarisation of the trigger (basically rising edge or falling edge)
        @param float timing: estimated time between triggers
        @return object, float: current trigger polarity [TriggerEdge.RISING, TriggerEdge.FALLING],
            trigger timing
        """
        return 0.1, 0.1

    def set_internal_trigger(self):
        """
        Set internal trigger to SING (one trigger equals next frequency) and to stop at the end of the frequency sweep.
        """
        return

    def trigger(self):
        """ Trigger the next element in the list or sweep mode programmatically.
        @return int: error code (0:OK, -1:error)
        Ensure that the Frequency was set AFTER the function returns, or give
        the function at least a save waiting time.
        """

        # WARNING:
        # The manual trigger functionality was not tested for this device!
        # Might not work well! Please check that!
        return 0
    '''
    def modulation_on(self):
        # current_mode, is_running = self.get_status()
        is_mod_running = bool(float(int(self._connection.query(':MOD?'))))
        
        #if is_running:
        #    if is_mod_running:
        #        return 0
        #    else:
        #        self.off()
        
        if not is_mod_running:
            self._command_wait(':MOD ON')

        return 0

    def modulation_off(self):
        # current_mode, is_running = self.get_status()
        is_mod_running = bool(float(int(self._connection.query(':MOD?'))))
        
        #if is_running:
        #    if not is_mod_running:
        #        return 0
        #    else:
                self.off()
        
        if is_mod_running:
            self._command_wait(':MOD OFF')

        return 0
    '''
    def reference_on(self):
        return 0

    def reference_off(self):
        return 0

    def set_reference(self, shape = None, freq = None, mode=None, dev=None):
        '''
        @param float deviation:
        @param str (or int) source: {EXT1|NOISe|LF1|LF2|INTernal|EXTernal}
        @param str (or int) deviation_mode: {UNCouples|TOtal|RATio}
        @param str (or int) mode: {HBANdwidth|LNOise}
        there are other parameters that can be set through remote operation (sum and ratio).
        Should I take those into consideration as well?

        @return tuple(float, str, str, str) with the relation
            current deviation in Hz (?)
            current source
            current deviation_mode
            current mode
        '''
        # fm should not be on when set_fm is called. Nevertheless: check if fm is on or not and return it off at
        #                                                                                   the end in any case
        # If fm is on: turn it off, set new params, leave if off
        # If fm is off: set new params, leave it off

        return 'Sine', 100, 'HBAN', 190
