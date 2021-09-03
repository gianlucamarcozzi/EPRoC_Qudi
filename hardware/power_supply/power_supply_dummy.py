# -*- coding: utf-8 -*-
"""

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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""
import time
import visa

from core.module import Base
from core.configoption import ConfigOption
from interface.process_control_interface import ProcessControlInterface


class PowerSupplyDummy(Base, ProcessControlInterface):
    """ Hardware module for power supply Keysight E3631A.

    Example config :
        voltage_generator:
            module.Class: 'power_supply.Keysight_E3631A.E3631A'
            address: 'GBIP0::5::INSTR'
    """

    def on_activate(self):
        """ Startup the module """
        return

    def on_deactivate(self):
        """ Stops the module """
        return

    def _write(self, cmd):
        """ Function to write command to hardware"""
        return

    def _query(self, cmd):
        """ Function to query hardware"""
        return

    def output_on(self):
        return '1'

    def output_off(self):
        return '0'

    def change_to_output1(self):
        return

    def change_to_output2(self):
        return

    def set_control_value(self, value, outp):
        """ Set control value, here heating power.

            @param flaot value: control value
        """
        return value

    def get_control_value(self):
        return

    def set_current_max(self, maxi, outp):
        return maxi

    def get_control_unit(self):
        """ Get unit of control value.

            @return tuple(str): short and text unit of control value
        """
        return 'V', 'Volt'

    def get_control_limit(self):
        """ Get minimum and maximum of control value.

            @return tuple(float, float): minimum and maximum of control value
        """
        return self._voltage_min, self._voltage_max
