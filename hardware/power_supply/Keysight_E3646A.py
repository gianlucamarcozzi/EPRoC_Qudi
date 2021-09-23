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
    _low_voltage_max = ConfigOption('low_voltage_max', 8)
    _high_voltage_max = ConfigOption('high_voltage_max', 20)
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
        time.sleep(0.5)
        self._query("*OPC?")

        self._write("VOLT:RANG LOW")
        self._write("VOLT 0")
        self._write("CURR 0")
        return

    def on_deactivate(self):
        """ Stops the module """
        self._inst.close()
        '''
        if self._inst.session is not None:
            print('not none')
            self._write("OUTP OFF")
            self._inst.close()
        '''
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

    def change_output(self, outp):
        """ Switch from the current output to output outp

            @:param outp: {1|2} target output
        """
        self._write('INST OUT{}'.format(outp))
        return

    def set_control_value(self, value, outp):
        """ Set control value, here voltage.

            @param float value: control value
            @param int outp: {1|2} output to change
            @return float: actual control value
        """
        self.change_output(outp)
        mini, maxi1, maxi2 = self.get_control_limit()
        if mini <= value <= maxi1:
            self._write('VOLT:RANG LOW')
            self._write('VOLT {}'.format(value))
        elif maxi1 < value <= maxi2:
            self._write('VOLT:RANG HIGH')
            self._write('VOLT {}'.format(value))
        else:
            self.log.error('Voltage value {} out of range'.format(value))
        return self.get_control_value()

    def get_control_value(self):
        return float(self._query("VOLT?").split('\r')[0])

    def set_current_max(self, maxi, ch):
        self.change_output(ch)
        self._write('CURR {}'.format(maxi))
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
        return self._voltage_min, self._low_voltage_max, self._high_voltage_max
