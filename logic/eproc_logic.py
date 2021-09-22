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

from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex
from core.connector import Connector
from core.configoption import ConfigOption
from core.statusvariable import StatusVar

class EPRoCLogic(GenericLogic):
    """This is the Logic class for EPRoC."""

    # declare connectors
    microwave1 = Connector(interface='MicrowaveInterface')
    lockin = Connector(interface='LockinInterface')
    savelogic = Connector(interface='SaveLogic')
    magnet = Connector(interface='EprocMagnetInterface')
    powersupply1 = Connector(interface='ProcessControlInterface')
    powersupply2 = Connector(interface='ProcessControlInterface')

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

    is_microwave_sweep = StatusVar('is_microwave_sweep', True)
    is_external_reference = StatusVar('is_external_reference', True)

    # Internal signals
    sigNextMeasure = QtCore.Signal()

    # Update signals, e.g. for GUI module
    sigParameterUpdated = QtCore.Signal(dict)
    sigOutputStateUpdated = QtCore.Signal(bool)
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
             4]     # writing it for 2 channels, but this should become a method get_lockin_channels of some sort
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
        # Connect signals
        self.sigNextMeasure.connect(self._next_measure, QtCore.Qt.QueuedConnection)
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

    def _initialize_eproc_plots(self):
        """ Initializing the EPRoC plots. """
        if self.is_microwave_sweep:
            self.eproc_plot_x = np.array(np.arange(self.ms_start, self.ms_stop + self.ms_step, self.ms_step))
        else:
            self.eproc_plot_x = np.array(np.arange(self.fs_start, self.fs_stop + self.fs_step, self.fs_step))
        self.eproc_plot_y = np.zeros([self.eproc_plot_x.size, 4]) # writing it for 4 channels, but this should become a method get_lockin_channels of some sort

        if self.is_microwave_sweep:
            self.sigEprocPlotsUpdated.emit(self.eproc_plot_x * self.frequency_multiplier, self.eproc_plot_y)
        else:
            self.sigEprocPlotsUpdated.emit(self.eproc_plot_x, self.eproc_plot_y)
        self.sigSetLabelEprocPlots.emit(self.is_microwave_sweep)
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
        # sigParameterUpdated.emit() is not present because this module is only called in start_eproc() and it is
        # placed before another method that calls sigParameterUpdated.emit()
        num_step = int(np.rint((self.ms_stop - self.ms_start) / self.ms_step))
        self.ms_stop = self.ms_start + num_step * self.ms_step
        num_step = int(np.rint((self.fs_stop - self.fs_start) / self.fs_step))
        self.fs_stop = self.fs_start + num_step * self.fs_step
        return

    def set_lia_parameters(self, input_range, uac, coupling, int_ref_freq, tauA, phaseA, tauB, phaseB, waiting_time_factor,
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
                      'lia_int_ref_freq': self.lia_int_ref_freq, 'lia_tauA': self.lia_tauA, 'lia_phaseA': self.lia_phaseA,
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
            # setting the values for the reference
            self.ref_shape, \
            self.ref_freq, \
            self.ref_mode, \
            self.ref_deviation = self._mw_device.set_reference(self.ref_shape, self.ref_freq, self.ref_mode, self.ref_deviation)
            error_code = self._lockin_device.change_reference('ext')
            # error_code = {0|1} where 0 means internal reference and 1 external reference
            # is this hardware dependent?
            if error_code == 0:
                self.log.error('Change of reference failed')
        return

    def lockin_ext_ref_off(self):
        if self.module_state() == 'locked':
            self.log.error('Can not change lockin reference. EPRoCLogic is already locked.')
        else:
            error_code = self._lockin_device.change_reference('int')
            if error_code == 1:
                self.log.error('Change of reference failed')
        return

    def set_ref_parameters(self, shape, freq, mode, dev):
        if self.module_state() != 'locked':
            if isinstance(freq, (int, float)) and isinstance(dev, (int, float)):
                self.ref_shape, self.ref_freq, self.ref_mode, self.ref_deviation  = self._mw_device.set_reference(shape, freq, mode, dev)

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

        param_dict = {'frequency_multiplier', self.frequency_multiplier}
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
        '''
        if self.module_state() == 'locked':
            self.log.error('Can not start microwave in CW mode. EPRoCLogic is already locked.')
        else:
            self.fs_mw_frequency, \
            self.fs_mw_power, \
            mode = self._mw_device.set_cw(self.fs_mw_frequency, self.fs_mw_power)
            param_dict = {'fs_mw_frequency': self.fs_mw_frequency, 'fs_mw_power': self.fs_mw_power}
            self.sigParameterUpdated.emit(param_dict)
            if mode != 'cw':
                self.log.error('Switching to CW microwave output mode failed.')
            else:
                err_code = self._mw_device.cw_on()
                if err_code < 0:
                    self.log.error('Activation of microwave output failed.')
        '''
        self.fs_mw_frequency, \
        self.fs_mw_power, \
        mode = self._mw_device.set_cw(self.fs_mw_frequency, self.fs_mw_power)
        param_dict = {'fs_mw_frequency': self.fs_mw_frequency, 'fs_mw_power': self.fs_mw_power}
        self.sigParameterUpdated.emit(param_dict)
        if mode != 'cw':
            self.log.error('Switching to CW microwave output mode failed.')
        else:
            err_code = self._mw_device.cw_on()
            if err_code < 0:
                self.log.error('Activation of microwave output failed.')

        mode, is_running = self._mw_device.get_status()
        return mode, is_running

    def mw_off(self):
        """ Switching off the MW source.

        @return str, bool: active mode ['cw', 'list', 'sweep'], is_running
        """
        error_code = self._mw_device.off()
        if error_code < 0:
            self.log.error('Switching off microwave source failed.')

        mode, is_running = self._mw_device.get_status()
        return mode, is_running

    def modulation_on(self):
        self._mw_device.reference_on()
        return

    def modulation_off(self):
        self._mw_device.reference_off()
        return

    def start_eproc(self):
        with self.threadlock:
            if self.module_state() == 'locked':
                self.log.error('Can not start EPRoC scan. Logic is already locked.')
                return -1

            mode, is_running = self._mw_device.get_status()
            if not is_running:
                self.log.error('The scan cannot be started while the microwave is off')

            self.check_ranges()
            if self.is_microwave_sweep:
                self.ms_start, self.ms_step, self.ms_stop, self.ms_field, self.ms_mw_power = \
                    self.set_ms_parameters(self.ms_start, self.ms_step, self.ms_stop, self.ms_field, self.ms_mw_power)
                self.ms_actual_frequency = self.ms_start
            else:
                self.fs_start, self.fs_step, self.fs_stop, self.fs_mw_frequency, self.fs_mw_power = \
                    self.set_fs_parameters(self.fs_start, self.fs_step, self.fs_stop, self.fs_mw_frequency, self.fs_mw_power)
                self.fs_actual_field = self.fs_start

            # can be modified, look at lockin manual
            if self.lia_tauB > self.lia_tauA:
                self.lia_waiting_time = self.lia_tauB * self.lia_waiting_time_factor    # in seconds
            else:
                self.lia_waiting_time = self.lia_tauA * self.lia_waiting_time_factor

            self.elapsed_sweeps = 0
            self.elapsed_accumulations = 0
            self.actual_index = 0    # maybe this could be called elapsed_index to be coherent, but I think there should be some changes in the rest of the code then

            remaining_time = self.lia_waiting_time * self.number_of_accumulations * self.eproc_plot_x.size * self.number_of_sweeps
            self._startTime = time.time()


            # if self.is_external_reference:
            #     self._mw_device.reference_on()
            # mode, is_running = self.mw_on()
            # if not is_running:
            #     self.module_state.unlock()
            #     return -1

            self._initialize_eproc_plots()
            self.eproc_raw_data = np.zeros(
                [self.number_of_sweeps,
                self.number_of_accumulations,
                self.eproc_plot_x.size,
                4]  # number of channels {2 or 4}
            )

            self.module_state.lock()
            self.stopRequested = False
            self.stopNextSweepRequested = False
            # self.fc.clear_result()

            self.sigEprocRemainingTimeUpdated.emit(remaining_time, self.elapsed_sweeps)
            self.sigOutputStateUpdated.emit(is_running)
            self.sigNextMeasure.emit()
            return 0

    def stop_eproc(self):
        """ Stop the EPRoC scan.

        @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.module_state() == 'locked':
                self.stopRequested = True
        return 0

    def stop_eproc_next_sweep(self):
        """ Stop the EPRoC scan.

        @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.module_state() == 'locked':
                self.stopNextSweepRequested = True
        return 0

    def _next_measure(self):
        with self.threadlock:
            if self.module_state() != 'locked':
                return

            if self.stopRequested:
                self.stopRequested = False
                self.measurement_duration = time.time() - self._startTime
                # self.mw_off()
                # if self.is_external_reference:
                #     self._mw_device.reference_off()
                self.module_state.unlock()
                self.sigOutputStateUpdated.emit(False)
                return

            time.sleep(self.lia_waiting_time)
            self.eproc_raw_data[self.elapsed_sweeps, self.elapsed_accumulations, self.actual_index,
                                :] = self._lockin_device.get_data_lia()[:4] #this is for 4 channels
            # sometimes the lia returns values that are really close to zero and not the real values.
            # the measurement is performed again in that case
            for i in range(len(self.eproc_raw_data[0, 0, 0, :])):
                while self.eproc_raw_data[self.elapsed_sweeps, self.elapsed_accumulations, self.actual_index, i] < 1e-7:
                    time.sleep(0.01)
                    self.eproc_raw_data[self.elapsed_sweeps, self.elapsed_accumulations, self.actual_index,
                                        :] = self._lockin_device.get_data_lia()[:4]  # this is for 4 channels

            '''
            if error:
                self.stopRequested = True
                self.sigNextLine.emit()
                return
            '''

            self.elapsed_accumulations += 1

            remaining_time = self.lia_waiting_time * (
                    self.number_of_accumulations * self.eproc_plot_x.size * self.number_of_sweeps - (
                        self.elapsed_accumulations + self.number_of_accumulations * self.actual_index +
                        self.number_of_accumulations * self.eproc_plot_x.size * self.elapsed_sweeps))

            if self.elapsed_accumulations == self.number_of_accumulations:
                # average over accumulations for the current frequency and the current sweep
                new_value = np.mean(self.eproc_raw_data[self.elapsed_sweeps, :, self.actual_index, :],
                                    axis=0,     #axis = 0 in this case means an average over accumulations
                                    dtype=np.float64)

                self.eproc_plot_y[self.actual_index, :] = (self.eproc_plot_y[self.actual_index, :] *
                                                           self.elapsed_sweeps + new_value) / (self.elapsed_sweeps + 1)

                self.elapsed_accumulations = 0

                # I can move this to the end of the method, can't I?
                self.sigEprocPlotsUpdated.emit(self.eproc_plot_x * self.frequency_multiplier, self.eproc_plot_y)

                # understand where to put this: at the start or end?
                if self.actual_index == self.eproc_plot_x.size - 1:
                    if self.is_microwave_sweep:
                        # this is going to go at the end
                        self.ms_actual_frequency = self.ms_start
                    else:
                        self.fs_actual_field = self.fs_start
                    self.elapsed_sweeps += 1
                    self.actual_index = 0
                    if self.elapsed_sweeps == self.number_of_sweeps or self.stopNextSweepRequested:
                        # stop scan or stop requested
                        self.stopRequested = True
                else:
                    if self.is_microwave_sweep:
                        self.ms_actual_frequency, self.ms_mw_power, mode = self._mw_device.set_cw(
                            self.ms_actual_frequency + self.ms_step, self.ms_mw_power)
                    else:
                        self.fs_actual_field = self._magnet.set_central_field(self.fs_actual_field + self.fs_step)
                    self.actual_index += 1
            # here is the old method, where we update the all eproc_plot_y array at each frequency
            '''
            # the average of the last line is the same for evey value of elapsed_sweeps
            average_last_line = np.mean(self.eproc_raw_data[self.elapsed_sweeps, :, :self.actual_index + 1, :], axis=0) #axis = 0 in this case means an average over accumulations

            # if elapsed_sweeps == 0: we are done, the values at frequency larger than the one we are at are going
            # to stay equal to zero
            if self.elapsed_sweeps == 0:

                # average_last_line is shorter than eproc_plot_y, therefore we need this for cycle
                for i in range(len(average_last_line)):
                    self.eproc_plot_y[i, :] = average_last_line[i, :]

            # if elapsed_sweeps > 0 then we have to deal with the previous lines as well
            else:

                # here we average over all frequency indexes
                average_previous_sweeps = np.mean(self.eproc_raw_data[:self.elapsed_sweeps, :, :, :],
                                              axis=(0, 1))

                # we start from the previous averages and then update the indexes that are also in the last line
                self.eproc_plot_y = average_previous_sweeps
                for i in range(len(average_last_line)):
                    self[i] = (average_previous_sweeps[i] * self.elapsed_sweeps + average_last_line[i]) / (self.elapsed_sweeps + 1)
            '''
            self.sigEprocRemainingTimeUpdated.emit(remaining_time, self.elapsed_sweeps)
            self.sigNextMeasure.emit()
            return

    def get_hw_constraints(self):
        """ Return the names of all ocnfigured fit functions.
        @return object: Hardware constraints object
        """
        constraints = self._mw_device.get_limits()
        return constraints

    def get_time_constants(self):
        return self._lockin_device.tau_values

    def save_eproc_data(self, tag=None):
        """ Saves the current EPRoC data to a file."""
        timestamp = datetime.datetime.now()
        filepath = self._save_logic.get_path_for_module(module_name='EPRoC')

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
            # If the measurement was interrupted: we want to include also the last sweep, which is not complete
            # This sweep is the sweep number (self.elapsed_sweep+1)
            for sweep in range(self.elapsed_sweeps+1):
                eproc_raw_data_list.append(np.mean(self.eproc_raw_data[sweep, :, :, channel],
                                                   axis=0,     #axis = 0 in this case means an average over accumulations
                                                   dtype=np.float64))
                # If the measurement was complete (no interruption) then self.elapsed_sweeps == self.number_of_sweeps
                # Thus if sweep == self.number_of_sweeps we have to break the for cycle
                if sweep == self.number_of_sweeps:
                    break

        eproc_data = OrderedDict()
        eproc_raw_data = OrderedDict()
        parameters = OrderedDict()

        if self.is_microwave_sweep:
            eproc_data['Frequency\t\tChannel 1\t\tChannel 2\t\tChannel 3\t\tChannel 4'] = np.array(eproc_data_list).transpose()
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
            eproc_data['Field\t\tChannel 1\t\tChannel 2\t\tChannel 3\t\tChannel 4'] = np.array(eproc_data_list).transpose()
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
            parameters['Microwave Frequency (Hz)'] = str(self.fs_mw_frequency)
            parameters['Microwave Power (dBm)'] = str(self.fs_mw_power)
            parameters['Start Field (G)'] = str(self.fs_start)
            parameters['Step Size (G)'] = str(self.fs_step)
            parameters['Stop Field (G)'] = str(self.fs_stop)

        parameters['Duration Of The Experiment'] = time.strftime('%Hh%Mm%Ss', time.gmtime(self.measurement_duration))
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

        parameters['Frequency Multiplier'] = self.frequency_multiplier

        if self.is_external_reference:
            parameters['Modulation Signal Shape'] = self.ref_shape
            parameters['Modulation Frequency (Hz)'] = str(self.ref_freq)
            parameters['Modulation Deviation (Hz)'] = str(self.ref_deviation)
            parameters['Modulation Mode'] = self.ref_mode
        else:
            parameters['Lockin Internal Modulation Frequency (Hz)'] = self.lia_int_ref_freq

        self._save_logic.save_data(eproc_data,
                                   filepath=filepath,
                                   parameters=parameters,
                                   filename=tag+ending,
                                   fmt='%.6e',
                                   delimiter='\t')

        self._save_logic.save_data(eproc_raw_data,
                                   filepath=filepath,
                                   parameters=parameters,
                                   filename=tag_raw+ending,
                                   fmt='%.6e',
                                   delimiter='\t')

        self.log.info('EPRoC data saved to:\n{0}'.format(filepath))
        return
