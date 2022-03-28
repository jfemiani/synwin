# pip install fake-blender-module-2.93
import bpy
import bmesh 
import mathutils
from glob import glob
from random import choice, uniform,  gauss
import os
import math
import time
import os

def reload():
    mod = bpy.data.texts['synwin.py'].as_module()
    return mod


# Locate objects
window = bpy.data.objects['Window']
wall = bpy.data.objects['Wall']

wall: bpy.types.Object
assert isinstance(wall.data, bpy.types.Mesh)

# Locate texture map images
hdr_res = '1k'   # or 8k
hdrs_root = f'data/HDRI/{hdr_res}'
hdrs = glob(f'{hdrs_root}/*.hdr') + glob(f'{hdrs_root}/*.exf')

#  Place to set the default scale / size of a pbr texture for the wall
#  ... sveral of them seem to be at greatly different sizes
pbr_scales = {
    'BrickWall02_2K': 3,
    'OldWoodenWall02_2K': 2
}

def make_pbr_material(stem: str):
    bn = os.path.basename(stem)
    return dict(
        stem = stem, 
        bn = bn,
        path_ao = stem + '_AO.png',
        path_basecolor = stem + '_BaseColor.png',
        path_height = stem + '_Height.png',
        path_normal = stem + '_Normal.png',
        path_metalic = stem + '_Metalic.png',
        path_roughness = stem + '_Roughness.png',
        default_scale = pbr_scales.get(bn, 1.0)
    )
    
    



walls_root = 'data/PBRS/walls'
wall_pbrs = [make_pbr_material(f.rsplit('_', 1)[0]) for f in glob(f'{walls_root}/*_BaseColor.png')]


# Choose Randomized Parameters....
hdr = choice(hdrs)
hdr_rotation_z = math.radians(uniform(0, 360))
pbr = choice(wall_pbrs)


wall_uv_scale = uniform(pbr['default_scale'], 2*pbr['default_scale'])
wall_uv_loc = mathutils.Vector((uniform(0, 1), uniform(0, 1)))

print("Selected Env:", os.path.basename(hdr))

print("Selected Material:", pbr['bn'])
print("uv-scale:", wall_uv_scale)
print("uv-loc:", wall_uv_loc)


# make sure we are using cycles
bpy.context.scene.render.engine = 'CYCLES'



# Set the HDR
#  => Assumes that the nodes already exist.....
world = bpy.context.scene.world
environment_node = world.node_tree.nodes['Environment Texture']
mapping_node = world.node_tree.nodes['Mapping']

environment_node.image  = bpy.data.images.load(hdr)
mapping_node.inputs['Rotation'].default_value[2] = hdr_rotation_z


# UV-Map the wall

wall.select_set(True)
bpy.ops.uv.lightmap_pack()
# Randomize the mapping a bit
for loop in wall.data.loops:
    pt = wall.data.uv_layers.active.data[loop.index]
    pt.uv = (pt.uv + wall_uv_loc)*wall_uv_scale
        
# Subdivide the wall
wall.select_set(True)
bpy.context.view_layer.objects.active = wall
subd = wall.modifiers.get('Subdivision')
if subd is None: 
    subd = wall.modifiers.new(name='Subdivision', type='SUBSURF')
    
bpy.ops.object.modifier_move_to_index(modifier=subd.name, index=0)
subd.subdivision_type = 'SIMPLE'
subd.levels=8
subd.render_levels=8




# 2.  Set the material textures
wall2_outside =  bpy.data.materials['Wall2_outside']
node_tree = wall2_outside.node_tree
nodes = node_tree.nodes

# Remove all nodes except output
nodes.clear()
output = nodes.new('ShaderNodeOutputMaterial')


# Create the PBR Node
principled_brdf = nodes.new('ShaderNodeBsdfPrincipled')
node_tree.links.new(principled_brdf.outputs['BSDF'], output.inputs['Surface'])



# Create the Albedo and AO
albedo_node = nodes.new('ShaderNodeTexImage')
albedo_node.image = bpy.data.images.load(pbr['path_basecolor'])
albedo_node.name = 'Albedo'
node_tree.links.new(albedo_node.outputs['Color'], principled_brdf.inputs['Base Color'])


# No Need for AO -- Cycles computes this just fine

# Create the metalic, if it exists

if os.path.isfile(bpy.path.abspath(pbr['path_metalic'])):
    metalic_node = nodes.new('ShaderNodeTexImage')
    metalic_node.image = bpy.data.images.load(pbr['path_metalic'])
    matalic_node.name = 'Metalic'
    metalic_node.image.colorspace_settings.name = 'Non-Color'
    node_tree.links.new(matalic_node.outputs['Color'], principled_brdf.inputs['Metalic'])
else:
    metalic_node = None    


# Create the Roughness
roughness_node = nodes.new('ShaderNodeTexImage')
roughness_node.image = bpy.data.images.load(pbr['path_roughness'])
roughness_node.name = 'Roughness'
roughness_node.image.colorspace_settings.name = 'Non-Color'
node_tree.links.new(roughness_node.outputs['Color'], principled_brdf.inputs['Roughness'])


# Create the Normals
normals_node = nodes.new('ShaderNodeTexImage')
normals_node.image = bpy.data.images.load(pbr['path_normal'])
normals_node.name = 'Normals'
normals_node.image.colorspace_settings.name = 'Non-Color'

# =>  We need to invert the G channel
invert_green = nodes.new('ShaderNodeRGBCurve')
invert_green.name = 'Invert Green'
invert_green.mapping.curves[1].points[0].location.y = 1
invert_green.mapping.curves[1].points[1].location.y = 0
invert_green.mapping.update()

# => And we need to use a Normal Mapping Node
normal_map = nodes.new('ShaderNodeNormalMap')

node_tree.links.new(normals_node.outputs['Color'], invert_green.inputs['Color'])
node_tree.links.new(invert_green.outputs['Color'], normal_map.inputs['Color'])
node_tree.links.new(normal_map.outputs['Normal'], principled_brdf.inputs['Normal'])

use_displacement = False
if use_displacement:
    #  Add displacement -- I was hoping this would not be needed but I think it looks fake without it
    height_node = nodes.new('ShaderNodeTexImage')
    height_node.image = bpy.data.images.load(pbr['path_height'])
    height_node.name = 'Height'
    height_node.image.colorspace_settings.name = 'Non-Color'

    displace_node  = nodes.new('ShaderNodeDisplacement')
    # Maybe randomized the midlevel and scale???
    displace_node.inputs['Midlevel'].default_value = 0.5
    displace_node.inputs['Scale'].default_value = 1
    

    node_tree.links.new(height_node.outputs['Color'], displace_node.inputs['Height'])
    node_tree.links.new(displace_node.outputs['Displacement'], output.inputs['Displacement'])
    
    
def make_window():
    window.select_set(True)
    win = window.data.archipack_window[0]
    
    
    # Width
    win.x = uniform(0.5, 2) # Default: 1.2

    # Depth
    win.y = 0.2  # Must match the wall --> Not really visible

    # Height
    win.z = uniform(0.5, 2) # Default: 1.1

    # Altitude
    win.altitude = uniform(0.5, 1.4) #  1.0

    # Offset
    win.offset = uniform(-0.09, 0.2) #  0.1
    
    # Shape
    shapes = ['RECTANGLE', 'ROUND', 'ELLIPSIS', 'QUADRI', 'CIRCLE']
    win.window_shape =choice(shapes) # 'RECTANGLE'
    
    # Glass
    win.enable_glass = True
    
    # Frame Width
    win.frame_x = gauss(0.06, 0.03) #0.06
    
    # Frame Depth
    win.frame_y =  gauss(0.06, 0.03) # 0.06
    
    
    # Handles (generally inside...)
    win.handle_enable = False
    win.handle_altitude = 1.4

    # Show an outer window frame (molding)
    win.out_frame = uniform(0, 100) < 80 # True 
    
    # Front Width
    win.out_frame_x = 0.04

    # Front Depth
    win.out_frame_y = 0.02
    
    # Side Depth
    win.out_frame_y2 = 0.02
    
    # ???
    win.out_frame_offset = 0
    

    # Outside Tablet (sill)
    win.out_tablet_enable
    
    # Width
    win.out_tablet_x 
    
    # Depth
    win.out_tablet_y
    
    # Height
    win.out_tablet_z
    
    # Inside Tablet (sill)
    win.in_tablet_enable
    
    # Width
    win.in_tablet_x   
    
    # Depth 
    win.in_tablet_y
    
    # Height
    win.in_tablet_z
    
    # Blind 
    win.blind_enable = uniform(0, 100) > 50
    
    # Percent Blind Open (0.0 = closed, 100.0 = Open)
    win.blind_open = uniform(0, 100)
    
    # Depth (Of Folds)
    win.blind_y = 0.002
    
    # Height (of Folds)
    win.blind_z  = 0.03
    
    # Number of rows of panels
    win.n_rows
    
    
    #### Per Row ####
    
    # Height of the panel (Row Heights must sum to height)
    #    \-->  that is  win.archipack_window[0].z 
    win.rows[0].height
    
    # Number of Panels on the row
    win.rows[0].cols
    
    # Width of the column/panel (up to 32 of them)
    #    \--> Must sum to .x  (Width) of the whole window
    win.rows[0].width[0]
    
    # Whether the panel is fixed (cannot be opened)
    win.rows[0].fixed[0]
    
    return win
    
    
    
materials = bpy.data.materials
for i, m in enumerate(materials, start=1):
    m.pass_index = i
    

outdir = 'data/generated'
basename = time.strftime("%Y%m%d-%H%M%S")

os.makedirs(outdir, exist_ok=True)


bpy.data.scenes["Scene"].node_tree.nodes["depth-output"].base_path = os.path.join(outdir, basename + '-depth')
bpy.data.scenes["Scene"].node_tree.nodes["normals-output"].base_path= os.path.join(outdir, basename + '-normals')
bpy.data.scenes["Scene"].node_tree.nodes["uv-output"].base_path= os.path.join(outdir, basename + '-uv')
bpy.data.scenes["Scene"].node_tree.nodes["material-index-output"].base_path= os.path.join(outdir, basename + '-matindex')

def render_frame():
    path = os.path.join(outdir, basename + '.jpg')
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def random_window():
    make_window()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(outdir, basename + '.blend'))
    render_frame()
    
    
random_window()