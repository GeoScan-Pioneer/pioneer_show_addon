import bpy
from bpy_extras.io_utils import ExportHelper
from bpy.types import Operator, Panel, WindowManager
from bpy.props import StringProperty, BoolProperty, FloatProperty, IntProperty

import os
import math
import struct

bl_info = {
    "name": "pioneer-show",
    "author": "GeoScan Group",
    "version": (0, 2, 0),
    "blender": (2, 80, 0),
    "warning": "",
    "category": "GeoScan"
}

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
SYSTEM_PROPS_PUBLIC = [
    ("positionFreq", IntProperty(name="Position FPS",
                                 default=2)),
    ("colorFreq", IntProperty(name="Color FPS",
                              default=5)),
]

SYSTEM_PROPS_PRIVATE = [
    ("export_allowed", BoolProperty(default=False)),
    ("language", BoolProperty(default=False)),
]

LANGUAGE_PACK_ENGLISH = {
    "using_name_filter": "Use name filter for drones",
    "drones_name": "Name",
    "minimum_drone_distance": "Minimal distance (m)",
    "speed_exceed_value": "Limit of  speed (m/s)",
    "positionFreq": "Position FPS (Hz)",
    "colorFreq": "Color FPS (Hz)",
    "x_offset": "Start point X offset (m)",
    "y_offset": "Start point Y offset (m)",
    "z_offset": "Start point Z offset (m)",
    "ExportLuaBinaries": "Export LUA binaries",
    "CheckForLimits": "Check if is animation correct",
    "CheckSuccess": "Check is success",
    "SystemProperties": "GeoScan system properties",
    "ChangeLanguage": "Сменить язык",
}

LANGUAGE_PACK_RUSSIAN = {
    "using_name_filter": "Использовать фильтр имен",
    "drones_name": "Имя",
    "minimum_drone_distance": "Минимальное расстояние (м)",
    "speed_exceed_value": "Предел скорости (м/с)",
    "positionFreq": "Частота сохранения позиции (Гц)",
    "colorFreq": "Частота сохранения цветов (Гц)",
    "x_offset": "Смещение 0 точки по Х (м)",
    "y_offset": "Смещение 0 точки по У (м)",
    "z_offset": "Смещение 0 точки по Z (м)",
    "ExportLuaBinaries": "Экспорт бинарников",
    "CheckForLimits": "Проверка корректности анимации",
    "CheckSuccess": "Проверка успешно пройдена",
    "SystemProperties": "GeoScan системные параметры",
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

    x_offset: FloatProperty(
        name="X_offset",
        description="X coordinate offset",
        default=0,
        step=0.5,
    )
    y_offset: FloatProperty(
        name="Y offset",
        description="Y coordinate offset",
        default=0,
        step=0.5,
    )
    z_offset: FloatProperty(
        name="Z offset",
        description="Z coordinate offset",
        default=0,
        step=0.5,
    )
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
        local_props = ["x_offset",
                       "y_offset",
                       "z_offset", ]

        layout = self.layout
        for prop_name in global_props:
            col = layout.column()
            row = col.row()
            row.label(text=(LANGUAGE_PACK.get(context.scene.language)).get(prop_name))
            row.prop(context.scene, prop_name, text='')

        for prop_name in local_props:
            col = layout.column()
            row = col.row()
            row.label(text=(LANGUAGE_PACK.get(context.scene.language)).get(prop_name))
            row.prop(self, prop_name, text='')

    def execute(self, context):
        scene = context.scene
        objects = context.visible_objects
        pioneers = []
        fps = context.scene.render.fps
        if self.using_name_filter:
            for pioneers_obj in objects:
                if self.drones_name.lower() in pioneers_obj.name.lower():
                    pioneers.append(pioneers_obj)
        else:
            pioneers = objects

        pioneer_id = 1
        for pioneer in pioneers:
            coords_array = list()
            colors_array = list()
            faults = False
            for frame in range(scene.frame_start, scene.frame_end + 1):
                scene.frame_set(frame)
                if frame % int(fps / context.scene.positionFreq) == 0:
                    x, y, z = pioneer.matrix_world.to_translation()
                    coords_array.append((x + self.x_offset, y + self.y_offset, -z))
                if frame % int(fps / context.scene.colorFreq) == 0:
                    r, g, b, _ = pioneer.active_material.diffuse_color
                    if r is None:
                        faults = True
                        self.report({"ERROR"}, "No color found on %s on frame %d" % (pioneer.name, frame))
                        return {"CANCELLED"}
                    colors_array.append((r, g, b))
            if not faults:
                self.write_to_bin_old(pioneer_id, coords_array, colors_array, self.filepath)
            pioneer_id += 1
        self.report({"INFO"}, "GeoScan show is better than urs")
        return {"FINISHED"}

    @staticmethod
    def write_to_bin(droneNum, meta_data, coords_array, colors_array):
        HeaderFormat = '<BLBBBBBBBBHHfffff'
        size = struct.calcsize(HeaderFormat)
        outBinPath = ''.join([dirPath, '/', prefix, str(droneNum), '.bin'])
        print(outBinPath)
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
                f.write(struct.pack('<fff', point[1], point[2], point[3]))

            # Colors data starts at offset of 43300 bytes
            if coords_size < 3600:
                for _ in range(coords_size, 3600):
                    f.write(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
            # Write colors
            for color in colors_array:
                f.write(struct.pack('<BBB', color[1], color[2], color[3]))

    @staticmethod
    def write_to_bin_old(droneNum, coords_array, colors_array, filepath):
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
            "TimeStart": -1,
            "TimeEnd": -1,
            "LatOrigin": 0,
            "LonOrigin": 0,
            "AltOrigin": 0,  # not used == 0
        }

        outBinPath = ''.join([filepath, '_', str(droneNum), '.bin'])
        coords_size = len(coords_array)
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
        col.operator(CheckForLimits.bl_idname, text=(LANGUAGE_PACK.get(context.scene.language)).get("CheckForLimits"))


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
        col.operator(ChangeLanguage.bl_idname, text=(LANGUAGE_PACK.get(context.scene.language)).get("ChangeLanguage"))


class ChangeLanguage(Operator):
    bl_idname = "show.change_language"
    bl_label = "Сменить язык"

    def execute(self, context):
        context.scene.language = not context.scene.language
        return {"FINISHED"}


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
            for frame in range(scene.frame_start, scene.frame_end + 1):
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
            self.report({"INFO"}, "Check is success")
        else:
            bpy.context.scene.export_allowed = False
            if speed_exceeded:
                self.report({"ERROR"},
                            "Speed exceeded on frame %d on drone %s. speed: %.2f m/s" % (frame_speed_exceeded,
                                                                                         speed_exceeded_drone,
                                                                                         exceeded_speed))
            else:
                self.report({"ERROR"}, "Distance less than minimums n frame %d on drones  %s & %s" % (
                    frame_low_distance, low_distance_drones[0], low_distance_drones[1]))
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
        layout.menu("TOPBAR_MT_custom_sub_menu")
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


def change_handler(scene):
    bpy.context.scene.export_allowed = False


def register():
    for (prop_name, prop_value) in CONFIG_PROPS:
        setattr(bpy.types.Scene, prop_name, prop_value)

    for (prop_name, prop_value) in SYSTEM_PROPS_PUBLIC:
        setattr(bpy.types.Scene, prop_name, prop_value)

    for (prop_name, prop_value) in SYSTEM_PROPS_PRIVATE:
        setattr(bpy.types.Scene, prop_name, prop_value)

    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_editor_menus.append(TOPBAR_MT_geoscan_menu.menu_draw)
    bpy.app.handlers.depsgraph_update_pre.append(change_handler)


def unregister():
    bpy.context.scene.export_allowed = False
    [bpy.app.handlers.depsgraph_update_pre.remove(h) for h in bpy.app.handlers.depsgraph_update_pre if
     h.__name__ == "change_handler"]
    bpy.types.TOPBAR_MT_editor_menus.remove(TOPBAR_MT_geoscan_menu.menu_draw)
    for (prop_name, _) in CONFIG_PROPS:
        delattr(bpy.types.Scene, prop_name)

    for (prop_name, _) in SYSTEM_PROPS_PUBLIC:
        delattr(bpy.types.Scene, prop_name)

    for (prop_name, _) in SYSTEM_PROPS_PRIVATE:
        delattr(bpy.types.Scene, prop_name)

    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
