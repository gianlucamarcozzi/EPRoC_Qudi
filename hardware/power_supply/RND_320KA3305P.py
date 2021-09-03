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


class KA3305P(Base, ProcessControlInterface):
    """ Hardware module for power supply Keysight E3631A.

    Example config :
        voltage_generator:
            module.Class: 'power_supply.RND_320KA3305P.KA3305P'
            address: 'GBIP0::12::INSTR'
    """

    _address = ConfigOption('address', missing='error')

    _voltage_min = ConfigOption('voltage_min', 0)
    _voltage_max = ConfigOption('voltage_max', 30)
    _current_min = ConfigOption('current_min', 0)
    _current_max = ConfigOption('current_max', 5)

    _inst = None
    model = ''

    def on_activate(self):
        """ Startup the module """

        rm = visa.ResourceManager()
        try:
            self._inst = rm.open_resource(self._address)
        except visa.VisaIOError:
            self.log.error('Could not connect to hardware. Please check the wires and the address.')

        self.model = self._inst.query('*IDN?').split(' ')[1]

        self._write("*RST;*CLS")
        time.sleep(0.5)
        self._write("*OPC?")

        self.set_control_value(0, 1)
        self.set_control_value(0, 2)
        self._write('OCP1')
        self.set_current_max(0, 1)
        self.set_current_max(0, 2)
        return

    def on_deactivate(self):
        """ Stops the module """
        self.output_off()
        self._inst.close()
        return

    def _write(self, cmd):
        """ Function to write command to hardware"""
        self._inst.write(cmd)
        time.sleep(.01)
        return

    def _query(self, cmd):
        """ Function to query command to hardware"""
        value = float(self._inst.query(cmd)[:-2])
        time.sleep(.01)
        return value

    def output_on(self):
        self._write("OUT1")
        # STATUS?
        '''
        actual_status = int(self._write('OUTP?')[0])
        while actual_status != 1:
            time.sleep(0.2)
            actual_status = int(self._write('OUTP?')[0])
        '''
        # return actual_status
        return

    def output_off(self):
        self._write("OUT0")
        # STATUS?
        '''
        actual_status = int(self._write('OUTP?')[0])
        while actual_status == 1:
            time.sleep(0.2)
            actual_status = int(self._write('OUTP?')[0])
        '''
        # return actual_status
        return

    def set_control_value(self, value, outp):
        """ Set control value, here heating power.

            @param flaot value: control value
        """
        mini, maxi = self.get_control_limit()
        if mini <= value <= maxi:
            self._write("VSET{}:{}".format(outp, value))
        else:
            self.log.error('Voltage value {} out of range'.format(value))
        return self.get_control_value(outp)

    def get_control_value(self, outp):
        return float(self._query("VSET{}?".format(outp)))

    def set_current_max(self, maxi, outp):
        if self._current_min <= maxi < self._current_max:
            self._write('OCPSET{}:{}'.format(outp, maxi))
        else:
            self.log.error('Max current value {} out of range'.format(maxi))
        # Query OCPSTE is not in the manual
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
