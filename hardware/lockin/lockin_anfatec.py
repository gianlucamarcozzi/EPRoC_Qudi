import time
import numpy as np
import requests
import os
import subprocess

from core.module import Base
from core.configoption import ConfigOption
from interface.test_lockin_interface import LockinInterface


class LockinAnfatec(Base, LockinInterface):
    """
    Example config for copy-paste:

    lockin_anfatec_203:
        module.Class: 'lockin.test_lockin_anfatec_203.lockin_anfatec_203'
        gpib_address: '192.168.1.7'
    """

    # visa address of the hardware : this can be over ethernet, the name is here for
    # backward compatibility
    _address = ConfigOption('gpib_address', missing='error')
    _delay = 0.1

    _username = 'long'
    _password = 'nga'

    tau_values = [0.0002, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50,
                  100, 200, 500, 1000]

    def on_activate(self):
        """ Initialisation performed during activation of the module. """
        r = requests.get('http://' + self._address + '/cgi-bin/login.cgi?username=' + self._username + '&password=' + self._password)
        if 'no_authentication' in r.text:
            self.log.error('Could not connect to the address >>{}<<.'.format(self._address))
            raise Exception('Could not connect to the address >>{}<<.'.format(self._address))
        return

    def on_deactivate(self):
        return

    def get_actual_value(self, param):
        """
        get the value of a parameter from Lockin.ini

        :param param: str {Amplitude|Frequency|Timeconstant|Rolloff|InputRange|Phase|Harmonic|AmplCaretPos|
                            FreqCaretPos|FreqCaretPosTail|PhaseCaretPos|DisplayChannel|Channel1Type|Channel1Range|
                            Channel2Type|Channel2Range|Channel3Type|Channel3Range|Channel4Type|Channel4Range|
                            InputCouple|InputMode|RefInFlag|TimeConstLoL|RollOffLoL|SyncLoL|Sync0|Phase0}
        :return: str parameter value
        """

        url = ('http://' + self._address + '/setup/lockin.ini')
        r = requests.get(url)
        lines = r.text.split('\n')
        for line in lines:
            if param in line:
                return line.split(' ')[1]
        return -1

    def set_input_range(self, r):
        """
        :param r: str {'0.1'|'1'|'10'}
                        '0.1': low noise
                        '1': normal
                        '10': high dyn. reserve
        """
        if r == '0.1':
            r = '1'
        else:
            r = str(10 * int(r))
        query = '899_' + r + '_'
        url = ('http://' + self._address + '/cgi-bin/remote.cgi?' + query)
        r = requests.get(url)
        time.sleep(self._delay)
        actual_range = self.get_actual_value('InputRange')
        if actual_range == '1':
            actual_range = '0.1'
        else:
            actual_range = str(int(actual_range) / 10)
        return actual_range

    def set_coupling_type(self, coupl):
        """
        :param coupl: int {0|1}:
                        0: dc coupled
                        1: ac coupled
        :return actual_coupl:
        """
        if coupl == 'dc':
            coupl = 0
        else:
            coupl = 1
        query = '89D_' + str(coupl) + '_'
        url = ('http://' + self._address + '/cgi-bin/remote.cgi?' + query)
        r = requests.get(url)
        time.sleep(self._delay)
        actual_coupl = int(self.get_actual_value('InputCoupl'))
        if actual_coupl == 0:
            actual_coupl = 'dc'
        else:
            actual_coupl = 'ac'
        return actual_coupl

    def set_time_constants(self, tauA=None, tau1=None):
        """

        :param: tauA 0.1ms is not supported, tau1 {...|-10} -10: same value as tauA
        :return:
        """
        if tauA is not None:
            query = '8959_' + str(self.tau_values.index(tauA) + 1) + '_'
            url = ('http://' + self._address + '/cgi-bin/remote.cgi?' + query)
            r = requests.get(url)
            time.sleep(self._delay)
        if tau1 is not None:
            query = '8955_' + str(self.tau_values.index(tau1) + 1) + '_'
            url = ('http://' + self._address + '/cgi-bin/remote.cgi?' + query)
            r = requests.get(url)
            time.sleep(self._delay)
        actual_tauA = self.tau_values[int(self.get_actual_value('Timeconstant')) - 1]
        actual_tau1 = self.tau_values[int(self.get_actual_value('TimeConstLoL')) - 1]
        return actual_tauA, actual_tau1

    def set_sync_filter_settings(self, val):
        """
        manual is not really clear about this
        :param val: 0: off, 1: on
        :return:
        """
        query = '895D_' + str(val) + '_'
        url = ('http://' + self._address + '/cgi-bin/remote.cgi?' + query)
        r = requests.get(url)
        time.sleep(self._delay)
        actual_val = int(self.get_actual_value('Sync0'))
        syncLoL = int(self.get_actual_value('SyncLoL'))  # confused about this syncLoL thing that changes accordingly to Sync0
        return actual_val, syncLoL

    def set_rolloff(self, dB):
        """
        RollOff and RollOffLoL change together with this command
        :param dB: dB/oct {6|12|24}
        :return:
        """
        query = '891_' + str(dB) + '_'
        url = ('http://' + self._address + '/cgi-bin/remote.cgi?' + query)
        r = requests.get(url)
        time.sleep(self._delay)
        actual_slope = self.get_actual_value('Rolloff')
        return actual_slope

    def set_input_config(self, i):
        """
        :param i: 0: A, 1: A-B, 2: A&B
        :return:
        """
        query = '89A_' + '2' + '_'
        url = ('http://' + self._address + '/cgi-bin/remote.cgi?' + query)
        r = requests.get(url)
        time.sleep(self._delay)
        actual_config = int(self.get_actual_value('InputMode'))
        if actual_config == 0:
            actual_config = 'A'
        elif actual_config == 1:
            actual_config = 'A-B'
        else:
            actual_config = 'A&B'
        return actual_config

    def set_amplitude(self, uac):
        query = '8D9_' + str(uac) + '_'
        url = ('http://' + self._address + '/cgi-bin/remote.cgi?' + query)
        r = requests.get(url)
        time.sleep(self._delay)
        actual_uac = float(self.get_actual_value('Amplitude'))
        return actual_uac

    def set_frequency(self, f):
        """
        set frequency
        :param f: f
        :return: act_f
        """
        query = '8DD_' + str(f) + '_'
        url = ('http://' + self._address + '/cgi-bin/remote.cgi?' + query)
        r = requests.get(url)
        time.sleep(self._delay)
        actual_freq = float(self.get_actual_value('Frequency'))
        return actual_freq

    def set_phases(self, phase=None, phase0=None):
        if phase is not None:
            query = '8D59_' + str(phase) + '_'
            url = ('http://'+self._address+'/cgi-bin/remote.cgi?' + query)
            r = requests.get(url)
            time.sleep(self._delay)
        if phase0 is not None:
            query = '8D5D_' + str(phase0) + '_'
            url = ('http://' + self._address + '/cgi-bin/remote.cgi?' + query)
            r = requests.get(url)
            time.sleep(self._delay)
        actual_phase = float(self.get_actual_value('Phase'))
        actual_phase0 = float(self.get_actual_value('Phase0'))
        return actual_phase, actual_phase0

    def set_harmonic(self, i):
        query = '8D1_' + str(i) + '_'
        url = ('http://' + self._address + '/cgi-bin/remote.cgi?' + query)
        r = requests.get(url)
        time.sleep(self._delay)
        actual_harmonic = int(self.get_actual_value('Harmonic'))
        return actual_harmonic

    def change_reference(self, ref):
        """
        change reference signal
        :param ref: str {0|1}:
                         '0': internal reference
                         '1': external reference
        :return actual_ref: int {0|1}:
                         0: internal
                         1: external
        """
        if ref == 'int':
            ref = '0'
        else:
            ref = '1'
        query = '8DA_' + ref + '_'
        url = ('http://' + self._address + '/cgi-bin/remote.cgi?' + query)
        r = requests.get(url)
        time.sleep(self._delay)
        actual_ref = int(self.get_actual_value('RefInFlag'))
        return actual_ref

    def get_data_lia(self):
        url = ('http://' + self._address + '/data/lia.dat')
        r = requests.get(url)
        data_raw = r.text.replace(" ", "")
        data = data_raw.split("\r\n")
        for i in range(0, 4):
            data[i] = float(data[i])
        return data

