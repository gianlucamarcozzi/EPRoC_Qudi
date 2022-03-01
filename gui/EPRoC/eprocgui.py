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
        ui_file = os.path.join(this_dir, 'ui_eprocgui.ui')

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

class EPRoCCheckDevicesDialog(QtWidgets.QDialog):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_eproc_check_devices.ui')

        # Load it
        super(EPRoCCheckDevicesDialog, self).__init__()
        uic.loadUi(ui_file, self)

class EPRoCPowerSupplyOnDialog(QtWidgets.QDialog):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_eproc_power_supply_on.ui')

        # Load it
        super(EPRoCPowerSupplyOnDialog, self).__init__()
        uic.loadUi(ui_file, self)


class EPRoCPowerSupplyOffDialog(QtWidgets.QDialog):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_eproc_power_supply_on.ui')

        # Load it
        super(EPRoCPowerSupplyOffDialog, self).__init__()
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

    # Signals to connect the GUI to the Logic
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
    sigHome = QtCore.Signal(str)
    sigToggleXMotorOn = QtCore.Signal()
    sigToggleXMotorOff = QtCore.Signal()
    sigToggleYMotorOn = QtCore.Signal()
    sigToggleYMotorOff = QtCore.Signal()
    sigToggleZMotorOn = QtCore.Signal()
    sigToggleZMotorOff = QtCore.Signal()
    sigMove = QtCore.Signal(str)
    sigXPosition = QtCore.Signal()
    sigStartEprocMapping = QtCore.Signal(str)
    sigStopEprocMapping = QtCore.Signal()


    sigMsParamsChanged = QtCore.Signal(float, float, float, float, float)
    sigFsParamsChanged = QtCore.Signal(float, float, float, float, float)
    sigScanParamsChanged = QtCore.Signal(int, int)
    sigRefParamsChanged = QtCore.Signal(str, float, str, float)
    sigLockinParamsChanged = QtCore.Signal(str, float, str, float, float, float, float, float, float, int, str, str)
    sigFrequencyMultiplierChanged = QtCore.Signal(int)
    sigPowerSupplyBoardParamsChanged = QtCore.Signal(float, float, float, float)
    sigPowerSupplyAmplifierParamsChanged = QtCore.Signal(float, float, float, float)
    sigMotorParamsChanged = QtCore.Signal(float, float, float, float, float, float, float, float, float, float, float,
                                          float)

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
        self._checkdevdialog = EPRoCCheckDevicesDialog()
        self._psondialog = EPRoCPowerSupplyOnDialog()
        self._psoffdialog = EPRoCPowerSupplyOffDialog()
        self._KDC101 = EPRoCMotorizedStages()


        # Create a QSettings object for the mainwindow and store the actual GUI layout
        self.mwsettings = QtCore.QSettings("QUDI", "EPRoC")
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

        # Add values of time constants of lockin taking them from the hardware
        time_constants = self._eproc_logic.get_time_constants()
        for tau in time_constants:
            self._mw.lia_taua_ComboBox.addItem(self.tau_float_to_str(tau))
            self._mw.lia_taub_ComboBox.addItem(self.tau_float_to_str(tau))

        if self._eproc_logic.is_microwave_sweep:
            self._eproc_logic.plot_x = self._eproc_logic.eproc_plot_x * self._eproc_logic.frequency_multiplier
        else:
            self._eproc_logic.plot_x = self._eproc_logic.eproc_plot_x

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

        '''        
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
        '''

        ########################################################################
        #          Configuration of the various display Widgets                #
        ########################################################################
        # Take the default values from logic:
        # ms = microwave sweep, fs = field sweep, lia = lockin amplifier, psa = power supply amplifier, psb = power supply board
        # ref = reference signal=modulation signal
        self._mw.ms_field_DoubleSpinBox.setValue(self._eproc_logic.ms_field)
        self._mw.ms_mw_power_DoubleSpinBox.setValue(self._eproc_logic.ms_mw_power)
        self._mw.ms_start_DoubleSpinBox.setValue(self._eproc_logic.ms_start)
        self._mw.ms_stop_DoubleSpinBox.setValue(self._eproc_logic.ms_stop)
        self._mw.ms_step_DoubleSpinBox.setValue(self._eproc_logic.ms_step)
        self._mw.ms_start_LineEdit.setText(self.mw_to_field(self._eproc_logic.ms_start))
        self._mw.ms_step_LineEdit.setText(self.mw_to_field(self._eproc_logic.ms_step))
        self._mw.ms_stop_LineEdit.setText(self.mw_to_field(self._eproc_logic.ms_stop))

        self._mw.fs_mw_frequency_DoubleSpinBox.setValue(self._eproc_logic.fs_mw_frequency)
        self._mw.fs_mw_frequency_LineEdit.setText(self.multiplied_mw(self._eproc_logic.fs_mw_frequency))
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

        self._mw.frequency_multiplier_ComboBox.setCurrentText(str(self._eproc_logic.frequency_multiplier))

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
        self._mw.ref_deviation_ppG_LineEdit.setText(self.mw_to_field(self._eproc_logic.ref_deviation))
        self._mw.ref_deviation_ppHz_LineEdit.setText(
        self.multiplied_mw(2 * self._eproc_logic.ref_deviation))  # factor 2 to have pp
        self._mw.ref_deviation_ppG_LineEdit.setText(self.mw_to_field(2 * self._eproc_logic.ref_deviation))
        self._mw.ref_mode_ComboBox.setCurrentText(self._eproc_logic.ref_mode)

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
        self._mw.ref_RadioButton.toggled.connect(self.on_off_external_reference)
        self._mw.power_supply_board_RadioButton.toggled.connect(self.on_off_psb)
        self._mw.power_supply_amplifier_RadioButton.toggled.connect(self.on_off_psa)

        self._mw.number_of_sweeps_SpinBox.editingFinished.connect(self.change_scan_params)
        self._mw.number_of_accumulations_SpinBox.editingFinished.connect(self.change_scan_params)

        self._mw.frequency_multiplier_ComboBox.currentTextChanged.connect(self.change_frequency_multiplier)

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
        self.sigToggleModulationOn.connect(self._eproc_logic.modulation_on, QtCore.Qt.QueuedConnection)
        self.sigToggleModulationOff.connect(self._eproc_logic.modulation_off, QtCore.Qt.QueuedConnection)
        self.sigExtRefOn.connect(self._eproc_logic.lockin_ext_ref_on, QtCore.Qt.QueuedConnection)
        self.sigExtRefOff.connect(self._eproc_logic.lockin_ext_ref_off, QtCore.Qt.QueuedConnection)
        self.sigPowerSupplyBoardOn.connect(self._eproc_logic.psb_on, QtCore.Qt.QueuedConnection)
        self.sigPowerSupplyBoardOff.connect(self._eproc_logic.psb_off, QtCore.Qt.QueuedConnection)
        self.sigPowerSupplyAmplifierOn.connect(self._eproc_logic.psa_on, QtCore.Qt.QueuedConnection)
        self.sigPowerSupplyAmplifierOff.connect(self._eproc_logic.psa_off, QtCore.Qt.QueuedConnection)
        self.sigFrequencyMultiplierChanged.connect(self._eproc_logic.set_frequency_multiplier,
                                                   QtCore.Qt.QueuedConnection)

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
            # Disable everything in the fs Dockwidget except for the RadioButton
            self._mw.ms_RadioButton.setChecked(True)
            for widget_name in self._mw.__dict__.keys():
                if widget_name.startswith('fs_'):
                    widg = getattr(self._mw, widget_name)
                    widg.setEnabled(False)
            self._mw.fs_RadioButton.setEnabled(True)

        else:
            # Disable everything in the fs Dockwidget except for the RadioButton
            self._mw.fs_RadioButton.setChecked(True)
            for widget_name in self._mw.__dict__.keys():
                if widget_name.startswith('ms_'):
                    widg = getattr(self._mw, widget_name)
                    widg.setEnabled(False)
            self._mw.ms_RadioButton.setEnabled(True)

        # connect settings signals
        self._mw.action_Analysis.triggered.connect(self._menu_analysis)
        self._mw.action_Motorized_Stages.triggered.connect(self._menu_motorized_stages)

        self._checkdevdialog.accepted.connect(self.check_devices_accepted)
        self._psondialog.accepted.connect(self.power_supply_on_accepted)
        self._psondialog.rejected.connect(self.power_supply_on_rejected)
        self._psoffdialog.accepted.connect(self.power_supply_off_accepted)
        self._psoffdialog.rejected.connect(self.power_supply_off_rejected)

        # Show the Main EPRoC GUI:
        self.show()

        #######################
        #####Signal Motors#####
        #######################

        self._KDC101.action_Play.triggered.connect(self.run_stop_mapping)
        self._KDC101.save_tag_LineEdit = QtWidgets.QLineEdit(self._KDC101)
        self._KDC101.save_tag_LineEdit.setMaximumWidth(300)
        self._KDC101.save_tag_LineEdit.setMinimumWidth(200)
        self._KDC101.save_tag_LineEdit.setToolTip('Enter a nametag which will be\n'
                                              'added to the filename.')
        self._KDC101.toolBar.addWidget(self._KDC101.save_tag_LineEdit)



        # x_motor
        self._KDC101.action_toggle_x_motor.triggered.connect(self.connect_x_motor)
        self._KDC101.x_Home_PushButton.clicked.connect(self.x_home)
        self._KDC101.x_Set_Position_doubleSpinBox.setValue(self._eproc_logic.x_motor_set_position)
        self._KDC101.x_Set_Position_doubleSpinBox.editingFinished.connect(self.change_motor_params)
        #self._KDC101.x_Set_Position_doubleSpinBox.editingFinished.connect(self.x_move_to_position)
        self._KDC101.x_Move_PushButton.clicked.connect(self.x_move_to_position)
        self._KDC101.x_Start_doubleSpinBox.setValue(self._eproc_logic.x_start)
        self._KDC101.x_Start_doubleSpinBox.editingFinished.connect(self.change_motor_params)
        self._KDC101.x_Step_doubleSpinBox.setValue(self._eproc_logic.x_step)
        self._KDC101.x_Step_doubleSpinBox.editingFinished.connect(self.change_motor_params)
        self._KDC101.x_Stop_doubleSpinBox.setValue(self._eproc_logic.x_stop)
        self._KDC101.x_Stop_doubleSpinBox.editingFinished.connect(self.change_motor_params)

        #self._KDC101.x_Position_lineEdit.setText(self.x_read_position(self._eproc_logic.read_position))

        # y_motor
        self._KDC101.action_toggle_y_motor.triggered.connect(self.connect_y_motor)
        self._KDC101.y_Home_PushButton.clicked.connect(self.y_home)
        self._KDC101.y_Set_Position_doubleSpinBox.setValue(self._eproc_logic.y_motor_set_position)
        self._KDC101.y_Set_Position_doubleSpinBox.editingFinished.connect(self.change_motor_params)
        #self._KDC101.y_Set_Position_doubleSpinBox.editingFinished.connect(self.y_move_to_position)
        self._KDC101.y_Move_PushButton.clicked.connect(self.y_move_to_position)
        self._KDC101.y_Start_doubleSpinBox.setValue(self._eproc_logic.y_start)
        self._KDC101.y_Start_doubleSpinBox.editingFinished.connect(self.change_motor_params)
        self._KDC101.y_Step_doubleSpinBox.setValue(self._eproc_logic.y_step)
        self._KDC101.y_Step_doubleSpinBox.editingFinished.connect(self.change_motor_params)
        self._KDC101.y_Stop_doubleSpinBox.setValue(self._eproc_logic.y_stop)
        self._KDC101.y_Stop_doubleSpinBox.editingFinished.connect(self.change_motor_params)

        # z_motor
        self._KDC101.action_toggle_z_motor.triggered.connect(self.connect_z_motor)
        self._KDC101.z_Home_PushButton.clicked.connect(self.z_home)
        self._KDC101.z_Set_Position_doubleSpinBox.setValue(self._eproc_logic.z_motor_set_position)
        self._KDC101.z_Set_Position_doubleSpinBox.editingFinished.connect(self.change_motor_params)
        #self._KDC101.z_Set_Position_doubleSpinBox.editingFinished.connect(self.z_move_to_position)
        self._KDC101.z_Move_PushButton.clicked.connect(self.z_move_to_position)
        self._KDC101.z_Start_doubleSpinBox.setValue(self._eproc_logic.z_start)
        self._KDC101.z_Start_doubleSpinBox.editingFinished.connect(self.change_motor_params)
        self._KDC101.z_Step_doubleSpinBox.setValue(self._eproc_logic.z_step)
        self._KDC101.z_Step_doubleSpinBox.editingFinished.connect(self.change_motor_params)
        self._KDC101.z_Stop_doubleSpinBox.setValue(self._eproc_logic.z_stop)
        self._KDC101.z_Stop_doubleSpinBox.editingFinished.connect(self.change_motor_params)

        # internal trigger signals
        self.sigToggleXMotorOn.connect(self._eproc_logic.x_motor_on, QtCore.Qt.QueuedConnection)
        self.sigToggleXMotorOff.connect(self._eproc_logic.x_motor_off, QtCore.Qt.QueuedConnection)
        self.sigToggleYMotorOn.connect(self._eproc_logic.y_motor_on, QtCore.Qt.QueuedConnection)
        self.sigToggleYMotorOff.connect(self._eproc_logic.y_motor_off, QtCore.Qt.QueuedConnection)
        self.sigToggleZMotorOn.connect(self._eproc_logic.z_motor_on, QtCore.Qt.QueuedConnection)
        self.sigToggleZMotorOff.connect(self._eproc_logic.z_motor_off, QtCore.Qt.QueuedConnection)
        self.sigHome.connect(self._eproc_logic.home, QtCore.Qt.QueuedConnection)
        self.sigMotorParamsChanged.connect(self._eproc_logic.set_motor_parameters, QtCore.Qt.QueuedConnection)
        self.sigMove.connect(self._eproc_logic.move, QtCore.Qt.QueuedConnection)
        self.sigStartEprocMapping.connect(self._eproc_logic.start_eproc_mapping, QtCore.Qt.QueuedConnection)
        self.sigStopEprocMapping.connect(self._eproc_logic.stop_eproc_mapping, QtCore.Qt.QueuedConnection)
        #self.sigReadPosition.connect(self._eproc_logic.read_position, QtCore.Qt.QueuedConnection)

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        # Disconnect signals
        self._sd.accepted.disconnect()
        self._sd.rejected.disconnect()
        self._checdevdialog.accept.disconnect()
        self._psondialog.accepted.disconnect()
        self._psoffdialog.accepted.disconnect()
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
        self.sigFrequencyMultiplierChanged.disconnect()
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

        self._mw.frequency_multiplier_ComboBox.editingFinished.disconnect()

        self._mw.psb_voltage_outp1_DoubleSpinBox.editingFinished.disconnect()
        self._mw.psb_voltage_outp2_DoubleSpinBox.editingFinished.disconnect()
        self._mw.psb_current_max_outp1_DoubleSpinBox.editingFinished.disconnect()
        self._mw.psb_current_max_outp2_DoubleSpinBox.editingFinished.disconnect()
        self._mw.psa_voltage_outp1_DoubleSpinBox.editingFinished.disconnect()
        self._mw.psa_voltage_outp2_DoubleSpinBox.editingFinished.disconnect()
        self._mw.psa_current_max_outp1_DoubleSpinBox.editingFinished.disconnect()
        self._mw.psa_current_max_outp2_DoubleSpinBox.editingFinished.disconnect()

        ################
        #####motors#####
        ################

        self._KDC101.action_Play.triggered.disconnect()

        self._KDC101.x_Home_PushButton.clicked.disconnect()
        self._KDC101.y_Home_PushButton.clicked.disconnect()
        self._KDC101.z_Home_PushButton.clicked.disconnect()

        self._KDC101.action_toggle_x_motor.triggered.disconnect()
        self._KDC101.action_toggle_y_motor.triggered.disconnect()
        self._KDC101.action_toggle_z_motor.triggered.disconnect()
        self._KDC101.x_Set_Position_doubleSpinBox.editingFinished.disconnect(self.change_motor_params)
        self._KDC101.x_Move_PushButton.clicked.disconnect(self.x_move_to_position)
        self._KDC101.y_Set_Position_doubleSpinBox.editingFinished.disconnect(self.change_motor_params)
        self._KDC101.y_Move_PushButton.clicked.disconnect(self.y_move_to_position)
        self._KDC101.z_Set_Position_doubleSpinBox.editingFinished.disconnect(self.change_motor_params)
        self._KDC101.z_Move_PushButton.clicked.disconnect(self.z_move_to_position)
        self._KDC101.x_Start_doubleSpinBox.editingFinished.disconnect(self.change_motor_params)
        self._KDC101.x_Step_doubleSpinBox.editingFinished.disconnect(self.change_motor_params)
        self._KDC101.x_Stop_doubleSpinBox.editingFinished.disconnect(self.change_motor_params)
        self._KDC101.y_Start_doubleSpinBox.editingFinished.disconnect(self.change_motor_params)
        self._KDC101.y_Step_doubleSpinBox.editingFinished.disconnect(self.change_motor_params)
        self._KDC101.y_Stop_doubleSpinBox.editingFinished.disconnect(self.change_motor_params)
        self._KDC101.z_Start_doubleSpinBox.editingFinished.disconnect(self.change_motor_params)
        self._KDC101.z_Step_doubleSpinBox.editingFinished.disconnect(self.change_motor_params)
        self._KDC101.z_Stop_doubleSpinBox.editingFinished.disconnect(self.change_motor_params)

        self.sigHome.disconnect()
        self.sigMotorParamsChanged.disconnected()
        self.sigMove.diconnect(self._eproc_logic.move, QtCore.Qt.QueuedConnection)
        self.sigReadPosition.disconnect(self._eproc_logic.read_position, QtCore.Qt.QueuedConnection)
        self.sigStartEprocMapping.disconnect(self._eproc_logic.start_eproc_mapping, QtCore.Qt.QueuedConnection)
        self.sigStopEprocMapping.disconnect(self._eproc_logic.stop_eproc_mapping, QtCore.Qt.QueuedConnection)

        self._mw.close()
        self._KDC101.close()
        return 0

    def show(self):
        """Make window visible and put it above all other windows. """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

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
        """Toggle cw before starting the measurement."""
        if is_checked:
            self.sigToggleCwOn.emit()
        else:
            self.sigToggleCwOff.emit()
        return

    def toggle_modulation(self, is_checked):
        """Toggle the modulation before starting the measurement."""
        if is_checked:
            self.sigToggleModulationOn.emit()
        else:
            self.sigToggleModulationOff.emit()
        return

    def check_devices_accepted(self):
        self._mw.action_stop_next_sweep.setEnabled(True)
        self._mw.action_toggle_cw.setEnabled(False)
        self._mw.action_toggle_modulation.setEnabled(False)
        # Set every Box and Button in the gui as not enabled
        for widget_name in self._mw.__dict__.keys():
            if widget_name.endswith('Box') or widget_name.endswith('Button'):
                widg = getattr(self._mw, widget_name)
                widg.setEnabled(False)
        self.sigStartEproc.emit()
        return

    def run_stop_scan(self, is_checked):
        """ Manage what happens if eproc scan is started/stopped. """
        if is_checked:
            # Control the status of power supplies, RF and LF
            if self._checkdevdialog.apply_checkBox.isChecked() or\
                    (
                    self._mw.action_toggle_cw.isChecked()
                    and self._mw.action_toggle_modulation.isChecked()
                    and self._mw.power_supply_board_RadioButton.isChecked()
                    and self._mw.power_supply_amplifier_RadioButton.isChecked()
                    ):
                # If everything is on: start eproc
                self._checkdevdialog.accept()
            else:
                # Possibility to start the experiment even if some devices are off
                if self._mw.action_toggle_cw.isChecked():
                    self._checkdevdialog.mw_Label.setText('on')
                else:
                    self._checkdevdialog.mw_Label.setText('off')
                if self._mw.action_toggle_modulation.isChecked():
                    self._checkdevdialog.ref_Label.setText('on')
                else:
                    self._checkdevdialog.ref_Label.setText('off')
                if self._mw.power_supply_board_RadioButton.isChecked():
                    self._checkdevdialog.psb_Label.setText('on')
                else:
                    self._checkdevdialog.psb_Label.setText('off')
                if self._mw.power_supply_amplifier_RadioButton.isChecked():
                    self._checkdevdialog.psa_Label.setText('on')
                else:
                    self._checkdevdialog.psa_Label.setText('off')
                self._checkdevdialog.show()
            # Stop eproc
            self._mw.action_stop_next_sweep.setEnabled(False)
            self._mw.action_toggle_cw.setEnabled(True)
            self._mw.action_toggle_modulation.setEnabled(True)
            # Set every Box and Button in the gui as not enabled
            for widget_name in self._mw.__dict__.keys():
                if widget_name.endswith('Box') or widget_name.endswith('Button'):
                    widg = getattr(self._mw, widget_name)
                    widg.setEnabled(True)
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
            self._mw.action_stop_next_sweep.setEnabled(False)
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
            self._mw.fs_mw_frequency_LineEdit.setText(self.multiplied_mw(param))

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
            self._mw.ref_deviation_ppHz_LineEdit.setText(self.multiplied_mw(2 * param))  # factor 2 to have pp
            self._mw.ref_deviation_ppG_LineEdit.setText(self.mw_to_field(2 * param))

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

        param = param_dict.get('frequency_multiplier')
        if param is not None:
            self._mw.frequency_multiplier_ComboBox.blockSignals(True)
            self._mw.frequency_multiplier_ComboBox.setCurrentText(str(param))
            self._mw.frequency_multiplier_ComboBox.blockSignals(False)
            self._mw.ms_start_LineEdit.setText(self.mw_to_field(self._eproc_logic.ms_start))
            self._mw.ms_step_LineEdit.setText(self.mw_to_field(self._eproc_logic.ms_step))
            self._mw.ms_stop_LineEdit.setText(self.mw_to_field(self._eproc_logic.ms_stop))
            self._mw.fs_mw_frequency_LineEdit.setText(self.multiplied_mw(self._eproc_logic.fs_mw_frequency))
            self._mw.ref_deviation_ppHz_LineEdit.setText(self.multiplied_mw(2 * self._eproc_logic.ref_deviation))  # factor 2 to have pp
            self._mw.ref_deviation_ppG_LineEdit.setText(self.mw_to_field(2 * self._eproc_logic.ref_deviation))

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

        #motor parameter
        param = param_dict.get('x_position')
        if param is not None:
            self._KDC101.x_Position_lineEdit.blockSignals(True)
            self._KDC101.x_Position_lineEdit.setText(str(round(param, 3)))
            self._KDC101.x_Position_lineEdit.blockSignals(False)

        param = param_dict.get('y_position')
        if param is not None:
            self._KDC101.y_Position_lineEdit.blockSignals(True)
            self._KDC101.y_Position_lineEdit.setText(str(round(param, 3)))
            self._KDC101.y_Position_lineEdit.blockSignals(False)

        param = param_dict.get('z_position')
        if param is not None:
            self._KDC101.z_Position_lineEdit.blockSignals(True)
            self._KDC101.z_Position_lineEdit.setText(str(round(param, 4)))
            self._KDC101.z_Position_lineEdit.blockSignals(False)
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
        """Interchange between microwave and field sweep"""
        if self._mw.ms_RadioButton.isChecked():
            widg_value = True
            self.change_ms_params()
        else:
            widg_value = False
            self.change_fs_params()
        self._eproc_logic.is_microwave_sweep = widg_value

        for widget_name in self._mw.__dict__.keys():
            if widget_name.startswith('fs_'):
                widg = getattr(self._mw, widget_name)
                widg.setEnabled(not widg_value)
        for widget_name in self._mw.__dict__.keys():
            if widget_name.startswith('ms_'):
                widg = getattr(self._mw, widget_name)
                widg.setEnabled(widg_value)
        self._mw.fs_RadioButton.setEnabled(True)
        self._mw.ms_RadioButton.setEnabled(True)
        return

    def on_off_external_reference(self):
        """Select between internal and external reference of the lockin"""
        if self._mw.ref_RadioButton.isChecked():
            widg_value = True
            self.sigExtRefOn.emit()
        else:
            widg_value = False
            self.sigExtRefOff.emit()

        self._eproc_logic.is_external_reference = widg_value
        self._mw.lia_frequency_DoubleSpinBox.setEnabled(not widg_value)
        for widget_name in self._mw.__dict__.keys():
            if widget_name.startswith('ref_'):
                widg = getattr(self._mw, widget_name)
                widg.setEnabled(widg_value)
        self._mw.ref_RadioButton.setEnabled(True)
        return

    def change_ref_params(self):
        """ Change parameters of the reference signal"""
        shape = self._mw.ref_shape_ComboBox.currentText()
        freq = self._mw.ref_frequency_DoubleSpinBox.value()
        mode = self._mw.ref_mode_ComboBox.currentText()
        dev = self._mw.ref_deviation_DoubleSpinBox.value()
        self.sigRefParamsChanged.emit(shape, freq, mode, dev)
        return

    def change_scan_params(self):
        """ Change parameters from the sweep parameters Dock Widget """
        number_of_sweeps = self._mw.number_of_sweeps_SpinBox.value()
        number_of_accumulations = self._mw.number_of_accumulations_SpinBox.value()
        self.sigScanParamsChanged.emit(number_of_sweeps, number_of_accumulations)
        return

    def change_frequency_multiplier(self):
        multiplier = int(self._mw.frequency_multiplier_ComboBox.currentText())
        self.sigFrequencyMultiplierChanged.emit(multiplier)
        return

    def on_off_psb(self, is_checked):
        if is_checked:
            self._psondialog.power_supply_Label.setText(
                'The power supply for the board is set with the following values:'
            )
            self._psondialog.v1_LineEdit.setText(
                str(self._mw.psb_voltage_outp1_DoubleSpinBox.value()) + ' V')
            self._psondialog.v2_LineEdit.setText(
                str(self._mw.psb_voltage_outp2_DoubleSpinBox.value()) + ' V')
            self._psondialog.maxi1_LineEdit.setText(
                str(self._mw.psb_current_max_outp1_DoubleSpinBox.value()) + ' I')
            self._psondialog.maxi2_LineEdit.setText(
                str(self._mw.psb_current_max_outp2_DoubleSpinBox.value()) + ' I')
            self._psondialog.show()
        else:
            self._psoffdialog.power_supply_Label.setText(
                'The power supply of the board will be turned off.'
            )
            self._psoffdialog.show()
        return

    def power_supply_on_accepted(self):
        if 'board' in self._psondialog.power_supply_Label.text():
            self._mw.psb_voltage_outp1_DoubleSpinBox.setEnabled(False)
            self._mw.psb_voltage_outp2_DoubleSpinBox.setEnabled(False)
            self._mw.psb_current_max_outp1_DoubleSpinBox.setEnabled(False)
            self._mw.psb_current_max_outp2_DoubleSpinBox.setEnabled(False)
            self.sigPowerSupplyBoardOn.emit()
        else:
            self._mw.psa_voltage_outp1_DoubleSpinBox.setEnabled(False)
            self._mw.psa_voltage_outp2_DoubleSpinBox.setEnabled(False)
            self._mw.psa_current_max_outp1_DoubleSpinBox.setEnabled(False)
            self._mw.psa_current_max_outp2_DoubleSpinBox.setEnabled(False)
            self.sigPowerSupplyAmplifierOn.emit()
        return

    def power_supply_on_rejected(self):
        if 'board' in self._psondialog.power_supply_Label.text():
            self._mw.power_supply_board_RadioButton.blockSignals(True)
            self._mw.power_supply_board_RadioButton.setChecked(False)
            self._mw.power_supply_board_RadioButton.blockSignals(False)
        else:
            self._mw.power_supply_amplifier_RadioButton.blockSignals(True)
            self._mw.power_supply_amplifier_RadioButton.setChecked(False)
            self._mw.power_supply_amplifier_RadioButton.blockSignals(False)
        return

    def power_supply_off_accepted(self):
        if 'board' in self._psoffdialog.power_supply_Label.text():
            self._mw.psb_voltage_outp1_DoubleSpinBox.setEnabled(True)
            self._mw.psb_voltage_outp2_DoubleSpinBox.setEnabled(True)
            self._mw.psb_current_max_outp1_DoubleSpinBox.setEnabled(True)
            self._mw.psb_current_max_outp2_DoubleSpinBox.setEnabled(True)
            self.sigPowerSupplyBoardOff.emit()
        else:
            self._mw.psa_voltage_outp1_DoubleSpinBox.setEnabled(True)
            self._mw.psa_voltage_outp2_DoubleSpinBox.setEnabled(True)
            self._mw.psa_current_max_outp1_DoubleSpinBox.setEnabled(True)
            self._mw.psa_current_max_outp2_DoubleSpinBox.setEnabled(True)
            self.sigPowerSupplyAmplifierOff.emit()
        return

    def power_supply_off_rejected(self):
        if 'board' in self._psondialog.power_supply_Label.text():
            self._mw.power_supply_board_RadioButton.blockSignals(True)
            self._mw.power_supply_board_RadioButton.setChecked(True)
            self._mw.power_supply_board_RadioButton.blockSignals(False)
        else:
            self._mw.power_supply_amplifier_RadioButton.blockSignals(True)
            self._mw.power_supply_amplifier_RadioButton.setChecked(True)
            self._mw.power_supply_amplifier_RadioButton.blockSignals(False)
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
            self._psondialog.power_supply_Label.setText(
                'The power supply for the amplifier is set with the following values:'
            )
            self._psondialog.v1_LineEdit.setText(
                str(self._mw.psa_voltage_outp1_DoubleSpinBox.value()) + ' V')
            self._psondialog.v2_LineEdit.setText(
                str(self._mw.psa_voltage_outp2_DoubleSpinBox.value()) + ' V')
            self._psondialog.maxi1_LineEdit.setText(
                str(self._mw.psa_current_max_outp1_DoubleSpinBox.value()) + ' I')
            self._psondialog.maxi2_LineEdit.setText(
                str(self._mw.psa_current_max_outp2_DoubleSpinBox.value()) + ' I')
            self._psondialog.show()
        else:
            self._psoffdialog.power_supply_Label.setText(
                'The power supply of the amplifier will be turned off.'
            )
            self._psoffdialog.show()
        return

    def change_psa_params(self):
        """ Change parameters from the power supply amplifier Dock Widget """
        v1 = self._mw.psa_voltage_outp1_DoubleSpinBox.value()
        v2 = self._mw.psa_voltage_outp2_DoubleSpinBox.value()
        maxi1 = self._mw.psa_current_max_outp1_DoubleSpinBox.value()
        maxi2 = self._mw.psa_current_max_outp2_DoubleSpinBox.value()
        self.sigPowerSupplyAmplifierParamsChanged.emit(v1, v2, maxi1, maxi2)
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

    def update_remainingtime(self, remaining_time, scanned_lines):
        """ Updates current elapsed measurement time and completed sweeps """
        self._mw.remaining_time_DisplayWidget.display(int(np.rint(remaining_time)))
        self._mw.elapsed_sweeps_DisplayWidget.display(scanned_lines)
        return

    def save_data(self):
        """ Save data """
        filetag = self._mw.save_tag_LineEdit.text()
        self.sigSaveMeasurement.emit(filetag)
        return

    def _menu_analysis(self):
        """ Open the settings menu """
        self._sd.show()

    def _menu_motorized_stages(self):
        """ Open the settings menu """
        self._KDC101.show()

    def field_to_mw(self, field):
        return str(round((field * 2.8), 2)) + 'MHz'

    def multiplied_mw(self, freq):
        # return str(round(freq * self._eproc_logic.frequency_multiplier / 1000000, 2)) + ' MHz'
        return str(freq * self._eproc_logic.frequency_multiplier / 1000000) + ' MHz'

    def mw_to_field(self, freq):
        return str(round(freq * self._eproc_logic.frequency_multiplier * 1e-6 / 2.8, 5)) + ' G'

    def x_home(self):
        self.sigHome.emit('x')
        return

    def y_home(self):
        self.sigHome.emit('y')
        return

    def z_home(self):
        self.sigHome.emit('z')
        return

    def connect_x_motor(self, is_checked):
        """Toggle cw before starting the measurement"""
        if is_checked:
            self.sigToggleXMotorOn.emit()
        else:
            self.sigToggleXMotorOff.emit()
        return

    def connect_y_motor(self, is_checked):
        """Toggle cw before starting the measurement"""
        if is_checked:
            self.sigToggleYMotorOn.emit()
        else:
            self.sigToggleYMotorOff.emit()
        return

    def connect_z_motor(self, is_checked):
        """Toggle cw before starting the measurement"""
        if is_checked:
            self.sigToggleZMotorOn.emit()
        else:
            self.sigToggleZMotorOff.emit()
        return


    def change_motor_params(self):
        """ Change parameters from the motor Dock Widget """
        x_motor_set_position = self._KDC101.x_Set_Position_doubleSpinBox.value()
        x_start = self._KDC101.x_Start_doubleSpinBox.value()
        x_step = self._KDC101.x_Step_doubleSpinBox.value()
        x_stop = self._KDC101.x_Stop_doubleSpinBox.value()
        y_motor_set_position = self._KDC101.y_Set_Position_doubleSpinBox.value()
        y_start = self._KDC101.y_Start_doubleSpinBox.value()
        y_step = self._KDC101.y_Step_doubleSpinBox.value()
        y_stop = self._KDC101.y_Stop_doubleSpinBox.value()
        z_motor_set_position = self._KDC101.z_Set_Position_doubleSpinBox.value()
        z_start = self._KDC101.z_Start_doubleSpinBox.value()
        z_step = self._KDC101.z_Step_doubleSpinBox.value()
        z_stop = self._KDC101.z_Stop_doubleSpinBox.value()

        self.sigMotorParamsChanged.emit(x_motor_set_position, x_start, x_step, x_stop,
                                        y_motor_set_position, y_start, y_step, y_stop,
                                        z_motor_set_position, z_start, z_step, z_stop)

        return

    def x_move_to_position(self):
        self.sigMove.emit('x')
        return

    def y_move_to_position(self):
        self.sigMove.emit('y')
        return

    def z_move_to_position(self):
        self.sigMove.emit('z')
        return

    def x_read_position(self, pos):

        if self._KDC101.action_toggle_x_motor.isChecked():
             return pos

        return '0'

    def run_stop_mapping(self, is_checked):
        """ Start the mapping of the field """
        if is_checked:
            self._mw.action_stop_next_sweep.setEnabled(True)
            self._mw.action_toggle_cw.setEnabled(False)
            self._mw.action_toggle_modulation.setEnabled(False)
            # Set every Box and Button in the gui as not enabled
            for widget_name in self._mw.__dict__.keys():
                if widget_name.endswith('Box') or widget_name.endswith('Button'):
                    widg = getattr(self._mw, widget_name)
                    widg.setEnabled(False)
            for widget_name in self._KDC101.__dict__.keys():
                if widget_name.endswith('Box') or widget_name.endswith('Button'):
                    widg = getattr(self._KDC101, widget_name)
                    widg.setEnabled(False)

            filetag = self._KDC101.save_tag_LineEdit.text()

            self.sigStartEprocMapping.emit(filetag)
        else:
            self.sigStopEprocMapping.emit()
        return