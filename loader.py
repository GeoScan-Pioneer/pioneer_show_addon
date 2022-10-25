import time

import proto
import os

import sys
import glob
import serial

import threading
import multiprocessing


class SerialMaster:
    baudrate = None
    baudrate_list = [57600, 230400, 1000000, 2000000]
    serial = None
    ports = None

    messenger = None
    stream = None
    hub = None
    connected = None

    auto_connect = None
    auto_port_detect = None
    reconnect_callback = None
    disconnect_callback = None
    __is_working = None

    def __init__(self, connect_callback, disconnect_callback, auto_connect: bool = True):
        self.connect_callback = connect_callback
        self.disconnect_callback = disconnect_callback
        self.auto_connect = auto_connect
        self.auto_port_detect = auto_connect
        self.__is_working = True

        self.port_handler_thread = threading.Thread(target=self.port_handler)
        self.port_handler_thread.start()

        self.auto_connect_thread = multiprocessing.Process(target=self.__auto_connect)
        # self.serial_handler_thread.start()

    def set_serial(self, serial):
        if not serial:
            raise Exception("Select COM-port device")
        self.serial = serial

    def set_baudrate(self, baudrate):
        if not baudrate:
            raise Exception('Set baudrate')
        self.baudrate = baudrate

    def set_baudrate_list(self, baudrate_list: list):
        if not baudrate_list:
            raise Exception('Baudrate list is empty')
        self.baudrateList = baudrate_list

    def open_serial(self, serial, baudrate):
        self.close_serial()
        try:
            self.stream = proto.SerialStream(serial, baudrate)
            self.messenger = proto.Messenger(self.stream, os.path.join('cache'))
            self.hub = self.messenger.hub
        except Exception:
            raise Exception('Failed to open port {}. Try another port and reconnect the droneNum'.format(serial))

    def port_handler(self):
        while self.__is_working:
            if self.ports:
                _cached_ports = self.ports
                self.ports = self.available_ports()
                if _cached_ports != self.ports and _cached_ports:
                    if len(_cached_ports) > len(self.ports) and self.connected:
                        for i in range(len(_cached_ports)):
                            if _cached_ports[i] not in self.ports:
                                if self.serial == _cached_ports[i]:
                                    print("disconnected port {}".format(_cached_ports[i]))
                                    self.auto_connect_thread.terminate()
                                    self.close_serial()
                                    self.disconnect_callback()
                        if self.auto_port_detect:
                            self.serial = self.ports[0]
                            print("need to connect {}".format(self.serial))
                            self.auto_connect_thread.start()
                    else:
                        if not self.connected:
                            if self.auto_port_detect:
                                if self.serial != self.ports[0]:
                                    self.serial = self.ports[0]
                                    if self.auto_connect_thread.is_alive():
                                        self.auto_connect_thread.terminate()
                                    print("need to connect {}".format(self.serial))
                                    self.auto_connect_thread.start()
            else:
                self.ports = self.available_ports()
                if self.auto_port_detect:
                    if len(self.ports) > 0:
                        self.serial = self.ports[0]
                        print("need to connect {}".format(self.serial))
                        self.auto_connect_thread.start()

    def __auto_connect(self):
        print("run auto connect")
        print(self.auto_connect)
        for baudrate in self.baudrate_list:
            self.open_serial(self.serial, baudrate)
            print(baudrate)
            try:
                if self.stream.socket.is_open:
                    self.baudrate = baudrate
                    self.connected = self.connect_messenger()
                    if self.connected:
                        print("Connected port {}".format(self.serial))

                        break
            except Exception as e:
                pass

    def connect_messenger(self):
        connected = False
        for i in range(10):
            connected = self.hub.connect()
            print(self.hub)
            if connected and self.hub['LuaScript'] is not None:
                break
        if not connected:
            raise Exception('Connection failed')
        else:
            self.connect_callback(self.stream, self.messenger, self.hub)
            return True

    def close_serial(self):
        self.connected = False
        if self.messenger:
            self.messenger.stop()
        try:
            self.stream.__del__()
        except:
            pass

    @staticmethod
    def available_ports():
        """ Lists serial port names

            :raises EnvironmentError:
                On unsupported or unknown platforms
            :returns:
                A list of the serial ports available on the system
        """
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')

        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass
        return result


class Loader:
    stream = None
    messenger = None
    hub = None

    connected = None

    def __init__(self, auto_connect: bool = True):
        self.serial_master = SerialMaster(self.connect_callback, self.disconnect_callback, auto_connect=auto_connect)

    def connect_callback(self, stream, messenger, hub):
        self.stream = stream
        self.messenger = messenger
        self.hub = hub
        self.connected = True
        print("Connected to board version {}".format(self.get_ap_firmware_version()))

    def disconnect_callback(self):
        print("Disconnected")
        self.connected = False

    def get_ap_firmware_version(self):
        try:
            for i in range(0, len(self.hub.components)):
                if self.hub.components[i].name == 'UavMonitor' or self.hub.components[i].name == 'BaseMonitor':
                    componentId = i

            version = self.hub.components[componentId].swVersion[2]
        except:
            raise Exception('Failed to get autopilot firmware version')

        return version


if __name__ == '__main__':
    showLoader = Loader(False)
    showLoader.serial_master.open_serial("/dev/ttyUSB0", 57600)
    # print("Opened serial")
    showLoader.serial_master.connect_messenger()
    while True:
        time.sleep(1)

    # print(showLoader.getApFirmwareVersion())
