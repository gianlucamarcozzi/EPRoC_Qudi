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


class E3646A(Base, ProcessControlInterface):
    """ Hardware module for power supply Keysight E3631A.

    Example config :
        voltage_generator:
            module.Class: 'power_supply.Keysight_E3631A.E3631A'
            address: 'GBIP0::5::INSTR'
    """

    _address = ConfigOption('address', missing='error')

    _voltage_min = ConfigOption('voltage_min', 0)
    _voltage_max = ConfigOption('voltage_max', 8)
    _current_max = ConfigOption('current_max', 1.5)

    _inst = None
    model = ''

    def on_activate(self):
        """ Startup the module """

        rm = visa.ResourceManager()
        try:
            self._inst = rm.open_resource(self._address)
        except visa.VisaIOError:
            self.log.error('Could not connect to hardware. Please check the wires and the address.')

        self.model = self._query('*IDN?').split(',')[1]

        self._write("*RST;*CLS")
        time.sleep(3)
        self._query("*OPC?")

        self._write("INST P6V")
        self._write("VOLT 0")
        self._write("CURR 0")
        return

    def on_deactivate(self):
        """ Stops the module """
        actual_status = int(self._query('OUTP?')[0])
        while actual_status == 1:
            self._write("OUTP OFF")
            time.sleep(0.2)
            actual_status = int(self._query('OUTP?')[0])
        self._inst.close()
        return

    def _write(self, cmd):
        """ Function to write command to hardware"""
        self._inst.write(cmd)
        time.sleep(.01)
        return

    def _query(self, cmd):
        """ Function to query hardware"""
        return self._inst.query(cmd)

    def output_on(self):
        self._write("OUTP ON")
        actual_status = int(self._query('OUTP?')[0])
        while actual_status != 1:
            time.sleep(0.2)
            actual_status = int(self._query('OUTP?')[0])
        return actual_status

    def output_off(self):
        self._write("OUTP OFF")
        actual_status = int(self._query('OUTP?')[0])
        while actual_status == 1:
            time.sleep(0.2)
            actual_status = int(self._query('OUTP?')[0])
        return actual_status

    def change_to_output1(self):
        self._write('INST OUT1')
        return

    def change_to_output2(self):
        self._write('INST OUT2')
        return

    def set_control_value(self, value):
        """ Set control value, here heating power.

            @param flaot value: control value
        """
        mini, maxi = self.get_control_limit()
        if mini <= value <= maxi:
            self._write("VOLT {}".format(value))
        else:
            self.log.error('Voltage value {} out of range'.format(value))
        return self.get_control_value()

    def get_control_value(self):
        return float(self._query("VOLT?").split('\r')[0])

    def set_current_max(self, maxi):
        if maxi < self._current_max:
            self._write('CURR {}'.format(maxi))
        else:
            self.log.error('Max current value {} out of range'.format(maxi))
        return float(self._query("CURR?").split('\r')[0])

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
