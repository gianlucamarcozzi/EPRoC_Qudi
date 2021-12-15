# -*- coding: utf-8 -*-
"""
This file contains the Qudi GUI module for EPRoC control.

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

import numpy as np
import os
import pyqtgraph as pg
from core.util.modules import get_main_dir
from core.connector import Connector
from core.util import units
from gui.guibase import GUIBase
from gui.guiutils import ColorBar
from gui.colordefs import ColorScaleInferno
from gui.colordefs import QudiPalettePale as palette
from gui.fitsettings import FitSettingsDialog, FitSettingsComboBox
from qtpy import QtCore
from qtpy import QtCore, QtWidgets, uic
from qtwidgets.scientific_spinbox import ScienDSpinBox
from qtpy import uic
from functools import partial


class EPRoCMainWindow(QtWidgets.QMainWindow):
    """
    The main window for the EPRoC measurement GUI.
    """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_mw_and_field.ui')

        # Load it
        super(EPRoCMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()

class EPRoCAnalysis(QtWidgets.QMainWindow):
    """ The settings dialog for ODMR measurements.
    """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_eproc_analysis.ui')

        # Load it
        super(EPRoCAnalysis, self).__init__()
        uic.loadUi(ui_file, self)

class EPRoCMotorizedStages(QtWidgets.QMainWindow):
    """ The settings dialog for Motorized Stages.
    """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_eproc_motorized_stages.ui')

        # Load it
        super(EPRoCMotorizedStages, self).__init__()
        uic.loadUi(ui_file, self)



class EPRoCGui(GUIBase):
    """
    This is the GUI Class for EPRoC measurements
    """

    # declare connectors
    eproclogic1 = Connector(interface='EPRoCLogic')
    savelogic = Connector(interface='SaveLogic')

    sigStartEproc = QtCore.Signal()
    sigStopEproc = QtCore.Signal()
    sigToggleCwOn = QtCore.Signal()
    sigToggleCwOff = QtCore.Signal()
    sigToggleModulationOn = QtCore.Signal()
    sigToggleModulationOff = QtCore.Signal()
    sigExtRefOn = QtCore.Signal()
    sigExtRefOff = QtCore.Signal()
    sigPowerSupplyBoardOn = QtCore.Signal()
    sigPowerSupplyBoardOff = QtCore.Signal()
    sigPowerSupplyAmplifierOn = QtCore.Signal()
    sigPowerSupplyAmplifierOff = QtCore.Signal()

    sigMsParamsChanged = QtCore.Signal(float, float, float, float, float)
    sigFsParamsChanged = QtCore.Signal(float, float, float, float, float)
    sigScanParamsChanged = QtCore.Signal(int, int)
    sigRefParamsChanged = QtCore.Signal(str, float, str, float)
    sigLockinParamsChanged = QtCore.Signal(str, float, str, float, float, float, float, float, float, int, str, str)
    sigPowerSupplyBoardParamsChanged = QtCore.Signal(float, float, float, float)
    sigPowerSupplyAmplifierParamsChanged = QtCore.Signal(float, float, float, float)

    sigSaveMeasurement = QtCore.Signal(str)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Definition, configuration and initialisation of the EPRoC GUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        """

        self._eproc_logic = self.eproclogic1()

        # Use the inherited class 'Ui_EPRoCGuiUI' to create now the GUI element:
        self._mw = EPRoCMainWindow()
        self._sd = EPRoCAnalysis()
        self._KDC101 = EPRoCMotorizedStages()

        # Create a QSettings object for the mainwindow and store the actual GUI layout
        self.mwsettings = QtCore.QSettings("QUDI", "ODMR")
        self.mwsettings.setValue("geometry", self._mw.saveGeometry())
        self.mwsettings.setValue("windowState", self._mw.saveState())

        # Get hardware constraints to set limits for input widgets
        constraints = self._eproc_logic.get_hw_constraints()

        # Adjust range of scientific spinboxes above what is possible in Qt Designer
        self._mw.fs_mw_frequency_DoubleSpinBox.setMaximum(constraints.max_frequency)
        self._mw.fs_mw_frequency_DoubleSpinBox.setMinimum(constraints.min_frequency)
        self._mw.fs_mw_power_DoubleSpinBox.setMaximum(constraints.max_power)
        self._mw.fs_mw_power_DoubleSpinBox.setMinimum(constraints.min_power)
        self._mw.ms_mw_power_DoubleSpinBox.setMaximum(constraints.max_power)
        self._mw.ms_mw_power_DoubleSpinBox.setMinimum(constraints.min_power)

        self._mw.save_tag_LineEdit = QtWidgets.QLineEdit(self._mw)
        self._mw.save_tag_LineEdit.setMaximumWidth(300)
        self._mw.save_tag_LineEdit.setMinimumWidth(200)
        self._mw.save_tag_LineEdit.setToolTip('Enter a nametag which will be\n'
                                              'added to the filename.')
        self._mw.save_ToolBar.addWidget(self._mw.save_tag_LineEdit)

        # Add values of time constants taking them from the hardware
        time_constants = self._eproc_logic.get_time_constants()
        for tau in time_constants:
            self._mw.lia_taua_ComboBox.addItem(self.tau_float_to_str(tau))
            self._mw.lia_taub_ComboBox.addItem(self.tau_float_to_str(tau))

        '''
        # add a clear button to clear the ODMR plots:
        self._mw.clear_odmr_PushButton = QtWidgets.QPushButton(self._mw)
        self._mw.clear_odmr_PushButton.setText('Clear ODMR')
        self._mw.clear_odmr_PushButton.setToolTip('Clear the data of the\n'
                                                  'current ODMR measurements.')
        self._mw.clear_odmr_PushButton.setEnabled(False)
        self._mw.toolBar.addWidget(self._mw.clear_odmr_PushButton)
        '''
        self.ch1_image = pg.PlotDataItem(self._eproc_logic.eproc_plot_x,
                                         self._eproc_logic.eproc_plot_y[:, 0],
                                         pen=pg.mkPen(palette.c1, style=QtCore.Qt.DotLine),
                                         symbol='o',
                                         symbolPen=palette.c1,
                                         symbolBrush=palette.c1,
                                         symbolSize=7)

        self.ch2_image = pg.PlotDataItem(self._eproc_logic.eproc_plot_x,
                                         self._eproc_logic.eproc_plot_y[:, 1],
                                         pen=pg.mkPen(palette.c1, style=QtCore.Qt.DotLine),
                                         symbol='o',
                                         symbolPen=palette.c1,
                                         symbolBrush=palette.c1,
                                         symbolSize=7)

        self.ch3_image = pg.PlotDataItem(self._eproc_logic.eproc_plot_x,
                                         self._eproc_logic.eproc_plot_y[:, 2],
                                         pen=pg.mkPen(palette.c1, style=QtCore.Qt.DotLine),
                                         symbol='o',
                                         symbolPen=palette.c1,
                                         symbolBrush=palette.c1,
                                         symbolSize=7)

        self.ch4_image = pg.PlotDataItem(self._eproc_logic.eproc_plot_x,
                                         self._eproc_logic.eproc_plot_y[:, 3],
                                         pen=pg.mkPen(palette.c1, style=QtCore.Qt.DotLine),
                                         symbol='o',
                                         symbolPen=palette.c1,
                                         symbolBrush=palette.c1,
                                         symbolSize=7)

        if self._eproc_logic.is_microwave_sweep:
            x_label = 'Frequency'
            x_units = 'Hz'
        else:
            x_label = 'Magnetic field'
            x_units = 'G'

        # Add the display item to the xy and xz ViewWidget, which was defined in the UI file.
        self._mw.ch1_PlotWidget.addItem(self.ch1_image)
        self._mw.ch1_PlotWidget.setLabel(axis='left', text='Ch 1')
        self._mw.ch1_PlotWidget.setLabel(axis='bottom', text=x_label, units=x_units)
        self._mw.ch1_PlotWidget.showGrid(x=True, y=True, alpha=0.8)

        self._mw.ch2_PlotWidget.addItem(self.ch2_image)
        self._mw.ch2_PlotWidget.setLabel(axis='left', text='Ch 2')
        self._mw.ch2_PlotWidget.setLabel(axis='bottom', text=x_label, units=x_units)
        self._mw.ch2_PlotWidget.showGrid(x=True, y=True, alpha=0.8)

        self._mw.ch3_PlotWidget.addItem(self.ch3_image)
        self._mw.ch3_PlotWidget.setLabel(axis='left', text='Ch 3')
        self._mw.ch3_PlotWidget.setLabel(axis='bottom', text=x_label, units=x_units)
        self._mw.ch3_PlotWidget.showGrid(x=True, y=True, alpha=0.8)

        self._mw.ch4_PlotWidget.addItem(self.ch4_image)
        self._mw.ch4_PlotWidget.setLabel(axis='left', text='Ch 4')
        self._mw.ch4_PlotWidget.setLabel(axis='bottom', text=x_label, units=x_units)
        self._mw.ch4_PlotWidget.showGrid(x=True, y=True, alpha=0.8)

        # Add the display item to the xy and xz ViewWidget, which was defined in the UI file for the analysis.

        self._sd.ch1_PlotWidget.addItem(self.ch1_image)
        self._sd.ch1_PlotWidget.setLabel(axis='left', text='Ch 1')
        self._sd.ch1_PlotWidget.setLabel(axis='bottom', text=x_label, units=x_units)
        self._sd.ch1_PlotWidget.showGrid(x=True, y=True, alpha=0.8)

        self._sd.ch2_PlotWidget.addItem(self.ch2_image)
        self._sd.ch2_PlotWidget.setLabel(axis='left', text='Ch 2')
        self._sd.ch2_PlotWidget.setLabel(axis='bottom', text=x_label, units=x_units)
        self._sd.ch2_PlotWidget.showGrid(x=True, y=True, alpha=0.8)

        self._sd.ch3_PlotWidget.addItem(self.ch3_image)
        self._sd.ch3_PlotWidget.setLabel(axis='left', text='Ch 3')
        self._sd.ch3_PlotWidget.setLabel(axis='bottom', text=x_label, units=x_units)
        self._sd.ch3_PlotWidget.showGrid(x=True, y=True, alpha=0.8)

        self._sd.ch4_PlotWidget.addItem(self.ch4_image)
        self._sd.ch4_PlotWidget.setLabel(axis='left', text='Ch 4')
        self._sd.ch4_PlotWidget.setLabel(axis='bottom', text=x_label, units=x_units)
        self._sd.ch4_PlotWidget.showGrid(x=True, y=True, alpha=0.8)

        ########################################################################
        #          Configuration of the various display Widgets                #
        ########################################################################
        # Take the default values from logic:
        self._mw.ms_field_DoubleSpinBox.setValue(self._eproc_logic.ms_field)
        self._mw.ms_mw_power_DoubleSpinBox.setValue(self._eproc_logic.ms_mw_power)
        self._mw.ms_start_DoubleSpinBox.setValue(self._eproc_logic.ms_start)
        self._mw.ms_stop_DoubleSpinBox.setValue(self._eproc_logic.ms_stop)
        self._mw.ms_step_DoubleSpinBox.setValue(self._eproc_logic.ms_step)
        self._mw.ms_start_LineEdit.setText(self.mw_to_field(self._eproc_logic.ms_start))
        self._mw.ms_step_LineEdit.setText(self.mw_to_field(self._eproc_logic.ms_step))
        self._mw.ms_stop_LineEdit.setText(self.mw_to_field(self._eproc_logic.ms_stop))

        self._mw.fs_mw_frequency_DoubleSpinBox.setValue(self._eproc_logic.fs_mw_frequency)
        self._mw.fs_mw_power_DoubleSpinBox.setValue(self._eproc_logic.fs_mw_power)
        self._mw.fs_start_DoubleSpinBox.setValue(self._eproc_logic.fs_start)
        self._mw.fs_stop_DoubleSpinBox.setValue(self._eproc_logic.fs_stop)
        self._mw.fs_step_DoubleSpinBox.setValue(self._eproc_logic.fs_step)
        self._mw.fs_start_LineEdit.setText(self.field_to_mw(self._eproc_logic.fs_start))
        self._mw.fs_step_LineEdit.setText(self.field_to_mw(self._eproc_logic.fs_step))
        self._mw.fs_stop_LineEdit.setText(self.field_to_mw(self._eproc_logic.fs_stop))

        self._mw.lia_range_ComboBox.setCurrentText(self._eproc_logic.lia_range)
        self._mw.lia_uac_DoubleSpinBox.setValue(self._eproc_logic.lia_uac)
        self._mw.lia_acdc_coupling_ComboBox.setCurrentText(self._eproc_logic.lia_coupling)
        self._mw.lia_frequency_DoubleSpinBox.setValue(self._eproc_logic.lia_int_ref_freq)
        self._mw.lia_taua_ComboBox.setCurrentText(self.tau_float_to_str(self._eproc_logic.lia_tauA))
        self._mw.lia_phasea_DoubleSpinBox.setValue(self._eproc_logic.lia_phaseA)
        self._mw.lia_taub_ComboBox.setCurrentText(self.tau_float_to_str(self._eproc_logic.lia_tauB))
        self._mw.lia_phaseb_DoubleSpinBox.setValue(self._eproc_logic.lia_phaseB)
        self._mw.lia_waiting_time_factor_DoubleSpinBox.setValue(self._eproc_logic.lia_waiting_time_factor)
        self._mw.lia_harmonic_SpinBox.setValue(int(self._eproc_logic.lia_harmonic))
        self._mw.lia_slope_ComboBox.setCurrentText(self._eproc_logic.lia_slope)
        self._mw.lia_configuration_ComboBox.setCurrentText(self._eproc_logic.lia_configuration)

        self._mw.number_of_sweeps_SpinBox.setValue(self._eproc_logic.number_of_sweeps)
        self._mw.number_of_accumulations_SpinBox.setValue(self._eproc_logic.number_of_accumulations)

        self._mw.psb_voltage_outp1_DoubleSpinBox.setValue(self._eproc_logic.psb_voltage_outp1)
        self._mw.psb_voltage_outp2_DoubleSpinBox.setValue(self._eproc_logic.psb_voltage_outp2)
        self._mw.psb_current_max_outp1_DoubleSpinBox.setValue(self._eproc_logic.psb_current_max_outp1)
        self._mw.psb_current_max_outp2_DoubleSpinBox.setValue(self._eproc_logic.psb_current_max_outp2)
        self._mw.psa_voltage_outp1_DoubleSpinBox.setValue(self._eproc_logic.psa_voltage_outp1)
        self._mw.psa_voltage_outp2_DoubleSpinBox.setValue(self._eproc_logic.psa_voltage_outp2)
        self._mw.psa_current_max_outp1_DoubleSpinBox.setValue(self._eproc_logic.psa_current_max_outp1)
        self._mw.psa_current_max_outp2_DoubleSpinBox.setValue(self._eproc_logic.psa_current_max_outp2)

        self._mw.ref_shape_ComboBox.setCurrentText(self._eproc_logic.ref_shape)
        self._mw.ref_frequency_DoubleSpinBox.setValue(self._eproc_logic.ref_freq)
        self._mw.ref_deviation_DoubleSpinBox.setValue(self._eproc_logic.ref_deviation)
        self._mw.ref_deviation_LineEdit.setText(self.mw_to_field(self._eproc_logic.ref_deviation))
        self._mw.ref_mode_ComboBox.setCurrentText(self._eproc_logic.ref_mode)

        # to add: a remaining time display
        self._mw.elapsed_sweeps_DisplayWidget.display(self._eproc_logic.elapsed_sweeps)

        ########################################################################
        #                       Connect signals                                #
        ########################################################################
        # Internal user input changed signals

        self._mw.ms_field_DoubleSpinBox.editingFinished.connect(self.change_ms_params)
        self._mw.ms_mw_power_DoubleSpinBox.editingFinished.connect(self.change_ms_params)
        self._mw.ms_start_DoubleSpinBox.editingFinished.connect(self.change_ms_params)
        self._mw.ms_step_DoubleSpinBox.editingFinished.connect(self.change_ms_params)
        self._mw.ms_stop_DoubleSpinBox.editingFinished.connect(self.change_ms_params)


        self._mw.fs_mw_frequency_DoubleSpinBox.editingFinished.connect(self.change_fs_params)
        self._mw.fs_mw_power_DoubleSpinBox.editingFinished.connect(self.change_fs_params)
        self._mw.fs_start_DoubleSpinBox.editingFinished.connect(self.change_fs_params)
        self._mw.fs_step_DoubleSpinBox.editingFinished.connect(self.change_fs_params)
        self._mw.fs_stop_DoubleSpinBox.editingFinished.connect(self.change_fs_params)

        self._mw.lia_range_ComboBox.currentTextChanged.connect(self.change_lockin_params)
        self._mw.lia_acdc_coupling_ComboBox.currentTextChanged.connect(self.change_lockin_params)
        self._mw.lia_taua_ComboBox.currentTextChanged.connect(self.change_lockin_params)
        self._mw.lia_taub_ComboBox.currentTextChanged.connect(self.change_lockin_params)
        self._mw.lia_slope_ComboBox.currentTextChanged.connect(self.change_lockin_params)
        self._mw.lia_configuration_ComboBox.currentTextChanged.connect(self.change_lockin_params)
        self._mw.lia_uac_DoubleSpinBox.editingFinished.connect(self.change_lockin_params)
        self._mw.lia_frequency_DoubleSpinBox.editingFinished.connect(self.change_lockin_params)
        self._mw.lia_phasea_DoubleSpinBox.editingFinished.connect(self.change_lockin_params)
        self._mw.lia_phaseb_DoubleSpinBox.editingFinished.connect(self.change_lockin_params)
        self._mw.lia_harmonic_SpinBox.editingFinished.connect(self.change_lockin_params)
        self._mw.lia_waiting_time_factor_DoubleSpinBox.editingFinished.connect(self.change_lockin_params)

        self._mw.ms_RadioButton.toggled.connect(self.on_off_sweep)
        self._mw.fs_RadioButton.toggled.connect(self.on_off_sweep)
        self._mw.ref_RadioButton.toggled.connect(self.on_off_reference)
        self._mw.power_supply_board_RadioButton.toggled.connect(self.on_off_psb)
        self._mw.power_supply_amplifier_RadioButton.toggled.connect(self.on_off_psa)

        self._mw.number_of_sweeps_SpinBox.editingFinished.connect(self.change_scan_params)
        self._mw.number_of_accumulations_SpinBox.editingFinished.connect(self.change_scan_params)

        self._mw.ref_shape_ComboBox.currentTextChanged.connect(self.change_ref_params)
        self._mw.ref_frequency_DoubleSpinBox.editingFinished.connect(self.change_ref_params)
        self._mw.ref_deviation_DoubleSpinBox.editingFinished.connect(self.change_ref_params)
        self._mw.ref_mode_ComboBox.currentTextChanged.connect(self.change_ref_params)

        self._mw.psb_voltage_outp1_DoubleSpinBox.editingFinished.connect(self.change_psb_params)
        self._mw.psb_voltage_outp2_DoubleSpinBox.editingFinished.connect(self.change_psb_params)
        self._mw.psb_current_max_outp1_DoubleSpinBox.editingFinished.connect(self.change_psb_params)
        self._mw.psb_current_max_outp2_DoubleSpinBox.editingFinished.connect(self.change_psb_params)
        self._mw.psa_voltage_outp1_DoubleSpinBox.editingFinished.connect(self.change_psa_params)
        self._mw.psa_voltage_outp2_DoubleSpinBox.editingFinished.connect(self.change_psa_params)
        self._mw.psa_current_max_outp1_DoubleSpinBox.editingFinished.connect(self.change_psa_params)
        self._mw.psa_current_max_outp2_DoubleSpinBox.editingFinished.connect(self.change_psa_params)

        # Internal trigger signals
        self._mw.action_run_stop.triggered.connect(self.run_stop_scan)
        self._mw.action_stop_next_sweep.triggered.connect(self._eproc_logic.stop_eproc_next_sweep)
        self._mw.action_toggle_cw.triggered.connect(self.toggle_cw)
        self._mw.action_toggle_modulation.triggered.connect(self.toggle_modulation)
        self._mw.action_Save.triggered.connect(self.save_data)

        # Control/values-changed signals to logic
        self.sigStartEproc.connect(self._eproc_logic.start_eproc, QtCore.Qt.QueuedConnection)
        self.sigStopEproc.connect(self._eproc_logic.stop_eproc, QtCore.Qt.QueuedConnection)
        self.sigToggleCwOn.connect(self._eproc_logic.mw_on, QtCore.Qt.QueuedConnection)
        self.sigToggleCwOff.connect(self._eproc_logic.mw_off, QtCore.Qt.QueuedConnection)
        self.sigToggleModulationOn.connect(self._eproc_logic.mw_on, QtCore.Qt.QueuedConnection)
        self.sigToggleModulationOff.connect(self._eproc_logic.mw_off, QtCore.Qt.QueuedConnection)
        self.sigExtRefOn.connect(self._eproc_logic.lockin_ext_ref_on, QtCore.Qt.QueuedConnection)
        self.sigExtRefOff.connect(self._eproc_logic.lockin_ext_ref_off, QtCore.Qt.QueuedConnection)
        self.sigPowerSupplyBoardOn.connect(self._eproc_logic.psb_on, QtCore.Qt.QueuedConnection)
        self.sigPowerSupplyBoardOff.connect(self._eproc_logic.psb_off, QtCore.Qt.QueuedConnection)
        self.sigPowerSupplyAmplifierOn.connect(self._eproc_logic.psa_on, QtCore.Qt.QueuedConnection)
        self.sigPowerSupplyAmplifierOff.connect(self._eproc_logic.psa_off, QtCore.Qt.QueuedConnection)

        self.sigMsParamsChanged.connect(self._eproc_logic.set_ms_parameters, QtCore.Qt.QueuedConnection)
        self.sigFsParamsChanged.connect(self._eproc_logic.set_fs_parameters, QtCore.Qt.QueuedConnection)
        self.sigLockinParamsChanged.connect(self._eproc_logic.set_lia_parameters, QtCore.Qt.QueuedConnection)
        self.sigRefParamsChanged.connect(self._eproc_logic.set_ref_parameters, QtCore.Qt.QueuedConnection)
        self.sigScanParamsChanged.connect(self._eproc_logic.set_eproc_scan_parameters, QtCore.Qt.QueuedConnection)
        self.sigPowerSupplyBoardParamsChanged.connect(self._eproc_logic.set_psb_parameters, QtCore.Qt.QueuedConnection)
        self.sigPowerSupplyAmplifierParamsChanged.connect(self._eproc_logic.set_psa_parameters, QtCore.Qt.QueuedConnection)

        self.sigSaveMeasurement.connect(self._eproc_logic.save_eproc_data, QtCore.Qt.QueuedConnection)

        # Update signals coming from logic:
        self._eproc_logic.sigParameterUpdated.connect(self.update_parameter,
                                                      QtCore.Qt.QueuedConnection)
        self._eproc_logic.sigOutputStateUpdated.connect(self.update_status,
                                                        QtCore.Qt.QueuedConnection)
        self._eproc_logic.sigSetLabelEprocPlots.connect(self.set_label_eproc_plots, QtCore.Qt.QueuedConnection)
        self._eproc_logic.sigEprocPlotsUpdated.connect(self.update_plots, QtCore.Qt.QueuedConnection)
        self._eproc_logic.sigEprocRemainingTimeUpdated.connect(self.update_remainingtime,
                                                               QtCore.Qt.QueuedConnection)

        self._mw.action_stop_next_sweep.setEnabled(False)
        # External reference is basically always used
        self._mw.ref_RadioButton.setChecked(True)
        self._mw.lia_frequency_DoubleSpinBox.setEnabled(False)
        if self._eproc_logic.is_microwave_sweep:
            self._mw.ms_RadioButton.setChecked(True)
            self._mw.fs_mw_frequency_DoubleSpinBox.setEnabled(False)
            self._mw.fs_mw_power_DoubleSpinBox.setEnabled(False)
            self._mw.fs_start_DoubleSpinBox.setEnabled(False)
            self._mw.fs_step_DoubleSpinBox.setEnabled(False)
            self._mw.fs_stop_DoubleSpinBox.setEnabled(False)
            self._mw.fs_start_LineEdit.setEnabled(False)
            self._mw.fs_step_LineEdit.setEnabled(False)
            self._mw.fs_stop_LineEdit.setEnabled(False)

        else:
            self._mw.fs_RadioButton.setChecked(True)
            self._mw.ms_field_DoubleSpinBox.setEnabled(False)
            self._mw.ms_mw_power_DoubleSpinBox.setEnabled(False)
            self._mw.ms_start_DoubleSpinBox.setEnabled(False)
            self._mw.ms_step_DoubleSpinBox.setEnabled(False)
            self._mw.ms_stop_DoubleSpinBox.setEnabled(False)
            self._mw.ms_start_LineEdit.setEnabled(False)
            self._mw.ms_step_LineEdit.setEnabled(False)
            self._mw.ms_stop_LineEdit.setEnabled(False)


        # connect settings signals
        self._mw.action_Analysis.triggered.connect(self._menu_analysis)
        self._mw.action_Motorized_Stages.triggered.connect(self._menu_motorized_stages)
        #self._sd.accepted.connect(self.update_settings)
        #self._sd.rejected.connect(self.reject_settings)
        #self._sd.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(
            #self.update_settings)
        #self.reject_settings()

        # Show the Main EPRoC GUI:
        self.show()

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        # Disconnect signals
        self._sd.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.disconnect()
        self._sd.accepted.disconnect()
        self._sd.rejected.disconnect()
        self._eproc_logic.sigParameterUpdated.disconnect()
        self._eproc_logic.sigOutputStateUpdated.disconnect()
        self._eproc_logic.sigSetLabelEprocPlots.disconnect()
        self._eproc_logic.sigEprocPlotsUpdated.disconnect()
        self._eproc_logic.sigEprocRemainingTimeUpdated.disconnect()

        self.sigStartEproc.disconnect()
        self.sigStopEproc.disconnect()
        self.sigExtRefOn.disconnect()
        self.sigExtRefOff.disconnect()
        self.sigPowerSupplyBoardOn.disconnect()
        self.sigPowerSupplyBoardOff.disconnect()
        self.sigPowerSupplyAmplifierOn.disconnect()
        self.sigPowerSupplyAmplifierOff.disconnect()
        self.sigMsParamsChanged.disconnect()
        self.sigFsParamsChanged.disconnect()
        self.sigLockinParamsChanged.disconnect()
        self.sigRefParamsChanged.disconnect()
        self.sigScanParamsChanged.disconnect()
        self.sigPowerSupplyBoardParamsChanged.disconnect()
        self.sigPowerSupplyAmplifierParamsChanged.disconnect()
        self.sigSaveMeasurement.disconnect()

        self._mw.action_Analysis.triggered.disconnect()

        self._mw.action_run_stop.triggered.disconnect()
        self._mw.action_stop_next_sweep.triggered.disconnect()
        self._mw.action_toggle_cw.triggered.disconnect()
        self._mw.action_toggle_modulation.triggered.disconnect()
        self._mw.action_Save.triggered.disconnect()

        self._mw.ms_field_DoubleSpinBox.editingFinished.disconnect()
        self._mw.ms_mw_power_DoubleSpinBox.editingFinished.disconnect()
        self._mw.ms_start_DoubleSpinBox.editingFinished.disconnect()
        self._mw.ms_step_DoubleSpinBox.editingFinished.disconnect()
        self._mw.ms_stop_DoubleSpinBox.editingFinished.disconnect()

        self._mw.fs_mw_frequency_DoubleSpinBox.editingFinished.disconnect()
        self._mw.fs_mw_power_DoubleSpinBox.editingFinished.disconnect()
        self._mw.fs_start_DoubleSpinBox.editingFinished.disconnect()
        self._mw.fs_step_DoubleSpinBox.editingFinished.disconnect()
        self._mw.fs_stop_DoubleSpinBox.editingFinished.disconnect()

        self._mw.lia_range_ComboBox.currentTextChanged.disconnect()
        self._mw.lia_acdc_coupling_ComboBox.currentTextChanged.disconnect()
        self._mw.lia_taua_ComboBox.currentTextChanged.disconnect()
        self._mw.lia_taub_ComboBox.currentTextChanged.disconnect()
        self._mw.lia_slope_ComboBox.currentTextChanged.disconnect()
        self._mw.lia_configuration_ComboBox.currentTextChanged.disconnect()
        self._mw.lia_uac_DoubleSpinBox.editingFinished.disconnect()
        self._mw.lia_frequency_DoubleSpinBox.editingFinished.disconnect()
        self._mw.lia_phasea_DoubleSpinBox.editingFinished.disconnect()
        self._mw.lia_phaseb_DoubleSpinBox.editingFinished.disconnect()
        self._mw.lia_harmonic_SpinBox.editingFinished.disconnect()
        self._mw.lia_waiting_time_factor_DoubleSpinBox.editingFinished.disconnect()

        self._mw.ms_RadioButton.toggled.disconnect()
        self._mw.fs_RadioButton.toggled.disconnect()
        self._mw.ref_RadioButton.toggled.disconnect()
        self._mw.power_supply_board_RadioButton.toggled.disconnect()
        self._mw.power_supply_amplifier_RadioButton.toggled.disconnect()

        self._mw.number_of_sweeps_SpinBox.editingFinished.disconnect()
        self._mw.number_of_accumulations_SpinBox.editingFinished.disconnect()

        self._mw.ref_shape_ComboBox.currentTextChanged.disconnect()
        self._mw.ref_frequency_DoubleSpinBox.editingFinished.disconnect()
        self._mw.ref_deviation_DoubleSpinBox.editingFinished.disconnect()
        self._mw.ref_mode_ComboBox.currentTextChanged.disconnect()

        self._mw.psb_voltage_outp1_DoubleSpinBox.editingFinished.disconnect()
        self._mw.psb_voltage_outp2_DoubleSpinBox.editingFinished.disconnect()
        self._mw.psb_current_max_outp1_DoubleSpinBox.editingFinished.disconnect()
        self._mw.psb_current_max_outp2_DoubleSpinBox.editingFinished.disconnect()
        self._mw.psa_voltage_outp1_DoubleSpinBox.editingFinished.disconnect()
        self._mw.psa_voltage_outp2_DoubleSpinBox.editingFinished.disconnect()
        self._mw.psa_current_max_outp1_DoubleSpinBox.editingFinished.disconnect()
        self._mw.psa_current_max_outp2_DoubleSpinBox.editingFinished.disconnect()

        self._mw.close()
        return 0

    def show(self):
        """Make window visible and put it above all other windows. """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    '''
    def add_ranges_gui_elements_clicked(self):
        """
        When button >>add range<< is pushed add some buttons to the gui and connect accordingly to the
        logic.
        :return:
        """
        # make sure the logic keeps track
        groupBox = self._mw.mwsweep_eproc_control_DockWidget.ranges_groupBox
        gridLayout = groupBox.layout()
        constraints = self._eproc_logic.get_hw_constraints()

        insertion_row = self._eproc_logic.ranges
        # start
        start_label = QtWidgets.QLabel(groupBox)
        start_label.setText('Start:')
        setattr(self._mw.mwsweep_eproc_control_DockWidget, 'start_label_{}'.format(insertion_row), start_label)
        start_freq_DoubleSpinBox = ScienDSpinBox(groupBox)
        start_freq_DoubleSpinBox.setSuffix('Hz')
        start_freq_DoubleSpinBox.setMaximum(constraints.max_frequency)
        start_freq_DoubleSpinBox.setMinimum(constraints.min_frequency)
        start_freq_DoubleSpinBox.setMinimumSize(QtCore.QSize(80, 0))
        start_freq_DoubleSpinBox.setValue(self._eproc_logic.mw_starts[0])
        start_freq_DoubleSpinBox.setMinimumWidth(75)
        start_freq_DoubleSpinBox.setMaximumWidth(100)
        start_freq_DoubleSpinBox.editingFinished.connect(self.change_sweep_params)
        setattr(self._mw.mwsweep_eproc_control_DockWidget, 'start_freq_DoubleSpinBox_{}'.format(insertion_row),
                start_freq_DoubleSpinBox)
        gridLayout.addWidget(start_label, insertion_row, 1, 1, 1)
        gridLayout.addWidget(start_freq_DoubleSpinBox, insertion_row, 2, 1, 1)

        # step
        step_label = QtWidgets.QLabel(groupBox)
        step_label.setText('Step:')
        setattr(self._mw.mwsweep_eproc_control_DockWidget, 'step_label_{}'.format(insertion_row), step_label)
        step_freq_DoubleSpinBox = ScienDSpinBox(groupBox)
        step_freq_DoubleSpinBox.setSuffix('Hz')
        step_freq_DoubleSpinBox.setMaximum(100e9)
        step_freq_DoubleSpinBox.setMinimumSize(QtCore.QSize(80, 0))
        step_freq_DoubleSpinBox.setValue(self._eproc_logic.mw_steps[0])
        step_freq_DoubleSpinBox.setMinimumWidth(75)
        step_freq_DoubleSpinBox.setMaximumWidth(100)
        step_freq_DoubleSpinBox.editingFinished.connect(self.change_sweep_params)
        setattr(self._mw.mwsweep_eproc_control_DockWidget, 'step_freq_DoubleSpinBox_{}'.format(insertion_row),
                step_freq_DoubleSpinBox)
        gridLayout.addWidget(step_label, insertion_row, 3, 1, 1)
        gridLayout.addWidget(step_freq_DoubleSpinBox, insertion_row, 4, 1, 1)

        # stop
        stop_label = QtWidgets.QLabel(groupBox)
        stop_label.setText('Stop:')
        setattr(self._mw.mwsweep_eproc_control_DockWidget, 'stop_label_{}'.format(insertion_row), stop_label)
        stop_freq_DoubleSpinBox = ScienDSpinBox(groupBox)
        stop_freq_DoubleSpinBox.setSuffix('Hz')
        stop_freq_DoubleSpinBox.setMaximum(constraints.max_frequency)
        stop_freq_DoubleSpinBox.setMinimum(constraints.min_frequency)
        stop_freq_DoubleSpinBox.setMinimumSize(QtCore.QSize(80, 0))
        stop_freq_DoubleSpinBox.setValue(self._eproc_logic.mw_stops[0])
        stop_freq_DoubleSpinBox.setMinimumWidth(75)
        stop_freq_DoubleSpinBox.setMaximumWidth(100)
        stop_freq_DoubleSpinBox.editingFinished.connect(self.change_sweep_params)
        setattr(self._mw.mwsweep_eproc_control_DockWidget, 'stop_freq_DoubleSpinBox_{}'.format(insertion_row),
                stop_freq_DoubleSpinBox)

        gridLayout.addWidget(stop_label, insertion_row, 5, 1, 1)
        gridLayout.addWidget(stop_freq_DoubleSpinBox, insertion_row, 6, 1, 1)

        starts = self.get_frequencies_from_spinboxes('start')
        stops = self.get_frequencies_from_spinboxes('stop')
        steps = self.get_frequencies_from_spinboxes('step')
        power = self._mw.ms_mw_power_DoubleSpinBox.value()

        self.sigMwSweepParamsChanged.emit(starts, stops, steps, power)
        self._mw.fit_range_SpinBox.setMaximum(self._eproc_logic.ranges)
        self._mw.mwsweep_eproc_control_DockWidget.matrix_range_SpinBox.setMaximum(self._eproc_logic.ranges)
        self._eproc_logic.ranges += 1

        # remove stuff that remained from the old range that might have been in place there
        key = 'channel: {0}, range: {1}'.format(self.display_channel, self._eproc_logic.ranges - 1)
        if key in self._eproc_logic.fits_performed:
            self._eproc_logic.fits_performed.pop(key)
        return

    def remove_ranges_gui_elements_clicked(self):
        if self._eproc_logic.ranges == 1:
            return

        remove_row = self._eproc_logic.ranges - 1

        groupBox = self._mw.mwsweep_eproc_control_DockWidget.ranges_groupBox
        gridLayout = groupBox.layout()

        object_dict = self.get_objects_from_groupbox_row(remove_row)

        for object_name in object_dict:
            if 'DoubleSpinBox' in object_name:
                object_dict[object_name].editingFinished.disconnect()
            object_dict[object_name].hide()
            gridLayout.removeWidget(object_dict[object_name])
            del self._mw.mwsweep_eproc_control_DockWidget.__dict__[object_name]

        starts = self.get_frequencies_from_spinboxes('start')
        stops = self.get_frequencies_from_spinboxes('stop')
        steps = self.get_frequencies_from_spinboxes('step')
        power = self._mw.ms_mw_power_DoubleSpinBox.value()
        self.sigMwSweepParamsChanged.emit(starts, stops, steps, power)

        # in case the removed range is the one selected for fitting right now adjust the value
        self._eproc_logic.ranges -= 1
        max_val = self._eproc_logic.ranges - 1
        self._mw.fit_range_SpinBox.setMaximum(max_val)
        if self._eproc_logic.range_to_fit > max_val:
            self._eproc_logic.range_to_fit = max_val

        self._mw.fit_range_SpinBox.setMaximum(max_val)

        self._mw.mwsweep_eproc_control_DockWidget.matrix_range_SpinBox.setMaximum(max_val)
        if self._mw.mwsweep_eproc_control_DockWidget.matrix_range_SpinBox.value() > max_val:
            self._mw.mwsweep_eproc_control_DockWidget.matrix_range_SpinBox.setValue(max_val)

        return

    def get_objects_from_groupbox_row(self, row):
        # get elements from the row
        # first strings

        start_label_str = 'start_label_{}'.format(row)
        step_label_str = 'step_label_{}'.format(row)
        stop_label_str = 'stop_label_{}'.format(row)

        # get widgets
        start_freq_DoubleSpinBox_str = 'start_freq_DoubleSpinBox_{}'.format(row)
        step_freq_DoubleSpinBox_str = 'step_freq_DoubleSpinBox_{}'.format(row)
        stop_freq_DoubleSpinBox_str = 'stop_freq_DoubleSpinBox_{}'.format(row)

        # now get the objects
        start_label = getattr(self._mw.mwsweep_eproc_control_DockWidget, start_label_str)
        step_label = getattr(self._mw.mwsweep_eproc_control_DockWidget, step_label_str)
        stop_label = getattr(self._mw.mwsweep_eproc_control_DockWidget, stop_label_str)

        start_freq_DoubleSpinBox = getattr(self._mw.mwsweep_eproc_control_DockWidget, start_freq_DoubleSpinBox_str)
        step_freq_DoubleSpinBox = getattr(self._mw.mwsweep_eproc_control_DockWidget, step_freq_DoubleSpinBox_str)
        stop_freq_DoubleSpinBox = getattr(self._mw.mwsweep_eproc_control_DockWidget, stop_freq_DoubleSpinBox_str)

        return_dict = {start_label_str: start_label, step_label_str: step_label,
                       stop_label_str: stop_label,
                       start_freq_DoubleSpinBox_str: start_freq_DoubleSpinBox,
                       step_freq_DoubleSpinBox_str: step_freq_DoubleSpinBox,
                       stop_freq_DoubleSpinBox_str: stop_freq_DoubleSpinBox
                       }

        return return_dict

    def get_freq_dspinboxes_from_groubpox(self, identifier):
        dspinboxes = []
        for name in self._mw.mwsweep_eproc_control_DockWidget.__dict__:
            box_name = identifier + '_freq_DoubleSpinBox'
            if box_name in name:
                freq_DoubleSpinBox = getattr(self._mw.mwsweep_eproc_control_DockWidget, name)
                dspinboxes.append(freq_DoubleSpinBox)

        return dspinboxes

    def get_all_dspinboxes_from_groupbox(self):
        identifiers = ['start', 'step', 'stop']

        all_spinboxes = {}
        for identifier in identifiers:
            all_spinboxes[identifier] = self.get_freq_dspinboxes_from_groubpox(identifier)

        return all_spinboxes

    def get_frequencies_from_spinboxes(self, identifier):
        dspinboxes = self.get_freq_dspinboxes_from_groubpox(identifier)
        freqs = [dspinbox.value() for dspinbox in dspinboxes]
        return freqs

    def get_frequencies_from_row(self, row):
        object_dict = self.get_objects_from_groupbox_row(row)
        for object_name in object_dict:
            if "DoubleSpinBox" in object_name:
                if "start" in object_name:
                    start = object_dict[object_name].value()
                elif "step" in object_name:
                    step = object_dict[object_name].value()
                elif "stop" in object_name:
                    stop = object_dict[object_name].value()

        return start, stop, step
    '''
    # these two shouldnt be in the gui file probably :|
    def tau_float_to_str(self, tau):
        if tau < 1:
            tau *= 1000
            if tau < 1:
                tau = str(int(tau * 1000)) + ' us'
            else:
                tau = str(int(tau)) + ' ms'
        elif tau < 1000:
            tau = str(int(tau)) + ' s'
        else:
            tau = str(int(tau / 1000)) + ' ks'
        return tau

    def tau_str_to_float(self, tau):
        num, unit = tau.split(' ')
        tau = float(num)
        if unit == 'us':
            tau /= 1000000
        elif unit == 'ms':
            tau /= 1000
        elif unit == 'ks':
            tau *= 1000
        return tau

    def set_label_eproc_plots(self, is_ms):
        if is_ms:
            x_label = 'Frequency'
            x_units = 'Hz'
        else:
            x_label = 'Magnetic field'
            x_units = 'G'
        self._mw.ch1_PlotWidget.setLabel(axis='bottom', text=x_label, units=x_units)
        self._mw.ch2_PlotWidget.setLabel(axis='bottom', text=x_label, units=x_units)
        self._mw.ch3_PlotWidget.setLabel(axis='bottom', text=x_label, units=x_units)
        self._mw.ch4_PlotWidget.setLabel(axis='bottom', text=x_label, units=x_units)
        return

    # all the procedure should be checked comparing with odmrgui: set enabled false and then enabled through update status? investigate!!
    def toggle_cw(self, is_checked):
        if is_checked:
            self.sigToggleCwOn.emit()
        else:
            self.sigToggleCwOff.emit()
        return

    def toggle_modulation(self, is_checked):
        if is_checked:
            self.sigToggleModulationOn.emit()
        else:
            self.sigToggleModulationOff.emit()
        return

    def run_stop_scan(self, is_checked):
        """ Manages what happens if eproc scan is started/stopped. """
        # Update measurement status (activate/deactivate widgets/actions)
        if is_checked:
            self._mw.action_stop_next_sweep.setEnabled(True)
            self._mw.action_toggle_cw.setEnabled(False)
            self._mw.action_toggle_modulation.setEnabled(False)
            # Set every Box and Button in the gui as not enabled
            for widget_name in self._mw.__dict__.keys():
                if widget_name.endswith('Box') or widget_name.endswith('Button'):
                    widg = getattr(self._mw, widget_name)
                    widg.setEnabled(False)
            self.sigStartEproc.emit()
        else:
            self.sigStopEproc.emit()
        return

    def update_status(self, is_running):
        """
        Update the display for a change in the microwave status (mode and output).

        @param str mw_mode: is the microwave output active?
        @param bool is_running: is the microwave output active?
        """
        # Block signals from firing
        self._mw.action_run_stop.blockSignals(True)
        self._mw.action_stop_next_sweep.blockSignals(True)
        self._mw.action_toggle_cw.blockSignals(True) # are these two necessary?
        self._mw.action_toggle_modulation.blockSignals(True)

        if not is_running:
            self._mw.action_run_stop.setChecked(False)
            self._mw.action_stop_next_sweep.setChecked(False)
            self._mw.action_stop_next_sweep.setEnabled(False) # is this necessary?
            self._mw.action_toggle_cw.setEnabled(True)
            self._mw.action_toggle_modulation.setEnabled(True)
            # Set enabled every Box and Button in the gui
            for widget_name in self._mw.__dict__.keys():
                if widget_name.endswith('Box') or widget_name.endswith('Button'):
                    widg = getattr(self._mw, widget_name)
                    widg.setEnabled(True)
            # Set disabled Boxes depending on which RadioButton is checked
            if self._mw.ms_RadioButton.isChecked():
                self._mw.fs_mw_frequency_DoubleSpinBox.setEnabled(False)
                self._mw.fs_mw_power_DoubleSpinBox.setEnabled(False)
                self._mw.fs_start_DoubleSpinBox.setEnabled(False)
                self._mw.fs_step_DoubleSpinBox.setEnabled(False)
                self._mw.fs_stop_DoubleSpinBox.setEnabled(False)
            else:
                self._mw.ms_field_DoubleSpinBox.setEnabled(False)
                self._mw.ms_mw_power_DoubleSpinBox.setEnabled(False)
                self._mw.ms_start_DoubleSpinBox.setEnabled(False)
                self._mw.ms_step_DoubleSpinBox.setEnabled(False)
                self._mw.ms_stop_DoubleSpinBox.setEnabled(False)
            if self._mw.ref_RadioButton.isChecked():
                self._mw.lia_frequency_DoubleSpinBox.setEnabled(False)
            else:
                self._mw.ref_shape_ComboBox.setEnabled(False)
                self._mw.ref_frequency_DoubleSpinBox.setEnabled(False)
                self._mw.ref_deviation_DoubleSpinBox.setEnabled(False)
                self._mw.ref_mode_ComboBox.setEnabled(False)

        # Unblock signal firing
        self._mw.action_run_stop.blockSignals(False)
        self._mw.action_stop_next_sweep.blockSignals(False)
        self._mw.action_toggle_cw.blockSignals(False)
        self._mw.action_toggle_modulation.blockSignals(False)
        return

    def update_plots(self, eproc_data_x, eproc_data_y):
        """ Refresh the plot widgets with new data. """
        # Update mean signal plot
        self.ch1_image.setData(eproc_data_x, eproc_data_y[:, 0])
        self.ch2_image.setData(eproc_data_x, eproc_data_y[:, 1])
        self.ch3_image.setData(eproc_data_x, eproc_data_y[:, 2])
        self.ch4_image.setData(eproc_data_x, eproc_data_y[:, 3])
        return

    def update_parameter(self, param_dict):
        """ Update the parameter display in the GUI.

        @param param_dict:
        @return:

        Any change event from the logic should call this update function.
        The update will block the GUI signals from emitting a change back to the
        logic.
        """
        # Microwave sweep parameters Dock widget
        param = param_dict.get('ms_field')
        if param is not None:
            self._mw.ms_field_DoubleSpinBox.blockSignals(True)
            self._mw.ms_field_DoubleSpinBox.setValue(param)
            self._mw.ms_field_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('ms_mw_power')
        if param is not None:
            self._mw.ms_mw_power_DoubleSpinBox.blockSignals(True)
            self._mw.ms_mw_power_DoubleSpinBox.setValue(param)
            self._mw.ms_mw_power_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('ms_start')
        if param is not None:
            self._mw.ms_start_DoubleSpinBox.blockSignals(True)
            self._mw.ms_start_DoubleSpinBox.setValue(param)
            self._mw.ms_start_DoubleSpinBox.blockSignals(False)
            self._mw.ms_start_LineEdit.setText(self.mw_to_field(param))

        param = param_dict.get('ms_step')
        if param is not None:
            self._mw.ms_step_DoubleSpinBox.blockSignals(True)
            self._mw.ms_step_DoubleSpinBox.setValue(param)
            self._mw.ms_step_DoubleSpinBox.blockSignals(False)
            self._mw.ms_step_LineEdit.setText(self.mw_to_field(param))

        param = param_dict.get('ms_stop')
        if param is not None:
            self._mw.ms_stop_DoubleSpinBox.blockSignals(True)
            self._mw.ms_stop_DoubleSpinBox.setValue(param)
            self._mw.ms_stop_DoubleSpinBox.blockSignals(False)
            self._mw.ms_stop_LineEdit.setText(self.mw_to_field(param))

        # Field sweep parameters Dock widget
        param = param_dict.get('fs_mw_frequency')
        if param is not None:
            self._mw.fs_mw_frequency_DoubleSpinBox.blockSignals(True)
            self._mw.fs_mw_frequency_DoubleSpinBox.setValue(param)
            self._mw.fs_mw_frequency_DoubleSpinBox.blockSignals(False)


        param = param_dict.get('fs_mw_power')
        if param is not None:
            self._mw.fs_mw_power_DoubleSpinBox.blockSignals(True)
            self._mw.fs_mw_power_DoubleSpinBox.setValue(param)
            self._mw.fs_mw_power_DoubleSpinBox.blockSignals(False)


        param = param_dict.get('fs_start')
        if param is not None:
            self._mw.fs_start_DoubleSpinBox.blockSignals(True)
            self._mw.fs_start_DoubleSpinBox.setValue(param)
            self._mw.fs_start_DoubleSpinBox.blockSignals(False)
            self._mw.fs_start_LineEdit.setText(self.field_to_mw(param))

        param = param_dict.get('fs_step')
        if param is not None:
            self._mw.fs_step_DoubleSpinBox.blockSignals(True)
            self._mw.fs_step_DoubleSpinBox.setValue(param)
            self._mw.fs_step_DoubleSpinBox.blockSignals(False)
            self._mw.fs_step_LineEdit.setText(self.field_to_mw(param))

        param = param_dict.get('fs_stop')
        if param is not None:
            self._mw.fs_stop_DoubleSpinBox.blockSignals(True)
            self._mw.fs_stop_DoubleSpinBox.setValue(param)
            self._mw.fs_stop_DoubleSpinBox.blockSignals(False)
            self._mw.fs_stop_LineEdit.setText(self.field_to_mw(param))

        # Lockin parameters Dock widget
        param = param_dict.get('lia_range')
        if param is not None:
            self._mw.lia_range_ComboBox.blockSignals(True)
            self._mw.lia_range_ComboBox.setCurrentText(param)
            self._mw.lia_range_ComboBox.blockSignals(False)

        param = param_dict.get('lia_uac')
        if param is not None:
            self._mw.lia_uac_DoubleSpinBox.blockSignals(True)
            self._mw.lia_uac_DoubleSpinBox.setValue(param)
            self._mw.lia_uac_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('lia_coupling')
        if param is not None:
            self._mw.lia_acdc_coupling_ComboBox.blockSignals(True)
            self._mw.lia_acdc_coupling_ComboBox.setCurrentText(param)
            self._mw.lia_acdc_coupling_ComboBox.blockSignals(False)

        param = param_dict.get('lia_int_ref_freq')
        if param is not None:
            self._mw.lia_frequency_DoubleSpinBox.blockSignals(True)
            self._mw.lia_frequency_DoubleSpinBox.setValue(param)
            self._mw.lia_frequency_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('lia_tauA')
        if param is not None:
            self._mw.lia_taua_ComboBox.blockSignals(True)
            self._mw.lia_taua_ComboBox.setCurrentText(self.tau_float_to_str(param))
            self._mw.lia_taua_ComboBox.blockSignals(False)

        param = param_dict.get('lia_phase_A')
        if param is not None:
            self._mw.lia_phasea_DoubleSpinBox.blockSignals(True)
            self._mw.lia_phasea_DoubleSpinBox.setValue(param)
            self._mw.lia_phasea_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('lia_tauB')
        if param is not None:
            self._mw.lia_taub_ComboBox.blockSignals(True)
            self._mw.lia_taub_ComboBox.setCurrentText(self.tau_float_to_str(param))
            self._mw.lia_taub_ComboBox.blockSignals(False)

        param = param_dict.get('lia_phaseB')
        if param is not None:
            self._mw.lia_phaseb_DoubleSpinBox.blockSignals(True)
            self._mw.lia_phaseb_DoubleSpinBox.setValue(param)
            self._mw.lia_phaseb_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('lia_waiting_time_factor')
        if param is not None:
            self._mw.lia_waiting_time_factor_DoubleSpinBox.blockSignals(True)
            self._mw.lia_waiting_time_factor_DoubleSpinBox.setValue(param)
            self._mw.lia_waiting_time_factor_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('lia_harmonic')
        if param is not None:
            self._mw.lia_harmonic_SpinBox.blockSignals(True)
            self._mw.lia_harmonic_SpinBox.setValue(param)
            self._mw.lia_harmonic_SpinBox.blockSignals(False)

        param = param_dict.get('lia_slope')
        if param is not None:
            self._mw.lia_slope_ComboBox.blockSignals(True)
            self._mw.lia_slope_ComboBox.setCurrentText(param)
            self._mw.lia_slope_ComboBox.blockSignals(False)

        param = param_dict.get('lia_configuration')
        if param is not None:
            self._mw.lia_configuration_ComboBox.blockSignals(True)
            self._mw.lia_configuration_ComboBox.setCurrentText(param)
            self._mw.lia_configuration_ComboBox.blockSignals(False)

        # Order from here
        param = param_dict.get('fm_shape')
        if param is not None:
            self._mw.ref_shape_ComboBox.blockSignals(True)
            self._mw.ref_shape_ComboBox.setCurrentText(param)
            self._mw.ref_shape_ComboBox.blockSignals(False)

        param = param_dict.get('fm_ext_freq')
        if param is not None:
            self._mw.ref_frequency_DoubleSpinBox.blockSignals(True)
            self._mw.ref_frequency_DoubleSpinBox.setValue(param)
            self._mw.ref_frequency_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('ref_deviation')
        if param is not None:
            self._mw.ref_deviation_DoubleSpinBox.blockSignals(True)
            self._mw.ref_deviation_DoubleSpinBox.setValue(param)
            self._mw.ref_deviation_DoubleSpinBox.blockSignals(False)
            self._mw.ref_deviation_LineEdit.setText(self.field_to_mw(param))


        param = param_dict.get('fm_mode')
        if param is not None:
            self._mw.ref_mode_ComboBox.blockSignals(True)
            self._mw.ref_mode_ComboBox.setCurrentText(param)
            self._mw.ref_mode_ComboBox.blockSignals(False)

        param = param_dict.get('number_of_sweeps')
        if param is not None:
            self._mw.number_of_sweeps_SpinBox.blockSignals(True)
            self._mw.number_of_sweeps_SpinBox.setValue(param)
            self._mw.number_of_sweeps_SpinBox.blockSignals(False)

        param = param_dict.get('number_of_accumulations')
        if param is not None:
            self._mw.number_of_accumulations_SpinBox.blockSignals(True)
            self._mw.number_of_accumulations_SpinBox.setValue(param)
            self._mw.number_of_accumulations_SpinBox.blockSignals(False)

        param = param_dict.get('psb_voltage_outp1')
        if param is not None:
            self._mw.psb_voltage_outp1_DoubleSpinBox.blockSignals(True)
            self._mw.psb_voltage_outp1_DoubleSpinBox.setValue(param)
            self._mw.psb_voltage_outp1_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('psb_voltage_outp2')
        if param is not None:
            self._mw.psb_voltage_outp2_DoubleSpinBox.blockSignals(True)
            self._mw.psb_voltage_outp2_DoubleSpinBox.setValue(param)
            self._mw.psb_voltage_outp2_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('psb_current_max_outp1')
        if param is not None:
            self._mw.psb_current_max_outp1_DoubleSpinBox.blockSignals(True)
            self._mw.psb_current_max_outp1_DoubleSpinBox.setValue(param)
            self._mw.psb_current_max_outp1_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('psb_current_max_outp2')
        if param is not None:
            self._mw.psb_current_max_outp2_DoubleSpinBox.blockSignals(True)
            self._mw.psb_current_max_outp2_DoubleSpinBox.setValue(param)
            self._mw.psb_current_max_outp2_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('psa_voltage_outp1')
        if param is not None:
            self._mw.psa_voltage_outp1_DoubleSpinBox.blockSignals(True)
            self._mw.psa_voltage_outp1_DoubleSpinBox.setValue(param)
            self._mw.psa_voltage_outp1_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('psa_voltage_outp2')
        if param is not None:
            self._mw.psa_voltage_outp2_DoubleSpinBox.blockSignals(True)
            self._mw.psa_voltage_outp2_DoubleSpinBox.setValue(param)
            self._mw.psa_voltage_outp2_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('psa_current_max_outp1')
        if param is not None:
            self._mw.psa_current_max_outp1_DoubleSpinBox.blockSignals(True)
            self._mw.psa_current_max_outp1_DoubleSpinBox.setValue(param)
            self._mw.psa_current_max_outp1_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('psa_current_max_outp2')
        if param is not None:
            self._mw.psa_current_max_outp2_DoubleSpinBox.blockSignals(True)
            self._mw.psa_current_max_outp2_DoubleSpinBox.setValue(param)
            self._mw.psa_current_max_outp2_DoubleSpinBox.blockSignals(False)
        return

    def change_fs_params(self):
        """ Change parameters from the field sweep Dock Widget """
        frequency = self._mw.fs_mw_frequency_DoubleSpinBox.value()
        power = self._mw.fs_mw_power_DoubleSpinBox.value()
        start = self._mw.fs_start_DoubleSpinBox.value()
        step = self._mw.fs_step_DoubleSpinBox.value()
        stop = self._mw.fs_stop_DoubleSpinBox.value()
        self.sigFsParamsChanged.emit(start, step, stop, frequency, power)
        return

    def change_ms_params(self):
        """ Change parameters from the field sweep Dock Widget """
        field = self._mw.ms_field_DoubleSpinBox.value()
        power = self._mw.ms_mw_power_DoubleSpinBox.value()
        start = self._mw.ms_start_DoubleSpinBox.value()
        step = self._mw.ms_step_DoubleSpinBox.value()
        stop = self._mw.ms_stop_DoubleSpinBox.value()
        self.sigMsParamsChanged.emit(start, step, stop, field, power)
        return

    def change_lockin_params(self):
        """ Change lockin parameters """
        input_range = self._mw.lia_range_ComboBox.currentText()
        uac = self._mw.lia_uac_DoubleSpinBox.value()
        coupling = self._mw.lia_acdc_coupling_ComboBox.currentText()
        int_ref_freq = self._mw.lia_frequency_DoubleSpinBox.value()
        tauA = self.tau_str_to_float(self._mw.lia_taua_ComboBox.currentText())
        phaseA = self._mw.lia_phasea_DoubleSpinBox.value()
        tauB = self.tau_str_to_float(self._mw.lia_taub_ComboBox.currentText())
        phaseB = self._mw.lia_phaseb_DoubleSpinBox.value()
        waiting_time_factor = self._mw.lia_waiting_time_factor_DoubleSpinBox.value()
        harmonic = self._mw.lia_harmonic_SpinBox.value()
        slope = self._mw.lia_slope_ComboBox.currentText()
        configuration = self._mw.lia_configuration_ComboBox.currentText()
        self.sigLockinParamsChanged.emit(input_range, uac, coupling, int_ref_freq, tauA, phaseA, tauB, phaseB,
                                         waiting_time_factor, harmonic, slope, configuration)
        return

    def on_off_sweep(self):
        if self._mw.ms_RadioButton.isChecked():
            self._eproc_logic.is_microwave_sweep = True
            self._mw.ms_field_DoubleSpinBox.setEnabled(True)
            self._mw.ms_mw_power_DoubleSpinBox.setEnabled(True)
            self._mw.ms_start_DoubleSpinBox.setEnabled(True)
            self._mw.ms_step_DoubleSpinBox.setEnabled(True)
            self._mw.ms_stop_DoubleSpinBox.setEnabled(True)
            self._mw.ms_start_LineEdit.setEnabled(True)
            self._mw.ms_step_LineEdit.setEnabled(True)
            self._mw.ms_stop_LineEdit.setEnabled(True)
            self._mw.fs_mw_frequency_DoubleSpinBox.setEnabled(False)
            self._mw.fs_mw_power_DoubleSpinBox.setEnabled(False)
            self._mw.fs_start_DoubleSpinBox.setEnabled(False)
            self._mw.fs_step_DoubleSpinBox.setEnabled(False)
            self._mw.fs_stop_DoubleSpinBox.setEnabled(False)
            self._mw.fs_start_LineEdit.setEnabled(False)
            self._mw.fs_step_LineEdit.setEnabled(False)
            self._mw.fs_stop_LineEdit.setEnabled(False)
            self.change_ms_params()
        else:
            self._eproc_logic.is_microwave_sweep = False
            self._mw.fs_mw_frequency_DoubleSpinBox.setEnabled(True)
            self._mw.fs_mw_power_DoubleSpinBox.setEnabled(True)
            self._mw.fs_start_DoubleSpinBox.setEnabled(True)
            self._mw.fs_step_DoubleSpinBox.setEnabled(True)
            self._mw.fs_stop_DoubleSpinBox.setEnabled(True)
            self._mw.fs_start_LineEdit.setEnabled(True)
            self._mw.fs_step_LineEdit.setEnabled(True)
            self._mw.fs_stop_LineEdit.setEnabled(True)
            self._mw.ms_field_DoubleSpinBox.setEnabled(False)
            self._mw.ms_mw_power_DoubleSpinBox.setEnabled(False)
            self._mw.ms_start_DoubleSpinBox.setEnabled(False)
            self._mw.ms_step_DoubleSpinBox.setEnabled(False)
            self._mw.ms_stop_DoubleSpinBox.setEnabled(False)
            self._mw.ms_start_LineEdit.setEnabled(False)
            self._mw.ms_step_LineEdit.setEnabled(False)
            self._mw.ms_stop_LineEdit.setEnabled(False)
            self.change_fs_params()
        return

    def on_off_reference(self):
        if self._mw.ref_RadioButton.isChecked():
            self._eproc_logic.is_external_reference = True
            self._mw.lia_frequency_DoubleSpinBox.setEnabled(False)
            self._mw.ref_shape_ComboBox.setEnabled(True)
            self._mw.ref_frequency_DoubleSpinBox.setEnabled(True)
            self._mw.ref_deviation_DoubleSpinBox.setEnabled(True)
            self._mw.ref_mode_ComboBox.setEnabled(True)
            self.sigExtRefOn.emit()
        else:
            self._eproc_logic.is_external_reference = False
            self._mw.lia_frequency_DoubleSpinBox.setEnabled(True)
            self._mw.ref_shape_ComboBox.setEnabled(False)
            self._mw.ref_frequency_DoubleSpinBox.setEnabled(False)
            self._mw.ref_deviation_DoubleSpinBox.setEnabled(False)
            self._mw.ref_mode_ComboBox.setEnabled(False)
            self.sigExtRefOff.emit()
        return

    def change_ref_params(self):
        shape = self._mw.ref_shape_ComboBox.currentText()
        freq = self._mw.ref_frequency_DoubleSpinBox.value()
        mode = self._mw.ref_mode_ComboBox.currentText()
        dev = self._mw.ref_deviation_DoubleSpinBox.value()
        self.sigRefParamsChanged.emit(shape, freq, mode, dev)
        return

    def change_scan_params(self):
        number_of_sweeps = self._mw.number_of_sweeps_SpinBox.value()
        number_of_accumulations = self._mw.number_of_accumulations_SpinBox.value()
        self.sigScanParamsChanged.emit(number_of_sweeps, number_of_accumulations)
        return

    def on_off_psb(self, is_checked):
        if is_checked:
            self._mw.psb_voltage_outp1_DoubleSpinBox.setEnabled(False)
            self._mw.psb_voltage_outp2_DoubleSpinBox.setEnabled(False)
            self._mw.psb_current_max_outp1_DoubleSpinBox.setEnabled(False)
            self._mw.psb_current_max_outp2_DoubleSpinBox.setEnabled(False)
            self.sigPowerSupplyBoardOn.emit()
        else:
            self._mw.psb_voltage_outp1_DoubleSpinBox.setEnabled(True)
            self._mw.psb_voltage_outp2_DoubleSpinBox.setEnabled(True)
            self._mw.psb_current_max_outp1_DoubleSpinBox.setEnabled(True)
            self._mw.psb_current_max_outp2_DoubleSpinBox.setEnabled(True)
            self.sigPowerSupplyBoardOff.emit()
        return

    def change_psb_params(self):
        v1 = self._mw.psb_voltage_outp1_DoubleSpinBox.value()
        v2 = self._mw.psb_voltage_outp2_DoubleSpinBox.value()
        maxi1 = self._mw.psb_current_max_outp1_DoubleSpinBox.value()
        maxi2 = self._mw.psb_current_max_outp2_DoubleSpinBox.value()
        self.sigPowerSupplyBoardParamsChanged.emit(v1, v2, maxi1, maxi2)
        return

    def on_off_psa(self, is_checked):
        if is_checked:
            self._mw.psa_voltage_outp1_DoubleSpinBox.setEnabled(False)
            self._mw.psa_voltage_outp2_DoubleSpinBox.setEnabled(False)
            self._mw.psa_current_max_outp1_DoubleSpinBox.setEnabled(False)
            self._mw.psa_current_max_outp2_DoubleSpinBox.setEnabled(False)
            self.sigPowerSupplyAmplifierOn.emit()
        else:
            self._mw.psa_voltage_outp1_DoubleSpinBox.setEnabled(True)
            self._mw.psa_voltage_outp2_DoubleSpinBox.setEnabled(True)
            self._mw.psa_current_max_outp1_DoubleSpinBox.setEnabled(True)
            self._mw.psa_current_max_outp2_DoubleSpinBox.setEnabled(True)
            self.sigPowerSupplyAmplifierOff.emit()
        return

    def change_psa_params(self):
        v1 = self._mw.psa_voltage_outp1_DoubleSpinBox.value()
        v2 = self._mw.psa_voltage_outp2_DoubleSpinBox.value()
        maxi1 = self._mw.psa_current_max_outp1_DoubleSpinBox.value()
        maxi2 = self._mw.psa_current_max_outp2_DoubleSpinBox.value()
        self.sigPowerSupplyAmplifierParamsChanged.emit(v1, v2, maxi1, maxi2)
        return

    def update_remainingtime(self, remaining_time, scanned_lines):
        """ Updates current elapsed measurement time and completed frequency sweeps """
        self._mw.remaining_time_DisplayWidget.display(int(np.rint(remaining_time)))
        self._mw.elapsed_sweeps_DisplayWidget.display(scanned_lines)
        return

    def save_data(self):
        """ Save the sum plot, the scan marix plot and the scan data """
        filetag = self._mw.save_tag_LineEdit.text()
        self.sigSaveMeasurement.emit(filetag)
        return

    def _menu_analysis(self):
        """ Open the settings menu """
        self._sd.show()


    def _menu_motorized_stages(self):
        """ Open the settings menu """
        self._KDC101.show()

    def update_settings(self):
        """ Write the new settings from the gui to the file. """
        number_of_lines = self._sd.matrix_lines_SpinBox.value()
        clock_frequency = self._sd.clock_frequency_DoubleSpinBox.value()
        oversampling = self._sd.oversampling_SpinBox.value()
        lock_in = self._sd.lock_in_CheckBox.isChecked()
        self.sigOversamplingChanged.emit(oversampling)
        self.sigLockInChanged.emit(lock_in)
        self.sigClockFreqChanged.emit(clock_frequency)
        self.sigNumberOfLinesChanged.emit(number_of_lines)
        return

    def getLoadFile(self):
        """ Ask the user for a file where the configuration should be loaded
            from
        """
        defaultconfigpath = os.path.join(get_main_dir(), 'config')
        filename = QtWidgets.QFileDialog.getOpenFileName(
            self._sd,
            'Load Configration',
            defaultconfigpath,
            'Configuration files (*.cfg)')[0]
        if filename != '':
            reply = QtWidgets.QMessageBox.question(
                self._sd,
                'Restart',
                'Do you want to restart to use the configuration?',
                QtWidgets.QMessageBox.Yes,
                QtWidgets.QMessageBox.No
            )
            restart = (reply == QtWidgets.QMessageBox.Yes)
            self.sigLoadConfig.emit(filename, restart)

    def field_to_mw(self, field):
        return str(round((field * 2.8), 2)) + 'MHz'

    def mw_to_field(self, freq):
        return str(round((freq * 1e-6 / 2.8), 2)) + 'G'



