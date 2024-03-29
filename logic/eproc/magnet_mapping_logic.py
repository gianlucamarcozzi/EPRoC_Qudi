# -*- coding: utf-8 -*-

"""
This file contains the Qudi Logic module base class.

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

from PyQt5.QtWidgets import QFileDialog
from qtpy import QtCore
from collections import OrderedDict
from interface.microwave_interface import MicrowaveMode
from interface.microwave_interface import TriggerEdge
import numpy as np
import time
import datetime
import matplotlib.pyplot as plt
import os
from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex
from core.connector import Connector
from core.configoption import ConfigOption
from core.statusvariable import StatusVar


class EPRoCLogic(GenericLogic):
    """This is the Logic class for eproc."""

    # declare connectors
    microwave1 = Connector(interface='MicrowaveInterface')
    lockin = Connector(interface='LockinInterface')
    savelogic = Connector(interface='SaveLogic')
    magnet = Connector(interface='EprocMagnetInterface')
    powersupply1 = Connector(interface='ProcessControlInterface')
    powersupply2 = Connector(interface='ProcessControlInterface')
    motorX = Connector(interface='MotorInterface')
    motorY = Connector(interface='MotorInterface')
    motorZ = Connector(interface='MotorInterface')

    # config option
    mw_scanmode = ConfigOption(
        'scanmode',
        'SWEEP',
        missing='warn',
        converter=lambda x: MicrowaveMode[x.upper()])

    # these go here or in on_activate()?
    number_of_sweeps = StatusVar('number_of_sweeps', 1)
    number_of_accumulations = StatusVar('number_of_accumulations', 10)

    # Parameters for microwave sweep
    ms_field = StatusVar('ms_field', 3480.)
    ms_mw_power = StatusVar('ms_mw_power', -30)
    ms_start = StatusVar('ms_start', 2800e6)
    ms_stop = StatusVar('ms_stop', 2950e6)
    ms_step = StatusVar('ms_step', 2e6)

    # Parameters for field sweep
    fs_mw_frequency = StatusVar('fs_mw_frequency', 2870e6)
    fs_mw_power = StatusVar('fs_mw_power', -30)
    fs_start = StatusVar('fs_start', 3400.)
    fs_stop = StatusVar('fs_stop', 3500.)
    fs_step = StatusVar('fs_step', 1.)

    # Change these initial values
    lia_range = StatusVar('lia_range', '0.1')
    lia_uac = StatusVar('lia_uac', 0)
    lia_coupling = StatusVar('lia_coupling', 'ac')
    lia_int_ref_freq = StatusVar('lia_int_ref_freq', 0)
    lia_tauA = StatusVar('lia_tauA', 0.1)
    lia_phaseA = StatusVar('lia_phaseA', 0)
    lia_tauB = StatusVar('lia_tauB', 0.0005)
    lia_phaseB = StatusVar('lia_phaseB', 0)
    lia_waiting_time_factor = StatusVar('lia_waiting_time_factor', 1)
    lia_harmonic = StatusVar('lia_harmonic', '1')
    lia_slope = StatusVar('lia_slope', '6')
    lia_configuration = StatusVar('lia_configuration', 'A&B')

    # Parameters for reference signal
    ref_shape = StatusVar('ref_shape', 'SIN')
    ref_freq = StatusVar('ref_freq', 1000000)
    ref_mode = StatusVar('ref_mode', 'HBAN')
    ref_deviation = StatusVar('ref_deviation', 1000)

    frequency_multiplier = StatusVar('frequency_multiplier', 32)

    psb_voltage_outp1 = StatusVar('psb_voltage_oup2', 2)
    psb_voltage_outp2 = StatusVar('psb_voltage_outp2', 2)
    psb_current_max_outp1 = StatusVar('psb_voltage_current_max_outp1', 0.1)
    psb_current_max_outp2 = StatusVar('psb_voltage_current_max_outp2', 0.1)

    psa_voltage_outp1 = StatusVar('psa_voltage_oup2', 2)
    psa_voltage_outp2 = StatusVar('psa_voltage_outp2', 2)
    psa_current_max_outp1 = StatusVar('psa_voltage_current_max_outp1', 0.1)
    psa_current_max_outp2 = StatusVar('psa_voltage_current_max_outp2', 0.1)

    is_ms = StatusVar('is_ms', True)    # True if microwave sweep is set, false if magnetic field sweep is set
    is_lia_ext_ref = StatusVar('is_lia_ext_ref', True)

    x_motor_set_position = StatusVar('x_motor_set_position', 1)
    y_motor_set_position = StatusVar('y_motor_set_position', 1)
    z_motor_set_position = StatusVar('z_motor_set_position', 1)

    x_position = StatusVar('x_position', 0)
    y_position = StatusVar('y_position', 0)
    z_position = StatusVar('z_position', 0)

    x_start = StatusVar('x_start', 0)
    x_step = StatusVar('x_step', 0)
    x_stop = StatusVar('x_stop', 0)

    y_start = StatusVar('y_start', 0)
    y_step = StatusVar('y_step', 0)
    y_stop = StatusVar('y_stop', 0)

    z_start = StatusVar('z_start', 0)
    z_step = StatusVar('z_step', 0)
    z_stop = StatusVar('z_stop', 0)

    # Internal signals
    sigNextMeasure = QtCore.Signal()
    sigStartNextEproc = QtCore.Signal()
    sigNextPosition = QtCore.Signal()
    sigNextMeasureMapping = QtCore.Signal()

    # Update signals, e.g. for GUI module
    sigParameterUpdated = QtCore.Signal(dict)
    sigStatusUpdated = QtCore.Signal()
    sigEprocPlotsUpdated = QtCore.Signal(np.ndarray, np.ndarray)
    sigSetLabelEprocPlots = QtCore.Signal(bool)
    sigEprocRemainingTimeUpdated = QtCore.Signal(float, int)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self.threadlock = Mutex()

    def on_activate(self):
        """
        Initialisation performed during activation of the module.
        """
        # Get connectors
        self._mw_device = self.microwave1()
        self._lockin_device = self.lockin()
        self._save_logic = self.savelogic()
        self._magnet = self.magnet()
        self._power_supply_board = self.powersupply1()
        self._power_supply_amplifier = self.powersupply2()
        self._x_motor = self.motorX()
        self._y_motor = self.motorY()
        self._z_motor = self.motorZ()

        # Get hardware constraints
        limits = self.get_hw_constraints()

        # Set/recall microwave source parameters
        self.fs_mw_frequency = limits.frequency_in_range(self.fs_mw_frequency)
        self.fs_mw_power = limits.power_in_range(self.fs_mw_power)
        self.ms_mw_power = limits.power_in_range(self.ms_mw_power)

        # Elapsed measurement time and number of sweeps
        self.elapsed_time = 0.0
        self.elapsed_sweeps = 0
        self.elapsed_accumulations = 0

        self.is_eproc_running = False
        self.is_eproc_mapping_running = False

        # Set flag for stopping a measurement
        self.stopRequested = False
        self.stopNextSweepRequested = False

        # Initalize the data arrays
        self._initialize_eproc_plots()
        # Raw data array
        self.eproc_raw_data = np.zeros(
            [self.number_of_sweeps,
             self.number_of_accumulations,
             self.eproc_plot_x.size,
             4]  # writing it for 2 channels, but this should become a method get_lockin_channels of some sort
        )

        # Switch off microwave and set CW frequency and power
        self.mw_off()

        # Set only the continuous values
        self.set_ms_parameters(self.ms_start, self.ms_step, self.ms_stop, self.ms_field, self.ms_mw_power)
        self.set_fs_parameters(self.fs_start, self.fs_step, self.fs_stop, self.fs_mw_frequency, self.fs_mw_power)

        self.set_lia_parameters(self.lia_range, self.lia_uac, self.lia_coupling, self.lia_int_ref_freq, self.lia_tauA,
                                self.lia_phaseA, self.lia_tauB, self.lia_phaseB, self.lia_waiting_time_factor,
                                self.lia_harmonic, self.lia_slope, self.lia_configuration)

        self.set_ref_parameters(self.ref_shape, self.ref_freq, self.ref_mode, self.ref_deviation)
        self.set_eproc_scan_parameters(self.number_of_sweeps, self.number_of_accumulations)
        self.set_psb_parameters(self.psb_voltage_outp1, self.psb_voltage_outp2,
                                self.psb_current_max_outp1, self.psb_current_max_outp2)
        self.set_psa_parameters(self.psa_voltage_outp1, self.psa_voltage_outp2,
                                self.psa_current_max_outp1, self.psa_current_max_outp2)
        self.set_motor_parameters(self.x_motor_set_position, self.x_start, self.x_step, self.x_stop,
                                  self.y_motor_set_position, self.y_start, self.y_step, self.y_stop,
                                  self.z_motor_set_position, self.z_start, self.z_step, self.z_stop)

        # Connect signals
        self.sigNextMeasure.connect(self._next_measure, QtCore.Qt.QueuedConnection)
        self.sigStartNextEproc.connect(self.start_eproc, QtCore.Qt.QueuedConnection)
        self.sigNextPosition.connect(self._next_position, QtCore.Qt.QueuedConnection)
        return

    def on_deactivate(self):
        """
        Deinitialisation performed during deactivation of the module.
        """
        # Stop measurement if it is still running
        if self.module_state() == 'locked':
            self.stop_microwavesweep_scan()
        timeout = 30.0
        start_time = time.time()
        while self.module_state() == 'locked':
            time.sleep(0.5)
            timeout -= (time.time() - start_time)
            if timeout <= 0.0:
                self.log.error('Failed to properly deactivate eproc logic. Eproc scan is still '
                               'running but can not be stopped after 30 sec.')
                break
        # Switch off microwave source for sure (also if CW mode is active or module is still locked)
        self._mw_device.off()
        # Disconnect signals
        self.sigNextMeasure.disconnect()
        self.sigStartNextEproc.disconnect()
        self.sigNextPosition.disconnect()

    def _initialize_eproc_plots(self):
        """ Initializing the eproc plots. """
        if self.is_ms:
            self.eproc_plot_x = np.array(np.arange(self.ms_start, self.ms_stop + self.ms_step, self.ms_step))
        else:
            self.eproc_plot_x = np.array(np.arange(self.fs_start, self.fs_stop + self.fs_step, self.fs_step))
        self.eproc_plot_y = np.zeros([self.eproc_plot_x.size,
                                      4])  # writing it for 4 channels, but this should become a method get_lockin_channels of some sort

        self.sigEprocPlotsUpdated.emit(self.eproc_plot_x, self.eproc_plot_y)
        self.sigSetLabelEprocPlots.emit(self.is_ms)
        return

    def ms_on(self):
        if self.module_state() == 'locked':
            self.log.error('Can not change to microwave sweep. EPRoCLogic is already locked.')
        else:
            self.set_ms_parameters(self.ms_start, self.ms_step, self.ms_stop, self.ms_field, self.ms_mw_power)
            self.is_ms = True
            self.sigStatusUpdated.emit()
        return

    def ms_off(self):
        if self.module_state() == 'locked':
            self.log.error('Can not change to field sweep. EPRoCLogic is already locked.')
        else:
            self.set_fs_parameters(self.fs_start, self.fs_step, self.fs_stop, self.fs_mw_frequency, self.ms_mw_power)
            self.is_ms = False
            self.sigStatusUpdated.emit()
        return

    def set_ms_parameters(self, start, step, stop, field, power):
        """ Set the desired parameters for a microwave sweep. This means that start, step and stop refer to the
        microwave.

        @param list starts: list of start frequencies to set in Hz
        @param list stops: list of stop frequencies to set in Hz
        @param list steps: list of step frequencies to set in Hz
        @param list power: mw power to set in dBm

        @return list, list, list, float: current start_freq, current stop_freq,
                                            current freq_step, current power
        """
        limits = self.get_hw_constraints()

        if self.module_state() != 'locked':
            if isinstance(start, (int, float)) and isinstance(power, (int, float)):
                start = limits.frequency_in_range(start)
                # power = limits.power_in_range(power)
                self.ms_start, self.ms_mw_power, dummy = self._mw_device.set_cw(start, power)
            if isinstance(stop, (int, float)) and isinstance(step, (int, float)):
                self.ms_step = limits.sweep_step_in_range(step)
                if stop <= start:
                    stop = start + step
                self.ms_stop = limits.frequency_in_range(stop)
            if isinstance(field, (int, float)):
                # This should be changed when the methods to check field limits is implemented
                self.ms_field = self._magnet.set_central_field(field)
        else:
            self.log.warning('set_ms_parameters failed. Logic is locked.')

        param_dict = {'ms_start': self.ms_start, 'ms_stop': self.ms_stop, 'ms_step': self.ms_step,
                      'ms_mw_power': self.ms_mw_power, 'ms_field': self.ms_field}
        self.sigParameterUpdated.emit(param_dict)
        return self.ms_start, self.ms_step, self.ms_stop, self.ms_field, self.ms_mw_power

    def set_fs_parameters(self, start, step, stop, frequency, power):
        # To fix: use limits, like in set_ms_mw_frequency
        if self.module_state() != 'locked':
            limits = self.get_hw_constraints()

            if isinstance(start, (int, float)):
                self.fs_start = self._magnet.set_central_field(start)
            if isinstance(stop, (int, float)) and isinstance(step, (int, float)):
                if stop <= start:
                    stop = start + step
                self.fs_stop = stop
                self.fs_step = step
            if isinstance(frequency, (int, float)) and isinstance(power, (int, float)):
                frequency = limits.frequency_in_range(frequency)
                power = limits.power_in_range(power)
                self.fs_mw_frequency, self.fs_mw_power, dummy = self._mw_device.set_cw(frequency, power)
        else:
            self.log.warning('set_fs_field_parameters failed. Logic is locked.')

        param_dict = {'fs_start': self.fs_start, 'fs_stop': self.fs_stop, 'fs_step': self.fs_step,
                      'fs_mw_frequency': self.fs_mw_frequency, 'fs_mw_power': self.fs_mw_power}
        self.sigParameterUpdated.emit(param_dict)
        return self.fs_start, self.fs_step, self.fs_stop, self.fs_mw_frequency, self.fs_mw_power

    def check_ranges(self):
        """
        Write the stop point as  start + n * step, where n is the number of steps
        """
        # sigParameterUpdated.emit() is not present because this module is only called in start_eproc() and it is
        # placed before another method that calls sigParameterUpdated.emit()
        num_step = int(np.rint((self.ms_stop - self.ms_start) / self.ms_step))
        self.ms_stop = self.ms_start + num_step * self.ms_step
        num_step = int(np.rint((self.fs_stop - self.fs_start) / self.fs_step))
        self.fs_stop = self.fs_start + num_step * self.fs_step
        return

    def set_lia_parameters(self, input_range, uac, coupling, int_ref_freq, tauA, phaseA, tauB, phaseB,
                           waiting_time_factor,
                           harmonic, slope, configuration):
        if self.module_state() != 'locked':
            if isinstance(uac, (int, float)) and isinstance(int_ref_freq, (int, float)) \
                    and isinstance(phaseA, (int, float)) and isinstance(phaseB, (int, float)) \
                    and isinstance(waiting_time_factor, (int, float)) and waiting_time_factor > 0:
                self.lia_range = self._lockin_device.set_input_range(input_range)
                self.lia_uac = self._lockin_device.set_amplitude(uac)
                self.lia_coupling = self._lockin_device.set_coupling_type(coupling)
                self.lia_int_ref_freq = self._lockin_device.set_frequency(int_ref_freq)
                self.lia_tauA, self.lia_tauB = self._lockin_device.set_time_constants(tauA, tauB)
                self.lia_phaseA, self.lia_phaseB = self._lockin_device.set_phases(phaseA, phaseB)
                self.lia_waiting_time_factor = waiting_time_factor
                self.lia_harmonic = self._lockin_device.set_harmonic(harmonic)
                self.lia_slope = self._lockin_device.set_rolloff(slope)
                self.lia_configuration = self._lockin_device.set_input_config(configuration)
            else:
                self.log.warning('set_lia_parameters failed. At least one value is not of the correct type.')
        else:
            self.log.warning('set_lia_parameters failed. The logic is locked.')
        # not updating tau value for now because the indexes are useful for the gui and the value for the logic,
        # im giving it the value for now
        param_dict = {'lia_range': self.lia_range, 'lia_uac': self.lia_uac, 'lia_coupling': self.lia_coupling,
                      'lia_int_ref_freq': self.lia_int_ref_freq, 'lia_tauA': self.lia_tauA,
                      'lia_phaseA': self.lia_phaseA,
                      'lia_tauB': self.lia_tauB, 'lia_phaseB': self.lia_phaseB,
                      'lia_waiting_time_factor': self.lia_waiting_time_factor, 'lia_harmonic': self.lia_harmonic,
                      'lia_slope': self.lia_slope, 'lia_configuration': self.lia_configuration}
        self.sigParameterUpdated.emit(param_dict)
        return self.lia_range, self.lia_uac, self.lia_coupling, self.lia_int_ref_freq, self.lia_tauA, self.lia_tauB, \
               self.lia_phaseA, self.lia_phaseB, self.lia_waiting_time_factor, self.lia_harmonic, self.lia_slope, \
               self.lia_configuration

    def lockin_ext_ref_on(self):
        if self.module_state() == 'locked':
            self.log.error('Can not change lockin reference. EPRoCLogic is already locked.')
        else:
            error_code = self._lockin_device.change_reference('ext')
            # error_code = {0|1} where 0 means internal reference and 1 external reference
            # is this hardware dependent?
            if error_code == 0:
                self.log.error('Change of reference failed')
            else:
                self.set_ref_parameters(self.ref_shape, self.ref_freq, self.ref_mode, self.ref_deviation)
                self.is_lia_ext_ref = True
            self.sigStatusUpdated.emit()
        return

    def lockin_ext_ref_off(self):
        if self.module_state() == 'locked':
            self.log.error('Can not change lockin reference. EPRoCLogic is already locked.')
        else:
            error_code = self._lockin_device.change_reference('int')
            if error_code == 1:
                self.log.error('Change of reference failed')
            else:
                self.is_lia_ext_ref = False
            self.sigStatusUpdated.emit()
        return

    def set_ref_parameters(self, shape, freq, mode, dev):
        if self.module_state() != 'locked':
            if isinstance(freq, (int, float)) and isinstance(dev, (int, float)):
                self.ref_shape, self.ref_freq, self.ref_mode, self.ref_deviation = self._mw_device.set_reference(
                                                                                        shape, freq, mode, dev)

        param_dict = {'ref_shape': self.ref_shape, 'ref_freq': self.ref_freq, 'ref_deviation': self.ref_deviation,
                      'ref_mode': self.ref_mode}
        self.sigParameterUpdated.emit(param_dict)
        return self.ref_shape, self.ref_freq, self.ref_deviation, self.ref_mode

    def set_eproc_scan_parameters(self, number_of_sweeps, number_of_accumulations):
        if self.module_state() != 'locked':
            if isinstance(number_of_sweeps, int) and isinstance(number_of_accumulations, int):
                self.number_of_sweeps = number_of_sweeps
                self.number_of_accumulations = number_of_accumulations
        else:
            self.log.warning('set_eproc_scan_parameters failed. Logic is either locked or input value is '
                             'no integer.')

        param_dict = {'number_of_sweeps': self.number_of_sweeps,
                      'number_of_accumulations': self.number_of_accumulations}
        self.sigParameterUpdated.emit(param_dict)
        return self.number_of_sweeps, self.number_of_accumulations

    def set_frequency_multiplier(self, multiplier):
        if self.module_state() != 'locked':
            self.frequency_multiplier = multiplier
        else:
            self.log.warning('set_frequency_multiplier failed. Logic is locked.')

        param_dict = {'frequency_multiplier': self.frequency_multiplier}
        self.sigParameterUpdated.emit(param_dict)
        return self.frequency_multiplier

    def psb_on(self):
        if self.module_state() != 'locked':
            status = self._power_supply_board.output_on()
            if status != 1:
                self.log.warning('psb_on failed. psb is still turned off.')
        else:
            self.log.warning('psb_on failed. Logic is locked.')
        return

    def psb_off(self):
        if self.module_state() != 'locked':
            status = self._power_supply_board.output_off()
            if status == 1:
                self.log.warning('psb_off failed. psb is still turned on.')
        else:
            self.log.warning('psb_off failed. Logic is locked.')
        return

    def set_psb_parameters(self, v1, v2, maxi1, maxi2):
        if self.module_state() != 'locked':
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)) and isinstance(maxi1, (int, float)) and \
                    isinstance(maxi1, (int, float)) and not v1 < 0 and not v2 < 0 and not maxi1 < 0 and not maxi2 < 0:
                self.psb_voltage_outp1 = self._power_supply_board.set_control_value(v1, 1)
                self.psb_current_max_outp1 = self._power_supply_board.set_current_max(maxi1, 1)
                self.psb_voltage_outp2 = self._power_supply_board.set_control_value(v2, 2)
                self.psb_current_max_outp2 = self._power_supply_board.set_current_max(maxi2, 2)
            else:
                self.log.warning('set_psb_parameters failed. Values are not float or int, or values are not positive')
        else:
            self.log.warning('set_psb_parameters failed. Logic is locked.')

        param_dict = {'psb_voltage_outp1': self.psb_voltage_outp1,
                      'psb_voltage_outp2': self.psb_voltage_outp2,
                      'psb_current_max_outp1': self.psb_current_max_outp1,
                      'psb_current_max_outp2': self.psb_current_max_outp2}
        self.sigParameterUpdated.emit(param_dict)
        return

    def psa_on(self):
        if self.module_state() != 'locked':
            self._power_supply_amplifier.output_on()
        else:
            self.log.warning('psa_on failed. Logic is locked.')
        return

    def psa_off(self):
        if self.module_state() != 'locked':
            self._power_supply_amplifier.output_off()
        else:
            self.log.warning('psa_off failed. Logic is locked.')
        return

    def set_psa_parameters(self, v1, v2, maxi1, maxi2):
        if self.module_state() != 'locked':
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)) and isinstance(maxi1, (int, float)) and \
                    isinstance(maxi1, (int, float)) and not v1 < 0 and not v2 < 0 and not maxi1 < 0 and not maxi2 < 0:
                self.psa_voltage_outp1 = self._power_supply_amplifier.set_control_value(v1, 1)
                self.psa_current_max_outp1 = self._power_supply_amplifier.set_current_max(maxi1, 1)
                self.psa_voltage_outp2 = self._power_supply_amplifier.set_control_value(v2, 2)
                self.psa_current_max_outp2 = self._power_supply_amplifier.set_current_max(maxi2, 2)
            else:
                self.log.warning('set_psb_parameters failed. Values are not float or int, or values are not positive')
        else:
            self.log.warning('set_psb_parameters failed. Logic is locked.')

        param_dict = {'psb_voltage_outp1': self.psb_voltage_outp1,
                      'psb_voltage_outp2': self.psb_voltage_outp2,
                      'psb_current_max_outp1': self.psb_current_max_outp1,
                      'psb_current_max_outp2': self.psb_current_max_outp2}
        self.sigParameterUpdated.emit(param_dict)
        return

    def mw_on(self):
        """
        Switching on the mw source in cw mode.

        @return str, bool: active mode ['cw', 'list', 'sweep'], is_running
        """
        self.fs_mw_frequency, self.fs_mw_power, mode = self._mw_device.set_cw(self.fs_mw_frequency, self.fs_mw_power)
        param_dict = {'fs_mw_frequency': self.fs_mw_frequency, 'fs_mw_power': self.fs_mw_power}
        self.sigParameterUpdated.emit(param_dict)
        err_code = self._mw_device.cw_on()
        if err_code < 0:
            self.log.error('Activation of microwave output failed.')

        mode, is_running = self._mw_device.get_status()
        # self.sigStatusUpdated.emit(is_running)
        return mode, is_running

    def mw_off(self):
        """ Switching off the MW source.

        @return str, bool: active mode ['cw', 'list', 'sweep'], is_running
        """
        error_code = self._mw_device.off()
        if error_code < 0:
            self.log.error('Switching off microwave source failed.')

        mode, is_running = self._mw_device.get_status()
        # self.sigStatusUpdated.emit(is_running)
        return mode, is_running

    def modulation_on(self):
        """ Switch on the reference LF signal and the frequency modulation."""
        is_running = self._mw_device.fm_on()
        if not is_running:
            self.log.error('Failed to switch on modulation.')
        is_running = self._mw_device.lf_on()
        if not is_running:
            self.log.error('Failed to switch on LF reference.')
        return

    def modulation_off(self):
        """ Switch on the reference LF signal and the frequency modulation."""
        is_running = self._mw_device.fm_off()
        if is_running:
            self.log.error('Failed to switch off modulation.')
        is_running = self._mw_device.lf_off()
        if is_running:
            self.log.error('Failed to switch off LF reference.')
        return

    def start_eproc(self):
        with self.threadlock:
            if self.module_state() == 'locked':
                self.log.error('Can not start eproc scan. Logic is already locked.')
                return -1

            self.check_ranges()

            # Set the checked parameters and update them if they are wrong
            if self.is_ms:
                self.ms_start, self.ms_step, self.ms_stop, self.ms_field, self.ms_mw_power = \
                    self.set_ms_parameters(self.ms_start, self.ms_step, self.ms_stop, self.ms_field, self.ms_mw_power)
                self.ms_actual_frequency = self.ms_start
            else:
                self.fs_start, self.fs_step, self.fs_stop, self.fs_mw_frequency, self.fs_mw_power = \
                    self.set_fs_parameters(self.fs_start, self.fs_step, self.fs_stop, self.fs_mw_frequency,
                                           self.fs_mw_power)
                self.fs_actual_field = self.fs_start

            tau = max(self.lia_tauA, self.lia_tauB)
            self.lia_waiting_time = tau * self.lia_waiting_time_factor  # in seconds

            self.elapsed_sweeps = 0
            self.elapsed_accumulations = 0
            self.actual_index = 0  # It is the index of the point along the sweep

            remaining_time = self.lia_waiting_time * (self.number_of_accumulations
                                                      * self.eproc_plot_x.size * self.number_of_sweeps)
            self._startTime = time.time()

            self._initialize_eproc_plots()
            self.eproc_raw_data = np.zeros(
                [self.number_of_sweeps,
                 self.number_of_accumulations,
                 self.eproc_plot_x.size,
                 4]  # number of channels {2 or 4}
            )

            # self.module_state.lock()
            self.stopRequested = False
            self.stopNextSweepRequested = False
            # self.fc.clear_result()

            self.is_eproc_running = True
            self.sigEprocRemainingTimeUpdated.emit(remaining_time, self.elapsed_sweeps)
            self.sigStatusUpdated.emit()
            self.sigNextMeasure.emit()
            return 0

    def stop_eproc(self):
        """ Stop the eproc scan.

        @return int: error code (0:OK, -1:error)
        """
        # with self.threadlock:
        #     if self.module_state() == 'locked':
        #         self.stopRequested = True
        #     else:
        #         self.log.error('Cannot stop eproc scan. Logic is not locked.')
        self.stopRequested = True
        return 0

    def stop_eproc_next_sweep(self):
        """ Stop the eproc scan.

        @return int: error code (0:OK, -1:error)
        """
        # with self.threadlock:
        #     if self.module_state() == 'locked':
        #         self.stopNextSweepRequested = True
        self.stopNextSweepRequested = True
        return 0

    def _next_measure(self):
        with self.threadlock:
            # if self.module_state() != 'locked':
            #     return

            if self.stopRequested:
                self.stopRequested = False
                self.is_eproc_running = False
                self.measurement_duration = time.time() - self._startTime
                # self.module_state.unlock()
                self.sigStatusUpdated.emit()
                return

            # Between two accumulations on the same point wait for an arbitrary value of tau/10
            time.sleep(self.lia_waiting_time)
            self._get_data_lia()

            self.elapsed_accumulations += 1
            self._set_new_parameters()

            self._update_remaining_time()
            self.sigEprocPlotsUpdated.emit(self.eproc_plot_x, self.eproc_plot_y)
            if (self.is_eproc_mapping_running and self.elapsed_sweeps != self.number_of_sweeps) or not self.is_eproc_mapping_running:
                self.sigNextMeasure.emit()
            return

    def _get_data_lia(self):
        """ Get data from the lockin amplifier. The number of channels is four."""
        self.eproc_raw_data[
            self.elapsed_sweeps, self.elapsed_accumulations,
            self.actual_index, :] = self._lockin_device.get_data_lia()

        # Measure again if data from Lia is not real data (when this happens the value is really close to zero)
        for i in range(len(self.eproc_raw_data[0, 0, 0, :])):
            while abs(self.eproc_raw_data[
                          self.elapsed_sweeps, self.elapsed_accumulations, self.actual_index, i]) < 1e-7:
                time.sleep(0.01)
                self.eproc_raw_data[self.elapsed_sweeps, self.elapsed_accumulations,
                                    self.actual_index, :] = self._lockin_device.get_data_lia()
        return 0

    def _set_new_parameters(self):
        """Set new field and microwave parameters if necessary.

        1. If all accumulations are completed: perform average and set new x position.
        2. If the x position reached the stop value: go back to initial x position.
        3. If all sweeps are completed or stopNextSweepRequested: stop.
        """
        if self.elapsed_accumulations == self.number_of_accumulations:
            self._average_data()  # average over accumulations for the current x and the current sweep to update the plots

            self.elapsed_accumulations = 0
            if self.actual_index == self.eproc_plot_x.size - 1:
                if self.is_ms:
                    self.ms_actual_frequency, self.ms_mw_power, mode = \
                        self._mw_device.set_cw(self.ms_start, self.ms_mw_power)
                else:
                    self.fs_actual_field = self._magnet.set_central_field(self.fs_start)
                self.elapsed_sweeps += 1
                self.actual_index = 0
                if self.elapsed_sweeps == self.number_of_sweeps or self.stopNextSweepRequested:
                    if self.is_eproc_mapping_running:
                        self.sigNextPosition.emit()
                    else:
                        self.stopRequested = True
            else:
                if self.is_ms:
                    self.ms_actual_frequency, self.ms_mw_power, mode = \
                        self._mw_device.set_cw(self.ms_actual_frequency + self.ms_step, self.ms_mw_power)
                else:
                    self.fs_actual_field = self._magnet.set_central_field(self.fs_actual_field + self.fs_step)
                self.actual_index += 1
        return 0

    def _average_data(self):
        """Average over the sweeps that were already performed and the accumulations at fixed value of index."""
        self.eproc_plot_y[self.actual_index] = np.mean(
            self.eproc_raw_data[:self.elapsed_sweeps + 1, :, self.actual_index, :],
            axis=(0, 1),
            dtype=np.float64
        )
        return 0

    def _update_remaining_time(self):
        """Compute new remaining time and emit signal to the gui."""
        updated_time = (self.lia_waiting_time
                        * (self.number_of_accumulations * (self.eproc_plot_x.size - self.actual_index)
                           + self.number_of_accumulations * self.eproc_plot_x.size * (self.number_of_sweeps
                                                                                      - self.elapsed_sweeps)
                           )
                        )
        self.sigEprocRemainingTimeUpdated.emit(updated_time, self.elapsed_sweeps)
        return 0

    #                 (self.number_of_accumulations * self.eproc_plot_x.size * self.number_of_sweeps -
    #                           (self.elapsed_accumulations + self.number_of_accumulations * self.actual_index +
    #                            self.number_of_accumulations * self.eproc_plot_x.size * self.elapsed_sweeps))

    def get_hw_constraints(self):
        """ Return the names of all ocnfigured fit functions.
        @return object: Hardware constraints object
        """
        constraints = self._mw_device.get_limits()
        return constraints

    def get_time_constants(self):
        return self._lockin_device.tau_values

    def save_eproc_data(self, tag=None):
        """ Saves the current eproc data to a file."""
        timestamp = datetime.datetime.now()
        filepath = self._save_logic.get_path_for_module(module_name='eproc')

        if tag == '':
            tag = str(timestamp).replace(' ', '_')
            tag = str(tag).replace(':', '-')
            tag = tag.split('.')[0]
        tag_raw = tag + '_rawdata'
        ending = '.txt'

        # Data, on which the average on accumulations and sweeps was performed
        eproc_data_list = [self.eproc_plot_x]

        for channel in range(len(self.eproc_raw_data[0, 0, 0, :])):
            eproc_data_list.append(self.eproc_plot_y[:, channel])

        # Raw data, only the average on the accumulations was performed
        eproc_raw_data_list = [self.eproc_plot_x]
        for channel in range(len(self.eproc_raw_data[0, 0, 0, :])):
            # fix: this works if the sweep is not finished, otherwise it doesnt work!!
            if self.elapsed_sweeps == self.number_of_sweeps:
                for sweep in range(self.elapsed_sweeps):
                    eproc_raw_data_list.append(np.mean(self.eproc_raw_data[sweep, :, :, channel],
                                                       axis=0,
                                                       # axis = 0 in this case means an average over accumulations
                                                       dtype=np.float64))
            else:
                for sweep in range(self.elapsed_sweeps + 1):
                    eproc_raw_data_list.append(np.mean(self.eproc_raw_data[sweep, :, :, channel],
                                                       axis=0,
                                                       # axis = 0 in this case means an average over accumulations
                                                       dtype=np.float64))

        eproc_data = OrderedDict()
        eproc_raw_data = OrderedDict()
        parameters = OrderedDict()

        if self.is_ms:
            eproc_data['Frequency\t\tChannel 1\t\tChannel 2\t\tChannel 3\t\tChannel 4'] = np.array(
                eproc_data_list).transpose()
            eproc_raw_data['Column 0: frequency\n'
                           'From column 1 to column {0}: channel 1, sweep 1 to sweep {0}\n'
                           'From column {1} to column {2}: channel 2, sweep 1 to sweep {0}\n'
                           'From column {3} to column {4}: channel 3, sweep 1 to sweep {0}\n'
                           'From column {5} to column {6}: channel 4, sweep 1 to sweep {0}\n'.format(
                (self.elapsed_sweeps + 1), (self.elapsed_sweeps + 2), 2 * (self.elapsed_sweeps + 1),
                (2 * (self.elapsed_sweeps + 1) + 1), (3 * (self.elapsed_sweeps + 1)),
                (3 * (self.elapsed_sweeps + 1) + 1), (4 * (self.elapsed_sweeps + 1)))] = \
                np.array(eproc_raw_data_list).transpose()
            # Saving parameters as str for readability
            parameters['Magnetic Field (G)'] = str(self.ms_field)
            parameters['Microwave Power (dBm)'] = str(self.ms_mw_power)
            parameters['Start Frequency (Hz)'] = str(self.ms_start)
            parameters['Step Size (Hz)'] = str(self.ms_step)
            parameters['Stop Frequency (Hz)'] = str(self.ms_stop)
        else:
            eproc_data['Field\t\tChannel 1\t\tChannel 2\t\tChannel 3\t\tChannel 4'] = np.array(
                eproc_data_list).transpose()
            eproc_raw_data['Column 0: field\n'
                           'From column 1 to column {0}: channel 1, sweep 1 to sweep {0}\n'
                           'From column {1} to column {2}: channel 2, sweep 1 to sweep {0}\n'
                           'From column {3} to column {4}: channel 3, sweep 1 to sweep {0}\n'
                           'From column {5} to column {6}: channel 4, sweep 1 to sweep {0}\n'.format(
                (self.elapsed_sweeps + 1), (self.elapsed_sweeps + 2), 2 * (self.elapsed_sweeps + 1),
                (2 * (self.elapsed_sweeps + 1) + 1), (3 * (self.elapsed_sweeps + 1)),
                (3 * (self.elapsed_sweeps + 1) + 1), (4 * (self.elapsed_sweeps + 1)))] = \
                np.array(eproc_raw_data_list).transpose()
            # Saving parameters as str for readability
            parameters['Microwave Frequency (Hz)'] = str(self.fs_mw_frequency)
            parameters['Microwave Power (dBm)'] = str(self.fs_mw_power)
            parameters['Start Field (G)'] = str(self.fs_start)
            parameters['Step Size (G)'] = str(self.fs_step)
            parameters['Stop Field (G)'] = str(self.fs_stop)

        parameters['Duration Of The Experiment'] = time.strftime('%Hh%Mm%Ss', time.gmtime(self.measurement_duration))
        parameters['Elapsed Sweeps'] = self.elapsed_sweeps
        parameters['Accumulations Per Point'] = self.number_of_accumulations

        parameters['Frequency Multiplier'] = self.frequency_multiplier

        parameters['Lockin Input Range (V)'] = self.lia_range
        parameters['Lockin Amplitude (V)'] = str(self.lia_uac)
        parameters['Lockin Coupling'] = self.lia_coupling
        parameters['Lockin tau A (s)'] = str(self.lia_tauA)
        parameters['Lockin Phase A (°)'] = str(self.lia_phaseA)
        parameters['Lockin tau B (s)'] = str(self.lia_tauB)
        parameters['Lockin Phase B (°)'] = str(self.lia_phaseB)
        parameters['Lockin Waiting Time Factor'] = str(self.lia_waiting_time_factor)
        parameters['Lockin Harmonic'] = self.lia_harmonic
        parameters['Lockin Slope (dB/oct)'] = self.lia_slope
        parameters['Lockin Configuration'] = self.lia_configuration

        if self.is_lia_ext_ref:
            parameters['Modulation Signal Shape'] = self.ref_shape
            parameters['Modulation Frequency (Hz)'] = str(self.ref_freq)
            parameters['Modulation Deviation (Hz)'] = str(self.ref_deviation)
            parameters['Modulation Mode'] = self.ref_mode
        else:
            parameters['Lockin Internal Modulation Frequency (Hz)'] = self.lia_int_ref_freq

        self._save_logic.save_data(eproc_data,
                                   filepath=filepath,
                                   parameters=parameters,
                                   filename=tag + ending,
                                   fmt='%.6e',
                                   delimiter='\t')

        self._save_logic.save_data(eproc_raw_data,
                                   filepath=filepath,
                                   parameters=parameters,
                                   filename=tag_raw + ending,
                                   fmt='%.6e',
                                   delimiter='\t')

        self.log.info('eproc data saved to:\n{0}'.format(filepath))
        return

    def x_motor_on(self):
        """
        Switching on the x motor.
        """
        return self._x_motor.connection_on()

    def y_motor_on(self):
        """
        Switching on the x motor.
        """
        return self._y_motor.connection_on()

    def z_motor_on(self):
        """
        Switching on the x motor.
        """
        return self._z_motor.connection_on()

    def x_motor_off(self):
        """
        Switching on the x motor.
        """
        return self._x_motor.connection_off()

    def y_motor_off(self):
        """
        Switching on the x motor.
        """
        return self._y_motor.connection_off()

    def z_motor_off(self):
        """
        Switching on the x motor.
        """
        return self._z_motor.connection_off()

    def home(self, p):
        """
        Move the stage at home
        """
        if p == 'x':
            self._x_motor.move_home()
            self.read_position(p)

        elif p == 'y':
            self._y_motor.move_home()
            self.read_position(p)

        elif p == 'z':
            self._z_motor.move_home()
            self.read_position(p)

        param_dict = {'x_position': self.x_position, 'y_position': self.y_position, 'z_position': self.z_position}

        self.sigParameterUpdated.emit(param_dict)
        return

    def set_motor_parameters(self, x_motor_set_position, x_start, x_step, x_stop,
                             y_motor_set_position, y_start, y_step, y_stop,
                             z_motor_set_position, z_start, z_step, z_stop):

        self.x_motor_set_position = x_motor_set_position
        self.x_start = x_start
        self.x_step = x_step
        self.x_stop = x_stop
        self.y_motor_set_position = y_motor_set_position
        self.y_start = y_start
        self.y_step = y_step
        self.y_stop = y_stop
        self.z_motor_set_position = z_motor_set_position
        self.z_start = z_start
        self.z_step = z_step
        self.z_stop = z_stop

        return

    def move(self, p):
        """
        Move the stage at a certain position
        """
        if p == 'x':
            self._x_motor.move(self.x_motor_set_position)
            self.read_position(p)

        elif p == 'y':
            self._y_motor.move(self.y_motor_set_position)
            self.read_position(p)

        elif p == 'z':
            self._z_motor.move(self.z_motor_set_position)
            self.read_position(p)

        param_dict = {'x_position': self.x_position, 'y_position': self.y_position, 'z_position': self.z_position}

        self.sigParameterUpdated.emit(param_dict)

        return

    def read_position(self, p):

        if p == 'x':
            self.x_position = self._x_motor.read_position()

        elif p == 'y':
            self.y_position = self._y_motor.read_position()

        elif p == 'z':
            self.z_position = self._z_motor.read_position()

        return

    def start_eproc_mapping(self, tag):
        if tag == "":
            timestamp = datetime.datetime.now()
            tag = str(timestamp).replace(' ', '_')
            tag = str(tag).replace(':', '-')
            tag = tag.split('.')[0]
        ending = '.txt'

        self.tag = tag + ending

        if self.module_state() == 'locked':
            self.log.error('Can not start eproc scan. Logic is already locked.')
            return -1

        self.n_step_x = 0
        self.n_step_y = 0
        self.n_step_z = 0
        self.check_ranges_motors()

        self.set_motor_parameters(self.x_motor_set_position, self.x_start, self.x_step, self.x_stop,
                                  self.y_motor_set_position, self.y_start, self.y_step, self.y_stop,
                                  self.z_motor_set_position, self.z_start, self.z_step, self.z_stop)

        self._x_motor.move(self.x_start)
        self._y_motor.move(self.y_start)
        self._z_motor.move(self.z_start)

        self.actual_x = self.x_start
        self.actual_y = self.y_start
        self.actual_z = self.z_start

        self.stopRequested = False
        self.stopNextSweepRequested = False

        # remaining_time = self.lia_waiting_time * self.number_of_accumulations * self.eproc_plot_x.size * self.number_of_sweeps

        # self.sigEprocRemainingTimeUpdated.emit(remaining_time, self.elapsed_sweeps)
        self.is_eproc_mapping_running = True
        param_dict = {'x_position': self.actual_x, 'y_position': self.actual_y, 'z_position': self.actual_z}
        self.sigParameterUpdated.emit(param_dict)
        self.sigStartNextEproc.emit()

        return 0

    def check_ranges_motors(self):
        """ Write the stop point as  start + n * step, where n is the number of steps."""
        # sigParameterUpdated.emit() is not present because this module is only called in start_eproc() and it is
        # placed before another method that calls sigParameterUpdated.emit()
        if self.x_start != self.x_stop:
            self.n_step_x = int(np.rint((self.x_stop - self.x_start) / self.x_step))
        self.x_stop = round(self.x_start + self.n_step_x * self.x_step, 4)
        if self.y_start != self.y_stop:
            self.n_step_y = int(np.rint((self.y_stop - self.y_start) / self.y_step))
        self.y_stop = round(self.y_start + self.n_step_y * self.y_step,4)
        if self.z_start != self.z_stop:
            self.n_step_z = int(np.rint((self.z_stop - self.z_start) / self.z_step))
        self.z_stop = round(self.z_start + self.n_step_z * self.z_step, 4)
        return

    def _next_position(self):
        self.save_eproc_data_mapping()

        if self.actual_x == self.x_stop:
            self.actual_x = self.x_start
            if self.actual_y == self.y_stop:
                self.actual_y = self.y_start
                if self.actual_z == self.z_stop:
                    self.actual_z = self.z_start
                    self.stopRequested = True
                    self.is_eproc_mapping_running = False
                else:
                    self.actual_z = self.actual_z + self.z_step

            else:
                self.actual_y = self.actual_y + self.y_step
        else:
            self.actual_x = self.actual_x + self.x_step

        self._x_motor.move(self.actual_x)
        self._y_motor.move(self.actual_y)
        self._z_motor.move(self.actual_z)

        param_dict = {'x_position': self.actual_x, 'y_position': self.actual_y, 'z_position': self.actual_z}
        self.sigParameterUpdated.emit(param_dict)
        self.sigStartNextEproc.emit()
        return

    def save_eproc_data_mapping(self):
        """ Saves the current eproc data to a file."""

        filepath = self._save_logic.get_path_for_module(module_name='eproc')

        # Data, on which the average on accumulations and sweeps was performed

        eproc_data_list = [self.eproc_plot_x]

        for channel in range(len(self.eproc_raw_data[0, 0, 0, :])):
            eproc_data_list.append(self.eproc_plot_y[:, channel])

        eproc_data = OrderedDict()
        parameters = OrderedDict()

        if self.is_ms:
            eproc_data['Frequency\t\tChannel 1\t\tChannel 2\t\tChannel 3\t\tChannel 4'] = np.array(
                eproc_data_list).transpose()

            if not os.path.isfile(os.path.join(filepath, self.tag)):
                # Saving parameters as str for readability
                parameters['Magnetic Field (G)'] = str(self.ms_field)
                parameters['Microwave Power (dBm)'] = str(self.ms_mw_power)
                parameters['Start Frequency (Hz)'] = str(self.ms_start)
                parameters['Step Size (Hz)'] = str(self.ms_step)
                parameters['Stop Frequency (Hz)'] = str(self.ms_stop)
        else:
            eproc_data['Field\t\tChannel 1\t\tChannel 2\t\tChannel 3\t\tChannel 4'] = np.array(
                eproc_data_list).transpose()
            if not os.path.isfile(os.path.join(filepath, self.tag)):
                # Saving parameters as str for readability
                parameters['Microwave Frequency (Hz)'] = str(self.fs_mw_frequency)
                parameters['Microwave Power (dBm)'] = str(self.fs_mw_power)
                parameters['Start Field (Hz)'] = str(self.fs_start)
                parameters['Step Size (Hz)'] = str(self.fs_step)
                parameters['Stop Field (Hz)'] = str(self.fs_stop)

        if not os.path.isfile(os.path.join(filepath, self.tag)):
            # parameters['Duration Of The Experiment'] = time.strftime('%Hh%Mm%Ss', time.gmtime(self.measurement_duration))
            parameters['Elapsed Sweeps'] = self.elapsed_sweeps
            parameters['Accumulations Per Point'] = self.number_of_accumulations

            parameters['Lockin Input Range (V)'] = self.lia_range
            parameters['Lockin Amplitude (V)'] = str(self.lia_uac)
            parameters['Lockin Coupling'] = self.lia_coupling
            parameters['Lockin tau A (s)'] = str(self.lia_tauA)
            parameters['Lockin Phase A (°)'] = str(self.lia_phaseA)
            parameters['Lockin tau B (s)'] = str(self.lia_tauB)
            parameters['Lockin Phase B (°)'] = str(self.lia_phaseB)
            parameters['Lockin Waiting Time Factor'] = str(self.lia_waiting_time_factor)
            parameters['Lockin Harmonic'] = self.lia_harmonic
            parameters['Lockin Slope (dB/oct)'] = self.lia_slope
            parameters['Lockin Configuration'] = self.lia_configuration

            if self.is_lia_ext_ref:
                parameters['Modulation Signal Shape'] = self.ref_shape
                parameters['Modulation Frequency (Hz)'] = str(self.ref_freq)
                parameters['Modulation Deviation (Hz)'] = str(self.ref_deviation)
                parameters['Modulation Mode'] = self.ref_mode
            else:
                parameters['Lockin Internal Modulation Frequency (Hz)'] = self.lia_int_ref_freq

            parameters['n_x_pos'] = self.n_step_x + 1
            parameters['n_y_pos'] = self.n_step_y + 1
            parameters['n_z_pos'] = self.n_step_z + 1
            parameters['x_pos'] = self.actual_x
            parameters['y_pos'] = self.actual_y
            parameters['z_pos'] = self.actual_z

            self._save_logic.save_data(eproc_data,
                                       filepath=filepath,
                                       parameters=parameters,
                                       filename=self.tag,
                                       fmt='%.6e',
                                       delimiter='\t')

        else:

            parameters['x_pos'] = self.actual_x
            parameters['y_pos'] = self.actual_y
            parameters['z_pos'] = self.actual_z

            self._save_logic.save_data(eproc_data,
                                       filepath=filepath,
                                       parameters=parameters,
                                       filename=self.tag,
                                       fmt='%.6e',
                                       delimiter='\t')

        self.log.info('eproc data saved to:\n{0}'.format(filepath))
        return
