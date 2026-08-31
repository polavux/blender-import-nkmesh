bl_info = {
    "name": "Import/Export Nkmesh",
    "blender": (5, 2, 1),
    "category": "Import - Export",
}

import bpy, math
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty
from mathutils import Matrix
from itertools import chain, repeat
from nkmesh import Nkmesh

# expands a tuple of run length encoded tuples into one long tuple of tuples
def decode_rle(rle_data) -> tuple:
    return tuple(chain.from_iterable(repeat(data, run_length) for run_length, data in rle_data))

# i only wrote an import function, no export (that would require fully understanding the file format)
class ImportNkmesh(bpy.types.Operator, ImportHelper):
    bl_idname = "import_mesh.nkmesh"
    bl_label = "Import Nkmesh (.nkmesh)"
    
    filename_ext = ".nkmesh"
    filter_glob: StringProperty(default="*.nkmesh", options={"HIDDEN"})
    
    def execute(self, ctx):
        nkmesh = Nkmesh.from_file(self.filepath)
        
        # create nodes as a child of an empty "Nkmesh" object for convenience
        root_obj = bpy.data.objects.new("Nkmesh", None)
        bpy.context.collection.objects.link(root_obj)
        
        # recursive function to recreate the node hierarchy of the model
        # todo:
        # - automatically generating a material for each texture (texture node + color attribute node -> multiply node in "color" mode -> material output)
        # - assigning generated materials to meshes
        # - limb nodes, armatures, and other things relating to animations
        # - node transforms, whatever those unknown values in the node structure are for
        # - vertex normals (currently blender generates them automatically instead of using the ones imported from the file, though idk if it makes a difference)
        # - whatever that unknown stuff at the end of the mesh structure is for
        # - whatever that unknown stuff at the end of the whole file is for
        def recursive_get_nodes(node_data, parent_obj) -> None:
            scene_obj = None
            
            # Mesh
            if node_data.node_type == "Mesh":
                # make a mesh out of you
                mesh = nkmesh.meshes[node_data.mesh_index]
                scene_mesh = bpy.data.meshes.new(mesh.name)
                scene_obj = bpy.data.objects.new(node_data.name, scene_mesh)
                
                # import verts/tris
                scene_mesh.from_pydata(mesh.vert_coords, [], mesh.polygons)
                
                # create UV map and vert colors
                uv_layer = scene_mesh.uv_layers.new(name=mesh.name + "_UV", do_init=False)
                color_attribute = scene_mesh.color_attributes.new(name=mesh.name + "_color", type="BYTE_COLOR", domain="CORNER")
                vert_colors = tuple(element for i in mesh.vert_color_sets for element in decode_rle(i.runs))
                
                for polygon in scene_mesh.polygons:
                    for loop_index in polygon.loop_indices:
                        vert_index = scene_mesh.loops[loop_index].vertex_index
                        
                        # there may be a better way to flip the V-axis than this tbh
                        uv_layer.data[loop_index].uv = (mesh.uv_coords[vert_index][0], 1 - mesh.uv_coords[vert_index][1])
                        if vert_index < len(vert_colors):
                            color_attribute.data[loop_index].color = (vert_colors[vert_index][0] / 255.0, vert_colors[vert_index][1] / 255.0, vert_colors[vert_index][2] / 255.0, 1.0)
                
                # change axis alignment so X is forward and Z is up (should probably change this to use a local axis in the future)
                scene_obj.matrix_world = Matrix.Rotation(math.radians(90), 4, 'X') @ Matrix.Rotation(math.radians(90), 4, 'Y') @ scene_obj.matrix_world
                bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
                
                # wrap up
                scene_mesh.uv_layers.active = uv_layer
                scene_mesh.update()
                
            # LimbNode
            elif node_data.node_type == "LimbNode":
                # todo armature stuff
                
                scene_obj = bpy.data.objects.new(node_data.name, None)
            
            # Null
            else:
                scene_obj = bpy.data.objects.new(node_data.name, None)
                
            # add to scene
            scene_obj.parent = parent_obj
            bpy.context.collection.objects.link(scene_obj)
            
            # repeat for child nodes
            for node_index in node_data.child_nodes:
                recursive_get_nodes(nkmesh.nodes[node_index], scene_obj)
            
            return
        
        # start from root nodes
        for node in nkmesh.nodes:
            if node.parent_node_index == -1:
                recursive_get_nodes(node, root_obj)
        
        return {"FINISHED"}

def menu_func(self, ctx):
    self.layout.operator(ImportNkmesh.bl_idname, text=bl_label)

def register():
    bpy.utils.register_class(ImportNkmesh)
    bpy.types.TOPBAR_MT_file_import.append(menu_func)

def unregister():
    bpy.utils.unregister_class(ImportNkmesh)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func)
    
if __name__ == "__main__":
    register()
