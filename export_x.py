# ##### BEGIN ZLIB LICENSE BLOCK #####

# Copyright (c) <2026> <Dodgee Software> <svenvvv>

# This software is provided 'as-is', without any express or implied
# warranty. In no event will the authors be held liable for any damages
# arising from the use of this software.
#
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely, subject to the following restrictions:
#
# 1.  The origin of this software must not be misrepresented; you must not
#     claim that you wrote the original software. If you use this software
#     in a product, an acknowledgment in the product documentation would be
#     appreciated but is not required.
# 2.  Altered source versions must be plainly marked as such, and must not be
#     misrepresented as being the original software.
# 3.  This notice may not be removed or altered from any source distribution.

# ##### END ZLIB LICENSE BLOCK #####

# NOTE: Plugins need to through a pep8 checker. The following line
# sets the formatting requirements for this python file.
# <pep8 compliant>

import math
import mathutils
import bpy

# TODO: Support for vertex colours via mesh.vertex_colors
# TODO: Do I need to figure out how to do parented meshes (nested transforms)

DEFAULT_MATERIAL_NAME = "DefaultMat"


class XMeshObject:
    def __init__(self, fd: file, tag: str, parent: XMeshObject = None):
        self._fd = fd
        self._tag = tag
        if parent:
            self._indent = parent._indent
        else:
            self._indent = 0

    def __enter__(self):
        self.writeln(self._tag)
        self.writeln("{")
        self._indent += 1
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self._indent -= 1
        self.writeln("}")

    def writeln(self, line: str):
        indent_str = "  " * self._indent
        self._fd.write(f"{indent_str}{line}\n")

    def write(self, text: str):
        self._fd.write(text)

    def writeList(self, *args, terminator=";"):
        formatted_args = []
        for arg in args:
            if type(arg) is float:
                formatted_args.append(str("%.6f" % arg))
            else:
                formatted_args.append(str(arg))
        line = ";".join(formatted_args) + ";"
        line += terminator
        self.writeln(line)


def SanitizeMeshName(name: str):
    return name.replace(".", "")


def WriteMaterials(f: file, mesh):
    mesh_materials = mesh.materials[:]
    for material in mesh_materials:
        if material is None:
            continue
        with XMeshObject(f, f"Material {material.name}") as obj_mat:
            if material.use_nodes == False:
                print(
                    f"Material {material.name} doesn't use nodes. Doing best to export properties anyway."
                )
                # Write Diffuse Colour
                obj_mat.writeList(
                    material.diffuse_color[0],
                    material.diffuse_color[1],
                    material.diffuse_color[2],
                    material.diffuse_color[3],
                )
                # Write specular cooeffiencnt
                obj_mat.writeList(material.specular_intensity)
                # Non-node materials in Blender have no specular colour write a default one here (white)
                obj_mat.writeList(1.0, 1.0, 1.0)
                # Non-node materials in Blender have no emissive colour write a default one here (black)
                obj_mat.writeList(0.0, 0.0, 0.0)
            else:
                print(
                    "Exporter deliberately and only supports the Specular Material Node in the Shader Graph "
                )
                faceColor = [1.0, 1.0, 1.0, 1.0]
                power = 200.0
                specularColor = [1.0, 1.0, 1.0, 1.0]
                emissiveColor = [0.0, 0.0, 0.0, 1.0]
                tex_filename = None
                for node in material.node_tree.nodes:
                    if node.type == "SCRIPT":
                        # GRAB THE FACE COLOR
                        colorSocket = node.inputs[0]
                        faceColor[0] = colorSocket.default_value[0]
                        faceColor[1] = colorSocket.default_value[1]
                        faceColor[2] = colorSocket.default_value[2]
                        faceColor[3] = colorSocket.default_value[3]
                        # GRAB THE SPECULAR POWER
                        floatSocket = node.inputs[1]
                        # Convert the Roughness into specular cooefficient
                        power = floatSocket.default_value
                        # Specular power must be greater than 1
                        if power < 1.0:
                            power = 1.0
                        if power > 800.0:
                            power = 800.0
                        # GRAB THE SPECULAR COLOR
                        colorSocket = node.inputs[2]
                        specularColor[0] = colorSocket.default_value[0]
                        specularColor[1] = colorSocket.default_value[1]
                        specularColor[2] = colorSocket.default_value[2]
                        specularColor[3] = colorSocket.default_value[3]
                        # GRAB THE EMISSIVE COLOR
                        colorSocket = node.inputs[3]
                        emissiveColor[0] = colorSocket.default_value[0]
                        emissiveColor[1] = colorSocket.default_value[1]
                        emissiveColor[2] = colorSocket.default_value[2]
                        emissiveColor[3] = colorSocket.default_value[3]
                    if node.type == "EEVEE_SPECULAR":
                        # Grab Diffuse colour
                        colorSocket = node.inputs[0]
                        faceColor[0] = colorSocket.default_value[0]
                        faceColor[1] = colorSocket.default_value[1]
                        faceColor[2] = colorSocket.default_value[2]
                        faceColor[3] = colorSocket.default_value[3]
                        colorSocket = node.inputs[1]
                        # Grab Specular colour
                        specularColor[0] = colorSocket.default_value[0]
                        specularColor[1] = colorSocket.default_value[1]
                        specularColor[2] = colorSocket.default_value[2]
                        specularColor[3] = colorSocket.default_value[3]
                        floatSocket = node.inputs[2]
                        # Convert the Roughness into specular cooefficient
                        power = (1.0 - floatSocket.default_value) * 800.0
                        # Specular power must be greater than 1
                        if power < 1.0:
                            power = 1.0
                        if power > 800.0:
                            power = 800.0
                        colorSocket = node.inputs[3]
                        # Grab Emissive colour
                        emissiveColor[0] = colorSocket.default_value[0]
                        emissiveColor[1] = colorSocket.default_value[1]
                        emissiveColor[2] = colorSocket.default_value[2]
                        emissiveColor[3] = colorSocket.default_value[3]
                    # If there is a texture grab the filenameandpath
                    if node.type == "TEX_IMAGE":
                        if node.outputs[0].is_linked == True and node.image != None:
                            image = node.image
                            path = image.filepath
                            name = image.name
                            if path != None and len(path) > 0:
                                tex_filename = ExtractFilenameFromPath(path)
                            elif name != None and len(name) > 0:
                                tex_filename = name

                # Write the Diffuse Colour
                obj_mat.writeList(
                    faceColor[0], faceColor[1], faceColor[2], faceColor[3]
                )
                # Write the Specular Cooefficient
                obj_mat.writeList(power, terminator="")
                # Write the Specular Colour
                obj_mat.writeList(specularColor[0], specularColor[1], specularColor[2])
                # Write the Emissive Colour
                obj_mat.writeList(emissiveColor[0], emissiveColor[1], emissiveColor[2])
            # If there is a texture write the TexutreFilename node to the file
            if tex_filename:
                with XMeshObject(f, "TextureFilename", obj_mat) as obj_texname:
                    obj_texname.writeln(f'"{tex_filename}";')

    # If there are no materials then use a default one the file format must define at least one material being material 0
    if len(mesh_materials) == 0:
        # TODO: Cannot have spaces investigate valid names
        with XMeshObject(f, f"Material {DEFAULT_MATERIAL_NAME}") as obj_mat:
            # Write the Diffuse Colour
            obj_mat.writeList(1.0, 1.0, 1.0, 1.0)
            # Write the Specular Cooefficient
            obj_mat.writeList(2.0, terminator="")
            # Write the Specular Colour
            obj_mat.writeList(1.0, 1.0, 1.0)
            # Write the Emissive Colour
            obj_mat.writeList(0.0, 0.0, 0.0)


def ExportFile(
    filepath,
    apply_transforms=True,
    inline_materials=False,
    write_templates=False,
    write_frame=False,
    only_selected=True
):
    bpy.ops.object.mode_set(mode="OBJECT")

    print("Exporting File: " + filepath)
    f = open(filepath, "w", encoding="utf8", newline="\n")

    WriteHeader(f)
    f.write("\n")

    if write_templates:
        WriteTemplates(f)

    if only_selected:
        export_objects = bpy.context.selected_objects
    else:
        export_objects = bpy.data.objects

    # Go through all the objects in the scene
    for object in export_objects:
        if object.type != "MESH":
            continue
        mesh = object.data

        if not inline_materials:
            WriteMaterials(f, mesh)
            f.write("\n")

        if write_frame and not apply_transforms:
            f.write("# " + object.name + "\n")
            f.write("Frame\n")
            f.write("{\n")

            f.write("FrameTransformMatrix\n")
            f.write("{\n")
            # TODO: Try and replace this with a reusable function
            translationMatrix = mathutils.Matrix.Translation(
                (object.location[0], object.location[2], object.location[1])
            )
            # Rotation about the X Axis Matrix
            # rotationXMatrix = mathutils.Matrix.Rotation((object.rotation_euler[0]), 4, 'X')
            rotationXMatrix = mathutils.Matrix.Identity(4)
            rotationXMatrix[1][1] = math.cos(-object.rotation_euler[0])
            rotationXMatrix[1][2] = -math.sin(-object.rotation_euler[0])
            rotationXMatrix[2][1] = math.sin(-object.rotation_euler[0])
            rotationXMatrix[2][2] = math.cos(-object.rotation_euler[0])
            # Rotation about the Y Axis Matrix
            # rotationYMatrix = mathutils.Matrix.Rotation((object.rotation_euler[2]), 4, 'Y')
            rotationYMatrix = mathutils.Matrix.Identity(4)
            rotationYMatrix[0][0] = math.cos(-object.rotation_euler[2])
            rotationYMatrix[0][2] = math.sin(-object.rotation_euler[2])
            rotationYMatrix[2][0] = -math.sin(-object.rotation_euler[2])
            rotationYMatrix[2][2] = math.cos(-object.rotation_euler[2])
            # Rotation about the Z Axis Matrix
            # rotationZMatrix = mathutils.Matrix.Rotation((object.rotation_euler[1]), 4, 'Z')
            rotationZMatrix = mathutils.Matrix.Identity(4)
            rotationZMatrix[0][0] = math.cos(-object.rotation_euler[1])
            rotationZMatrix[0][1] = -math.sin(-object.rotation_euler[1])
            rotationZMatrix[1][0] = math.sin(-object.rotation_euler[1])
            rotationZMatrix[1][1] = math.cos(-object.rotation_euler[1])
            # Scale Matrix
            scaleXMatrix = mathutils.Matrix.Scale(object.scale[0], 4, (1.0, 0.0, 0.0))
            scaleYMatrix = mathutils.Matrix.Scale(object.scale[2], 4, (0.0, 1.0, 0.0))
            scaleZMatrix = mathutils.Matrix.Scale(object.scale[1], 4, (0.0, 0.0, 1.0))
            # Compute the final Model transformation matrix
            finalMatrix = mathutils.Matrix(
                translationMatrix
                @ rotationYMatrix
                @ rotationZMatrix
                @ rotationXMatrix
                @ scaleYMatrix
                @ scaleZMatrix
                @ scaleXMatrix
            )
            # Compute the matrix to transform the normals
            normalMatrix = mathutils.Matrix(
                rotationYMatrix @ rotationZMatrix @ rotationXMatrix
            )
            # The DirectX format stores  matrices
            # in row major format so we transpose the
            # matrix here before writing
            finalMatrix.transpose()
            # Write the Matrix
            for j in range(0, 4):
                for i in range(0, 4):
                    f.write(str("%.6f" % finalMatrix[j][i]))
                    if j == 3 and i == 3:
                        f.write(";;")
                    else:
                        f.write(",")
                f.write("\n")
            f.write("}\n")

        if apply_transforms:
            world_matrix = object.matrix_world
            world_normal_matrix = world_matrix.to_3x3().inverted_safe().transposed()

        with XMeshObject(f, f"Mesh {SanitizeMeshName(mesh.name)}") as obj_mesh:
            mesh_verts = mesh.vertices[:]
            mesh_polygons = mesh.polygons[:]

            vertexCount = 0
            for polygon in mesh_polygons:
                for vertex in polygon.vertices:
                    vertexCount = vertexCount + 1

            obj_mesh.writeln(str(vertexCount) + ";")

            subscriptOffset = 0
            for polygon in mesh_polygons:
                for i in range(len(polygon.vertices)):
                    vertex = mesh_verts[polygon.vertices[i]]

                    if apply_transforms:
                        co = world_matrix @ vertex.co
                    else:
                        co = vertex.co

                    terminator = "," 
                    if polygon == mesh_polygons[-1] and i == (len(polygon.vertices) - 1):
                        terminator = ";"

                    # Here I swap the Y and Z Axis
                    obj_mesh.writeList(co[0], co[2], co[1], terminator=terminator)

                # Increment our subscripts
                subscriptOffset += len(polygon.vertices)
            obj_mesh.writeln("")

            # WRITE POLYGON INDICES
            obj_mesh.writeln(str(len(mesh_polygons)) + ";")

            subscriptOffset = 0
            for polygon in mesh_polygons:
                line = str(len(polygon.vertices)) + ";"
                for index in range(0, len(polygon.vertices)):
                    indice = subscriptOffset + (len(polygon.vertices) - 1) - index
                    line += str(indice)
                    if index < len(polygon.vertices) - 1:
                        line += ","
                line += ";;" if polygon == mesh_polygons[-1] else ";,"
                obj_mesh.writeln(line)
                subscriptOffset = subscriptOffset + len(polygon.vertices)
            obj_mesh.writeln("")

            # WRITE NORMALS FOR THE MESH
            # TODO: Need to figure out how to provide support for per face vertex normals.
            # there must be away to create them in blender then detect them in script
            # and save them here when they exist. At the moment all polygons in a mesh
            # are hard edges and this is wrong
            # NOTE: We do NOT need to transform the normals.
            # It seems that the frametransform is applied automatically
            # to the normals
            with XMeshObject(f, "MeshNormals", obj_mesh) as obj_normals:
                # Write the Number of normals
                obj_normals.writeln(str(vertexCount) + ";")
                for polygon in mesh_polygons:
                    for vertex in polygon.vertices:
                        normal = polygon.normal
                        if apply_transforms:
                            normal = (world_normal_matrix @ normal).normalized()

                        terminator = ","
                        if polygon == mesh_polygons[-1] and vertex == polygon.vertices[-1]:
                                terminator = ";"

                        obj_normals.writeList(normal.x, normal.z, normal.y, terminator=terminator)

                # WRITE THE POLYGONS (face normals)
                # Write the Number of Polygons
                obj_normals.writeln(str(len(mesh_polygons)) + ";")
                # Write the Polygons
                subscriptOffset = 0
                for polygon in mesh_polygons:
                    line = str(len(polygon.vertices)) + ";"
                    for index in range(0, len(polygon.vertices)):
                        indice = subscriptOffset + (len(polygon.vertices) - 1) - index
                        line += str(indice)
                        if index < len(polygon.vertices) - 1:
                            line += ","
                    line += ";;" if polygon == mesh_polygons[-1] else ";,"
                    obj_normals.writeln(line)
                    subscriptOffset = subscriptOffset + len(polygon.vertices)

            # WRITE UVS (IF ANY)
            # Do we have uv data?
            if len(mesh.uv_layers) > 0:
                # NOTE: There can only be one active UVMap per mesh. This
                # is set by the user in the interface.
                uvs = mesh.uv_layers.active.data[:]
                # Write the Name of the UVMap
                obj_mesh.writeln("# " + str(mesh.uv_layers.active.name))
                with XMeshObject(f, "MeshTextureCoords", obj_mesh) as obj_uvs:
                    # Write the UV coords for faces
                    obj_uvs.writeln(str(len(mesh.uv_layers.active.data[:])) + ";")
                    # Write the UVs for each face
                    subscriptOffset = 0
                    for polygon in mesh_polygons:
                        for index in range(0, len(polygon.vertices)):
                            indice = subscriptOffset + index
                            u, v = mesh.uv_layers.active.data[indice].uv
                            
                            terminator=","
                            if polygon == mesh_polygons[-1] and index == len(polygon.vertices) - 1:
                                terminator=";"

                            obj_uvs.writeList(u, (1.0 - v), terminator=terminator)
                        subscriptOffset = subscriptOffset + len(polygon.vertices)

            # WRITE MATERIALS LIST
            # Grab the Materials used by this mesh
            mesh_materials = mesh.materials[:]
            # Write the MeshMaterial List
            with XMeshObject(f, "MeshMaterialList", obj_mesh) as obj_matlist:
                # Write the number of materials used by this mesh
                obj_matlist.writeln(str(len(mesh_materials)) + ";")
                obj_matlist.writeln(str(len(mesh_polygons)) + ";")
                line = ""
                for index in range(0, len(mesh_polygons), 1):
                    line += str(mesh_polygons[index].material_index)
                    if index < len(mesh_polygons) - 1:
                        line += ","
                obj_matlist.writeln(line + ";")

                if inline_materials:
                    WriteMaterials(f, mesh)
                else:
                    material_names = [material.name for material in mesh_materials]
                    if len(material_names) == 0:
                        material_names = [DEFAULT_MATERIAL_NAME]
                    obj_matlist.writeln("{ " + ",".join(material_names) + " }")

            # if there is an armature modifier then write
            # skeletal data to the file
            if object.modifiers.find("Armature") is not -1:
                # Grab the Armature object from the armature modifier
                armature = object.modifiers["Armature"].object.data
                boneCount = len(armature.bones.items())
                # Write the XSkinMeshHeader to file
                with XMeshObject(f, "XSkinMeshHeader", obj_mesh) as obj_skinheader:
                    obj_skinheader.writeln(str(boneCount) + "; #nMaxSkinWeightsPerVertex")
                    obj_skinheader.writeln(str(boneCount) + "; #nMaxSkinWeightsPerFace")
                    obj_skinheader.writeln(str(boneCount) + "; #nBones")

                for vertexGroup in object.vertex_groups:
                    with XMeshObject(f, "SkinWeights", obj_mesh) as obj_skin:
                        # WARNING: VertexGroup name isn't the same as Bone Name its the name in the heirachy which can be changed
                        # the name of the vertex group should never be different from the joint name
                        obj_skin.writeln('"' + vertexGroup.name + '"; # name of the bone')
                        # Count the verts in this skin
                        vertSkinCount = 0
                        # Go through each polygon in the Mesh
                        for polygon in mesh_polygons:
                            # Go through all the vertices in the polygon
                            for i in range(len(polygon.vertices)):
                                try:
                                    vertexGroup.weight(polygon.vertices[i])
                                    vertSkinCount += 1
                                except RuntimeError:
                                    # vertex is not in the group
                                    pass
                        # Write the number of vertices in the skin
                        obj_skin.writeln(str(vertSkinCount) + "; #verts in this skin")

                        # Create a dictionary for the weights
                        skinIndices = list()
                        skinWeights = list()
                        # Go through each polygon in the Mesh
                        for polygon in mesh_polygons:
                            # Go through all the vertices in the polygon
                            for i in range(len(polygon.vertices)):
                                try:
                                    skinWeights.append(
                                        vertexGroup.weight(polygon.vertices[i])
                                    )
                                    skinIndices.append(polygon.vertices[i])
                                except RuntimeError:
                                    # vertex is not in the group
                                    pass

                        obj_skin.writeln("# list of indices")
                        line = ""
                        for i in range(len(skinIndices)):
                            line += str(skinIndices[i])
                            if i < len(skinIndices) - 1:
                                line += ","
                        obj_skin.writeln(line + ";")

                        obj_skin.writeln("# list of weights")
                        line = ""
                        for i in range(len(skinWeights)):
                            line += str("%.6f" % skinWeights[i])
                            if i < len(skinWeights) - 1:
                                line += ","
                        obj_skin.writeln(line + ";")

                        obj_skin.writeln("# offset matrix")
                        # From official Documentation:
                        # The matrix matrixOffset transforms the mesh vertices to the space of the bone.
                        # When concatenated to the bone's transform, this provides the world space coordinates of the mesh as affected by the bone
                        bone = armature.bones[vertexGroup.name]

                        boneMatrix = bone.matrix_local
                        boneMatrix = boneMatrix.inverted()
                        boneMatrix = (
                            object.modifiers["Armature"].object.matrix_world.inverted()
                            @ boneMatrix
                        )
                        boneMatrix = object.matrix_world @ boneMatrix

                        # Grab bone location rotation and scale
                        boneLocation = [
                            boneMatrix[0][3],
                            boneMatrix[1][3],
                            boneMatrix[2][3],
                        ]
                        myQuaternion = boneMatrix.to_quaternion()
                        myEuler = myQuaternion.to_euler()
                        boneRotation = [myEuler[0], myEuler[1], myEuler[2]]
                        boneScale = [boneMatrix[0][0], boneMatrix[1][2], boneMatrix[2][1]]
                        # Create translation Matrix
                        tMatrix = mathutils.Matrix.Translation(
                            (boneLocation[0], boneLocation[2], boneLocation[1])
                        )
                        # Rotation about the X Axis Matrix
                        rXMatrix = mathutils.Matrix.Identity(4)
                        rXMatrix[1][1] = math.cos(-boneRotation[0])
                        rXMatrix[1][2] = -math.sin(-boneRotation[0])
                        rXMatrix[2][1] = math.sin(-boneRotation[0])
                        rXMatrix[2][2] = math.cos(-boneRotation[0])
                        # Rotation about the Y Axis Matrix
                        rYMatrix = mathutils.Matrix.Identity(4)
                        rYMatrix[0][0] = math.cos(-boneRotation[2])
                        rYMatrix[0][2] = math.sin(-boneRotation[2])
                        rYMatrix[2][0] = -math.sin(-boneRotation[2])
                        rYMatrix[2][2] = math.cos(-boneRotation[2])
                        # Rotation about the Z Axis Matrix
                        rZMatrix = mathutils.Matrix.Identity(4)
                        rZMatrix[0][0] = math.cos(-boneRotation[1])
                        rZMatrix[0][1] = -math.sin(-boneRotation[1])
                        rZMatrix[1][0] = math.sin(-boneRotation[1])
                        rZMatrix[1][1] = math.cos(-boneRotation[1])
                        # Create the Scale Matrices
                        sXMatrix = mathutils.Matrix.Scale(boneScale[0], 4, (1.0, 0.0, 0.0))
                        sYMatrix = mathutils.Matrix.Scale(boneScale[2], 4, (0.0, 1.0, 0.0))
                        sZMatrix = mathutils.Matrix.Scale(boneScale[1], 4, (0.0, 0.0, 1.0))
                        # Compute the final Model transformation matrix
                        fMatrix = mathutils.Matrix(
                            tMatrix
                            @ rYMatrix
                            @ rZMatrix
                            @ rXMatrix
                            @ sYMatrix
                            @ sZMatrix
                            @ sXMatrix
                        )
                        # Tranpose before writing
                        fMatrix.transpose()
                        # Write the matrix
                        for j in range(0, 4):
                            for i in range(0, 4):
                                obj_skin.write(str("%.6f" % fMatrix[j][i]))
                                if i == 3 and j == 3:
                                    obj_skin.write("; ")
                                else:
                                    obj_skin.write(", ")
                                if i == 3:
                                    obj_skin.write("\n")

                # Go through all bones looking for root bones
                for rootBone in armature.bones:
                    # if bone is a root bone
                    if rootBone.parent is None:
                        WriteBoneAndChildren(f, rootBone)

            if object.modifiers.find("Armature") is not -1:
                # Grab the Scene
                scene = bpy.context.scene
                # Write some interesting information into the file
                f.write(
                    "# Total Frames: " + str(scene.frame_end - scene.frame_start + 1) + "\n"
                )
                f.write("# FPS: " + str(bpy.context.scene.render.fps) + "\n")
                f.write("# FPS Base: " + str(bpy.context.scene.render.fps_base) + "\n")
                f.write("AnimationSet\n")
                f.write("{\n")
                # Cache the current frame so we can store it later
                cacheCurrentFrame = scene.frame_current
                # OLD CODE WAS (When confident remove it)
                ## Grab the Armature
                # armature = object.modifiers["Armature"].object.data
                ## Grab the Bones from the Armature
                # bones = armature.bones

                # Grab the name of the armature
                armatureName = object.modifiers["Armature"].object.name
                # Grab the armature
                armature = bpy.data.objects[armatureName]
                # Grab the Bones from the Armature
                bones = armature.pose.bones

                # Calculate frame count
                frameCount = (scene.frame_end - scene.frame_start) + 1
                # Go through the bones one by one
                for bone in bones:
                    with XMeshObject(f, "Animation", obj_mesh) as obj_anim:
                        with XMeshObject(f, "AnimationKey", obj_anim) as obj_animkey:
                            # TODO: Need to reconstruct the matrix for each frame here
                            # so that Y is up and that the rotations are correct. Since this happens
                            # a fair bit we need a function for it
                            obj_animkey.writeln("4; # keytype (4 is matrix type)")
                            obj_animkey.writeln(str(frameCount) + "; # numberofkeys")
                            # Go through the scene one frame at a time scrubbing through the timeline
                            for frame in range(scene.frame_start, scene.frame_end + 1, 1):
                                # Set the frame for the animation
                                scene.frame_set(frame)
                                # Grab bone location rotation and scale
                                boneLocation = bone.location
                                boneRotation = bone.rotation_euler
                                boneScale = bone.scale
                                tMatrix = mathutils.Matrix.Translation(
                                    (boneLocation[0], boneLocation[2], boneLocation[1])
                                )
                                # Rotation about the X Axis Matrix
                                rXMatrix = mathutils.Matrix.Identity(4)
                                rXMatrix[1][1] = math.cos(-boneRotation[0])
                                rXMatrix[1][2] = -math.sin(-boneRotation[0])
                                rXMatrix[2][1] = math.sin(-boneRotation[0])
                                rXMatrix[2][2] = math.cos(-boneRotation[0])
                                # Rotation about the Y Axis Matrix
                                rYMatrix = mathutils.Matrix.Identity(4)
                                rYMatrix[0][0] = math.cos(-boneRotation[2])
                                rYMatrix[0][2] = math.sin(-boneRotation[2])
                                rYMatrix[2][0] = -math.sin(-boneRotation[2])
                                rYMatrix[2][2] = math.cos(-boneRotation[2])
                                # Rotation about the Z Axis Matrix
                                rZMatrix = mathutils.Matrix.Identity(4)
                                rZMatrix[0][0] = math.cos(-boneRotation[1])
                                rZMatrix[0][1] = -math.sin(-boneRotation[1])
                                rZMatrix[1][0] = math.sin(-boneRotation[1])
                                rZMatrix[1][1] = math.cos(-boneRotation[1])
                                # Calculate Scale
                                sXMatrix = mathutils.Matrix.Scale(
                                    boneScale[0], 4, (1.0, 0.0, 0.0)
                                )
                                sYMatrix = mathutils.Matrix.Scale(
                                    boneScale[2], 4, (0.0, 1.0, 0.0)
                                )
                                sZMatrix = mathutils.Matrix.Scale(
                                    boneScale[1], 4, (0.0, 0.0, 1.0)
                                )
                                # Compute the final Model transformation matrix
                                boneMatrix = mathutils.Matrix(
                                    tMatrix
                                    @ rYMatrix
                                    @ rZMatrix
                                    @ rXMatrix
                                    @ sYMatrix
                                    @ sZMatrix
                                    @ sXMatrix
                                )
                                # Tranpose before writing
                                boneMatrix.transpose()
                                # Write the FrameNumber, NumberOfelementsIn4x4Matrix(16) and then the elements in the matrix
                                obj_animkey.writeln(str(frame) + ";16;")
                                # Write the bone Matrix
                                for j in range(0, 4):
                                    for i in range(0, 4):
                                        obj_animkey.write(str("%.6f" % boneMatrix[j][i]))
                                        if i == 3 and j == 3:
                                            obj_animkey.write(";;")
                                        else:
                                            obj_animkey.write(",")
                                    obj_animkey.write("\n")
                                if frame < scene.frame_end:
                                    obj_animkey.write(",\n")
                                else:
                                    obj_animkey.write(";\n")
                        obj_anim.writeln("{" + bone.name + "}")
                # Restore the current frame
                scene.frame_set(cacheCurrentFrame)
                f.write("}\n")
            f.write("\n")
        # Close the file
        f.close()
        # Complete the Export
        return {"FINISHED"}


def ExtractFilenameFromPath(filenameandpath):
    indexOfBeginingOfFilename = 0
    for index in range(len(filenameandpath)):
        i = (len(filenameandpath) - 1) - index
        if filenameandpath[i] == "\\" or filenameandpath[i] == "/":
            indexOfBeginingOfFilename = i + 1
            break
    return filenameandpath[indexOfBeginingOfFilename : len(filenameandpath) : 1]


def WriteHeader(f):
    f.write("xof 0302txt 0032\n")


def WriteTemplates(f):
    f.write("template Header\n")
    f.write("{\n")
    f.write("    <3D82AB43-62DA-11cf-AB39-0020AF71E433>\n")
    f.write("    WORD major;\n")
    f.write("    WORD minor;\n")
    f.write("    DWORD flags;\n")
    f.write("}\n\n")

    f.write("template Vector\n")
    f.write("{\n")
    f.write("    <3D82AB5E-62DA-11cf-AB39-0020AF71E433>\n")
    f.write("    FLOAT x;\n")
    f.write("    FLOAT y;\n")
    f.write("    FLOAT z;\n")
    f.write("}\n\n")

    f.write("template Coords2d\n")
    f.write("{\n")
    f.write("    <F6F23F44-7686-11cf-8F52-0040333594A3>\n")
    f.write("    FLOAT u;\n")
    f.write("    FLOAT v;\n")
    f.write("}\n\n")

    f.write("template Matrix4x4\n")
    f.write("{\n")
    f.write("    <F6F23F45-7686-11cf-8F52-0040333594A3>\n")
    f.write("    array FLOAT matrix[16];\n")
    f.write("}\n\n")

    f.write("template ColorRGBA\n")
    f.write("{\n")
    f.write("    <35FF44E0-6C7C-11cf-8F52-0040333594A3>\n")
    f.write("    FLOAT red;\n")
    f.write("    FLOAT green;\n")
    f.write("    FLOAT blue;\n")
    f.write("    FLOAT alpha;\n")
    f.write("}\n\n")

    f.write("template ColorRGB\n")
    f.write("{\n")
    f.write("    <D3E16E81-7835-11cf-8F52-0040333594A3>\n")
    f.write("    FLOAT red;\n")
    f.write("    FLOAT green;\n")
    f.write("    FLOAT blue;\n")
    f.write("}\n\n")

    f.write("template TextureFilename\n")
    f.write("{\n")
    f.write("    <A42790E1-7810-11cf-8F52-0040333594A3>\n")
    f.write("    STRING filename;\n")
    f.write("}\n\n")

    f.write("template Material\n")
    f.write("{\n")
    f.write("    <3D82AB4D-62DA-11cf-AB39-0020AF71E433>\n")
    f.write("    ColorRGBA faceColor;\n")
    f.write("    FLOAT power;\n")
    f.write("    ColorRGB specularColor;\n")
    f.write("    ColorRGB emissiveColor;\n")
    f.write("    [...]\n")
    f.write("}\n\n")

    f.write("template MeshFace\n")
    f.write("{\n")
    f.write("    <3D82AB5F-62DA-11cf-AB39-0020AF71E433>\n")
    f.write("    DWORD nFaceVertexIndices;\n")
    f.write("    array DWORD faceVertexIndices[nFaceVertexIndices];\n")
    f.write("}\n\n")

    f.write("template MeshTextureCoords\n")
    f.write("{\n")
    f.write("    <F6F23F40-7686-11cf-8F52-0040333594A3>\n")
    f.write("    DWORD nTextureCoords;\n")
    f.write("    array Coords2d textureCoords[nTextureCoords];\n")
    f.write("}\n\n")

    f.write("template MeshMaterialList\n")
    f.write("{\n")
    f.write("    <F6F23F42-7686-11cf-8F52-0040333594A3>\n")
    f.write("    DWORD nMaterials;\n")
    f.write("    DWORD nFaceIndexes;\n")
    f.write("    array DWORD faceIndexes[nFaceIndexes];\n")
    f.write("    [Material]\n")
    f.write("}\n\n")

    f.write("template MeshNormals\n")
    f.write("{\n")
    f.write("    <F6F23F43-7686-11cf-8F52-0040333594A3>\n")
    f.write("    DWORD nNormals;\n")
    f.write("    array Vector normals[nNormals];\n")
    f.write("    DWORD nFaceNormals;\n")
    f.write("    array MeshFace faceNormals[nFaceNormals];\n")
    f.write("}\n\n")

    f.write("template Mesh\n")
    f.write("{\n")
    f.write("    <3D82AB44-62DA-11cf-AB39-0020AF71E433>\n")
    f.write("    DWORD nVertices;\n")
    f.write("    array Vector vertices[nVertices];\n")
    f.write("    DWORD nFaces;\n")
    f.write("    array MeshFace faces[nFaces];\n")
    f.write("    [...]\n")
    f.write("}\n\n")

    f.write("template FrameTransformMatrix\n")
    f.write("{\n")
    f.write("    <F6F23F41-7686-11cf-8F52-0040333594A3>\n")
    f.write("    Matrix4x4 frameMatrix;\n")
    f.write("}\n\n")

    f.write("template Frame\n")
    f.write("{\n")
    f.write("    <3D82AB46-62DA-11cf-AB39-0020AF71E433>\n")
    f.write("    [...]\n")
    f.write("}\n\n")

    f.write("template FloatKeys\n")
    f.write("{\n")
    f.write("    <10DD46A9-775B-11cf-8F52-0040333594A3>\n")
    f.write("    DWORD nValues;\n")
    f.write("    array FLOAT values[nValues];\n")
    f.write("}\n\n")

    f.write("template TimedFloatKeys\n")
    f.write("{\n")
    f.write("    <F406B180-7B3B-11cf-8F52-0040333594A3>\n")
    f.write("    DWORD time;\n")
    f.write("    FloatKeys tfkeys;\n")
    f.write("}\n\n")

    f.write("template AnimationKey\n")
    f.write("{\n")
    f.write("    <10DD46A8-775B-11cf-8F52-0040333594A3>\n")
    f.write("    DWORD keyType;\n")
    f.write("    DWORD nKeys;\n")
    f.write("    array TimedFloatKeys keys[nKeys];\n")
    f.write("}\n\n")

    f.write("template AnimationOptions\n")
    f.write("{\n")
    f.write("    <E2BF56C0-840F-11cf-8F52-0040333594A3>\n")
    f.write("    DWORD openclosed;\n")
    f.write("    DWORD positionquality;\n")
    f.write("}\n\n")

    f.write("template Animation\n")
    f.write("{\n")
    f.write("    <3D82AB4F-62DA-11cf-AB39-0020AF71E433>\n")
    f.write("    [...]\n")
    f.write("}\n\n")

    f.write("template AnimationSet\n")
    f.write("{\n")
    f.write("    <3D82AB50-62DA-11cf-AB39-0020AF71E433>\n")
    f.write("    [Animation]\n")
    f.write("}\n\n")

    f.write("template XSkinMeshHeader\n")
    f.write("{\n")
    f.write("    <3cf169ce-ff7c-44ab-93c0-f78f62d172e2>\n")
    f.write("    WORD nMaxSkinWeightsPerVertex;\n")
    f.write("    WORD nMaxSkinWeightsPerFace;\n")
    f.write("    WORD nBones;\n")
    f.write("}\n\n")

    f.write("template VertexDuplicationIndices\n")
    f.write("{\n")
    f.write("    <b8d65549-d7c9-4995-89cf-53a9a8b031e3>\n")
    f.write("    DWORD nIndices;\n")
    f.write("    DWORD nOriginalVertices;\n")
    f.write("    array DWORD indices[nIndices];\n")
    f.write("}\n\n")

    f.write("template SkinWeights\n")
    f.write("{\n")
    f.write("    <6f0d123b-bad2-4167-a0d0-80224f25fabb>\n")
    f.write("    STRING transformNodeName;\n")
    f.write("    DWORD nWeights;\n")
    f.write("    array DWORD vertexIndices[nWeights];\n")
    f.write("    array FLOAT weights[nWeights];\n")
    f.write("    Matrix4x4 matrixOffset;\n")
    f.write("}\n\n")


def WriteBoneAndChildren(f, bone):
    # write its frame node
    f.write("Frame " + bone.name + "\n")
    f.write("{\n")
    # write its transform
    f.write("FrameTransformMatrix\n")
    f.write("{\n")
    # Grab the Bone Matrix relative to its parent
    boneMatrix = bone.matrix_local
    # Grab bone location rotation and scale
    boneLocation = [boneMatrix[0][3], boneMatrix[1][3], boneMatrix[2][3]]
    myQuaternion = boneMatrix.to_quaternion()
    myEuler = myQuaternion.to_euler()
    boneRotation = [myEuler[0], myEuler[1], myEuler[2]]  # [ 0.0, 0.0, 0.0 ]
    boneScale = [boneMatrix[0][0], boneMatrix[1][2], boneMatrix[2][1]]
    # Create translation Matrix
    tMatrix = mathutils.Matrix.Translation(
        (boneLocation[0], boneLocation[2], boneLocation[1])
    )
    # Rotation about the X Axis Matrix
    rXMatrix = mathutils.Matrix.Identity(4)
    rXMatrix[1][1] = math.cos(-boneRotation[0])
    rXMatrix[1][2] = -math.sin(-boneRotation[0])
    rXMatrix[2][1] = math.sin(-boneRotation[0])
    rXMatrix[2][2] = math.cos(-boneRotation[0])
    # Rotation about the Y Axis Matrix
    rYMatrix = mathutils.Matrix.Identity(4)
    rYMatrix[0][0] = math.cos(-boneRotation[2])
    rYMatrix[0][2] = math.sin(-boneRotation[2])
    rYMatrix[2][0] = -math.sin(-boneRotation[2])
    rYMatrix[2][2] = math.cos(-boneRotation[2])
    # Rotation about the Z Axis Matrix
    rZMatrix = mathutils.Matrix.Identity(4)
    rZMatrix[0][0] = math.cos(-boneRotation[1])
    rZMatrix[0][1] = -math.sin(-boneRotation[1])
    rZMatrix[1][0] = math.sin(-boneRotation[1])
    rZMatrix[1][1] = math.cos(-boneRotation[1])
    # Create the Scale Matrices
    sXMatrix = mathutils.Matrix.Scale(boneScale[0], 4, (1.0, 0.0, 0.0))
    sYMatrix = mathutils.Matrix.Scale(boneScale[2], 4, (0.0, 1.0, 0.0))
    sZMatrix = mathutils.Matrix.Scale(boneScale[1], 4, (0.0, 0.0, 1.0))
    # Compute the final Model transformation matrix
    finalMatrix = mathutils.Matrix(
        tMatrix @ rYMatrix @ rZMatrix @ rXMatrix @ sYMatrix @ sZMatrix @ sXMatrix
    )
    # Tranpose before writing
    finalMatrix.transpose()
    # Write the matrix
    for j in range(0, 4):
        for i in range(0, 4):
            f.write(str("%.6f" % finalMatrix[j][i]))
            if i == 3 and j == 3:
                f.write("; ")
            else:
                f.write(", ")
            if i == 3:
                f.write("\n")
    f.write("}\n")
    # Write the child bones
    for childBone in bone.children:
        WriteBoneAndChildren(f, childBone)
    f.write("}\n")


# TODO: Review this function, does this also convert righthand to left hand?
def ConvertMatrixToYAxisUp(matrix):
    # Decompose the Matrix into component parts
    location, rotation, scale = (
        matrix.decompose()
    )  # TODO: decompose is inaccurate need a better method

    # Translation Matrix
    translationMatrix = mathutils.Matrix.Translation(
        (location.x, location.z, location.y)
    )
    # Rotation about the X Axis Matrix
    # rotationXMatrix = mathutils.Matrix.Rotation((object.rotation_euler[0]), 4, 'X')
    rotationXMatrix = mathutils.Matrix.Identity(4)
    rotationXMatrix[1][1] = math.cos(-rotation.x)
    rotationXMatrix[1][2] = -math.sin(-rotation.x)
    rotationXMatrix[2][1] = math.sin(-rotation.x)
    rotationXMatrix[2][2] = math.cos(-rotation.x)
    # Rotation about the Y Axis Matrix
    # rotationYMatrix = mathutils.Matrix.Rotation((object.rotation_euler[2]), 4, 'Y')
    rotationYMatrix = mathutils.Matrix.Identity(4)
    rotationYMatrix[0][0] = math.cos(-rotation.z)
    rotationYMatrix[0][2] = math.sin(-rotation.z)
    rotationYMatrix[2][0] = -math.sin(-rotation.z)
    rotationYMatrix[2][2] = math.cos(-rotation.z)
    # Rotation about the Z Axis Matrix
    # rotationZMatrix = mathutils.Matrix.Rotation((object.rotation_euler[1]), 4, 'Z')
    rotationZMatrix = mathutils.Matrix.Identity(4)
    rotationZMatrix[0][0] = math.cos(-rotation.y)
    rotationZMatrix[0][1] = -math.sin(-rotation.y)
    rotationZMatrix[1][0] = math.sin(-rotation.y)
    rotationZMatrix[1][1] = math.cos(-rotation.y)
    # Scale Matrix
    scaleXMatrix = mathutils.Matrix.Scale(scale.x, 4, (1.0, 0.0, 0.0))
    scaleYMatrix = mathutils.Matrix.Scale(scale.z, 4, (0.0, 1.0, 0.0))
    scaleZMatrix = mathutils.Matrix.Scale(scale.y, 4, (0.0, 0.0, 1.0))

    # Compute the final Model transformation matrix
    finalMatrix = mathutils.Matrix.Identity(4)
    finalMatrix = mathutils.Matrix(
        translationMatrix
        @ rotationYMatrix
        @ rotationZMatrix
        @ rotationXMatrix
        @ scaleYMatrix
        @ scaleZMatrix
        @ scaleXMatrix
    )
    return finalMatrix
