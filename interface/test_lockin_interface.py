# -*- coding: utf-8 -*-

"""
This file contains the Qudi Interface file to control magnet devices.

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

from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass


class LockinInterface(metaclass=InterfaceMetaclass):
    """ This is the Interface class to define the controls for the devices
        controlling the magnetic field.
    """

    @abstract_interface_method
    def get_value(self, param):
        pass

    @abstract_interface_method
    def set_input_range(self, r):
        pass

    @abstract_interface_method
    def set_coupling_type(self, coupl):
        pass

    @abstract_interface_method
    def set_time_constants(self, tauA=None, tau1=None):
        pass

    @abstract_interface_method
    def set_sync_filter_settings(self, val):
        pass

    @abstract_interface_method
    def set_rolloff(self, dB):
        pass

    @abstract_interface_method
    def set_input_config(self, i):
        pass

    @abstract_interface_method
    def set_amplitude(self, uac):
        pass

    @abstract_interface_method
    def set_frequency(self, f):
        pass

    @abstract_interface_method
    def set_phases(self, phase=None, phase0=None):
        pass

    @abstract_interface_method
    def set_harmonic(self, i):
        pass

    @abstract_interface_method
    def change_reference(self, ref):
        pass