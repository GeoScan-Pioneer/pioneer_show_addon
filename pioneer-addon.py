import bpy
from bpy_extras.io_utils import ExportHelper
from bpy.types import Operator, Panel
from bpy.props import StringProperty, BoolProperty, FloatProperty, IntProperty

import os
import math

bl_info = {
    "name": "pioneer-show",
    "author": "GeoScan Group",
    "version": (0, 2, 0),
    "blender": (2, 80, 0),
    "warning": "",
    "category": "GeoScan"
}


# class TOPBAR_MT_custom_sub_menu(bpy.types.Menu):
#     bl_label = "Sub Menu"
#
#     def draw(self, context):
#         layout = self.layout
#         layout.operator("mesh.primitive_cube_add")

class ExportLuaBinaries(Operator, ExportHelper):
    bl_idname = "show.export_lua_binaries"
    bl_label = "Export LUA binaries for drones"
    filename_ext = ''

    using_name_filter: BoolProperty(
        name="Filter objects by name",
        default=True,
    )

    drones_name: StringProperty(
        name="Name identifier",
        description="Name identifier for all drone objects",
        default="Pioneer"
    )

    speed_exceed_value: FloatProperty(
        name="Speed limit",
        description="Limit of drone movement speed (m/s)",
        unit='VELOCITY',
        default=3,
        min=0,
    )
    minimum_drone_distance: FloatProperty(
        name="Distance limit",
        description="Closest possible distance between drones (m)",
        unit='LENGTH',
        default=1.5,
        min=0,
    )

    filepath: StringProperty(
        name="File Path",
        description="File path used for exporting csv files",
        maxlen=1024,
        subtype='DIR_PATH',
        default=""
    )

    def execute(self, context):
        scene = context.scene
        objects = context.visible_objects
        pioneers = []
        if self.using_name_filter:
            for pioneers_obj in objects:
                if self.drones_name.lower() in pioneers_obj.name.lower():
                    pioneers.append(pioneers_obj)
        else:
            pioneers = objects

        f = open(self.filepath, 'w')
        for pioneer in pioneers:
            prev_x, prev_y, prev_z = None, None, None
            for frame in range(scene.frame_start, scene.frame_end + 1):
                scene.frame_set(frame)
                x, y, z = pioneer.matrix_world.to_translation()
                rot_z = pioneer.matrix_world.to_euler('XYZ')[2]
                f.write("%.2f %.2f %.2f\n" % (x, y, z))
        f.close()
        self.report({"INFO"}, "GeoScan show is better than urs")
        return {"FINISHED"}


CONFIG_PROPS = [
    ('using_name_filter', BoolProperty(name='Use namefilter for drones',
                                       default=True)),
    ('drones_name', StringProperty(name='Name',
                                   default="Pioneer")),
    ('minimum_drone_distance', FloatProperty(name='Minimal distance (m)',
                                             default=3.0)),
    ('speed_exceed_value', FloatProperty(name='Limit of  speed (m/s)',
                                         default=1.5)),
]
SYSTEM_PROPS = [
    ('export_allowed', BoolProperty(default=False)),
]


class ConfigurePanel(Panel):
    bl_idname = 'VIEW3D_PT_geoscan_panel'
    bl_label = 'GeoScan show'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "GeoScan"

    def draw(self, context):
        col = self.layout.column()
        for (prop_name, _) in CONFIG_PROPS:
            row = col.row()
            row.prop(context.scene, prop_name)
        for (prop_name, _) in SYSTEM_PROPS:
            row = col.row()
            row.prop(context.scene, prop_name)
        col.operator(CheckForLimits.bl_idname, text=CheckForLimits.bl_label)


class CheckForLimits(Operator):
    bl_idname = "show.limits_checker"
    bl_label = "Check if is animation correct"

    def execute(self, context):
        params = {}
        for (prop_name, _) in CONFIG_PROPS:
            exec("params.update({prop_name: context.scene." + prop_name + "})")
        speed_exeeded = False
        frame_speed_exeeded = None
        speed_exeeded_drone = None
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
            if speed_exeeded or distance_underestimated:
                break
            for frame in range(scene.frame_start, scene.frame_end + 1):
                scene.frame_set(frame)
                x, y, z = pioneer.matrix_world.to_translation()
                if prev_x is not None and prev_y is not None and prev_z is not None:
                    speed = self.get_speed((x, y, z), (prev_x, prev_y, prev_z))
                    if speed > params["speed_exceed_value"]:
                        speed_exeeded = True
                        frame_speed_exeeded = frame
                        speed_exeeded_drone = pioneer.name
                        break
                prev_x, prev_y, prev_z = x, y, z

        if not speed_exeeded and not distance_underestimated:
            bpy.context.scene.export_allowed = True
            self.report({"INFO"}, "Check is success")
        else:
            bpy.context.scene.export_allowed = False
            if speed_exeeded:
                self.report({"ERROR"}, "Speed exceeded on frame %d on drone %s" % (frame_speed_exeeded,
                                                                                   speed_exeeded_drone))
            else:
                self.report({"ERROR"}, "Distance less than minimums")
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
        _export_lua.operator(ExportLuaBinaries.bl_idname, text=ExportLuaBinaries.bl_label)

        _check_limits = col.row()
        _check_limits.operator(CheckForLimits.bl_idname, text=CheckForLimits.bl_label)

    def menu_draw(self, context):
        self.layout.menu("TOPBAR_MT_geoscan_menu")


classes = []
# classes.append(TOPBAR_MT_custom_sub_menu)
classes.append(TOPBAR_MT_geoscan_menu)
classes.append(ExportLuaBinaries)
classes.append(ConfigurePanel)
classes.append(CheckForLimits)


def change_handler(scene):
    bpy.context.scene.export_allowed = False


def register():
    for (prop_name, prop_value) in CONFIG_PROPS:
        setattr(bpy.types.Scene, prop_name, prop_value)

    for (prop_name, prop_value) in SYSTEM_PROPS:
        setattr(bpy.types.Scene, prop_name, prop_value)
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_editor_menus.append(TOPBAR_MT_geoscan_menu.menu_draw)
    bpy.app.handlers.depsgraph_update_pre.append(change_handler)


def unregister():
    bpy.context.scene.export_allowed = False
    [bpy.app.handlers.depsgraph_update_pre.remove(h) for h in pre_handlers if h.__name__ == "change_handler"]
    bpy.types.TOPBAR_MT_editor_menus.remove(TOPBAR_MT_geoscan_menu.menu_draw)
    for (prop_name, _) in CONFIG_PROPS:
        delattr(bpy.types.Scene, prop_name)

    for (prop_name, _) in SYSTEM_PROPS:
        delattr(bpy.types.Scene, prop_name)

    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
