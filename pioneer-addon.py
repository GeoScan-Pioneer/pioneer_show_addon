import time

import bpy
from bpy_extras.io_utils import ExportHelper
from bpy.types import Operator, Panel, WindowManager
from bpy.props import StringProperty, BoolProperty, FloatProperty, IntProperty, EnumProperty
import os
import math
import struct
import threading
from loader import Loader

bl_info = {
    "name": "pioneer-show",
    "author": "GeoScan Group",
    "version": (0, 2, 0),
    "blender": (2, 80, 0),
    "warning": "",
    "category": "GeoScan"
}


def scene_change_handler(scene):
    bpy.context.scene.export_allowed = False


def connection_state_handler(status, value=None):
    if "scene" in dir(bpy.context):
        if "upload_allowed" in dir(bpy.context.scene):
            if bpy.context.scene.upload_allowed:
                bpy.context.scene.upload_allowed = False


def auto_connection_set_callback(self, context):
    if context.scene.auto_connection:
        loader = classes_loader[0].loader
        loader.enable_auto_connect()


def items_ports_callback(scene, context):
    loader = classes_loader[0].loader
    if loader:
        ports = loader.get_ports_list()
        items = []
        for i, port in enumerate(ports):
            items.append((port, port, "", i))
        return items
    else:
        return None


CONFIG_PROPS = [
    ("using_name_filter", BoolProperty(name="Use name filter for drones",
                                       default=True)),
    ("drones_name", StringProperty(name="Name",
                                   default="Pioneer")),
    ("minimum_drone_distance", FloatProperty(name="Minimal distance (m)",
                                             default=3.0)),
    ("speed_exceed_value", FloatProperty(name="Limit of  speed (m/s)",
                                         default=1.5)),

]

CONFIG_PROPS_NAV = [
    ("position_system", BoolProperty(name="Use GPS/LPS",
                                     default=False, update=connection_state_handler)),
    ("x_offset", FloatProperty(name="Limit of  speed (m/s)",
                               default=0)),
    ("y_offset", FloatProperty(name="Limit of  speed (m/s)",
                               default=0)),
    ("z_offset", FloatProperty(name="Limit of  speed (m/s)",
                               default=0)),
    ("lon_offset", FloatProperty(name="Limit of  speed (m/s)",
                                 default=30.347196)),
    ("lat_offset", FloatProperty(name="Limit of  speed (m/s)",
                                 default=60.010663)),
]

test_items = [
    ("RED", "Red", "", 1),  # value, display, hz, id
    ("GREEN", "Green", "", 2),
    ("BLUE", "Blue", "", 3),
    ("YELLOW", "Yellow", "", 4),
]

PIONEER_PROPS = [
    ("board_number", IntProperty(name="Board_number",
                                 default=1)),
    ("available_ports", EnumProperty(items=items_ports_callback, name="Available ports", default=None)),
    ("auto_connection", BoolProperty(name="Auto port connection", default=True, update=auto_connection_set_callback)),
]

SYSTEM_PROPS_PUBLIC = [
    ("positionFreq", IntProperty(name="Position FPS",
                                 default=2)),
    ("colorFreq", IntProperty(name="Color FPS",
                              default=5)),

]

SYSTEM_PROPS_PRIVATE = [
    ("export_allowed", BoolProperty(default=False)),
    ("upload_allowed", BoolProperty(default=False)),
    ("language", BoolProperty(default=False)),
]

LANGUAGE_PACK_ENGLISH = {
    "using_name_filter": "Use name filter for drones",
    "drones_name": "Name",
    "minimum_drone_distance": "Minimal distance (m)",
    "speed_exceed_value": "Limit of  speed (m/s)",
    "positionFreq": "Position FPS (Hz)",
    "colorFreq": "Color FPS (Hz)",
    "position_system_true": "Navigation system: outdoors",
    "position_system_false": "Navigation system: indoors",
    "x_offset": "Start point X offset (m)",
    "y_offset": "Start point Y offset (m)",
    "z_offset": "Start point Z offset (m)",
    "lon_offset": "Start point longitude (deg)",
    "lat_offset": "Start point latitude (deg)",
    "board_number": "Drone number",
    "ExportLuaBinaries": "Export LUA binaries",
    "CheckForLimits": "Check if is animation correct",
    "CheckSuccess": "Check is success",
    "ConnectPioneer": "Connect Pioneer",
    "DisconnectPioneer": "Disconnect Pioneer",
    "UploadNavSystemParams": "Upload params",
    "UploadFilesToPioneer": "Upload files",
    "auto_connection": "Auto port connection",
    "no_pioneer_connected": "No Pioneer connected",
    "pioneer_fw_version": "Pioneer firmware version: ",
    "pioneer_connected_port": "Pioneer port: ",
    "speed_exceeded_error": "Speed exceeded on frame %d on drone %s. speed: %.2f m/s",
    "distance_underestimated_error": "Distance less than minimums on frame %d on drones  %s & %s",
    "miss_color_error": "No color found on %s on frame %d",
    "export_succeed": "GeoScan show is better than urs!",
    "SystemProperties": "GeoScan System properties",
    "ConfigProperties": "GeoScan Show",
    "ConnectionPanel": "GeoScan Pioneer connection",
    "ChangeLanguage": "Сменить язык",
}

LANGUAGE_PACK_RUSSIAN = {
    "using_name_filter": "Использовать фильтр имен",
    "drones_name": "Имя",
    "minimum_drone_distance": "Минимальное расстояние (м)",
    "speed_exceed_value": "Предел скорости (м/с)",
    "positionFreq": "Частота сохранения позиции (Гц)",
    "colorFreq": "Частота сохранения цветов (Гц)",
    "position_system_true": "Навигация на улице",
    "position_system_false": "Навигация в помещении",
    "x_offset": "Смещение 0 точки по Х (м)",
    "y_offset": "Смещение 0 точки по У (м)",
    "z_offset": "Смещение 0 точки по Z (м)",
    "lon_offset": "Долгота стартовой точки (град)",
    "lat_offset": "Ширина стартовой точки (град)",
    "board_number": "Номер дрона",
    "ExportLuaBinaries": "Экспорт бинарников",
    "CheckForLimits": "Проверка корректности анимации",
    "CheckSuccess": "Проверка успешно пройдена",
    "ConnectPioneer": "Подключить Пионер",
    "DisconnectPioneer": "Отключить Пионер",
    "UploadNavSystemParams": "Загрузить параметры",
    "UploadFilesToPioneer": "Загрузить файлы",
    "auto_connection": "Автоматическое подключение",
    "no_pioneer_connected": "Пионер не подключен",
    "pioneer_fw_version": "Версия прошивки Пионера: ",
    "pioneer_connected_port": "Порт Пионера: ",
    "speed_exceeded_error": "Скорость превышена на кадре %d дроном %s. скорость: %.2f м/с",
    "distance_underestimated_error": "Расстояние меньше минимального на кадре %d между дронами  %s и %s",
    "miss_color_error": "Не найден цвет у %s на кадре %d",
    "export_succeed": "GeoScan шоу успешно создано",
    "SystemProperties": "GeoScan Системные параметры",
    "ConfigProperties": "GeoScan Шоу",
    "ConnectionPanel": "GeoScan Подключение к дрону",
    "ChangeLanguage": "Change language",
}

LANGUAGE_PACK = {
    False: LANGUAGE_PACK_ENGLISH,
    True: LANGUAGE_PACK_RUSSIAN
}


class ExportLuaBinaries(Operator, ExportHelper):
    bl_idname = "show.export_lua_binaries"
    bl_label = "Export LUA binaries for drones"
    filename_ext = ''
    filepath: StringProperty(
        name="File Path",
        description="File path used for exporting csv files",
        maxlen=1024,
        subtype='DIR_PATH',
        default=""
    )

    def draw(self, context):
        global_props = ["using_name_filter",
                        "drones_name",
                        "positionFreq",
                        "colorFreq", ]

        props_lps = ["x_offset",
                     "y_offset",
                     "z_offset", ]

        props_gps = ["lon_offset",
                     "lat_offset", ]

        layout = self.layout
        for prop_name in global_props:
            col = layout.column()
            row = col.row()
            row.label(text=(LANGUAGE_PACK.get(context.scene.language)).get(prop_name))
            row.prop(context.scene, prop_name, text='')

        col = layout.column()
        row = col.row()
        if context.scene.position_system:
            row.label(text=(LANGUAGE_PACK.get(context.scene.language)).get("position_system_true"))
        else:
            row.label(text=(LANGUAGE_PACK.get(context.scene.language)).get("position_system_false"))
        row.prop(context.scene, "position_system", text='')

        if context.scene.position_system:
            for prop_name in props_gps:
                col = layout.column()
                row = col.row()
                row.label(text=(LANGUAGE_PACK.get(context.scene.language)).get(prop_name))
                row.prop(context.scene, prop_name, text='')
        else:
            for prop_name in props_lps:
                col = layout.column()
                row = col.row()
                row.label(text=(LANGUAGE_PACK.get(context.scene.language)).get(prop_name))
                row.prop(context.scene, prop_name, text='')

    def execute(self, context):
        scene = context.scene
        objects = context.visible_objects
        pioneers = []
        if context.scene.using_name_filter:
            for pioneers_obj in objects:
                if scene.drones_name.lower() in pioneers_obj.name.lower():
                    pioneers.append(pioneers_obj)
        else:
            pioneers = objects

        pioneer_id = 1
        for pioneer in pioneers:
            coords_array, colors_array, faults = self.prepare_export_arrays(pioneer)
            if not faults:
                if self.position_system:
                    self.write_to_bin(pioneer_id, coords_array, colors_array, self.filepath,
                                      [self.lat_offset, self.lon_offset])
                else:
                    self.write_to_bin(pioneer_id, coords_array, colors_array, self.filepath,
                                      [self.x_offset, self.y_offset])
            else:
                return {"CANCELLED"}
            pioneer_id += 1
        self.report({"INFO"}, (LANGUAGE_PACK.get(context.scene.language)).get("export_succeed"))
        return {"FINISHED"}

    def prepare_export_arrays(self, pioneer, scene):
        coords_array = list()
        colors_array = list()
        faults = False
        for frame in range(scene.frame_start, scene.frame_end + 1):
            scene.frame_set(frame)
            if frame % int(scene.render.fps / scene.positionFreq) == 0:
                x, y, z = pioneer.matrix_world.to_translation()
                coords_array.append((x + self.x_offset * (not self.position_system),
                                     y + self.y_offset * (not self.position_system), z + self.z_offset) * (
                                        not self.position_system))
            if frame % int(scene.render.fps / scene.colorFreq) == 0:
                r, g, b, _ = pioneer.active_material.diffuse_color
                if r is None:
                    faults = True
                    self.report({"ERROR"}, (LANGUAGE_PACK.get(scene.language)).get("missed_color_error")
                                % (pioneer.name, frame))
                colors_array.append((r, g, b))
        return coords_array, colors_array, faults

    @staticmethod
    def write_to_bin(droneNum, coords_array, colors_array, filepath, origin, to_file: bool = True):
        HeaderFormat = '<BLBBBBBBBBHHfffff'
        size = struct.calcsize(HeaderFormat)
        meta_data = {
            # if -1 == should be calculated
            "Version": 2,
            "AnimationId": 1,
            "PreFlightColor": 249,
            "UserColorRed": 0,
            "UserColorGreen": 0,
            "UserColorBlue": 0,
            "FreqPositions": bpy.context.scene.positionFreq,
            "FreqColors": bpy.context.scene.colorFreq,
            "FormatPositions": struct.calcsize('f'),
            "FormatColors": struct.calcsize('B'),
            "NumberPositions": len(coords_array),
            "NumberColors": len(colors_array),
            "TimeStart": 0,
            "TimeEnd": round(len(coords_array) / bpy.context.scene.positionFreq, 2),
            "LatOrigin": origin[0],
            "LonOrigin": origin[1],
            "AltOrigin": 0,  # not used == 0
        }
        outBinPath = ''.join([filepath, '_', str(droneNum), '.bin'])
        coords_size = len(coords_array)
        with open(outBinPath, "wb") as f:
            # Control sequence
            f.write(b'\xaa\xbb\xcc\xdd')
            f.write(struct.pack(HeaderFormat, meta_data['Version'],
                                meta_data['AnimationId'],
                                meta_data['PreFlightColor'],
                                meta_data['UserColorRed'],
                                meta_data['UserColorGreen'],
                                meta_data['UserColorBlue'],
                                meta_data['FreqPositions'],
                                meta_data['FreqColors'],
                                meta_data['FormatPositions'],
                                meta_data['FormatColors'],
                                meta_data['NumberPositions'],
                                meta_data['NumberColors'],
                                meta_data['TimeStart'],
                                meta_data['TimeEnd'],
                                meta_data['LatOrigin'],
                                meta_data['LonOrigin'],
                                meta_data['AltOrigin']))
            # Points data starts at offset of 100 bytes
            for i in range(size + 4, 100):
                f.write(b'\x00')
            # Write points
            for point in coords_array:
                f.write(struct.pack('<fff', point[0], point[1], point[2]))

            # Colors data starts at offset of 43300 bytes
            if coords_size < 3600:
                for _ in range(coords_size, 3600):
                    f.write(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
            # Write colors
            for color in colors_array:
                f.write(struct.pack('<BBB', int(color[0] * 255), int(color[1] * 255), int(color[2] * 255)))

            f.close()

    @staticmethod
    def write_to_bin_old(droneNum, coords_array, colors_array, filepath, origin):
        headerFormat = "<BBBBBBHHfffff"
        size = struct.calcsize(headerFormat)
        meta_data = {
            # if -1 == should be calculated
            "Version": 1,
            "AnimationId": 0,
            "FreqPositions": bpy.context.scene.positionFreq,
            "FreqColors": bpy.context.scene.colorFreq,
            "FormatPositions": struct.calcsize('f'),
            "FormatColors": struct.calcsize('B'),
            "NumberPositions": len(coords_array),
            "NumberColors": len(colors_array),
            "TimeStart": 0,
            "TimeEnd": round(len(coords_array) / bpy.context.scene.positionFreq, 2),
            "LatOrigin": origin[0],
            "LonOrigin": origin[1],
            "AltOrigin": 0,  # not used == 0
        }

        coords_size = len(coords_array)
        outBinPath = ''.join([filepath, '_', str(droneNum - 1), '_old.bin'])
        with open(outBinPath, "wb") as f:
            # Control sequence
            f.write(b'\xaa\xbb\xcc\xdd')
            f.write(struct.pack(headerFormat, meta_data['Version'],
                                meta_data['AnimationId'],
                                meta_data['FreqPositions'],
                                meta_data['FreqColors'],
                                meta_data['FormatPositions'],
                                meta_data['FormatColors'],
                                meta_data['NumberPositions'],
                                meta_data['NumberColors'],
                                meta_data['TimeStart'],
                                meta_data['TimeEnd'],
                                meta_data['LatOrigin'],
                                meta_data['LonOrigin'],
                                meta_data['AltOrigin']))
            # Points data starts at offset of 100 bytes
            for i in range(size + 4, 100):
                f.write(b'\x00')
            # Write points
            for point in coords_array:
                f.write(struct.pack('<fff', point[0], point[1], point[2]))

            # Colors data starts at offset of 21700 bytes
            if coords_size < 1800:
                for _ in range(coords_size, 1800):
                    f.write(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
            # Write colors
            for color in colors_array:
                f.write(struct.pack('<BBB', int(color[0] * 255), int(color[1] * 255), int(color[2] * 255)))

            f.close()


class ConnectPioneer(Operator):
    bl_idname = "show.connect_pioneer"
    bl_label = "Подключить пионер"
    loader = None

    def execute(self, context):
        if self.loader:
            if context.scene.available_ports:
                context.scene.auto_connection = False
                self.loader.change_port(context.scene.available_ports)
                time.sleep(1)

        return {"FINISHED"}


class DisconnectPioneer(Operator):
    bl_idname = "show.disconnect_pioneer"
    bl_label = "Отключить пионер"
    loader = None

    def execute(self, context):
        if self.loader:
            if self.loader.connected:
                context.scene.auto_connection = False
                self.loader.disconnect()

        return {"FINISHED"}


class UploadNavSystemParams(Operator):
    bl_idname = "show.upload_navsystem_params"
    bl_label = "Обновить параметры под систему навигации"
    loader = None

    def execute(self, context):
        if self.loader:
            try:
                if context.scene.position_system:
                    self.loader.upload_gps_params()
                else:
                    self.loader.upload_lps_params()
                context.scene.upload_allowed = True
            except Exception as e:
                self.report({"ERROR"}, str(e))
                context.scene.upload_allowed = False
        return {"FINISHED"}


class UploadFilesToPioneer(Operator):
    bl_idname = "show.upload_files_to_pionner"
    bl_label = "Загрузить файлы на пионер"
    loader = None

    def execute(self, context):
        scene = context.scene
        if scene.upload_allowed:
            pass
        return {"FINISHED"}

    def prepare_export_arrays(self, pioneer, scene):
        coords_array = list()
        colors_array = list()
        faults = False
        for frame in range(scene.frame_start, scene.frame_end + 1):
            scene.frame_set(frame)
            if frame % int(scene.render.fps / scene.positionFreq) == 0:
                x, y, z = pioneer.matrix_world.to_translation()
                coords_array.append((x + self.x_offset * (not self.position_system),
                                     y + self.y_offset * (not self.position_system), z + self.z_offset) * (
                                        not self.position_system))
            if frame % int(scene.render.fps / scene.colorFreq) == 0:
                r, g, b, _ = pioneer.active_material.diffuse_color
                if r is None:
                    faults = True
                    self.report({"ERROR"}, (LANGUAGE_PACK.get(scene.language)).get("missed_color_error")
                                % (pioneer.name, frame))
                colors_array.append((r, g, b))
        return coords_array, colors_array, faults

    @staticmethod
    def write_to_bin(droneNum, coords_array, colors_array, filepath, origin, to_file: bool = True):
        HeaderFormat = '<BLBBBBBBBBHHfffff'
        size = struct.calcsize(HeaderFormat)
        meta_data = {
            # if -1 == should be calculated
            "Version": 2,
            "AnimationId": 1,
            "PreFlightColor": 249,
            "UserColorRed": 0,
            "UserColorGreen": 0,
            "UserColorBlue": 0,
            "FreqPositions": bpy.context.scene.positionFreq,
            "FreqColors": bpy.context.scene.colorFreq,
            "FormatPositions": struct.calcsize('f'),
            "FormatColors": struct.calcsize('B'),
            "NumberPositions": len(coords_array),
            "NumberColors": len(colors_array),
            "TimeStart": 0,
            "TimeEnd": round(len(coords_array) / bpy.context.scene.positionFreq, 2),
            "LatOrigin": origin[0],
            "LonOrigin": origin[1],
            "AltOrigin": 0,  # not used == 0
        }
        coords_size = len(coords_array)
        binary = b''
        binary += b'\xaa\xbb\xcc\xdd'
        binary += (struct.pack(HeaderFormat, meta_data['Version'],
                               meta_data['AnimationId'],
                               meta_data['PreFlightColor'],
                               meta_data['UserColorRed'],
                               meta_data['UserColorGreen'],
                               meta_data['UserColorBlue'],
                               meta_data['FreqPositions'],
                               meta_data['FreqColors'],
                               meta_data['FormatPositions'],
                               meta_data['FormatColors'],
                               meta_data['NumberPositions'],
                               meta_data['NumberColors'],
                               meta_data['TimeStart'],
                               meta_data['TimeEnd'],
                               meta_data['LatOrigin'],
                               meta_data['LonOrigin'],
                               meta_data['AltOrigin']))
        # Points data starts at offset of 100 bytes
        for i in range(size + 4, 100):
            binary += b'\x00'
        # Write points
        for point in coords_array:
            binary += struct.pack('<fff', point[0], point[1], point[2])

        # Colors data starts at offset of 43300 bytes
        if coords_size < 3600:
            for _ in range(coords_size, 3600):
                binary += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        # Write colors
        for color in colors_array:
            binary += struct.pack('<BBB', int(color[0] * 255), int(color[1] * 255), int(color[2] * 255))

        return binary

    @staticmethod
    def write_to_bin_old(droneNum, coords_array, colors_array, filepath, origin, to_file: bool = True):
        headerFormat = "<BBBBBBHHfffff"
        size = struct.calcsize(headerFormat)
        meta_data = {
            # if -1 == should be calculated
            "Version": 1,
            "AnimationId": 0,
            "FreqPositions": bpy.context.scene.positionFreq,
            "FreqColors": bpy.context.scene.colorFreq,
            "FormatPositions": struct.calcsize('f'),
            "FormatColors": struct.calcsize('B'),
            "NumberPositions": len(coords_array),
            "NumberColors": len(colors_array),
            "TimeStart": 0,
            "TimeEnd": round(len(coords_array) / bpy.context.scene.positionFreq, 2),
            "LatOrigin": origin[0],
            "LonOrigin": origin[1],
            "AltOrigin": 0,  # not used == 0
        }
        coords_size = len(coords_array)
        binary = b''
        binary += b'\xaa\xbb\xcc\xdd'
        binary += struct.pack(headerFormat, meta_data['Version'],
                              meta_data['AnimationId'],
                              meta_data['FreqPositions'],
                              meta_data['FreqColors'],
                              meta_data['FormatPositions'],
                              meta_data['FormatColors'],
                              meta_data['NumberPositions'],
                              meta_data['NumberColors'],
                              meta_data['TimeStart'],
                              meta_data['TimeEnd'],
                              meta_data['LatOrigin'],
                              meta_data['LonOrigin'],
                              meta_data['AltOrigin'])
        # Points data starts at offset of 100 bytes
        for i in range(size + 4, 100):
            binary += b'\x00'
        # Write points
        for point in coords_array:
            binary += struct.pack('<fff', point[0], point[1], point[2])

        # Colors data starts at offset of 21700 bytes
        if coords_size < 1800:
            for _ in range(coords_size, 1800):
                binary += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        # Write colors
        for color in colors_array:
            binary += struct.pack('<BBB', int(color[0] * 255), int(color[1] * 255), int(color[2] * 255))

        return binary


class ConfigurePanel(Panel):
    bl_idname = 'VIEW3D_PT_geoscan_config_panel'
    bl_label = 'GeoScan show'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "GeoScan"

    def draw(self, context):
        col = self.layout.column()
        for (prop_name, _) in CONFIG_PROPS:
            row = col.row()
            row.prop(context.scene, prop_name, text=(LANGUAGE_PACK.get(context.scene.language)).get(prop_name))
        col.operator(CheckForLimits.bl_idname,
                     text=(LANGUAGE_PACK.get(context.scene.language)).get("CheckForLimits"))


class SystemPanel(Panel):
    bl_idname = 'VIEW3D_PT_geoscan_system_panel'
    bl_label = 'GeoScan system properties'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "GeoScan"

    def draw(self, context):
        col = self.layout.column()
        for (prop_name, _) in SYSTEM_PROPS_PUBLIC:
            row = col.row()
            row.prop(context.scene, prop_name, text=(LANGUAGE_PACK.get(context.scene.language)).get(prop_name))
        col.operator(ChangeLanguage.bl_idname,
                     text=(LANGUAGE_PACK.get(context.scene.language)).get("ChangeLanguage"))


class ConnectionPanel(Panel):
    bl_idname = 'VIEW3D_PT_geoscan_connection_panel'
    bl_label = 'GeoScan Pioneer connection'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "GeoScan"''
    loader = None

    def draw(self, context):
        props_lps = ["x_offset",
                     "y_offset",
                     "z_offset", ]

        props_gps = ["lon_offset",
                     "lat_offset", ]

        layout = self.layout
        scene = context.scene
        col = layout.column()
        row = col.row()

        if scene.position_system:
            row.label(text=(LANGUAGE_PACK.get(context.scene.language)).get("position_system_true"))
        else:
            row.label(text=(LANGUAGE_PACK.get(context.scene.language)).get("position_system_false"))
        row.prop(scene, "position_system", text='')

        if context.scene.position_system:
            for prop_name in props_gps:
                col = layout.column()
                row = col.row()
                row.label(text=(LANGUAGE_PACK.get(context.scene.language)).get(prop_name))
                row.prop(scene, prop_name, text='')
        else:
            for prop_name in props_lps:
                col = layout.column()
                row = col.row()
                row.label(text=(LANGUAGE_PACK.get(context.scene.language)).get(prop_name))
                row.prop(scene, prop_name, text='')

        col = layout.column()
        row = col.row()
        row.label(text=(LANGUAGE_PACK.get(context.scene.language)).get("board_number"))
        row.prop(scene, "board_number", text='')

        row = col.row()
        row.label(text=(LANGUAGE_PACK.get(context.scene.language)).get("auto_connection"))
        row.prop(scene, "auto_connection", text='')

        row = col.row()
        row.prop(scene, "available_ports", text='')
        row.operator(ConnectPioneer.bl_idname, text=(LANGUAGE_PACK.get(context.scene.language)).get("ConnectPioneer"))

        if self.loader and self.loader.connected:
            row = col.row()
            row.label(text=(LANGUAGE_PACK.get(context.scene.language)).get("pioneer_connected_port") + str(
                self.loader.serial_master.serial))

        row = col.row()
        if self.loader:
            if self.loader.connected:
                row.label(text=(LANGUAGE_PACK.get(context.scene.language)).get("pioneer_fw_version") + str(
                    self.loader.get_ap_firmware_version()))
            else:
                row.label(text=(LANGUAGE_PACK.get(context.scene.language)).get("no_pioneer_connected"))
        else:
            row.label(text=(LANGUAGE_PACK.get(context.scene.language)).get("no_pioneer_connected"))
        row = col.row()
        row.operator(DisconnectPioneer.bl_idname,
                     text=(LANGUAGE_PACK.get(context.scene.language)).get("DisconnectPioneer"))

        row = col.row()
        row.operator(UploadNavSystemParams.bl_idname,
                     text=(LANGUAGE_PACK.get(context.scene.language)).get("UploadNavSystemParams"))

        _upload_binaries = row.row()
        _upload_binaries.enabled = scene.upload_allowed
        _upload_binaries.operator(UploadFilesToPioneer.bl_idname,
                                  text=(LANGUAGE_PACK.get(context.scene.language)).get("UploadFilesToPioneer"))


class ChangeLanguage(Operator):
    bl_idname = "show.change_language"
    bl_label = "Сменить язык"

    def execute(self, context):
        context.scene.language = not context.scene.language
        self.change_label(context, "VIEW3D_PT_geoscan_config_panel", "ConfigProperties")
        self.change_label(context, "VIEW3D_PT_geoscan_system_panel", "SystemProperties")
        self.change_label(context, "VIEW3D_PT_geoscan_connection_panel", "ConnectionPanel")
        return {"FINISHED"}

    @staticmethod
    def change_label(context, bl_idname, language_idname):
        system_panel = getattr(bpy.types, bl_idname)
        if system_panel.is_registered:
            bpy.utils.unregister_class(system_panel)
            system_panel.bl_label = (LANGUAGE_PACK.get(context.scene.language)).get(language_idname)
            bpy.utils.register_class(system_panel)


class CheckForLimits(Operator):
    bl_idname = "show.limits_checker"
    bl_label = "Check if is animation correct"

    def execute(self, context):
        params = {}
        for (prop_name, _) in CONFIG_PROPS:
            exec("params.update({prop_name: context.scene." + prop_name + "})")
        speed_exceeded = False
        frame_speed_exceeded = None
        speed_exceeded_drone = None
        exceeded_speed = None
        distance_underestimated = False
        frame_low_distance = None
        low_distance_drones = [None, None]

        scene = context.scene
        objects = context.visible_objects
        pioneers = []
        if params["using_name_filter"]:
            for pioneers_obj in objects:
                if params["drones_name"].lower() in pioneers_obj.name.lower():
                    pioneers.append(pioneers_obj)
        else:
            pioneers = objects

        for pioneer in pioneers:
            prev_x, prev_y, prev_z = None, None, None
            if speed_exceeded or distance_underestimated:
                break
            for frame in range(scene.frame_start, scene.frame_end + 1, int(scene.render.fps / scene.positionFreq)):
                scene.frame_set(frame)
                x, y, z = pioneer.matrix_world.to_translation()
                if prev_x is not None and prev_y is not None and prev_z is not None:
                    speed = self.get_speed((x, y, z), (prev_x, prev_y, prev_z))
                    if speed > params["speed_exceed_value"]:
                        speed_exceeded = True
                        frame_speed_exceeded = frame
                        speed_exceeded_drone = pioneer.name
                        exceeded_speed = speed
                        break
                prev_x, prev_y, prev_z = x, y, z
                for another_pioneer in pioneers[pioneers.index(pioneer) + 1:]:
                    _x, _y, _z = another_pioneer.matrix_world.to_translation()
                    distance = self.get_distance((x, y, z), (_x, _y, _z))
                    if distance < context.scene.minimum_drone_distance:
                        distance_underestimated = True
                        frame_low_distance = frame
                        low_distance_drones = [pioneer.name, another_pioneer.name]
                        break

        if not speed_exceeded and not distance_underestimated:
            bpy.context.scene.export_allowed = True
            self.report({"INFO"}, (LANGUAGE_PACK.get(context.scene.language)).get("CheckSuccess"))
        else:
            bpy.context.scene.export_allowed = False
            if speed_exceeded:
                self.report({"ERROR"}, (LANGUAGE_PACK.get(context.scene.language)).get("speed_exceeded_error") % (
                    frame_speed_exceeded,
                    speed_exceeded_drone,
                    exceeded_speed))
            else:
                self.report({"ERROR"},
                            (LANGUAGE_PACK.get(context.scene.language)).get("distance_underestimated_error")
                            % (frame_low_distance, low_distance_drones[0], low_distance_drones[1]))
        return {"FINISHED"}

    @staticmethod
    def get_distance(p1, p2):
        return math.sqrt((p1[0] - p2[0]) ** 2 +
                         (p1[1] - p2[1]) ** 2 +
                         (p1[2] - p2[2]) ** 2
                         )

    def get_speed(self, p1, p2):
        diff_time = 1 / bpy.context.scene.render.fps
        return self.get_distance(p1, p2) / diff_time


class TOPBAR_MT_geoscan_menu(bpy.types.Menu):
    bl_label = "GeoScan"

    def draw(self, context):
        layout = self.layout
        layout.menu("TOPBAR_MT_geoscan_sub_menu")
        col = layout.column()
        row = col.row()

        _export_lua = row.row()
        _export_lua.enabled = bpy.context.scene.export_allowed
        _export_lua.operator(ExportLuaBinaries.bl_idname,
                             text=(LANGUAGE_PACK.get(context.scene.language)).get("ExportLuaBinaries"))

        _check_limits = col.row()
        _check_limits.operator(CheckForLimits.bl_idname,
                               text=(LANGUAGE_PACK.get(context.scene.language)).get("CheckForLimits"))

        _change_language = col.row()
        _change_language.operator(ChangeLanguage.bl_idname,
                                  text=(LANGUAGE_PACK.get(context.scene.language)).get("ChangeLanguage"))

    def menu_draw(self, context):
        self.layout.menu("TOPBAR_MT_geoscan_menu")


classes = list()
classes.append(TOPBAR_MT_geoscan_menu)
classes.append(ExportLuaBinaries)
classes.append(ConfigurePanel)
classes.append(SystemPanel)
classes.append(CheckForLimits)
classes.append(ChangeLanguage)

classes_loader = list()
classes_loader.append(ConnectPioneer)
classes_loader.append(DisconnectPioneer)
classes_loader.append(UploadNavSystemParams)
classes_loader.append(UploadFilesToPioneer)
classes_loader.append(ConnectionPanel)


def _disable_uploading_on_startup():
    while not ("scene" in dir(bpy.context)):
        pass
    bpy.context.scene.upload_allowed = False


def register():
    for (prop_name, prop_value) in CONFIG_PROPS:
        setattr(bpy.types.Scene, prop_name, prop_value)

    for (prop_name, prop_value) in CONFIG_PROPS_NAV:
        setattr(bpy.types.Scene, prop_name, prop_value)

    for (prop_name, prop_value) in PIONEER_PROPS:
        setattr(bpy.types.Scene, prop_name, prop_value)

    for (prop_name, prop_value) in SYSTEM_PROPS_PUBLIC:
        setattr(bpy.types.Scene, prop_name, prop_value)

    for (prop_name, prop_value) in SYSTEM_PROPS_PRIVATE:
        setattr(bpy.types.Scene, prop_name, prop_value)

    for cls in classes:
        bpy.utils.register_class(cls)

    loader = Loader(connection_state_handler)
    time.sleep(1)
    for loader_cls in classes_loader:
        loader_cls.loader = loader

    for cls in classes_loader:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_editor_menus.append(TOPBAR_MT_geoscan_menu.menu_draw)
    bpy.app.handlers.depsgraph_update_pre.append(scene_change_handler)

    _disable_uploading_on_startup_thread = threading.Thread(target=_disable_uploading_on_startup)
    _disable_uploading_on_startup_thread.start()


def unregister():
    bpy.context.scene.export_allowed = False
    [bpy.app.handlers.depsgraph_update_pre.remove(h) for h in bpy.app.handlers.depsgraph_update_pre if
     h.__name__ == "scene_change_handler"]
    bpy.types.TOPBAR_MT_editor_menus.remove(TOPBAR_MT_geoscan_menu.menu_draw)
    for (prop_name, _) in CONFIG_PROPS:
        delattr(bpy.types.Scene, prop_name)

    for (prop_name, _) in CONFIG_PROPS_NAV:
        delattr(bpy.types.Scene, prop_name)

    for (prop_name, _) in PIONEER_PROPS:
        delattr(bpy.types.Scene, prop_name)

    for (prop_name, _) in SYSTEM_PROPS_PUBLIC:
        delattr(bpy.types.Scene, prop_name)

    for (prop_name, _) in SYSTEM_PROPS_PRIVATE:
        delattr(bpy.types.Scene, prop_name)

    for cls in classes:
        bpy.utils.unregister_class(cls)

    for cls in classes_loader:
        bpy.utils.unregister_class(cls)

    loader = classes_loader[0].loader
    if loader:
        loader.kill_serial_master()


if __name__ == "__main__":
    register()
