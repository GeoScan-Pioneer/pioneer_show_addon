import time
import threading
import struct
import os
import sys
import glob
import urllib.error
import urllib.request
import json
import ssl
import certifi
import subprocess
import os

if sys.platform.startswith('win'):
    py_exec = os.path.join(sys.prefix, 'bin', 'python.exe')
    target = os.path.join(sys.prefix, 'lib', 'site-packages')
    subprocess.call([py_exec, '-m', 'pip', 'install', '--upgrade', 'pip', '-t', target])
    subprocess.call([py_exec, '-m', 'pip', 'install', '--upgrade', 'pyserial', '-t', target])
else:
    py_exec = str(sys.executable)
    modules = (subprocess.check_output([py_exec, "-m", "pip", "list"])).decode("UTF-8")
    subprocess.call([py_exec, '-m', 'pip', 'install', '--upgrade', 'pip'])
    if not ("pyserial" in modules):
        subprocess.call([py_exec, "-m", "pip", "install", "pyserial"])

import proto
import serial

json_url = "https://storage.yandexcloud.net/pioneer.geoscan.aero/other/config.json"


class SerialMaster:
    baudrate = None
    baudrate_list = [57600, 115200, 230400, 1000000, 2000000]
    serial = None
    ports = None

    messenger = None
    stream = None
    hub = None

    auto_connect = None
    connected = False
    reconnect_callback = None
    disconnect_callback = None
    __is_working = None

    class Thread(threading.Thread):
        def __init__(self, target, args=None):
            threading.Thread.__init__(self)
            self.test = True
            self.target = target
            self.args = args

        def run(self):
            if self.args:
                self.target(self.args)
            else:
                self.target()

        def kill(self):
            self._tstate_lock.release()
            self._stop()

    def __init__(self, connect_callback, disconnect_callback, ports_update_callback, auto_connect: bool = True):
        self.connect_callback = connect_callback
        self.disconnect_callback = disconnect_callback
        self.ports_update_callback = ports_update_callback
        self.auto_connect = auto_connect

        self.__is_working = True

        self.port_handler_thread = self.Thread(self.__port_handler)
        self.port_handler_thread.start()

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
        self.baudrate_list = baudrate_list

    def open_serial(self, serial, baudrate):
        self.close_serial()
        try:
            self.stream = proto.SerialStream(serial, baudrate)
            self.messenger = proto.Messenger(self.stream, os.path.join('cache'))
            self.hub = self.messenger.hub
        except Exception:
            print('Failed to open port {}. Try another port and reconnect'.format(serial))

    def __port_handler(self):
        connection_thread = None
        while self.__is_working:
            if self.ports:
                _cached_ports = self.ports
                self.ports = self.available_ports()
                if _cached_ports != self.ports:
                    self.ports_update_callback()
                    if len(_cached_ports) > len(self.ports) and self.connected:
                        for i in range(len(_cached_ports)):
                            if _cached_ports[i] not in self.ports:
                                if self.serial == _cached_ports[i]:
                                    print("disconnected port {}".format(_cached_ports[i]))
                                    self.close_serial()
                                    self.disconnect_callback()
                                    self.serial = None
                        if self.auto_connect and len(self.ports):
                            self.serial = self.ports[0]
                            if connection_thread and connection_thread.is_alive():
                                connection_thread.kill()
                            connection_thread = self.__create_thread(self.__auto_connect)
                else:
                    if not self.connected:
                        if self.auto_connect and len(self.ports) > 0:
                            if self.serial != self.ports[0]:
                                self.serial = self.ports[0]
                                if connection_thread and connection_thread.is_alive():
                                    connection_thread.kill()
                                connection_thread = self.__create_thread(self.__auto_connect)
            else:
                self.ports = self.available_ports()
                if self.auto_connect:
                    if len(self.ports) > 0:
                        self.serial = self.ports[0]
                        if connection_thread and connection_thread.is_alive():
                            connection_thread.kill()
                        connection_thread = self.__create_thread(self.__auto_connect)

            if connection_thread and connection_thread.is_alive():
                if not self.auto_connect:
                    connection_thread.kill()

            if self.ports and self.auto_connect and not self.connected and not connection_thread.is_alive():
                connection_thread = self.__create_thread(self.__auto_connect)
            time.sleep(0.25)

    def __create_thread(self, target, args=None, join: bool = False):
        thread = self.Thread(target)
        thread.start()
        if join:
            thread.join()
        return thread

    def __auto_connect(self):
        print("run auto connect")
        time.sleep(0.5)
        self.__make_connection()

    def connect_serial(self, serial):
        print("run manual connect")
        time.sleep(0.5)
        self.auto_connect = False
        if serial != self.serial:
            self.close_serial()
            self.serial = serial
            self.__make_connection()

    def __make_connection(self):
        for baudrate in self.baudrate_list:
            try:
                self.open_serial(self.serial, baudrate)
            except serial.SerialException:
                pass
            try:
                if self.stream.socket.is_open:
                    self.baudrate = baudrate
                    connected = self.connect_messenger()
                    if connected:
                        print("Connected port {}".format(self.serial))
                        self.connected = True
                        break
                    else:
                        self.stream.socket.close()
            except Exception:
                pass

    def reconnect_after_restart(self):
        self.open_serial(self.serial, self.baudrate)
        try:
            self.connected = self.connect_messenger()
            return
        except Exception:
            pass
        self.__make_connection()

    def connect_messenger(self):
        connected = False
        for i in range(10):
            connected = self.hub.connect()
            if connected and self.hub['LuaScript'] is not None:
                break
        if connected:
            self.connect_callback(self.stream, self.messenger, self.hub)
            return True
        else:
            print('Connection failed')
            return False

    def close_serial(self):
        if self.connected:
            self.disconnect_callback()
        self.connected = False
        if self.messenger:
            self.messenger.stop()
        if self.stream:
            self.stream.socket.close()
        try:
            self.stream.__del__()
        except Exception:
            pass
        print(self.connected, self.serial, "close serial serialMaster")

    def available_ports(self):
        """ Lists serial port names

            :raises: EnvironmentError:
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
            if port == self.serial:
                result.append(port)
                continue
            elif port == "COM1":
                continue
            try:
                s = serial.Serial(port)
                s.close()
                if "USB" in port or "ACM" in port or "COM" in port:
                    result.append(port)
            except (OSError, serial.SerialException):
                pass

        return result


class Loader:
    stream = None
    messenger = None
    hub = None

    connected = None

    def __init__(self, addons_path, connection_callback=None, auto_connect: bool = True):
        data = None
        try:
            with urllib.request.urlopen(json_url, context=ssl.create_default_context(cafile=certifi.where()),
                                        timeout=5) as url:
                data = json.load(url)
                print("Json loaded from url")
                f = open(addons_path + "/addons/config.json", 'w')
                json.dump(data, f)
                f.close()
        except urllib.error.URLError:
            f = open(addons_path + "/addons/config.json", 'r')
            data = json.load(f)
            f.close()
            print("Json loaded from locals")
        except Exception as e:
            print(e)
        self.actual_ap_fw_version = data["ap_fw"]
        self.params_gps = data["params"]["gps"]
        self.params_lps = data["params"]["lps"]
        self.hubs_gps = data["fields"]["gps"]
        self.hubs_lps = data["fields"]["lps"]

        self.serial_master = SerialMaster(self.connect_callback, self.disconnect_callback,
                                          self.ports_update_callback,
                                          auto_connect=auto_connect)

        self._user_connection_callback = connection_callback

        self._sem = threading.Semaphore(1)

    def _acquire_sem(self, interval=1):
        timer = threading.Timer(interval, lambda: self._sem.release())
        timer.start()
        self._sem.acquire()

    def _check_bin(self, binary):
        check_bytes = b'\xaa\xbb\xcc\xdd'
        control_sequence = binary[:4]
        if control_sequence != check_bytes:
            return False
        bin_file_version = bytes(binary[4:5])
        bin_file_version = struct.unpack('<B', bin_file_version)[0]
        ap_firmware_version = self.get_ap_firmware_version()
        if (bin_file_version == 1 and ap_firmware_version > 8123) or \
                (bin_file_version == 2 and ap_firmware_version < 8016):
            return False
        return True

    def connect_callback(self, stream, messenger, hub):
        self.stream = stream
        self.messenger = messenger
        self.hub = hub
        self.connected = True
        print("Connected to board version {}".format(self.get_ap_firmware_version()))
        if self._user_connection_callback:
            self._user_connection_callback(self.connected)

    def disconnect_callback(self):
        print("Disconnected")
        self.connected = False
        if self._user_connection_callback:
            self._user_connection_callback(self.connected)

    def disconnect(self):
        print("loader disconnect")
        self.serial_master.close_serial()
        self.serial_master.serial = None

    @staticmethod
    def ports_update_callback():
        print("Ports updated")

    def enable_auto_connect(self):
        self.serial_master.auto_connect = True

    def disable_auto_connect(self):
        self.serial_master.auto_connect = False

    def kill_serial_master(self):
        self.serial_master.port_handler_thread.kill()
        self.serial_master.close_serial()

    def restart_board(self):
        if self.connected:
            self._acquire_sem(1)
            self._sem.acquire()
            for key, value in proto.Protocol.SYSTEM_COMMANDS.items():
                if value == 'Restart':
                    restart_command = key
            self.messenger.resetProgress()
            self.hub.sendCommand(restart_command, callback=self.restart_board_callback)
            self._sem.release()
            self.serial_master.reconnect_after_restart()

    @staticmethod
    def restart_board_callback(code, result):
        if result.value is not proto.Result.SUCCESS:
            print("Restarted unsuccessfully")

    def set_param(self, name, value):
        if self.connected:
            try:
                self.hub.setParam(value, name)
            except Exception as e:
                pass

    def get_board_number(self):
        if self.connected:
            board_number = self.hub.getProtocolInfo()[2]
            return board_number

    def get_ap_firmware_version(self):
        if self.connected:
            try:
                for i in range(0, len(self.hub.components)):
                    if self.hub.components[i].name == 'UavMonitor' or self.hub.components[i].name == 'BaseMonitor':
                        component_id = i

                version = self.hub.components[component_id].swVersion[2]
            except Exception:
                print('Failed to get autopilot firmware version')
                return None

            return version

    def get_ports_list(self):
        return self.serial_master.ports

    def change_port(self, port):
        self.serial_master.connect_serial(port)

    def upload_lps_params(self):
        for param in self.params_lps.keys():
            self.set_param(name=param, value=self.params_lps.get(param))

        self.restart_board()
        for hub_name in self.hubs_lps.keys():
            try:
                hub = self.hub[hub_name]
            except Exception:
                continue
            fields = self.hubs_lps[hub_name]
            for (_, field) in hub.fields.items():
                if field.name in fields.keys():
                    field.write(fields.get(field.name), self.field_written_callback)
        self.restart_board()

    def upload_gps_params(self):
        for param in self.params_gps.keys():
            self.set_param(name=param, value=self.params_gps.get(param))

        self.restart_board()
        for hub_name in self.hubs_gps.keys():
            try:
                hub = self.hub[hub_name]
            except Exception:
                continue
            fields = self.hubs_gps[hub_name]
            for (_, field) in hub.fields.items():
                if field.name in fields.keys():
                    print(field.name)
                    field.write(fields.get(field.name), self.field_written_callback)
        self.restart_board()

    def set_board_number(self, board_number):
        self.set_param(name="Board_number", value=board_number)

    @staticmethod
    def field_written_callback(_, result, value):
        if result.value is not proto.Result.SUCCESS:
            print("Field written unsuccessfully")

    def upload_lua_script(self, path):
        if self.connected:
            lua = self.hub["LuaScript"]
            if lua:
                try:
                    file = lua.files[0]
                    file.writeImpl(data=path.read(), chunkSize=48, burstSize=4, append=False, verify=True)
                except Exception:
                    pass

    def upload_bin(self, binary):
        if self.connected:
            lua = self.hub["LuaScript"]
            if lua:
                try:
                    checked = self._check_bin(binary)
                    if checked:
                        print("Begin upload bin")
                        file = lua.files[1]
                        file.writeImpl(data=binary, chunkSize=48, burstSize=4, append=False, verify=True)
                        print("Completed writing bin")
                    else:
                        raise
                except Exception as e:
                    print(e)
