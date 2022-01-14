from struct import pack, unpack
import serial
import time
from core.module import Base
from interface.motor_interface import MotorInterface
from core.configoption import ConfigOption


# Basic Python APT/Kinesis Command Protocol Example using KDC001 and MTS50-Z8
# Tested in Anaconda dsitrbution of Python 2.7 and virtual environment of Python 3.6
# Command Protol PDF can be found https://www.thorlabs.com/Software/Motion%20Control/APT_Communications_Protocol.pdf
# Pyserial is a not a native module installed within python and may need to be installed if not already

class MotorSerialKDC101(Base, MotorInterface):

    _address = ConfigOption('address', missing='error')

    # Port Settings
    # baud_rate = 115200
    data_bits = 8
    stop_bits = 1
    Parity = serial.PARITY_NONE

    # Controller's Port and Channel

    #COM_Port = 'COM13'  # Change to preferred
    Channel = 1  # Channel is always 1 for a K Cube/T Cube

    Device_Unit_SF = 34555.  # pg 34 of protocal PDF (as of Issue 23)
    Device_Unit_Velocity = 772981
    Device_Unit_Acceleration = 263
    destination = 0x50  # Destination byte; 0x50 for T Cube/K Cube, USB controllers
    source = 0x01  # Source Byte


    Continuos = 1
    Step = 2


    #def __init__(self):
    #    self.baud_rate = 115200

    def on_activate(self):
        # Create Serial Object
        self.baud_rate = 115200
        self.data_bits = 8
        self.stop_bits = 1
        self.Parity = serial.PARITY_NONE
        #self.KDC001 = serial.Serial(port=self._address, baudrate=self.baud_rate, bytesize=self.data_bits,
        #                            parity=self.Parity, stopbits=self.stop_bits, timeout=0.1)

    def connection_on(self):
        self.KDC001 = serial.Serial(port=self._address, baudrate=self.baud_rate, bytesize=self.data_bits,
                                    parity=self.Parity, stopbits=self.stop_bits, timeout=0.1)

    def connection_off(self):
        self.KDC001.close()

    def on_deactivate(self):
        self.KDC001.close()

    def able(self):
        # Get HW info; MGMSG_HW_REQ_INFO; may be require by a K Cube to allow confirmation Rx messages
        self.KDC001.write(pack('<HBBBB', 0x0005, 0x00, 0x00, 0x50, 0x01))
        self.KDC001.flushInput()
        self.KDC001.flushOutput()

        # Enable Stage; MGMSG_MOD_SET_CHANENABLESTATE
        self.KDC001.write(pack('<HBBBB', 0x0210, self.Channel, 0x01, self.destination, self.source))
        print('Stage Enabled')
        time.sleep(0.1)

    def disable(self):
        # Enable Stage; MGMSG_MOD_SET_CHANENABLESTATE
        self.KDC001.write(pack('<HBBBB', 0x0210, self.Channel, 0x02, self.destination, self.source))
        print('Stage Disabled')
        time.sleep(0.1)

    def move_home(self):
        """Home Stage; MGMSG_MOT_MOVE_HOME: send the stage at home"""

        self.KDC001.write(pack('<HBBBB', 0x0443, self.Channel, 0x00, self.destination, self.source))
        print('Homing stage...')

        # Confirm stage homed before advancing; MGMSG_MOT_MOVE_HOMED: check that the stage is at home
        Rx = ''
        Homed = pack('<H', 0x0444)
        while Rx != Homed:
            Rx = self.KDC001.read(2)
        print('Stage Homed')
        self.KDC001.flushInput()
        self.KDC001.flushOutput()

    def velocity(self):
        velmin = 0
        acc = 0.1
        velmax = 0.5
        self.dUnitvelmin = int(self.Device_Unit_Velocity * velmin)
        self.dUnitacc = int(self.Device_Unit_Acceleration * acc)
        self.dUnitvelmax = int(self.Device_Unit_Velocity * velmax)
        self.KDC001.write(pack('<HBBBBHIII', 0x0413, 0x0E, 0x00, self.destination | 0x80, self.source, self.Channel,
                               self.dUnitvelmin, self.dUnitacc, self.dUnitvelmax))

    def jog(self):
        jog_step = 5
        jog_min_vel = 0
        jog_acc = 0.1
        jog_vel_max = 0.5
        jog_stop = 2

        self.jogvelmin = int(self.Device_Unit_Velocity * jog_min_vel)
        self.jogacc = int(self.Device_Unit_Acceleration * jog_acc)
        self.jogvelmax = int(self.Device_Unit_Velocity * jog_vel_max)
        self.jogstep = int(self.Device_Unit_SF * jog_step)

        self.KDC001.write(pack('<HBBBBHHIIIIH', 0x0416, 0x06, 0x00, self.destination | 0x80, self.source, self.Channel,
                               self.Continuos, self.jogstep, self.jogvelmin, self.jogacc, self.jogvelmax, jog_stop))

    def jog_move(self):
        self.KDC001.write(pack('<HBBBB',0x046A, self.Channel, 0x01, self.destination, self.source))

        # Confirm stage completed move before advancing; MGMSG_MOT_MOVE_COMPLETED
        Rx = ''
        Moved = pack('<H', 0x0464)
        while Rx != Moved:
            Rx = self.KDC001.read(2)
        print('Move Complete')
        self.KDC001.flushInput()
        self.KDC001.flushOutput()

    def move(self, pos):
        """
        Move to absolute position; MGMSG_MOT_MOVE_ABSOLUTE (long version):
        set the position where you want to move the stage
        """

        self.dUnitpos = int(self.Device_Unit_SF * pos)
        self.KDC001.write(pack('<HBBBBHI', 0x0453, 0x06, 0x00, self.destination | 0x80, self.source,
                               self.Channel, self.dUnitpos))
        print('Moving stage')

        # Confirm stage completed move before advancing; MGMSG_MOT_MOVE_COMPLETED
        Rx = ''
        Moved = pack('<H', 0x0464)
        while Rx != Moved:
            Rx = self.KDC001.read(2)
        print('Move Complete')
        self.KDC001.flushInput()
        self.KDC001.flushOutput()


    def read_position(self):
        """Request Position; MGMSG_MOT_REQ_POSCOUNTER"""

        self.KDC001.write(pack('<HBBBB', 0x0411, self.Channel, 0x00, self.destination, self.source))

        # Read back position returns by the cube; Rx message MGMSG_MOT_GET_POSCOUNTER

        self.header, self.chan_dent, self.position_dUnits = unpack('<6sHI', self.KDC001.read(12))

        getpos = self.position_dUnits / float(self.Device_Unit_SF)
        #print('Position: %.4f mm' % (getpos))

        return getpos

    def get_constraints(self):
        return 0

    def move_rel(self, param_dict):
        return 0

    def abort(self):
        return 0

    def get_pos(self, param_list=None):
        return 0

    def get_status(self, param_list=None):
        return 0

    def calibrate(self, param_list=None):
        return 0

    def get_velocity(self, param_list=None):
        return 0

    def set_velocity(self, param_dict):
        return 0

    def move_abs(self, param_dict):
        return 0

# del KDC001
