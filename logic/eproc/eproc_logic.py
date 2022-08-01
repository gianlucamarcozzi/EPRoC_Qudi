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

    # config option
    mw_scanmode = ConfigOption(
        'scanmode',
        'SWEEP',
        missing='warn',
        converter=lambda x: MicrowaveMode[x.upper()])

    # Number of total sweeps and total accumulations. Not to confuse with the elapsed quantities.
    n_sweep = StatusVar('n_sweep', 1)
    n_accumulation = StatusVar('n_accumulation', 10)

    # Parameters for frequency sweep (acronym fs)
    fs_field = StatusVar('fs_field', 3480.)
    fs_mw_power = StatusVar('fs_mw_power', -30)
    fs_start = StatusVar('fs_start', 2800e6)
    fs_stop = StatusVar('fs_stop', 2950e6)
    fs_step = StatusVar('fs_step', 2e6)

    # Parameters for magnetic field B0 sweep (acronym bs)
    bs_frequency = StatusVar('bs_frequency', 2870e6)
    bs_mw_power = StatusVar('bs_mw_power', -30)
    bs_start = StatusVar('bs_start', 3400.)
    bs_stop = StatusVar('bs_stop', 3500.)
    bs_step = StatusVar('bs_step', 1.)

    # Change these initial values
    lia_range = StatusVar('lia_range', '0.1')
    lia_uac = StatusVar('lia_uac', 0)
    lia_coupling = StatusVar('lia_coupling', 'ac')
    lia_int_freq = StatusVar('lia_int_freq', 0)
    lia_tauA = StatusVar('lia_tauA', 0.1)
    lia_phaseA = StatusVar('lia_phaseA', 0)
    lia_tauB = StatusVar('lia_tauB', 0.0005)
    lia_phaseB = StatusVar('lia_phaseB', 0)
    lia_waiting_time_factor = StatusVar('lia_waiting_time_factor', 1)
    lia_harmonic = StatusVar('lia_harmonic', '1')
    lia_slope = StatusVar('lia_slope', '6')
    lia_configuration = StatusVar('lia_configuration', 'A&B')

    # Parameters for reference signal from microwave hardware (ref)
    ref_freq = StatusVar('ref_freq', 1000000)
    ref_mode = StatusVar('ref_mode', 'HBAN')
    ref_dev = StatusVar('ref_dev', 1000)

    f_multiplier = StatusVar('f_multiplier', 32)

    psb_voltage_outp1 = StatusVar('psb_voltage_oup2', 2)
    psb_voltage_outp2 = StatusVar('psb_voltage_outp2', 2)
    psb_current_max_outp1 = StatusVar('psb_voltage_current_max_outp1', 0.1)
    psb_current_max_outp2 = StatusVar('psb_voltage_current_max_outp2', 0.1)

    psa_voltage_outp1 = StatusVar('psa_voltage_oup2', 2)
    psa_voltage_outp2 = StatusVar('psa_voltage_outp2', 2)
    psa_current_max_outp1 = StatusVar('psa_voltage_current_max_outp1', 0.1)
    psa_current_max_outp2 = StatusVar('psa_voltage_current_max_outp2', 0.1)

    is_fs = StatusVar('is_fs', True)    # True if microwave sweep is set, false if magnetic field sweep is set
    is_lia_ext_ref = StatusVar('is_lia_ext_ref', True)

    # Internal signals
    sigNextDataPoint = QtCore.Signal()

    # Update signals, e.g. for GUI module
    sigParameterUpdated = QtCore.Signal(dict)
    sigStatusUpdated = QtCore.Signal()
    sigEprocPlotsUpdated = QtCore.Signal(np.ndarray, np.ndarray)
    sigSetLabelEprocPlots = QtCore.Signal()
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
        self._lia_device = self.lockin()
        self._save_logic = self.savelogic()
        self._magnet = self.magnet()
        self._psb = self.powersupply1()     # Power supply board
        self._psa = self.powersupply2()     # Power supply amplifier

        # Get hardware constraints
        limits = self.get_hw_constraints()

        # Set/recall microwave source parameters
        self.bs_frequency = limits.frequency_in_range(self.bs_frequency)
        self.bs_mw_power = limits.power_in_range(self.bs_mw_power)
        self.fs_mw_power = limits.power_in_range(self.fs_mw_power)

        # Elapsed measurement time and number of sweeps
        self.elapsed_time = 0.0
        self.elapsed_sweeps = 0
        self.elapsed_accumulations = 0

        self.is_eproc_running = False

        # Set flag for stopping a measurement
        self.stopRequested = False
        self.stopNextSweepRequested = False

        # Initalize the data arrays
        self._initialize_eproc_plots()
        # Raw data array
        self.eproc_raw_data = np.zeros(
             [self.n_accumulation,
             self.n_sweep,
             self.eproc_plot_x.size,
             4]  # for 4 channels, but this should become a method get_lockin_channels of some sort
        )

        # Switch off microwave and set CW frequency and power
        self.mw_off()

        # Set only the continuous values
        self.set_fs_parameters(self.fs_start, self.fs_step, self.fs_stop, self.fs_field, self.fs_mw_power, 0)
        self.set_bs_parameters(self.bs_start, self.bs_step, self.bs_stop, self.bs_frequency, self.bs_mw_power, 0)

        self.set_lia_parameters(self.lia_range, self.lia_uac, self.lia_coupling, self.lia_int_freq, self.lia_tauA,
                                self.lia_phaseA, self.lia_tauB, self.lia_phaseB, self.lia_waiting_time_factor,
                                self.lia_harmonic, self.lia_slope, self.lia_configuration)

        self.set_ref_parameters(self.ref_freq, self.ref_dev, self.ref_mode)
        self.set_eproc_scan_parameters(self.n_sweep, self.n_accumulation)
        self.set_psb_parameters(self.psb_voltage_outp1, self.psb_voltage_outp2,
                                self.psb_current_max_outp1, self.psb_current_max_outp2)
        self.set_psa_parameters(self.psa_voltage_outp1, self.psa_voltage_outp2,
                                self.psa_current_max_outp1, self.psa_current_max_outp2)

        # Connect signals
        self.sigNextDataPoint.connect(self._next_data_point, QtCore.Qt.QueuedConnection)
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
        self.sigNextDataPoint.disconnect()

    def get_hw_constraints(self):
        """ Return the names of all ocnfigured fit functions.
        @return object: Hardware constraints object
        """
        constraints = self._mw_device.get_limits()
        return constraints

    def get_time_constants(self):
        return self._lia_device.tau_values

    def _initialize_eproc_plots(self):
        """ Initializing the eproc plots. """
        if self.is_fs:
            self.eproc_plot_x = np.array(np.arange(self.fs_start, self.fs_stop + self.fs_step, self.fs_step))
        else:
            self.eproc_plot_x = np.array(np.arange(self.bs_start, self.bs_stop + self.bs_step, self.bs_step))
        self.eproc_plot_y = np.zeros([self.eproc_plot_x.size, 4])

        self.sigEprocPlotsUpdated.emit(self.eproc_plot_x, self.eproc_plot_y)
        self.sigSetLabelEprocPlots.emit()
        return

    def fs_on(self):
        if self.module_state() == 'locked':
            self.log.error('Can not change to microwave sweep. EPRoCLogic is already locked.')
        else:
            self.set_fs_parameters(self.fs_start, self.fs_step, self.fs_stop, self.fs_field, self.fs_mw_power, 0)
            self.is_fs = True
            self.sigStatusUpdated.emit()
        return

    def bs_on(self):
        if self.module_state() == 'locked':
            self.log.error('Can not change to field sweep. EPRoCLogic is already locked.')
        else:
            self.set_bs_parameters(self.bs_start, self.bs_step, self.bs_stop, self.bs_frequency, self.fs_mw_power, 0)
            self.is_fs = False
            self.sigStatusUpdated.emit()
        return

    def set_fs_parameters(self, start, step, stop, field, power, freq_pos):
        """ Set the desired parameters for a microwave sweep. This means that start, step and stop refer to the
        microwave.
        """
        limits = self.get_hw_constraints()

        if self.module_state() != 'locked':
            if (isinstance(start, (int, float)) and isinstance(step, (int, float))
                    and isinstance(stop, (int, float)) and isinstance(field, (int, float))
                    and isinstance(power, (int, float)) and isinstance(freq_pos, (int, float))):
                # power = limits.power_in_range(power)
                self.fs_start = limits.frequency_in_range(start)
                self.fs_step = limits.sweep_step_in_range(step)
                if stop <= start:
                    stop = start + step
                self.fs_stop = limits.frequency_in_range(stop)
                if freq_pos == 0:
                    self.fs_start, self.fs_mw_power, _ = self._mw_device.set_cw(self.fs_start, self.fs_mw_power)
                elif freq_pos == 1:
                    center = (self.fs_start + self.fs_stop)/2
                    _, self.fs_mw_power, _ = self._mw_device.set_cw(center, self.fs_mw_power)
                elif freq_pos == 2:
                    self.fs_stop, self.fs_mw_power, _ = self._mw_device.set_cw(self.fs_stop, self.fs_mw_power)

                # This should be changed when the methods to check field limits is implemented
                self.fs_field = self._magnet.set_central_field(field)
            else:
                self.log.warning('set_fs_parameters failed. One value is not int or float.')
        else:
            self.log.warning('set_fs_parameters failed. Logic is locked.')

        param_dict = {'fs_start': self.fs_start, 'fs_stop': self.fs_stop, 'fs_step': self.fs_step,
                      'fs_mw_power': self.fs_mw_power, 'fs_field': self.fs_field}
        self.sigParameterUpdated.emit(param_dict)
        return self.fs_start, self.fs_step, self.fs_stop, self.fs_field, self.fs_mw_power

    def set_bs_parameters(self, start, step, stop, frequency, power, field_pos):
        # To fix: use limits, like in set_fs_mw_frequency
        if self.module_state() != 'locked':
            limits = self.get_hw_constraints()
            if (isinstance(start, (int, float)) and isinstance(step, (int, float))
                    and isinstance(stop, (int, float)) and isinstance(frequency, (int, float))
                    and isinstance(power, (int, float)) and isinstance(field_pos, (int, float))):                # Change when there will be magnet contraints
                self.bs_start = start
                if stop <= start:
                    stop = start + step
                self.bs_stop = stop
                self.bs_step = step
                if field_pos == 0:
                    self.bs_start = self._magnet.set_central_field(self.bs_start)
                elif field_pos == 1:
                    center = (self.bs_start + self.bs_stop) / 2
                    self._magnet.set_central_field(center)
                elif field_pos == 2:
                    self.bs_stop = self._magnet.set_central_field(self.bs_stop)

                frequency = limits.frequency_in_range(frequency)
                power = limits.power_in_range(power)
                self.bs_frequency, self.bs_mw_power, _ = self._mw_device.set_cw(frequency, power)
            else:
                self.log.warning('set_bs_parameters failed. One value is not int or float.')
        else:
            self.log.warning('set_bs_parameters failed. Logic is locked.')

        param_dict = {'bs_start': self.bs_start, 'bs_stop': self.bs_stop, 'bs_step': self.bs_step,
                      'bs_frequency': self.bs_frequency, 'bs_mw_power': self.bs_mw_power}
        self.sigParameterUpdated.emit(param_dict)
        return self.bs_start, self.bs_step, self.bs_stop, self.bs_frequency, self.bs_mw_power

    def _check_range(self):
        """
        Write the stop point as  start + n * step, where n is the number of steps
        """
        limits = self.get_hw_constraints()
        # sigParameterUpdated.emit() is not present because this module is only called in start_eproc() and it is
        # placed before another method that calls sigParameterUpdated.emit()
        num_step = int(np.rint((self.fs_stop - self.fs_start) / self.fs_step))
        self.fs_stop = self.fs_start + num_step * self.fs_step
        num_step = int(np.rint((self.bs_stop - self.bs_start) / self.bs_step))
        self.bs_stop = self.bs_start + num_step * self.bs_step
        return

    def set_lia_parameters(self, input_range, uac, coupling, int_ref_freq, tauA, phaseA, tauB, phaseB,
                           waiting_time_factor, harmonic, slope, configuration):
        if self.module_state() != 'locked':
            if isinstance(uac, (int, float)) and isinstance(int_ref_freq, (int, float)) \
                    and isinstance(phaseA, (int, float)) and isinstance(phaseB, (int, float)) \
                    and isinstance(waiting_time_factor, (int, float)) and waiting_time_factor > 0:
                self.lia_range = self._lia_device.set_input_range(input_range)
                self.lia_uac = self._lia_device.set_amplitude(uac)
                self.lia_coupling = self._lia_device.set_coupling_type(coupling)
                self.lia_int_freq = self._lia_device.set_frequency(int_ref_freq)
                self.lia_tauA, self.lia_tauB = self._lia_device.set_time_constants(tauA, tauB)
                self.lia_phaseA, self.lia_phaseB = self._lia_device.set_phases(phaseA, phaseB)
                self.lia_waiting_time_factor = waiting_time_factor
                self.lia_harmonic = self._lia_device.set_harmonic(harmonic)
                self.lia_slope = self._lia_device.set_rolloff(slope)
                self.lia_configuration = self._lia_device.set_input_config(configuration)
            else:
                self.log.warning('set_lia_parameters failed. At least one value is not of the correct type.')
        else:
            self.log.warning('set_lia_parameters failed. The logic is locked.')
        # not updating tau value for now because the indexes are useful for the gui and the value for the logic,
        # im giving it the value for now
        param_dict = {'lia_range': self.lia_range, 'lia_uac': self.lia_uac, 'lia_coupling': self.lia_coupling,
                      'lia_int_freq': self.lia_int_freq, 'lia_tauA': self.lia_tauA,
                      'lia_phaseA': self.lia_phaseA,
                      'lia_tauB': self.lia_tauB, 'lia_phaseB': self.lia_phaseB,
                      'lia_waiting_time_factor': self.lia_waiting_time_factor, 'lia_harmonic': self.lia_harmonic,
                      'lia_slope': self.lia_slope, 'lia_configuration': self.lia_configuration}
        self.sigParameterUpdated.emit(param_dict)
        return self.lia_range, self.lia_uac, self.lia_coupling, self.lia_int_freq, self.lia_tauA, self.lia_tauB, \
               self.lia_phaseA, self.lia_phaseB, self.lia_waiting_time_factor, self.lia_harmonic, self.lia_slope, \
               self.lia_configuration

    def lia_ext_ref_on(self):
        if self.module_state() == 'locked':
            self.log.error('Can not change lockin reference. EPRoCLogic is already locked.')
        else:
            error_code = self._lia_device.change_reference('ext')
            # error_code = {0|1} where 0 means internal reference and 1 external reference
            # is this hardware dependent?
            if error_code == 0:
                self.log.error('Change of reference failed')
            else:
                self.set_ref_parameters(self.ref_freq, self.ref_dev, self.ref_mode)
                self.is_lia_ext_ref = True
            self.sigStatusUpdated.emit()
        return

    def lia_ext_ref_off(self):
        if self.module_state() == 'locked':
            self.log.error('Can not change lockin reference. EPRoCLogic is already locked.')
        else:
            error_code = self._lia_device.change_reference('int')
            if error_code == 1:
                self.log.error('Change of reference failed')
            else:
                self.is_lia_ext_ref = False
            self.sigStatusUpdated.emit()
        return

    def set_ref_parameters(self, freq, dev, mode):
        if self.module_state() != 'locked':
            if isinstance(freq, (int, float)) and isinstance(dev, (int, float)):
                self.ref_freq, self.ref_dev, self.ref_mode, _ = self._mw_device.set_reference(
                    freq, dev, mode)

        param_dict = {'ref_freq': self.ref_freq, 'ref_dev': self.ref_dev,
                      'ref_mode': self.ref_mode}
        self.sigParameterUpdated.emit(param_dict)
        return self.ref_freq, self.ref_dev, self.ref_mode

    def set_eproc_scan_parameters(self, n_sweep, n_accumulation):
        if self.module_state() != 'locked':
            if isinstance(n_sweep, int) and isinstance(n_accumulation, int):
                self.n_sweep = n_sweep
                self.n_accumulation = n_accumulation
        else:
            self.log.warning('set_eproc_scan_parameters failed. Logic is either locked or input value is '
                             'no integer.')

        param_dict = {'n_sweep': self.n_sweep,
                      'n_accumulation': self.n_accumulation}
        self.sigParameterUpdated.emit(param_dict)
        return self.n_sweep, self.n_accumulation

    def set_frequency_multiplier(self, multiplier):
        if self.module_state() != 'locked':
            self.f_multiplier = multiplier
        else:
            self.log.warning('set_frequency_multiplier failed. Logic is locked.')

        param_dict = {'f_multiplier': self.f_multiplier}
        self.sigParameterUpdated.emit(param_dict)
        return self.f_multiplier

    def psb_on(self):
        if self.module_state() != 'locked':
            status = self._psb.output_on()
            if status != 1:
                self.log.warning('psb_on failed. psb is still turned off.')
        else:
            self.log.warning('psb_on failed. Logic is locked.')
        return

    def psb_off(self):
        if self.module_state() != 'locked':
            status = self._psb.output_off()
            if status == 1:
                self.log.warning('psb_off failed. psb is still turned on.')
        else:
            self.log.warning('psb_off failed. Logic is locked.')
        return

    def set_psb_parameters(self, v1, v2, maxi1, maxi2):
        if self.module_state() != 'locked':
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)) and isinstance(maxi1, (int, float)) and \
                    isinstance(maxi1, (int, float)) and not v1 < 0 and not v2 < 0 and not maxi1 < 0 and not maxi2 < 0:
                self.psb_voltage_outp1 = self._psb.set_control_value(v1, 1)
                self.psb_current_max_outp1 = self._psb.set_current_max(maxi1, 1)
                self.psb_voltage_outp2 = self._psb.set_control_value(v2, 2)
                self.psb_current_max_outp2 = self._psb.set_current_max(maxi2, 2)
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
            self._psa.output_on()
        else:
            self.log.warning('psa_on failed. Logic is locked.')
        return

    def psa_off(self):
        if self.module_state() != 'locked':
            self._psa.output_off()
        else:
            self.log.warning('psa_off failed. Logic is locked.')
        return

    def set_psa_parameters(self, v1, v2, maxi1, maxi2):
        if self.module_state() != 'locked':
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)) and isinstance(maxi1, (int, float)) and \
                    isinstance(maxi1, (int, float)) and not v1 < 0 and not v2 < 0 and not maxi1 < 0 and not maxi2 < 0:
                self.psa_voltage_outp1 = self._psa.set_control_value(v1, 1)
                self.psa_current_max_outp1 = self._psa.set_current_max(maxi1, 1)
                self.psa_voltage_outp2 = self._psa.set_control_value(v2, 2)
                self.psa_current_max_outp2 = self._psa.set_current_max(maxi2, 2)
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
        self.bs_frequency, self.bs_mw_power, mode = self._mw_device.set_cw(self.bs_frequency, self.bs_mw_power)
        param_dict = {'bs_frequency': self.bs_frequency, 'bs_mw_power': self.bs_mw_power}
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

    def _set_frequency_sweep(self):
        """
        Switching on the mw source in list/sweep mode.

        @return str, bool: active mode ['cw', 'list', 'sweep'], is_running
        """
        limits = self.get_hw_constraints()
        if np.abs(self.fs_stop - self.fs_start)/self.fs_step >= limits.sweep_maxentries:
            self.log.warning('Number of frequency steps too large for microwave device. '
                             'Lowering resolution to fit the maximum length.')
            self.fs_step = np.abs(self.fs_stop - self.fs_start)/(limits.list_maxentries - 1)

        sweep_return = self._mw_device.set_sweep(
            self.fs_start, self.fs_stop, self.fs_step, self.fs_mw_power)
        self.fs_start, self.fs_stop, self.fs_step, self.fs_mw_power, mode = sweep_return

        self._mw_device.set_int_trigger()
        param_dict = {'fs_start': self.fs_start, 'fs_stop': self.fs_stop,
                      'fs_step': self.fs_step, 'fs_mw_power': self.fs_mw_power}

        self.sigParameterUpdated.emit(param_dict)

        '''
        if mode != 'list' and mode != 'sweep':
            self.log.error('Switching to list/sweep microwave output mode failed.')
        elif self.mw_scanmode == MicrowaveMode.SWEEP:
            err_code = self._mw_device.sweep_on()
            if err_code < 0:
                self.log.error('Activation of microwave output failed.')
        else:
            err_code = self._mw_device.list_on()
            if err_code < 0:
                self.log.error('Activation of microwave output failed.')

        mode, is_running = self._mw_device.get_status()
        self.sigOutputStateUpdated.emit(mode, is_running)
        '''
        return

    def _set_field_sweep(self):
        sweep_return = self._magnet.set_sweep(self.bs_start, self.bs_stop, self.bs_step)
        self.bs_start, self.bs_stop, self.bs_step = sweep_return

        param_dict = {'bs_start': self.bs_start, 'bs_stop': self.bs_stop,
                      'bs_step': self.bs_step}

        self.sigParameterUpdated.emit(param_dict)

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

            # Set the checked parameters and update them if they are wrong
            if self.is_fs:
                self._set_frequency_sweep()
                self.fs_field = self._magnet.set_central_field(self.fs_field)
            else:
                self._set_field_sweep()
                self.bs_frequency, self.bs_mw_power, _ = self._mw_device.set_cw(self.bs_frequency, self.bs_mw_power)

            tau = max(self.lia_tauA, self.lia_tauB)
            self.lia_waiting_time = tau * self.lia_waiting_time_factor  # in seconds

            self.elapsed_sweeps = 0
            self.elapsed_accumulations = 0
            self.elapsed_x = 0  # Index along x-axis (either frequency or field)

            self._initialize_eproc_plots()
            self.eproc_raw_data = np.zeros(
                [self.n_accumulation,
                 self.n_sweep,
                 self.eproc_plot_x.size,
                 4]  # number of channels
            )

            self.module_state.lock()
            self.stopRequested = False
            self.stopNextSweepRequested = False
            # self.fc.clear_result()

            self._update_remaining_time()
            self._startTime = time.time()
            self.is_eproc_running = True
            self._trigger_next_x()
            self.sigStatusUpdated.emit()
            self.sigNextDataPoint.emit()
            return 0

    def stop_eproc(self):
        """ Stop the eproc scan.

        @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.module_state() == 'locked':
                self.stopRequested = True
        return 0

    def stop_eproc_next_sweep(self):
        """ Stop the eproc scan.

        @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.module_state() == 'locked':
                self.stopNextSweepRequested = True
        return 0

    def _next_data_point(self):
        """ Gets the new data from the lia. This counts as one accumulation."""
        with self.threadlock:
            if self.module_state() != 'locked':
                return

            if self.stopRequested:
                self.stopRequested = False
                self.is_eproc_running = False
                self.measurement_duration = time.time() - self._startTime
                self.module_state.unlock()
                self.sigStatusUpdated.emit()
                return

            # Between two accumulations on the same point wait for an arbitrary value of tau/10
            time.sleep(self.lia_waiting_time)
            self._get_data_lia()
            self._set_new_x_value()

            self._update_remaining_time()
            self.sigEprocPlotsUpdated.emit(self.eproc_plot_x, self.eproc_plot_y)
            self.sigNextDataPoint.emit()
            return

    def _trigger_next_x(self):
        """ Trigger to next frequency (fs) or field (bs)."""
        if self.is_fs:
            self._mw_device.trigger()
        else:
            self._magnet.trigger()
        return

    def _get_data_lia(self):
        """ Get data from the lockin amplifier. The number of channels is four."""
        self.eproc_raw_data[self.elapsed_accumulations, self.elapsed_sweeps,
        self.elapsed_x, :] = self._lia_device.get_data_lia()[:4]

        # Measure again if data from Lia is not real data (when this happens the value is really close to zero)
        for i in range(len(self.eproc_raw_data[0, 0, 0, :])):
            while abs(self.eproc_raw_data[self.elapsed_accumulations,
                                          self.elapsed_sweeps, self.elapsed_x, i]) < 1e-7:
                time.sleep(0.01)
                self.eproc_raw_data[self.elapsed_accumulations, self.elapsed_sweeps,
                                    self.elapsed_x, :] = self._lia_device.get_data_lia()[:4]
        return 0

    def _set_new_x_value(self):
        """ Set new x value if necessary.

        1. If all accumulations are completed: perform average and set new x position.
        2. If the x position reached the stop value: go back to initial x position.
        3. If all sweeps are completed or stopNextSweepRequested: stop.
        """
        self.elapsed_accumulations += 1
        if self.elapsed_accumulations == self.n_accumulation:
            self._average_data()

            self.elapsed_x += 1
            self.elapsed_accumulations = 0
            if self.elapsed_x == self.eproc_plot_x.size:
                if self.is_fs:
                    self._mw_device.reset_sweeppos()
                else:
                    self._magnet.reset_sweeppos()

                self.elapsed_sweeps += 1
                self.elapsed_x = 0
                if self.elapsed_sweeps == self.n_sweep or self.stopNextSweepRequested:
                    self.stopRequested = True

            self._trigger_next_x()
        return 0

    def _average_data(self):
        """Average over sweeps and accumulations at fixed value of x."""
        self.eproc_plot_y[self.elapsed_x] = np.mean(
            self.eproc_raw_data[:, :self.elapsed_sweeps + 1, self.elapsed_x, :],
            axis=(0, 1),
            dtype=np.float64
        )
        return 0

    def _update_remaining_time(self):
        """Compute new remaining time and emit signal to the gui."""
        sweep_time = self.eproc_plot_x.size * self.n_accumulation * self.lia_waiting_time
        if not self.is_fs:
            # Take into consideration magnetic field settling time. If fs: settling time is small and can be ignored
            sweep_time += self.eproc_plot_x.size * self._magnet.SETTLING_TIME + self._magnet.SETTLING_TIME_LARGE

        remaining_time = sweep_time * (self.n_sweep - self.elapsed_sweeps
                                       - self.elapsed_x/self.eproc_plot_x.size)

        self.sigEprocRemainingTimeUpdated.emit(remaining_time, self.elapsed_sweeps)
        return 0

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

        ############################################
        # Save parameters (as str for readability) #
        ############################################
        parameters = OrderedDict()
        if self.is_fs:
            parameters['Magnetic Field (G)'] = str(self.fs_field)
            parameters['Microwave Power (dBm)'] = str(self.fs_mw_power)
            parameters['Start Frequency (Hz)'] = str(self.fs_start)
            parameters['Step Size (Hz)'] = str(self.fs_step)
            parameters['Stop Frequency (Hz)'] = str(self.fs_stop)
        else:
            parameters['Microwave Frequency (Hz)'] = str(self.bs_frequency)
            parameters['Microwave Power (dBm)'] = str(self.bs_mw_power)
            parameters['Start Field (G)'] = str(self.bs_start)
            parameters['Step Size (G)'] = str(self.bs_step)
            parameters['Stop Field (G)'] = str(self.bs_stop)

        parameters['Duration Of The Experiment'] = time.strftime('%Hh%Mm%Ss', time.gmtime(self.measurement_duration))
        parameters['Elapsed Sweeps'] = self.elapsed_sweeps
        parameters['Accumulations Per Point'] = self.n_accumulation

        parameters['Frequency Multiplier'] = self.f_multiplier

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
            parameters['Modulation Frequency (Hz)'] = str(self.ref_freq)
            parameters['Modulation Deviation (Hz)'] = str(self.ref_dev)
            parameters['Modulation Mode'] = self.ref_mode
        else:
            parameters['Lockin Internal Modulation Frequency (Hz)'] = self.lia_int_freq

        ###############
        # Save x-axis #
        ###############
        if self.is_fs:
            eproc_data = {'Frequency (Hz)': self.eproc_plot_x}
            eproc_raw_data = {'Frequency (Hz)': self.eproc_plot_x}
        else:
            eproc_data = {'Frequency (Hz)': self.eproc_plot_x}
            eproc_raw_data = {'Frequency (Hz)': self.eproc_plot_x}

        ####################
        # Save y-axis data #
        ####################
        for i in range(len(self.eproc_raw_data[0, 0, 0, :])):
            if self.elapsed_sweeps == 0:
                # Acquisition stopped before the first sweep was completed
                # The last points will have value equal to zero
                eproc_y_data = np.mean(self.eproc_raw_data[:, :self.elapsed_sweeps + 1, :, :],
                                       axis=(0, 1),
                                       dtype=np.float64)
            else:
                # If the acquisition was stopped in the middle of a sweep: the incomplete sweep is discarded
                eproc_y_data = np.mean(self.eproc_raw_data[:, :self.elapsed_sweeps, :, :],
                                       axis=(0, 1),
                                       dtype=np.float64)
            eproc_data['Channel {} (mV)'.format(i + 1)] = eproc_y_data[:, i]

        self._save_logic.save_data(eproc_data,
                                   filepath=filepath,
                                   parameters=parameters,
                                   filename=tag + ending,
                                   fmt='%.6e',
                                   delimiter='\t')

        ########################
        # Save y-axis raw data #
        ########################
        if self.elapsed_sweeps == self.n_sweep:
            # Acquisition stopped before the first sweep was completed
            # The last points will have value equal to zero
            self.raw_data_avg = np.mean(self.eproc_raw_data[:, :self.elapsed_sweeps, :, :],
                                   axis=0,
                                   dtype=np.float64)
        else:
            # If the acquisition was stopped in the middle of a sweep: save also the incomplete sweep
            self.raw_data_avg = np.mean(self.eproc_raw_data[:, :self.elapsed_sweeps + 1, :, :],
                                   axis=0,
                                   dtype=np.float64)

        for ch in range(len(self.raw_data_avg[0, 0, :])):
            for sw in range(len(self.raw_data_avg[:, 0, 0])):
                eproc_raw_data['Ch {0} sw {1} (mV)'.format(ch + 1, sw + 1)] = self.raw_data_avg[sw, :, ch]

        self._save_logic.save_data(eproc_raw_data,
                                   filepath=filepath,
                                   parameters=parameters,
                                   filename=tag_raw + ending,
                                   fmt='%.6e',
                                   delimiter='\t')

        self.log.info('EPRoC data saved to:\n{0}'.format(filepath))
        return
