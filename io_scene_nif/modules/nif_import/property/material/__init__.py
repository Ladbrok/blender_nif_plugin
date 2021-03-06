"""This script contains helper methods to import materials."""

# ***** BEGIN LICENSE BLOCK *****
# 
# Copyright © 2012, NIF File Format Library and Tools contributors.
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

from io_scene_nif.modules.nif_import.object.block_registry import block_store
from io_scene_nif.utils.util_logging import NifLog


class Material:

    @staticmethod
    def set_stencil(b_mat, n_alpha_prop):
        NifLog.debug("Stencil prop detected")
        b_mat.use_backface_culling = False

        return b_mat

    @staticmethod
    def set_alpha(b_mat, n_alpha_prop):
        NifLog.debug("Alpha prop detected")
        # flags is a bitfield
        blend_enable = 1 & n_alpha_prop.flags
        test_enable = (1 << 9) & n_alpha_prop.flags
        if blend_enable and test_enable:
            b_mat.blend_method = "HASHED"
            b_mat.shadow_method = "HASHED"
        elif blend_enable:
            b_mat.blend_method = "BLEND"
            b_mat.shadow_method = "HASHED"
        elif test_enable:
            b_mat.blend_method = "CLIP"
            b_mat.shadow_method = "CLIP"
        else:
            b_mat.blend_method = "OPAQUE"
            b_mat.shadow_method = "OPAQUE"

        b_mat.alpha_threshold = n_alpha_prop.threshold / 255 # transparency threshold
        b_mat.niftools_alpha.alphaflag = n_alpha_prop.flags

        return b_mat

    # TODO [texture][vertex][color] Reimplement in newer system
    """
    def import_material(self, n_mat_prop, n_texture_prop, n_alpha_prop, n_specular_prop, texture_effect, n_wire_prop, extra_datas):

        # texures
        if n_texture_prop:
            self.texturehelper.import_nitextureprop_textures(b_mat, n_texture_prop)
            if extra_datas:
                self.texturehelper.import_texture_extra_shader(b_mat, n_texture_prop, extra_datas)
        if texture_effect:
            self.texturehelper.import_texture_effect(b_mat, texture_effect)

    def set_material_vertex_mapping(self, b_mesh, f_map, n_uvco):
        b_mat = b_mesh.materials[0]
        if b_mat:
            # fix up vertex colors depending on whether we had textures in the material
            mbasetex = self.texturehelper.has_base_texture(b_mat)
            mglowtex = self.texturehelper.has_glow_texture(b_mat)
            if b_mesh.vertex_colors:
                if mbasetex or mglowtex:
                    # textured material: vertex colors influence lighting
                    b_mat.use_vertex_color_light = True
                else:
                    # non-textured material: vertex colors influence color
                    b_mat.use_vertex_color_paint = True
    """

    @staticmethod
    def import_material_specular(b_mat, n_specular_color):
        b_mat.specular_color = (n_specular_color.r, n_specular_color.g, n_specular_color.b)

    @staticmethod
    def import_material_emissive(b_mat, n_emissive_color):
        b_mat.niftools.emissive_color = (n_emissive_color.r, n_emissive_color.g, n_emissive_color.b)

    @staticmethod
    def import_material_diffuse(b_mat, n_diffuse_color):
        b_mat.diffuse_color = (n_diffuse_color.r, n_diffuse_color.g, n_diffuse_color.b, 1.0)
        # b_mat.diffuse_intensity = 1.0

    @staticmethod
    def import_material_ambient(b_mat, n_mat_prop):
        b_mat.niftools.ambient_color = (n_mat_prop.ambient_color.r, n_mat_prop.ambient_color.g, n_mat_prop.ambient_color.b)

    @staticmethod
    def import_material_gloss(b_mat, glossiness):
        # b_mat.specular_hardness = glossiness
        b_mat.specular_intensity = glossiness  # Blender multiplies specular color with this value

class NiMaterial(Material):

    def import_material(self, n_block, b_mat, n_mat_prop):
        """Creates and returns a material."""
        # First check if material has been created before.
        # TODO [property][material] Decide whether or not to keep the material hash
        # material_hash = self.get_material_hash(n_mat_prop, n_texture_prop, n_texture_effect, n_extra_data, n_alpha_prop)
        # try:
        #     return material.DICT_MATERIALS[material_hash]
        # except KeyError:
        #     pass

        # update material material name
        name = block_store.import_name(n_mat_prop)
        if name is None:
            name = (n_block.name.decode() + "_nt_mat")
        b_mat.name = name

        # Ambient color
        self.import_material_ambient(b_mat, n_mat_prop)

        # Diffuse color
        self.import_material_diffuse(b_mat, n_mat_prop.diffuse_color)

        # TODO [property][material] Detect fallout 3+, use emit multi as a degree of emission
        # Test some values to find emission maximium. 0-1 -> 0-max_val
        # Should we factor in blender bounds 0.0 - 2.0

        # Emissive
        self.import_material_emissive(b_mat, n_mat_prop.emissive_color)
        # b_mat.emit = n_mat_prop.emit_multi

        # gloss
        self.import_material_gloss(b_mat, n_mat_prop.glossiness)

        # Specular color
        self.import_material_specular(b_mat, n_mat_prop.specular_color)

        return b_mat
