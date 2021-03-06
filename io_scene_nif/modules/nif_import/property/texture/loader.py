"""This script contains helper methods for texture pathing."""

# ***** BEGIN LICENSE BLOCK *****
#
# Copyright © 2020, NIF File Format Library and Tools contributors.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials provided
#      with the distribution.
#
#    * Neither the name of the NIF File Format Library and Tools
#      project nor the names of its contributors may be used to endorse
#      or promote products derived from this software without specific
#      prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# ***** END LICENSE BLOCK *****

from functools import reduce
import operator
import os.path

import bpy
from pyffi.formats.nif import NifFormat

from io_scene_nif.modules.nif_import.property import texture
from io_scene_nif.utils.util_global import NifOp
from io_scene_nif.utils.util_logging import NifLog


class TextureLoader:

    # for reference
    # @staticmethod
    # def load_tex(tree, tex_path):
    #     name = os.path.basename(tex_path)
    #     if name not in bpy.data.images:
    #         try:
    #             img = bpy.data.images.load(tex_path)
    #         except:
    #             NifLog.debug("Could not find image " + tex_path + ", generating blank image!")
    #             img = bpy.data.images.new(name, 1, 1)
    #     else:
    #         img = bpy.data.images[name]
    #     tex = tree.nodes.new('ShaderNodeTexImage')
    #     tex.image = img
    #     tex.interpolation = "Smart"
    #
    #     return tex

    @staticmethod
    def get_texture_hash(source):
        """Helper function for import_texture. Returns a key that uniquely
        identifies a texture from its source (which is either a
        NiSourceTexture block, or simply a path string).
        """
        if not source:
            return None
        elif isinstance(source, NifFormat.NiSourceTexture):
            return source.get_hash()
        elif isinstance(source, str):
            return source.lower()
        else:
            raise TypeError("source must be NiSourceTexture block or string")

    def import_texture_source(self, source, tree):
        """Convert a NiSourceTexture block, or simply a path string, to a Blender Texture object.
        Stores it in the texture.DICT_TEXTURES dictionary to avoid future duplicate imports.
        :return Texture object
        """

        # if the source block is not linked then return None
        if not source:
            return None

        # calculate the texture hash key
        texture_hash = self.get_texture_hash(source)

        try:
            # look up the texture in the dictionary of imported textures and return it if found
            return texture.DICT_TEXTURES[texture_hash]
        except KeyError:
            NifLog.debug("Storing {0} texture in map".format(str(source)))
            pass

        if isinstance(source, NifFormat.NiSourceTexture) and not source.use_external and texture.IMPORT_EMBEDDED_TEXTURES:
            fn, b_image = self.import_embedded_texture_source(source)
        else:
            fn, b_image = self.import_external_source(source)

        b_text_name = os.path.basename(fn)
        # create a stub image if the image could not be loaded
        if not b_image:
            NifLog.warn("Texture '{0}' not found or not supported and no alternate available".format(fn))
            b_image = bpy.data.images.new(name=b_text_name, width=1, height=1, alpha=False)
            b_image.filepath = fn

        # create a texture node
        b_texture = tree.nodes.new('ShaderNodeTexImage')
        b_texture.image = b_image
        b_texture.interpolation = "Smart"

        # save texture to avoid duplicate imports, and return it
        texture.DICT_TEXTURES[texture_hash] = b_texture
        return b_texture

    def import_embedded_texture_source(self, source):

        fn, tex = self.generate_image_name()

        # save embedded texture as dds file
        stream = open(tex, "wb")
        try:
            NifLog.info("Saving embedded texture as {0}".format(tex))
            source.pixel_data.save_as_dds(stream)
        except ValueError:
            # value error means that the pixel format is not supported
            b_image = None
        else:
            # saving dds succeeded so load the file
            b_image = bpy.ops.image.open(tex)
            # Blender will return an image object even if the file format is not supported,
            # so to check if the image is actually loaded an error is forced via "b_image.size"
            try:
                b_image.size
            except:  # RuntimeError: couldn't load image data in Blender
                b_image = None  # not supported, delete image object
        finally:
            stream.close()

        return [fn, b_image]

    @staticmethod
    def generate_image_name():
        """Find a file name (but avoid overwriting)"""
        n = 0
        while n < 1000:
            fn = "image{:0>3d}.dds".format(n)
            tex = os.path.join(os.path.dirname(NifOp.props.filepath), fn)
            if not os.path.exists(tex):
                break
            n += 1
        return fn, tex

    def import_external_source(self, source):
        b_image = None
        fn = None

        # the texture uses an external image file
        if isinstance(source, NifFormat.NiSourceTexture):
            fn = source.file_name.decode()
        elif isinstance(source, str):
            fn = source
        else:
            raise TypeError("source must be NiSourceTexture or str")

        fn = fn.replace('\\', os.sep)
        fn = fn.replace('/', os.sep)
        # go searching for it
        import_path = os.path.dirname(NifOp.props.filepath)
        search_path_list = [import_path]
        if bpy.context.preferences.filepaths.texture_directory:
            search_path_list.append(bpy.context.preferences.filepaths.texture_directory)

        # TODO [general][path] Implement full texture path finding.
        nif_dir = os.path.join(os.getcwd(), 'nif')
        search_path_list.append(nif_dir)

        # if it looks like a Morrowind style path, use common sense to guess texture path
        meshes_index = import_path.lower().find("meshes")
        if meshes_index != -1:
            search_path_list.append(import_path[:meshes_index] + 'textures')

        # if it looks like a Civilization IV style path, use common sense to guess texture path
        art_index = import_path.lower().find("art")
        if art_index != -1:
            search_path_list.append(import_path[:art_index] + 'shared')

        # go through all texture search paths
        for texdir in search_path_list:
            texdir = texdir.replace('\\', os.sep)
            texdir = texdir.replace('/', os.sep)
            # go through all possible file names, try alternate extensions too; for linux, also try lower case versions of filenames
            texfns = reduce(operator.add,
                            [[fn[:-4] + ext, fn[:-4].lower() + ext]
                             for ext in ('.DDS', '.dds', '.PNG', '.png',
                                         '.TGA', '.tga', '.BMP', '.bmp',
                                         '.JPG', '.jpg')])

            texfns = [fn, fn.lower()] + list(set(texfns))
            for texfn in texfns:
                # now a little trick, to satisfy many Morrowind mods
                if texfn[:9].lower() == 'textures' + os.sep and texdir[-9:].lower() == os.sep + 'textures':
                    # strip one of the two 'textures' from the path
                    tex = os.path.join(texdir[:-9], texfn)
                else:
                    tex = os.path.join(texdir, texfn)

                # "ignore case" on linuxW
                tex = bpy.path.resolve_ncase(tex)
                NifLog.debug("Searching {0}".format(tex))
                if os.path.exists(tex):
                    # tries to load the file
                    b_image = bpy.data.images.load(tex)
                    # Blender will return an image object even if the file format is not supported,
                    # so to check if the image is actually loaded an error is forced via "b_image.size"
                    try:
                        b_image.size
                    except:  # RuntimeError: couldn't load image data in Blender
                        b_image = None  # not supported, delete image object
                    else:
                        # file format is supported
                        NifLog.debug("Found '{0}' at {1}".format(fn, tex))
                        break
            if b_image:
                return [tex, b_image]
        else:
            tex = os.path.join(search_path_list[0], fn)

        return [tex, b_image]
