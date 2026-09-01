# this script was written to be reusable outside of a blender extension (in case anyone wants to make an importer/exporter in a different format)
# hence why some of the structures aren't optimized for blender's bpy library
import struct
from dataclasses import dataclass

# helper functions
# maybe there's a better way to do this in python, i don't know
def unpack_next(format: str, data) -> tuple:
    return struct.unpack(format, data.read(struct.calcsize(format)))

def unpack_next_single_int(data) -> int:
    return unpack_next("<I", data)[0]

def unpack_next_string(data) -> str:
    length = unpack_next_single_int(data)
    return unpack_next(f"{length}s", data)[0].decode("utf-8")

def unpack_next_array(format : str, data, length : int, struct_size : int = 1) -> tuple:
    return tuple(unpack_next(format, data) for _ in range(length // struct_size))

def unpack_next_rle(format: str, data, length : int, struct_size : int = 1) -> tuple:
    count = 0
    values = []

    # the length corresponds to the total number of data types in the structure, not the total number of structures
    while(count < (length // struct_size)):
        run_length = unpack_next_single_int(data)
        count += run_length
        values.append((run_length, unpack_next(format, data)))

    return tuple(values)



@dataclass
class Nkmesh:
    @classmethod
    def from_file(self, file_path: str):
        with open(file_path, "rb") as data:
            version = unpack_next_single_int(data)
            
            print(f"reading {file_path} (version: {version})")

            num_nodes = unpack_next_single_int(data)
            nodes = tuple(self.NkmeshNode.from_stream(data) for _ in range(num_nodes))
            
            num_meshes = unpack_next_single_int(data)
            meshes = tuple(self.NkmeshMesh.from_stream(data) for _ in range(num_meshes))

            # todo: figure out the stuff that sometimes appears between these
            
            #num_anims = unpack_next_single_int(data)
            #anims = tuple(self.NkmeshAnim.from_stream(data) for _ in range(num_anims))

        return self(version, nodes, meshes, None) #return self(version, nodes, meshes, anims)



    @dataclass
    class NkmeshMesh:
        @classmethod
        def from_stream(self, data):

            name = unpack_next_string(data)
            texture = unpack_next_string(data)
            unknown_4_bytes = unpack_next_single_int(data) # might be a unix timestamp?

            print(f"Found mesh |name: {name:<50}|texture name: {texture:<50}|unknown bytes: {unknown_4_bytes}")

            num_uv_coords       = unpack_next_single_int(data)
            uv_coords           = unpack_next_array("<ff", data, num_uv_coords)
            
            num_vert_color_sets = unpack_next_single_int(data)
            vert_color_sets     = tuple(self.NkmeshVertexColorSet.from_stream(data) for _ in range(num_vert_color_sets))
            num_polygons        = unpack_next_single_int(data)
            polygons            = unpack_next_array("<III", data, num_polygons // 3)
            vert_coords         = unpack_next_array("<fff", data, num_uv_coords)
            vert_normals        = unpack_next_array("<fff", data, num_uv_coords)
            unknown_flag,       = unpack_next("<B", data)

            if unknown_flag:
                num_unknown_values  = unpack_next_single_int(data)
                unknown_values      = unpack_next_rle("<ffffff", data, num_unknown_values, 6)

            return self(
                name, texture, unknown_4_bytes,
                vert_coords, vert_normals, vert_color_sets, uv_coords, polygons
            )



        # temporary, may replace with a proper NkmeshVertex class later
        @dataclass
        class NkmeshVertexColorSet:
            @classmethod
            def from_stream(self, data):
                num_colors = unpack_next_single_int(data)
                num_colors_dupe = unpack_next_single_int(data)

                return self(unpack_next_rle("<BBB", data, num_colors, 3))

            # NkmeshVertexColors members
            runs: tuple[int, tuple[int, int, int]]

        # NkmeshMesh members
        name: str
        texture: str
        unknown_4_bytes: int

        vert_coords: tuple[tuple[float, float, float]]
        vert_normals: tuple[tuple[float, float, float]]
        vert_color_sets: tuple[NkmeshVertexColorSet]
        uv_coords: tuple[tuple[float, float]]
        polygons: tuple[tuple[int, int, int]]



    @dataclass
    class NkmeshNode:
        @classmethod
        def from_stream(self, data):
            name = unpack_next_string(data)
            node_type = unpack_next_string(data)            

            parent_node_index, mesh_index, grandparent_node_index, num_child_nodes, unknown_int_always_zero = unpack_next("<iiiII", data)
            child_nodes = unpack_next(f"<{num_child_nodes}I", data)

            unknown_values = unpack_next("<41f", data)
            unknown_flag_1, unknown_flag_2, unknown_flag_3, unknown_flag_4 = unpack_next("<BBBB", data)
            offset_next_node = unpack_next_single_int(data)
            
            print(f"Found node |name: {name:<50}|type: {node_type:<50}|flags: {unknown_flag_1} {unknown_flag_2} {unknown_flag_3} {unknown_flag_4}")

            return self(
                name, node_type,
                parent_node_index, mesh_index, grandparent_node_index, child_nodes,
                unknown_values, unknown_int_always_zero, unknown_flag_1, unknown_flag_2, unknown_flag_3, unknown_flag_4,
                offset_next_node
            )

        # NkmeshNode members
        name: str
        node_type: str
        parent_node_index: int
        mesh_index: int
        grandparent_node_index: int
        child_nodes: tuple[int]
        unknown_values: tuple[float]
        unknown_int_always_zero: int
        unknown_flag_1: int
        unknown_flag_2: int
        unknown_flag_3: int
        unknown_flag_4: int
        offset_next_node: int



    @dataclass
    class NkmeshAnim:
        @classmethod
        def from_stream(self, data):
            unknown_double, = unpack_next("<d", data)
            name = unpack_next_string(data)
            index = unpack_next_single_int(data)

            print(unknown_double, name, index)

            return self(
                name, unknown_double, index
            )

        # NkmeshAnim members
        name: str
        unknown_double: float
        index: int

    # Nkmesh members
    version: int
    nodes: tuple[NkmeshNode]
    meshes: tuple[NkmeshMesh]
    anims: tuple[NkmeshAnim]
