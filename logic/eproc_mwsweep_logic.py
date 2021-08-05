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
    taskrunner = Connector(interface='TaskRunner')
    magnet = Connector(interface='EprocMagnetInterface')

    # config option
    mw_scanmode = ConfigOption(
        'scanmode',
        'SWEEP',
        missing='warn',
        converter=lambda x: MicrowaveMode[x.upper()])

    # these go here or in on_activate()?
    number_of_sweeps = StatusVar('number_of_sweeps', 1)
    number_of_accumulations = StatusVar('number_of_accumulations', 10)

    cw_mw_frequency = StatusVar('cw_mw_frequency', 287e6)
    cw_mw_power = StatusVar('cw_mw_power', -30)
    sweep_mw_power = StatusVar('sweep_mw_power', -30)
    mw_starts = StatusVar('mw_starts', [2800e6])
    mw_stops = StatusVar('mw_stops', [2950e6])
    mw_steps = StatusVar('mw_steps', [2e6])
    ranges = StatusVar('ranges', 1)

    magnetic_field = StatusVar('magnetic_field', 3480)

    # change these initial values
    lockin_range_index = StatusVar('lockin_range_index', 1.)
    coupl = StatusVar('coupl', 'ac')
    # tauA = StatusVar('tauA', 0.0001)
    tauA_index = StatusVar('tauA_index', 1)
    # tauB = StatusVar('tauB', 0.0001)
    tauB_index = StatusVar('tauB_index', 1)
    slope = StatusVar('slope', 6)
    config = StatusVar('config', 'A&B')
    amplitude = StatusVar('amplitude', 0)
    fm_int_freq = StatusVar('fm_int_freq', 0)
    phase = StatusVar('phase', 0)
    phase1 = StatusVar('phase1', 0)
    harmonic = StatusVar('harmonic', 1)
    waiting_time_factor = StatusVar('waiting_time_factor', 1)

    fm_shape = StatusVar('fm_shape', 'SIN')
    fm_ext_freq = StatusVar('fm_ext_freq', 1000000)
    fm_dev = StatusVar('fm_dev', 1000)
    fm_mode = StatusVar('fm_mode', 'HBAN')

    # Internal signals
    sigNextMeasure = QtCore.Signal()

    # Update signals, e.g. for GUI module
    sigParameterUpdated = QtCore.Signal(dict)
    sigOutputStateUpdated = QtCore.Signal(str, bool)
    sigEprocPlotsUpdated = QtCore.Signal(np.ndarray, np.ndarray)
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
        self._taskrunner = self.taskrunner()
        self._magnet = self.magnet()

        # Get hardware constraints
        limits = self.get_hw_constraints()

        # Set/recall microwave source parameters
        self.cw_mw_frequency = limits.frequency_in_range(self.cw_mw_frequency)
        self.cw_mw_power = limits.power_in_range(self.cw_mw_power)
        self.sweep_mw_power = limits.power_in_range(self.sweep_mw_power)

        # Elapsed measurement time and number of sweeps
        self.elapsed_time = 0.0
        self.elapsed_sweeps = 0
        self. elapsed_accumulations = 0

        self.frequency_lists = []
        self.final_freq_list = []

        # Set flag for stopping a measurement
        self.stopRequested = False

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
        self.set_cw_parameters(self.cw_mw_frequency, self.cw_mw_power)
        self.set_magnetic_field(self.magnetic_field)
        self.set_lockin_parameters(self.lockin_range_index, self.coupl, self.tauA_index, self.tauB_index, self.slope, self.config, self.amplitude, self.fm_int_freq,
                              self.phase, self.phase1, self.harmonic, self.waiting_time_factor)
        self.set_fm_parameters(self.fm_shape, self.fm_ext_freq, self.fm_dev, self.fm_mode)
        self.set_eproc_scan_parameters(self.number_of_sweeps, self.number_of_accumulations)
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

        final_freq_list = []
        self.frequency_lists = []
        for mw_start, mw_stop, mw_step in zip(self.mw_starts, self.mw_stops, self.mw_steps):
            freqs = np.arange(mw_start, mw_stop + mw_step, mw_step)
            final_freq_list.extend(freqs)
            self.frequency_lists.append(freqs)

        if type(self.final_freq_list) == list:
            self.final_freq_list = np.array(final_freq_list)

        self.eproc_plot_x = np.array(self.final_freq_list)
        self.eproc_plot_y = np.zeros([self.eproc_plot_x.size, 4]) # writing it for 4 channels, but this should become a method get_lockin_channels of some sort

        self.sigEprocPlotsUpdated.emit(self.eproc_plot_x, self.eproc_plot_y)
        return

    def set_cw_parameters(self, frequency, power):
        """ Set the desired new cw mode parameters.

        @param float frequency: frequency to set in Hz
        @param float power: power to set in dBm

        @return (float, float): actually set frequency in Hz, actually set power in dBm
        """
        if self.module_state() != 'locked' and isinstance(frequency, (int, float)) and isinstance(power, (int, float)):
            constraints = self.get_hw_constraints()
            frequency_to_set = constraints.frequency_in_range(frequency)
            power_to_set = constraints.power_in_range(power)
            self.cw_mw_frequency, self.cw_mw_power, dummy = self._mw_device.set_cw(frequency_to_set,
                                                                                   power_to_set)
        else:
            self.log.warning('set_cw_frequency failed. Logic is either locked or input value is '
                             'no integer or float.')

        param_dict = {'cw_mw_frequency': self.cw_mw_frequency, 'cw_mw_power': self.cw_mw_power}
        self.sigParameterUpdated.emit(param_dict)
        return self.cw_mw_frequency, self.cw_mw_power

    def set_sweep_parameters(self, starts, stops, steps, power):
        """ Set the desired frequency parameters for list and sweep mode

        @param list starts: list of start frequencies to set in Hz
        @param list stops: list of stop frequencies to set in Hz
        @param list steps: list of step frequencies to set in Hz
        @param list power: mw power to set in dBm

        @return list, list, list, float: current start_freq, current stop_freq,
                                            current freq_step, current power
        """
        limits = self.get_hw_constraints()
        # as everytime all the elements are read when editing of a box is finished
        # also need to reset the lists in this case
        self.mw_starts = []
        self.mw_steps = []
        self.mw_stops = []

        if self.module_state() != 'locked':
            for start, step, stop in zip(starts, steps, stops):
                if isinstance(start, (int, float)):
                    self.mw_starts.append(limits.frequency_in_range(start))
                if isinstance(stop, (int, float)) and isinstance(step, (int, float)):
                    if stop <= start:
                        stop = start + step
                    self.mw_stops.append(limits.frequency_in_range(stop))
                    if self.mw_scanmode == MicrowaveMode.LIST:
                        self.mw_steps.append(limits.list_step_in_range(step))
                    elif self.mw_scanmode == MicrowaveMode.SWEEP:
                        if self.ranges == 1:
                            self.mw_steps.append(limits.sweep_step_in_range(step))
                        else:
                            self.log.error("Sweep mode will only work with one frequency range.")

            if isinstance(power, (int, float)):
                self.sweep_mw_power = limits.power_in_range(power)
        else:
            self.log.warning('set_sweep_parameters failed. Logic is locked.')

        param_dict = {'mw_starts': self.mw_starts, 'mw_stops': self.mw_stops, 'mw_steps': self.mw_steps,
                      'sweep_mw_power': self.sweep_mw_power}
        self.sigParameterUpdated.emit(param_dict)
        return self.mw_starts, self.mw_stops, self.mw_steps, self.sweep_mw_power

    def set_fm_parameters(self, shape, freq, dev, mode):
        if self.module_state() != 'locked':
            if isinstance(freq, (int, float)) and isinstance(dev, (int, float)):
                self.fm_shape, self.fm_ext_freq, self.fm_dev, self.fm_mode = self._mw_device.set_fm(shape, freq, dev, mode)

        param_dict = {'fm_shape': self.fm_shape, 'fm_ext_freq': self.fm_ext_freq, 'fm_dev': self.fm_dev,
                      'fm_mode': self.fm_mode}
        self.sigParameterUpdated.emit(param_dict)
        return self.fm_shape, self.fm_ext_freq, self.fm_dev, self.fm_mode

    def set_lockin_parameters(self, lockin_range_index, coupl, tauA_index, tauB_index, slope, config, amplitude, fm_int_freq,
                              phase, phase1, harmonic, waiting_time_factor):
        if self.module_state() != 'locked':
            if isinstance(amplitude, (int, float)) and \
                    isinstance(fm_int_freq, (int, float)) and isinstance(phase, (int, float)) and \
                    isinstance(phase1, (int, float)) and isinstance(harmonic, (int, float)):
                self.lockin_range_index = self._lockin_device.set_input_range(lockin_range_index)
                self.coupl = self._lockin_device.set_coupling_type(coupl)
                self.tauA_index, self.tauB_index = self._lockin_device.set_time_constants(tauA_index, tauB_index)
                self.slope = self._lockin_device.set_rolloff(slope)
                self.config = self._lockin_device.set_input_config(config)
                self.amplitude = self._lockin_device.set_amplitude(amplitude)
                self.fm_int_freq = self._lockin_device.set_frequency(fm_int_freq)
                self.phase, self.phase1 = self._lockin_device.set_phases(phase, phase1)
                self.harmonic = self._lockin_device.set_harmonic(harmonic)
            if isinstance(waiting_time_factor, (int, float)) and waiting_time_factor > 0:
                self.waiting_time_factor = waiting_time_factor
            else:
                self.log.warning('set_lockin_parameters failed. Waiting time factor input value is '
                                 'no integer or float or is not bigger than zero.')

        # not updating tau value for now because the indexes are useful for the gui and the value for the logic,
        # im giving it the value for now
        param_dict = {'lockin_range_index': self.lockin_range_index, 'coupl': self.coupl,
                      'tauA_index': self.tauA_index, 'tauB_index': self.tauB_index,
                      'slope': self.slope, 'config': self.config, 'amplitude': self.amplitude,
                      'fm_int_freq': self.fm_int_freq, 'phase': self.phase, 'phase1': self.phase1,
                      'harmonic': self.harmonic, 'waiting_time_factor': self.waiting_time_factor}
        self.sigParameterUpdated.emit(param_dict)
        return self.lockin_range_index, self.coupl, self.tauA_index, self.tauB_index, self.slope, self.config, self.amplitude, \
               self.fm_int_freq, self.phase, self.phase1, self.harmonic, self.waiting_time_factor

    def lockin_ext_ref_on(self):
        if self.module_state() == 'locked':
            self.log.error('Can not change lockin reference. EPRoCLogic is already locked.')
        else:
            # setting the values for the reference
            self.fm_shape, \
            self.fm_ext_freq, \
            self.fm_dev, \
            self.fm_mode = self._mw_device.set_fm(self.fm_shape, self.fm_ext_freq, self.fm_dev, self.fm_mode)
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

    def set_magnetic_field(self, field):
        if self.module_state() != 'locked':
            if isinstance(field, (int, float)):
                self.magnetic_field = self._magnet.set_central_field(field)
        else:
            self.log.warning('set_magnet_field failed. Logic is either locked or input value is '
                             'no integer or float.')

        param_dict = {'magnetic_field': self.magnetic_field}
        self.sigParameterUpdated.emit(param_dict)
        return self.magnetic_field

    def mw_cw_on(self):
        """
        Switching on the mw source in cw mode.

        @return str, bool: active mode ['cw', 'list', 'sweep'], is_running
        """
        if self.module_state() == 'locked':
            self.log.error('Can not start microwave in CW mode. EPRoCLogic is already locked.')
        else:
            self.cw_mw_frequency, \
            self.cw_mw_power, \
            mode = self._mw_device.set_cw(self.cw_mw_frequency, self.cw_mw_power)
            param_dict = {'cw_mw_frequency': self.cw_mw_frequency, 'cw_mw_power': self.cw_mw_power}
            self.sigParameterUpdated.emit(param_dict)
            if mode != 'cw':
                self.log.error('Switching to CW microwave output mode failed.')
            else:
                err_code = self._mw_device.cw_on()
                if err_code < 0:
                    self.log.error('Activation of microwave output failed.')

        mode, is_running = self._mw_device.get_status()
        self.sigOutputStateUpdated.emit(mode, is_running)
        return mode, is_running

    def mw_sweep_on(self):
        """
        Switching on the mw source in list/sweep mode.

        @return str, bool: active mode ['cw', 'list', 'sweep'], is_running
        """

        limits = self.get_hw_constraints()
        param_dict = {}
        self.final_freq_list = []
        if self.mw_scanmode == MicrowaveMode.LIST:
            final_freq_list = []
            used_starts = []
            used_steps = []
            used_stops = []
            for mw_start, mw_stop, mw_step in zip(self.mw_starts, self.mw_stops, self.mw_steps):
                num_steps = int(np.rint((mw_stop - mw_start) / mw_step))
                end_freq = mw_start + num_steps * mw_step
                freq_list = np.linspace(mw_start, end_freq, num_steps + 1)

                # adjust the end frequency in order to have an integer multiple of step size
                # The master module (i.e. GUI) will be notified about the changed end frequency
                final_freq_list.extend(freq_list)

                used_starts.append(mw_start)
                used_steps.append(mw_step)
                used_stops.append(end_freq)

            final_freq_list = np.array(final_freq_list)
            if len(final_freq_list) >= limits.list_maxentries:
                self.log.error('Number of frequency steps too large for microwave device.')
                mode, is_running = self._mw_device.get_status()
                self.sigOutputStateUpdated.emit(mode, is_running)
                return mode, is_running
            freq_list, self.sweep_mw_power, mode = self._mw_device.set_list(final_freq_list,
                                                                            self.sweep_mw_power)

            self.final_freq_list = np.array(freq_list)
            self.mw_starts = used_starts
            self.mw_stops = used_stops
            self.mw_steps = used_steps
            param_dict = {'mw_starts': used_starts, 'mw_stops': used_stops,
                          'mw_steps': used_steps, 'sweep_mw_power': self.sweep_mw_power}

            self.sigParameterUpdated.emit(param_dict)

        elif self.mw_scanmode == MicrowaveMode.SWEEP:
            if self.ranges == 1:
                mw_stop = self.mw_stops[0]
                mw_step = self.mw_steps[0]
                mw_start = self.mw_starts[0]

                if np.abs(mw_stop - mw_start) / mw_step >= limits.sweep_maxentries:
                    self.log.warning('Number of frequency steps too large for microwave device. '
                                     'Lowering resolution to fit the maximum length.')
                    mw_step = np.abs(mw_stop - mw_start) / (limits.list_maxentries - 1)
                    self.sigParameterUpdated.emit({'mw_steps': [mw_step]})

                sweep_return = self._mw_device.set_sweep(
                    mw_start, mw_stop, mw_step, self.sweep_mw_power)
                mw_start, mw_stop, mw_step, self.sweep_mw_power, mode = sweep_return

                param_dict = {'mw_starts': [mw_start], 'mw_stops': [mw_stop],
                              'mw_steps': [mw_step], 'sweep_mw_power': self.sweep_mw_power}
                self.final_freq_list = np.arange(mw_start, mw_stop + mw_step, mw_step)
            else:
                self.log.error('sweep mode only works for one frequency range.')

        else:
            self.log.error('Scanmode not supported. Please select SWEEP or LIST.')

        self.sigParameterUpdated.emit(param_dict)

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
        return mode, is_running

    def reset_sweep(self):
        """
        Resets the list/sweep mode of the microwave source to the first frequency step.
        """
        if self.mw_scanmode == MicrowaveMode.SWEEP:
            self._mw_device.reset_sweeppos()
        elif self.mw_scanmode == MicrowaveMode.LIST:
            self._mw_device.reset_listpos()
        return

    def mw_off(self):
        """ Switching off the MW source.

        @return str, bool: active mode ['cw', 'list', 'sweep'], is_running
        """
        error_code = self._mw_device.off()
        if error_code < 0:
            self.log.error('Switching off microwave source failed.')

        mode, is_running = self._mw_device.get_status()
        self.sigOutputStateUpdated.emit(mode, is_running)
        return mode, is_running

    def start_eproc(self):
        with self.threadlock:
            if self.module_state() == 'locked':
                self.log.error('Can not start EPRoC scan. Logic is already locked.')
                return -1

            self.module_state.lock()
            self.stopRequested = False
            # self.fc.clear_result()

            self.mws = 1 # microwve sweep index = 0 means field sweep
            if self.mws:
                self.set_magnetic_field(self.magnetic_field)
            else:
                self.set_cw_parameters(self.cw_mw_frequency, self.cw_mw_power)

            # can be modified, look at lockin manual
            if self.tauB_index > self.tauA_index and self.tauB_index != 22:
                self.waiting_time = self._lockin_device.tau_values[self.tauB_index] * self.waiting_time_factor    # in seconds
            else:
                self.waiting_time = self._lockin_device.tau_values[self.tauA_index] * self.waiting_time_factor

            self.elapsed_sweeps = 0
            self.elapsed_accumulations = 0
            self.actual_index = 0    # maybe this could be called elapsed_index to be coherent, but I think there should be some changes in the rest of the code then

            self.remaining_time = 0.
            self._startTime = time.time()
            self.total_time = (self.waiting_time + self.waiting_time/20 * self.number_of_accumulations) * self.eproc_plot_x.size * self.number_of_sweeps
            self.sigEprocRemainingTimeUpdated.emit(self.total_time, self.elapsed_sweeps)

            # is this necessary?
            self._mw_device.fm_on()
            if self.mws:
                self._mw_device.set_internal_trigger()
                mode, is_running = self.mw_sweep_on()
                if not is_running:
                    self.module_state.unlock()
                    return -1
            else:
                mode, is_running = self.mw_cw_on()
                if not is_running:
                    self.module_state.unlock()
                    return -1

            self._initialize_eproc_plots()
            self.eproc_raw_data = np.zeros(
                [self.number_of_sweeps,
                self.number_of_accumulations,
                self.eproc_plot_x.size,
                4]  # number of channels {2 or 4}
            )

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

    def _next_measure(self):
        with self.threadlock:
            # If the eproc measurement is not running do nothing
            if self.module_state() != 'locked':
                return

            if self.stopRequested:
                self.stopRequested = False
                self.mw_off()
                self.module_state.unlock()
                return

            # we put this here because the start of the sweep is at the frequency start-step
            if self.elapsed_accumulations == 0:
                if self.mws:
                    self._mw_device.trigger()
                    time.sleep(self.waiting_time)
                else:
                    self.next_field()
                    time.sleep(self.waiting_time)

            time.sleep(self.waiting_time/20) # this can be shortened almost for sure
            # SOLVED maybe stoprequested should also be checked in here somehow because if there are too many accumulations than one has to wait a lot
            self.eproc_raw_data[self.elapsed_sweeps, self.elapsed_accumulations, self.actual_index, :] = self._lockin_device.get_data_lia()[:4] #this is for 4 channels
            # this may be the solution for the stoprequested problem
            '''
            if error:
                self.stopRequested = True
                self.sigNextLine.emit()
                return
            '''

            self.elapsed_accumulations += 1
            if self.elapsed_accumulations == self.number_of_accumulations:
            # average over accumulations for the current frequency and the current sweep
                new_value = np.mean(self.eproc_raw_data[self.elapsed_sweeps, :, self.actual_index, :],
                                    axis=0,     #axis = 0 in this case means an average over accumulations
                                    dtype=np.float64)

                self.eproc_plot_y[self.actual_index, :] = (self.eproc_plot_y[self.actual_index, :] * self.elapsed_sweeps + new_value) / (self.elapsed_sweeps + 1)

                self.elapsed_accumulations = 0
                self.remaining_time = self.total_time - (time.time() - self._startTime)

                # understand where to put this: at the start or end?
                if self.actual_index == self.eproc_plot_x.size - 1:
                    if self.mws:
                        self.reset_sweep()
                    else:
                        self.reset_field_sweep()
                    self.elapsed_sweeps += 1
                    self.actual_index = 0
                    if self.elapsed_sweeps == self.number_of_sweeps:
                        # stop scan or stop requested
                        self.stopRequested = True
                else:
                    self.actual_index += 1

                self.sigEprocRemainingTimeUpdated.emit(self.remaining_time, self.elapsed_sweeps)
                self.sigEprocPlotsUpdated.emit(self.eproc_plot_x, self.eproc_plot_y)
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

            self.sigNextMeasure.emit()
            return

    def get_hw_constraints(self):
        """ Return the names of all ocnfigured fit functions.
        @return object: Hardware constraints object
        """
        constraints = self._mw_device.get_limits()
        return constraints

    def save_eproc_data(self, tag=None):
        """ Saves the current EPRoC data to a file."""
        timestamp = datetime.datetime.now()
        filepath = self._save_logic.get_path_for_module(module_name='EPRoC')

        if tag is None:
            tag = ''

        # first save raw data for each channel
        if len(tag) > 0:
            filelabel_raw = '{0}_EPRoC_data'.format(tag)
        else:
            filelabel_raw = 'EPRoC_data'

        eproc_data_list = [self.eproc_plot_x]
        for channel in range(4):
            eproc_data_list.append(self.eproc_plot_y[:, channel])
        eproc_data = OrderedDict()
        if self.mws:
            eproc_data['Frequency\t\tchannel 1\t\tchannel 2\t\tchannel 3\t\tchannel 4'] = np.array(eproc_data_list).transpose()
        parameters = OrderedDict()
        parameters['Microwave CW Power (dBm)'] = self.cw_mw_power
        parameters['Microwave Sweep Power (dBm)'] = self.sweep_mw_power
        parameters['Number of frequency sweeps (#)'] = self.elapsed_sweeps
        # this is a bad solution
        if self.lockin_range_index == 0:
            lockin_range = 0.1
        elif self.lockin_range_index == 1:
            lockin_range = 1.
        else:
            lockin_range = 10.
        parameters['lockin_range (V)'] = lockin_range
        if self.coupl == 0:
            coupl = 'dc'
        else:
            coupl = 'ac'
        parameters['coupling'] = coupl
        parameters['tauA (s)'] = self._lockin_device.tau_values[self.tauA_index]
        # find another solution for the line here with the 22
        if self.tauB_index == 22:
            parameters['tauB (s)'] = self._lockin_device.tau_values[self.tauA_index]
        else:
            parameters['tauB (s)'] = self._lockin_device.tau_values[self.tauB_index]
        parameters['slope (dB/oct)'] = self.slope
        parameters['config'] = self.config
        parameters['lockin amplitude (V)'] = self.amplitude
        parameters['lockin internal frequency modulation (Hz)'] = self.fm_int_freq
        parameters['phase (°)'] = self.phase
        parameters['phase1 (°)'] = self.phase1
        parameters['harmonic'] = self.harmonic
        parameters['waiting time factor'] = self.waiting_time_factor

        parameters['modulation shape'] = self.fm_shape
        parameters['modulation external frequency'] = self.fm_ext_freq
        parameters['modulation deviation'] = self.fm_dev
        parameters['modulation mode'] = self.fm_mode

        self._save_logic.save_data(eproc_data,
                                   filepath=filepath,
                                   parameters=parameters,
                                   filelabel=filelabel_raw,
                                   fmt='%.6e',
                                   delimiter='\t',
                                   timestamp=timestamp)

        '''
        # now create a plot for each scan range
        data_start_ind = 0
        for ii, frequency_arr in enumerate(self.frequency_lists):
            if len(tag) > 0:
                filelabel = '{0}_ODMR_data_ch{1}_range{2}'.format(tag, nch, ii)
            else:
                filelabel = 'ODMR_data_ch{0}_range{1}'.format(nch, ii)

            # prepare the data in a dict or in an OrderedDict:
            data = OrderedDict()
            data['frequency (Hz)'] = frequency_arr

            num_points = len(frequency_arr)
            data_end_ind = data_start_ind + num_points
            data['count data (counts/s)'] = self.odmr_plot_y[nch][data_start_ind:data_end_ind]
            data_start_ind += num_points

            parameters = OrderedDict()
            parameters['Microwave CW Power (dBm)'] = self.cw_mw_power
            parameters['Microwave Sweep Power (dBm)'] = self.sweep_mw_power
            parameters['Run Time (s)'] = self.run_time
            parameters['Number of frequency sweeps (#)'] = self.elapsed_sweeps
            parameters['Start Frequency (Hz)'] = frequency_arr[0]
            parameters['Stop Frequency (Hz)'] = frequency_arr[-1]
            parameters['Step size (Hz)'] = frequency_arr[1] - frequency_arr[0]
            parameters['Clock Frequencies (Hz)'] = self.clock_frequency
            parameters['Channel'] = '{0}: {1}'.format(nch, channel)
            parameters['frequency range'] = str(ii)

            key = 'channel: {0}, range: {1}'.format(nch, ii)
            if key in self.fits_performed.keys():
                parameters['Fit function'] = self.fits_performed[key][3]
                for name, param in self.fits_performed[key][2].params.items():
                    parameters[name] = str(param)
            # add all fit parameter to the saved data:

            fig = self.draw_figure(nch, ii,
                                   cbar_range=colorscale_range,
                                   percentile_range=percentile_range)

            self._save_logic.save_data(data,
                                       filepath=filepath,
                                       parameters=parameters,
                                       filelabel=filelabel,
                                       fmt='%.6e',
                                       delimiter='\t',
                                       timestamp=timestamp,
                                       plotfig=fig)
        '''
        self.log.info('EPRoC data saved to:\n{0}'.format(filepath))
        return
