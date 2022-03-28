# -*- coding: utf-8 -*-
"""
This file contains the Qudi GUI module for eproc control.

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
    The main window for the eproc measurement GUI.
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


class EPRoCGui(GUIBase):
    """ This is the GUI Class for eproc measurements."""
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
    sigFsOn = QtCore.Signal()
    sigFsOff = QtCore.Signal()
    sigLiaExtRefOn = QtCore.Signal()
    sigLiaExtRefOff = QtCore.Signal()
    sigPsbOn = QtCore.Signal()
    sigPsbOff = QtCore.Signal()
    sigPsaOn = QtCore.Signal()
    sigPsaOff = QtCore.Signal()

    sigFsParamsChanged = QtCore.Signal(float, float, float, float, float, int)
    sigBsParamsChanged = QtCore.Signal(float, float, float, float, float, int)
    sigScanParamsChanged = QtCore.Signal(int, int)
    sigRefParamsChanged = QtCore.Signal(float, float, str)
    sigLiaParamsChanged = QtCore.Signal(str, float, str, float, float, float, float, float, float, int, str, str)
    sigFrequencyMultiplierChanged = QtCore.Signal(int)
    sigPsbParamsChanged = QtCore.Signal(float, float, float, float)
    sigPsaParamsChanged = QtCore.Signal(float, float, float, float)

    sigSaveMeasurement = QtCore.Signal(str)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Definition, configuration and initialisation of the eproc GUI.

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

        # Create a QSettings object for the mainwindow and store the actual GUI layout
        self.mwsettings = QtCore.QSettings("QUDI", "eproc")
        self.mwsettings.setValue("geometry", self._mw.saveGeometry())
        self.mwsettings.setValue("windowState", self._mw.saveState())

        # Get hardware constraints to set limits for input widgets
        constraints = self._eproc_logic.get_hw_constraints()

        # Adjust range of scientific spinboxes above what is possible in Qt Designer
        self._mw.bs_frequency_DoubleSpinBox.setMaximum(constraints.max_frequency)
        self._mw.bs_frequency_DoubleSpinBox.setMinimum(constraints.min_frequency)
        self._mw.bs_mw_power_DoubleSpinBox.setMaximum(constraints.max_power)
        self._mw.bs_mw_power_DoubleSpinBox.setMinimum(constraints.min_power)
        self._mw.fs_mw_power_DoubleSpinBox.setMaximum(constraints.max_power)
        self._mw.fs_mw_power_DoubleSpinBox.setMinimum(constraints.min_power)

        self._mw.save_tag_LineEdit = QtWidgets.QLineEdit(self._mw)
        self._mw.save_tag_LineEdit.setMaximumWidth(300)
        self._mw.save_tag_LineEdit.setMinimumWidth(200)
        self._mw.save_tag_LineEdit.setToolTip('Enter a nametag which will be\n'
                                              'added to the filename.')
        self._mw.save_ToolBar.addWidget(self._mw.save_tag_LineEdit)

        self._mw.ref_mode_ComboBox.setMinimumWidth(130)
        self._mw.ref_deviation_pp_LineEdit.setMinimumWidth(150)

        # Add values of time constants of lockin taking them from the hardware
        time_constants = self._eproc_logic.get_time_constants()
        for tau in time_constants:
            self._mw.lia_taua_ComboBox.addItem(self.tau_float_to_str(tau))
            self._mw.lia_taub_ComboBox.addItem(self.tau_float_to_str(tau))

        # List of pg.PlotDataItems
        self.channel_images = []
        for i in range(len(self._eproc_logic.eproc_plot_y[0, :])):
            ch_image = pg.PlotDataItem(self._eproc_logic.eproc_plot_x,
                                         self._eproc_logic.eproc_plot_y[:, i],
                                         pen=pg.mkPen(palette.c1, style=QtCore.Qt.DotLine),
                                         symbol='o',
                                         symbolPen=palette.c1,
                                         symbolBrush=palette.c1,
                                         symbolSize=7)
            self.channel_images.append(ch_image)

        # Add the display item to the xy and xz ViewWidget, which was defined in the UI file.
        for i in range(len(self.channel_images)):
            for widget_name in self._mw.__dict__.keys():
                # Add each PlotDataItem to the corresponding PlotWidget
                if widget_name.endswith('PlotWidget') and str(i+1) in widget_name:
                    widg = getattr(self._mw, widget_name)
                    widg.addItem(self.channel_images[i])
                    widg.setLabel(axis='left', text='Ch {}'.format(i+1))
                    widg.showGrid(x=True, y=True, alpha=0.8)
        self.set_label_eproc_plots()

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
        # fs = microwave sweep, bs = magnetic field B sweep,
        # lia = lockin amplifier, psa = power supply amplifier, psb = power supply board
        # ref = reference signal
        self._mw.fs_field_DoubleSpinBox.setValue(self._eproc_logic.fs_field)
        self._mw.fs_field_LineEdit.setText(self.field_to_freq(self._eproc_logic.bs_frequency))
        self._mw.fs_mw_power_DoubleSpinBox.setValue(self._eproc_logic.fs_mw_power)
        self._mw.fs_start_DoubleSpinBox.setValue(self._eproc_logic.fs_start)
        self._mw.fs_stop_DoubleSpinBox.setValue(self._eproc_logic.fs_stop)
        self._mw.fs_step_DoubleSpinBox.setValue(self._eproc_logic.fs_step)
        self._mw.fs_start_LineEdit.setText(self.freq_to_field(self._eproc_logic.fs_start))
        self._mw.fs_step_LineEdit.setText(self.freq_to_field(self._eproc_logic.fs_step))
        self._mw.fs_stop_LineEdit.setText(self.freq_to_field(self._eproc_logic.fs_stop))

        self._mw.bs_frequency_DoubleSpinBox.setValue(self._eproc_logic.bs_frequency)
        self._mw.bs_frequency_LineEdit.setText(self.multiplied_mw(self._eproc_logic.bs_frequency))
        self._mw.bs_mw_power_DoubleSpinBox.setValue(self._eproc_logic.bs_mw_power)
        self._mw.bs_start_DoubleSpinBox.setValue(self._eproc_logic.bs_start)
        self._mw.bs_stop_DoubleSpinBox.setValue(self._eproc_logic.bs_stop)
        self._mw.bs_step_DoubleSpinBox.setValue(self._eproc_logic.bs_step)
        self._mw.bs_start_LineEdit.setText(self.field_to_freq(self._eproc_logic.bs_start))
        self._mw.bs_step_LineEdit.setText(self.field_to_freq(self._eproc_logic.bs_step))
        self._mw.bs_stop_LineEdit.setText(self.field_to_freq(self._eproc_logic.bs_stop))

        self._mw.lia_range_ComboBox.setCurrentText(self._eproc_logic.lia_range)
        self._mw.lia_uac_DoubleSpinBox.setValue(self._eproc_logic.lia_uac)
        self._mw.lia_coupling_ComboBox.setCurrentText(self._eproc_logic.lia_coupling)
        self._mw.lia_frequency_DoubleSpinBox.setValue(self._eproc_logic.lia_int_freq)
        self._mw.lia_taua_ComboBox.setCurrentText(self.tau_float_to_str(self._eproc_logic.lia_tauA))
        self._mw.lia_phasea_DoubleSpinBox.setValue(self._eproc_logic.lia_phaseA)
        self._mw.lia_taub_ComboBox.setCurrentText(self.tau_float_to_str(self._eproc_logic.lia_tauB))
        self._mw.lia_phaseb_DoubleSpinBox.setValue(self._eproc_logic.lia_phaseB)
        self._mw.lia_waiting_time_factor_DoubleSpinBox.setValue(self._eproc_logic.lia_waiting_time_factor)
        self._mw.lia_harmonic_SpinBox.setValue(int(self._eproc_logic.lia_harmonic))
        self._mw.lia_slope_ComboBox.setCurrentText(self._eproc_logic.lia_slope)
        self._mw.lia_configuration_ComboBox.setCurrentText(self._eproc_logic.lia_configuration)

        self._mw.n_sweep_SpinBox.setValue(self._eproc_logic.n_sweep)
        self._mw.n_accumulation_SpinBox.setValue(self._eproc_logic.n_accumulation)

        self._mw.frequency_multiplier_ComboBox.setCurrentText(str(self._eproc_logic.f_multiplier))

        self._mw.psb_voltage_outp1_DoubleSpinBox.setValue(self._eproc_logic.psb_voltage_outp1)
        self._mw.psb_voltage_outp2_DoubleSpinBox.setValue(self._eproc_logic.psb_voltage_outp2)
        self._mw.psb_current_max_outp1_DoubleSpinBox.setValue(self._eproc_logic.psb_current_max_outp1)
        self._mw.psb_current_max_outp2_DoubleSpinBox.setValue(self._eproc_logic.psb_current_max_outp2)
        self._mw.psa_voltage_outp1_DoubleSpinBox.setValue(self._eproc_logic.psa_voltage_outp1)
        self._mw.psa_voltage_outp2_DoubleSpinBox.setValue(self._eproc_logic.psa_voltage_outp2)
        self._mw.psa_current_max_outp1_DoubleSpinBox.setValue(self._eproc_logic.psa_current_max_outp1)
        self._mw.psa_current_max_outp2_DoubleSpinBox.setValue(self._eproc_logic.psa_current_max_outp2)

        self._mw.ref_frequency_DoubleSpinBox.setValue(self._eproc_logic.ref_freq)
        self._mw.ref_deviation_DoubleSpinBox.setValue(self._eproc_logic.ref_dev)
        self._mw.ref_deviation_pp_LineEdit.setText(self.freq_to_field(self._eproc_logic.ref_dev) + '='
                                                   + self.multiplied_mw(2*self._eproc_logic.ref_dev))
        self._mw.ref_mode_ComboBox.setCurrentText(self._eproc_logic.ref_mode)

        ########################################################################
        #                       Connect signals                                #
        ########################################################################
        # Internal user input changed signals

        self._mw.fs_field_DoubleSpinBox.editingFinished.connect(self.change_fs_params)
        self._mw.fs_mw_power_DoubleSpinBox.editingFinished.connect(self.change_fs_params)
        self._mw.fs_start_DoubleSpinBox.editingFinished.connect(self.change_fs_params)
        self._mw.fs_step_DoubleSpinBox.editingFinished.connect(self.change_fs_params)
        self._mw.fs_stop_DoubleSpinBox.editingFinished.connect(self.change_fs_params)
        self._mw.fs_frequency_pos_ComboBox.currentTextChanged.connect(self.change_fs_params)

        self._mw.bs_frequency_DoubleSpinBox.editingFinished.connect(self.change_bs_params)
        self._mw.bs_mw_power_DoubleSpinBox.editingFinished.connect(self.change_bs_params)
        self._mw.bs_start_DoubleSpinBox.editingFinished.connect(self.change_bs_params)
        self._mw.bs_step_DoubleSpinBox.editingFinished.connect(self.change_bs_params)
        self._mw.bs_stop_DoubleSpinBox.editingFinished.connect(self.change_bs_params)
        self._mw.bs_field_pos_ComboBox.currentTextChanged.connect(self.change_bs_params)

        self._mw.lia_range_ComboBox.currentTextChanged.connect(self.change_lia_params)
        self._mw.lia_coupling_ComboBox.currentTextChanged.connect(self.change_lia_params)
        self._mw.lia_taua_ComboBox.currentTextChanged.connect(self.change_lia_params)
        self._mw.lia_taub_ComboBox.currentTextChanged.connect(self.change_lia_params)
        self._mw.lia_slope_ComboBox.currentTextChanged.connect(self.change_lia_params)
        self._mw.lia_configuration_ComboBox.currentTextChanged.connect(self.change_lia_params)
        self._mw.lia_uac_DoubleSpinBox.editingFinished.connect(self.change_lia_params)
        self._mw.lia_frequency_DoubleSpinBox.editingFinished.connect(self.change_lia_params)
        self._mw.lia_phasea_DoubleSpinBox.editingFinished.connect(self.change_lia_params)
        self._mw.lia_phaseb_DoubleSpinBox.editingFinished.connect(self.change_lia_params)
        self._mw.lia_harmonic_SpinBox.editingFinished.connect(self.change_lia_params)
        self._mw.lia_waiting_time_factor_DoubleSpinBox.editingFinished.connect(self.change_lia_params)

        self._mw.fs_RadioButton.toggled.connect(self.on_off_sweep)
        self._mw.ref_RadioButton.toggled.connect(self.on_off_lia_ext_ref)
        self._mw.psb_RadioButton.toggled.connect(self.on_off_psb)
        self._mw.psa_RadioButton.toggled.connect(self.on_off_psa)

        self._mw.n_sweep_SpinBox.editingFinished.connect(self.change_scan_params)
        self._mw.n_accumulation_SpinBox.editingFinished.connect(self.change_scan_params)

        self._mw.frequency_multiplier_ComboBox.currentTextChanged.connect(self.change_frequency_multiplier)

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
        self.sigFsOn.connect(self._eproc_logic.fs_on, QtCore.Qt.QueuedConnection)
        self.sigFsOff.connect(self._eproc_logic.bs_on, QtCore.Qt.QueuedConnection)
        self.sigLiaExtRefOn.connect(self._eproc_logic.lia_ext_ref_on, QtCore.Qt.QueuedConnection)
        self.sigLiaExtRefOff.connect(self._eproc_logic.lia_ext_ref_off, QtCore.Qt.QueuedConnection)
        self.sigPsbOn.connect(self._eproc_logic.psb_on, QtCore.Qt.QueuedConnection)
        self.sigPsbOff.connect(self._eproc_logic.psb_off, QtCore.Qt.QueuedConnection)
        self.sigPsaOn.connect(self._eproc_logic.psa_on, QtCore.Qt.QueuedConnection)
        self.sigPsaOff.connect(self._eproc_logic.psa_off, QtCore.Qt.QueuedConnection)
        self.sigFrequencyMultiplierChanged.connect(self._eproc_logic.set_frequency_multiplier,
                                                   QtCore.Qt.QueuedConnection)

        self.sigFsParamsChanged.connect(self._eproc_logic.set_fs_parameters, QtCore.Qt.QueuedConnection)
        self.sigBsParamsChanged.connect(self._eproc_logic.set_bs_parameters, QtCore.Qt.QueuedConnection)
        self.sigLiaParamsChanged.connect(self._eproc_logic.set_lia_parameters, QtCore.Qt.QueuedConnection)
        self.sigRefParamsChanged.connect(self._eproc_logic.set_ref_parameters, QtCore.Qt.QueuedConnection)
        self.sigScanParamsChanged.connect(self._eproc_logic.set_eproc_scan_parameters, QtCore.Qt.QueuedConnection)
        self.sigPsbParamsChanged.connect(self._eproc_logic.set_psb_parameters, QtCore.Qt.QueuedConnection)
        self.sigPsaParamsChanged.connect(self._eproc_logic.set_psa_parameters, QtCore.Qt.QueuedConnection)

        self.sigSaveMeasurement.connect(self._eproc_logic.save_eproc_data, QtCore.Qt.QueuedConnection)

        # Update signals coming from logic:
        self._eproc_logic.sigParameterUpdated.connect(self.update_parameter,
                                                      QtCore.Qt.QueuedConnection)
        self._eproc_logic.sigStatusUpdated.connect(self.update_status,
                                                   QtCore.Qt.QueuedConnection)
        self._eproc_logic.sigSetLabelEprocPlots.connect(self.set_label_eproc_plots, QtCore.Qt.QueuedConnection)
        self._eproc_logic.sigEprocPlotsUpdated.connect(self.update_plots, QtCore.Qt.QueuedConnection)
        self._eproc_logic.sigEprocRemainingTimeUpdated.connect(self.update_remainingtime,
                                                               QtCore.Qt.QueuedConnection)

        self._mw.action_stop_next_sweep.setEnabled(False)

        # External reference is basically always used
        self.update_status()

        # connect settings signals
        self._mw.action_Analysis.triggered.connect(self._menu_analysis)

        self._checkdevdialog.accepted.connect(self.check_devices_accepted)
        self._checkdevdialog.rejected.connect(self.check_devices_rejected)
        self._psondialog.accepted.connect(self.power_supply_on_accepted)
        self._psondialog.rejected.connect(self.power_supply_on_rejected)
        self._psoffdialog.accepted.connect(self.power_supply_off_accepted)
        self._psoffdialog.rejected.connect(self.power_supply_off_rejected)

        # Show the Main eproc GUI:
        self.show()

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        # Disconnect signals
        self._checkdevdialog.accepted.disconnect()
        self._checkdevdialog.rejected.disconnect()
        self._psondialog.accepted.disconnect()
        self._psoffdialog.accepted.disconnect()
        self._eproc_logic.sigParameterUpdated.disconnect()
        self._eproc_logic.sigStatusUpdated.disconnect()
        self._eproc_logic.sigSetLabelEprocPlots.disconnect()
        self._eproc_logic.sigEprocPlotsUpdated.disconnect()
        self._eproc_logic.sigEprocRemainingTimeUpdated.disconnect()

        self.sigStartEproc.disconnect()
        self.sigStopEproc.disconnect()
        self.sigFsOn.disconnect()
        self.sigFsOff.disconnect()
        self.sigLiaExtRefOn.disconnect()
        self.sigLiaExtRefOff.disconnect()
        self.sigPsbOn.disconnect()
        self.sigPsbOff.disconnect()
        self.sigPsaOn.disconnect()
        self.sigPsaOff.disconnect()
        self.sigFsParamsChanged.disconnect()
        self.sigBsParamsChanged.disconnect()
        self.sigLiaParamsChanged.disconnect()
        self.sigRefParamsChanged.disconnect()
        self.sigScanParamsChanged.disconnect()
        self.sigFrequencyMultiplierChanged.disconnect()
        self.sigPsbParamsChanged.disconnect()
        self.sigPsaParamsChanged.disconnect()
        self.sigSaveMeasurement.disconnect()

        self._mw.action_Analysis.triggered.disconnect()

        self._mw.action_run_stop.triggered.disconnect()
        self._mw.action_stop_next_sweep.triggered.disconnect()
        self._mw.action_toggle_cw.triggered.disconnect()
        self._mw.action_toggle_modulation.triggered.disconnect()
        self._mw.action_Save.triggered.disconnect()

        self._mw.fs_field_DoubleSpinBox.editingFinished.disconnect()
        self._mw.fs_mw_power_DoubleSpinBox.editingFinished.disconnect()
        self._mw.fs_start_DoubleSpinBox.editingFinished.disconnect()
        self._mw.fs_step_DoubleSpinBox.editingFinished.disconnect()
        self._mw.fs_stop_DoubleSpinBox.editingFinished.disconnect()

        self._mw.bs_frequency_DoubleSpinBox.editingFinished.disconnect()
        self._mw.bs_mw_power_DoubleSpinBox.editingFinished.disconnect()
        self._mw.bs_start_DoubleSpinBox.editingFinished.disconnect()
        self._mw.bs_step_DoubleSpinBox.editingFinished.disconnect()
        self._mw.bs_stop_DoubleSpinBox.editingFinished.disconnect()

        self._mw.lia_range_ComboBox.currentTextChanged.disconnect()
        self._mw.lia_coupling_ComboBox.currentTextChanged.disconnect()
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

        self._mw.fs_RadioButton.toggled.disconnect()
        self._mw.ref_RadioButton.toggled.disconnect()
        self._mw.psb_RadioButton.toggled.disconnect()
        self._mw.psa_RadioButton.toggled.disconnect()

        self._mw.n_sweep_SpinBox.editingFinished.disconnect()
        self._mw.n_accumulation_SpinBox.editingFinished.disconnect()

        self._mw.ref_frequency_DoubleSpinBox.editingFinished.disconnect()
        self._mw.ref_deviation_DoubleSpinBox.editingFinished.disconnect()
        self._mw.ref_mode_ComboBox.currentTextChanged.disconnect()

        self._mw.frequency_multiplier_ComboBox.currentTextChanged.disconnect()

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

    def set_label_eproc_plots(self):
        if self._eproc_logic.is_fs:
            x_label = 'Frequency'
            x_units = 'Hz'
        else:
            x_label = 'Magnetic field'
            x_units = 'G'
        for i in range(len(self.channel_images)):
            for widget_name in self._mw.__dict__.keys():
                if widget_name.endswith('PlotWidget') and str(i + 1) in widget_name:
                    widg = getattr(self._mw, widget_name)
                    widg.setLabel(axis='bottom', text=x_label, units=x_units)
        return

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
        """Method to start eproc."""
        self.sigStartEproc.emit()
        return

    def check_devices_rejected(self):
        """Method in case eproc will not start."""
        self._mw.action_run_stop.blockSignals(True)
        self._mw.action_run_stop.setChecked(False)
        self._mw.action_run_stop.blockSignals(False)
        return

    def run_stop_scan(self, is_checked):
        """ Manage what happens if eproc scan is started/stopped. """
        if is_checked:
            # Control the status of power supplies, RF and LF
            if self._checkdevdialog.apply_checkBox.isChecked() or\
                    (
                    self._mw.action_toggle_cw.isChecked()
                    and self._mw.action_toggle_modulation.isChecked()
                    and self._mw.psb_RadioButton.isChecked()
                    and self._mw.psa_RadioButton.isChecked()
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
                if self._mw.psb_RadioButton.isChecked():
                    self._checkdevdialog.psb_Label.setText('on')
                else:
                    self._checkdevdialog.psb_Label.setText('off')
                if self._mw.psa_RadioButton.isChecked():
                    self._checkdevdialog.psa_Label.setText('on')
                else:
                    self._checkdevdialog.psa_Label.setText('off')
                self._checkdevdialog.show()
        else:
            # Stop eproc
            self.sigStopEproc.emit()
        return

    def update_status(self):
        """
        Update the display for a change in the microwave status (mode and output).

        @param str mw_mode: is the microwave output active?
        @param bool is_running: is the microwave output active?
        """
        # Block signals from firing
        self._mw.action_run_stop.blockSignals(True)
        self._mw.action_stop_next_sweep.blockSignals(True)
        self._mw.action_toggle_cw.blockSignals(True)    # Are these two necessary?
        self._mw.action_toggle_modulation.blockSignals(True)

        if self._eproc_logic.is_eproc_running:
            for widget_name in self._mw.__dict__.keys():
                if widget_name.endswith('DockWidgetContents'):
                    widg = getattr(self._mw, widget_name)
                    widg.setEnabled(False)
            self._mw.action_run_stop.setChecked(True)
        else:
            # Set enabled every Box and Button and LineEdit in the gui
            for widget_name in self._mw.__dict__.keys():
                if not widget_name.endswith(('Button', 'Group')):
                    widg = getattr(self._mw, widget_name)
                    widg.setEnabled(True)
            self._mw.action_run_stop.setChecked(False)

            # Set disabled Boxes depending on status
            if self._eproc_logic.is_fs:
                for widget_name in self._mw.__dict__.keys():
                    if widget_name.startswith('bs') and not widget_name.endswith('Contents'):
                        widg = getattr(self._mw, widget_name)
                        widg.setEnabled(False)
                self._mw.bs_RadioButton.setEnabled(True)
                self._mw.fs_RadioButton.setChecked(True)
            else:
                for widget_name in self._mw.__dict__.keys():
                    if widget_name.startswith('fs') and not widget_name.endswith('Contents'):
                        widg = getattr(self._mw, widget_name)
                        widg.setEnabled(False)
                self._mw.fs_RadioButton.setEnabled(True)
                self._mw.bs_RadioButton.setChecked(True)
            if self._eproc_logic.is_lia_ext_ref:
                self._mw.lia_frequency_DoubleSpinBox.setEnabled(False)
                self._mw.ref_RadioButton.setChecked(True)
            else:
                for widget_name in self._mw.__dict__.keys():
                    if widget_name.startswith('ref_'):
                        widg = getattr(self._mw, widget_name)
                        widg.setEnabled(False)
                self._mw.ref_RadioButton.setEnabled(True)
                self._mw.ref_RadioButton.setChecked(False)

        # Unblock signal firing
        self._mw.action_run_stop.blockSignals(False)
        self._mw.action_stop_next_sweep.blockSignals(False)
        self._mw.action_toggle_cw.blockSignals(False)
        self._mw.action_toggle_modulation.blockSignals(False)
        return

    def update_plots(self, eproc_data_x, eproc_data_y):
        """ Refresh the plot widgets with new data. """
        # Update mean signal plot
        for i in range(len(self.channel_images)):
            ch_image = self.channel_images[i]
            ch_image.setData(eproc_data_x, eproc_data_y[:, i])
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
        param = param_dict.get('fs_field')
        if param is not None:
            self._mw.fs_field_DoubleSpinBox.blockSignals(True)
            self._mw.fs_field_DoubleSpinBox.setValue(param)
            self._mw.fs_field_DoubleSpinBox.blockSignals(False)
            self._mw.fs_field_LineEdit.setText(self.field_to_freq(param))

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
            self._mw.fs_start_LineEdit.setText(self.freq_to_field(param))

        param = param_dict.get('fs_step')
        if param is not None:
            self._mw.fs_step_DoubleSpinBox.blockSignals(True)
            self._mw.fs_step_DoubleSpinBox.setValue(param)
            self._mw.fs_step_DoubleSpinBox.blockSignals(False)
            self._mw.fs_step_LineEdit.setText(self.freq_to_field(param))

        param = param_dict.get('fs_stop')
        if param is not None:
            self._mw.fs_stop_DoubleSpinBox.blockSignals(True)
            self._mw.fs_stop_DoubleSpinBox.setValue(param)
            self._mw.fs_stop_DoubleSpinBox.blockSignals(False)
            self._mw.fs_stop_LineEdit.setText(self.freq_to_field(param))

        # Field sweep parameters Dock widget
        param = param_dict.get('bs_frequency')
        if param is not None:
            self._mw.bs_frequency_DoubleSpinBox.blockSignals(True)
            self._mw.bs_frequency_DoubleSpinBox.setValue(param)
            self._mw.bs_frequency_DoubleSpinBox.blockSignals(False)
            self._mw.bs_frequency_LineEdit.setText(self.multiplied_mw(param))

        param = param_dict.get('bs_mw_power')
        if param is not None:
            self._mw.bs_mw_power_DoubleSpinBox.blockSignals(True)
            self._mw.bs_mw_power_DoubleSpinBox.setValue(param)
            self._mw.bs_mw_power_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('bs_start')
        if param is not None:
            self._mw.bs_start_DoubleSpinBox.blockSignals(True)
            self._mw.bs_start_DoubleSpinBox.setValue(param)
            self._mw.bs_start_DoubleSpinBox.blockSignals(False)
            self._mw.bs_start_LineEdit.setText(self.field_to_freq(param))

        param = param_dict.get('bs_step')
        if param is not None:
            self._mw.bs_step_DoubleSpinBox.blockSignals(True)
            self._mw.bs_step_DoubleSpinBox.setValue(param)
            self._mw.bs_step_DoubleSpinBox.blockSignals(False)
            self._mw.bs_step_LineEdit.setText(self.field_to_freq(param))

        param = param_dict.get('bs_stop')
        if param is not None:
            self._mw.bs_stop_DoubleSpinBox.blockSignals(True)
            self._mw.bs_stop_DoubleSpinBox.setValue(param)
            self._mw.bs_stop_DoubleSpinBox.blockSignals(False)
            self._mw.bs_stop_LineEdit.setText(self.field_to_freq(param))

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
            self._mw.lia_coupling_ComboBox.blockSignals(True)
            self._mw.lia_coupling_ComboBox.setCurrentText(param)
            self._mw.lia_coupling_ComboBox.blockSignals(False)

        param = param_dict.get('lia_int_freq')
        if param is not None:
            self._mw.lia_frequency_DoubleSpinBox.blockSignals(True)
            self._mw.lia_frequency_DoubleSpinBox.setValue(param)
            self._mw.lia_frequency_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('lia_tauA')
        if param is not None:
            self._mw.lia_taua_ComboBox.blockSignals(True)
            self._mw.lia_taua_ComboBox.setCurrentText(self.tau_float_to_str(param))
            self._mw.lia_taua_ComboBox.blockSignals(False)

        param = param_dict.get('lia_phaseA')
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

        param = param_dict.get('ref_freq')
        if param is not None:
            self._mw.ref_frequency_DoubleSpinBox.blockSignals(True)
            self._mw.ref_frequency_DoubleSpinBox.setValue(param)
            self._mw.ref_frequency_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('ref_dev')
        if param is not None:
            self._mw.ref_deviation_DoubleSpinBox.blockSignals(True)
            self._mw.ref_deviation_DoubleSpinBox.setValue(param)
            self._mw.ref_deviation_DoubleSpinBox.blockSignals(False)
            self._mw.ref_deviation_pp_LineEdit.setText(self.multiplied_mw(2 * param) + '='
                                                       + self.freq_to_field(2 * param))

        param = param_dict.get('ref_mode')
        if param is not None:
            self._mw.ref_mode_ComboBox.blockSignals(True)
            self._mw.ref_mode_ComboBox.setCurrentText(param)
            self._mw.ref_mode_ComboBox.blockSignals(False)

        param = param_dict.get('n_sweep')
        if param is not None:
            self._mw.n_sweep_SpinBox.blockSignals(True)
            self._mw.n_sweep_SpinBox.setValue(param)
            self._mw.n_sweep_SpinBox.blockSignals(False)

        param = param_dict.get('n_accumulation')
        if param is not None:
            self._mw.n_accumulation_SpinBox.blockSignals(True)
            self._mw.n_accumulation_SpinBox.setValue(param)
            self._mw.n_accumulation_SpinBox.blockSignals(False)

        param = param_dict.get('f_multiplier')
        if param is not None:
            self._mw.frequency_multiplier_ComboBox.blockSignals(True)
            self._mw.frequency_multiplier_ComboBox.setCurrentText(str(param))
            self._mw.frequency_multiplier_ComboBox.blockSignals(False)
            self._mw.fs_field_LineEdit.setText(self.field_to_freq(self._eproc_logic.fs_field))
            self._mw.fs_start_LineEdit.setText(self.freq_to_field(self._eproc_logic.fs_start))
            self._mw.fs_step_LineEdit.setText(self.freq_to_field(self._eproc_logic.fs_step))
            self._mw.fs_stop_LineEdit.setText(self.freq_to_field(self._eproc_logic.fs_stop))
            self._mw.bs_frequency_LineEdit.setText(self.multiplied_mw(self._eproc_logic.bs_frequency))
            self._mw.ref_deviation_pp_LineEdit.setText(self.multiplied_mw(2 * self._eproc_logic.ref_dev) + '='
                                                       + self.freq_to_field(2 * self._eproc_logic.ref_dev))

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

    def change_fs_params(self):
        """ Change parameters from the field sweep Dock Widget """
        field = self._mw.fs_field_DoubleSpinBox.value()
        power = self._mw.fs_mw_power_DoubleSpinBox.value()
        start = self._mw.fs_start_DoubleSpinBox.value()
        step = self._mw.fs_step_DoubleSpinBox.value()
        stop = self._mw.fs_stop_DoubleSpinBox.value()
        freq_pos = self._mw.fs_frequency_pos_ComboBox.currentIndex()
        self.sigFsParamsChanged.emit(start, step, stop, field, power, freq_pos)
        return

    def change_bs_params(self):
        """ Change parameters from the field sweep Dock Widget """
        frequency = self._mw.bs_frequency_DoubleSpinBox.value()
        power = self._mw.bs_mw_power_DoubleSpinBox.value()
        start = self._mw.bs_start_DoubleSpinBox.value()
        step = self._mw.bs_step_DoubleSpinBox.value()
        stop = self._mw.bs_stop_DoubleSpinBox.value()
        field_pos = self._mw.bs_field_pos_ComboBox.currentIndex()
        self.sigBsParamsChanged.emit(start, step, stop, frequency, power, field_pos)
        return

    def change_lia_params(self):
        """ Change lockin parameters """
        input_range = self._mw.lia_range_ComboBox.currentText()
        uac = self._mw.lia_uac_DoubleSpinBox.value()
        coupling = self._mw.lia_coupling_ComboBox.currentText()
        int_ref_freq = self._mw.lia_frequency_DoubleSpinBox.value()
        tauA = self.tau_str_to_float(self._mw.lia_taua_ComboBox.currentText())
        phaseA = self._mw.lia_phasea_DoubleSpinBox.value()
        tauB = self.tau_str_to_float(self._mw.lia_taub_ComboBox.currentText())
        phaseB = self._mw.lia_phaseb_DoubleSpinBox.value()
        waiting_time_factor = self._mw.lia_waiting_time_factor_DoubleSpinBox.value()
        harmonic = self._mw.lia_harmonic_SpinBox.value()
        slope = self._mw.lia_slope_ComboBox.currentText()
        configuration = self._mw.lia_configuration_ComboBox.currentText()
        self.sigLiaParamsChanged.emit(input_range, uac, coupling, int_ref_freq, tauA, phaseA, tauB, phaseB,
                                      waiting_time_factor, harmonic, slope, configuration)
        return

    def on_off_sweep(self, is_checked):
        """Interchange between microwave and field sweep"""
        if is_checked:
            self.sigFsOn.emit()
        else:
            self.sigFsOff.emit()
        return

    def on_off_lia_ext_ref(self, is_checked):
        """Select between internal and external reference of the lockin"""
        if is_checked:
            self.sigLiaExtRefOn.emit()
        else:
            self.sigLiaExtRefOff.emit()
        return

    def change_ref_params(self):
        """ Change parameters of the reference signal"""
        freq = self._mw.ref_frequency_DoubleSpinBox.value()
        dev = self._mw.ref_deviation_DoubleSpinBox.value()
        mode = self._mw.ref_mode_ComboBox.currentText()
        self.sigRefParamsChanged.emit(freq, dev, mode)
        return

    def change_scan_params(self):
        """ Change parameters from the sweep parameters Dock Widget """
        n_sweep = self._mw.n_sweep_SpinBox.value()
        n_accumulation = self._mw.n_accumulation_SpinBox.value()
        self.sigScanParamsChanged.emit(n_sweep, n_accumulation)
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
            self.sigPsbOn.emit()
        else:
            self._mw.psa_voltage_outp1_DoubleSpinBox.setEnabled(False)
            self._mw.psa_voltage_outp2_DoubleSpinBox.setEnabled(False)
            self._mw.psa_current_max_outp1_DoubleSpinBox.setEnabled(False)
            self._mw.psa_current_max_outp2_DoubleSpinBox.setEnabled(False)
            self.sigPsaOn.emit()
        return

    def power_supply_on_rejected(self):
        if 'board' in self._psondialog.power_supply_Label.text():
            self._mw.psb_RadioButton.blockSignals(True)
            self._mw.psb_RadioButton.setChecked(False)
            self._mw.psb_RadioButton.blockSignals(False)
        else:
            self._mw.psa_RadioButton.blockSignals(True)
            self._mw.psa_RadioButton.setChecked(False)
            self._mw.psa_RadioButton.blockSignals(False)
        return

    def power_supply_off_accepted(self):
        if 'board' in self._psoffdialog.power_supply_Label.text():
            self._mw.psb_voltage_outp1_DoubleSpinBox.setEnabled(True)
            self._mw.psb_voltage_outp2_DoubleSpinBox.setEnabled(True)
            self._mw.psb_current_max_outp1_DoubleSpinBox.setEnabled(True)
            self._mw.psb_current_max_outp2_DoubleSpinBox.setEnabled(True)
            self.sigPsbOff.emit()
        else:
            self._mw.psa_voltage_outp1_DoubleSpinBox.setEnabled(True)
            self._mw.psa_voltage_outp2_DoubleSpinBox.setEnabled(True)
            self._mw.psa_current_max_outp1_DoubleSpinBox.setEnabled(True)
            self._mw.psa_current_max_outp2_DoubleSpinBox.setEnabled(True)
            self.sigPsaOff.emit()
        return

    def power_supply_off_rejected(self):
        if 'board' in self._psondialog.power_supply_Label.text():
            self._mw.psb_RadioButton.blockSignals(True)
            self._mw.psb_RadioButton.setChecked(True)
            self._mw.psb_RadioButton.blockSignals(False)
        else:
            self._mw.psa_RadioButton.blockSignals(True)
            self._mw.psa_RadioButton.setChecked(True)
            self._mw.psa_RadioButton.blockSignals(False)
        return

    def change_psb_params(self):
        v1 = self._mw.psb_voltage_outp1_DoubleSpinBox.value()
        v2 = self._mw.psb_voltage_outp2_DoubleSpinBox.value()
        maxi1 = self._mw.psb_current_max_outp1_DoubleSpinBox.value()
        maxi2 = self._mw.psb_current_max_outp2_DoubleSpinBox.value()
        self.sigPsbParamsChanged.emit(v1, v2, maxi1, maxi2)
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
        self.sigPsaParamsChanged.emit(v1, v2, maxi1, maxi2)
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

    def field_to_freq(self, field):
        return str(round((field * 2.8), 2)) + 'MHz'

    def multiplied_mw(self, freq):
        # return str(round(freq * self._eproc_logic.f_multiplier / 1000000, 2)) + ' MHz'
        return str(freq * self._eproc_logic.f_multiplier / 1000000) + ' MHz'

    def freq_to_field(self, freq):
        return str(round(freq * self._eproc_logic.f_multiplier * 1e-6 / 2.8, 5)) + ' G'

