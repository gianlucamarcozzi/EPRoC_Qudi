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


class MicrowaveDummy(Base, MicrowaveInterface):
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

    model = 'SMB100A'

    def on_activate(self):
        return

    def on_deactivate(self):
        return

    def _command_wait(self, command_str):
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

        if self.model == 'SMB100A':
            limits.max_frequency = 3.2e9

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
        return 0

    def get_status(self):
        return 'cw', 1

    def get_power(self):
        return

    def get_frequency(self):
        return

    def cw_on(self):
        return 0

    def set_cw(self, frequency=None, power=None):
        return frequency, power, 'cw'

    def list_on(self):
        return

    def set_list(self, frequency=None, power=None):
        return

    def reset_listpos(self):
        return

    def sweep_on(self):
        return

    def set_sweep(self, start=None, stop=None, step=None, power=None):
        return start, stop, step, power

    def reset_sweeppos(self):
        return

    def set_ext_trigger(self, pol, timing):
        return

    def set_internal_trigger(self):
        return

    def trigger(self):
        return

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
        return

    def reference_off(self):
        return

    def set_reference(self, shape=None, freq=None, mode=None, dev=None):
        return shape, freq, mode, dev
