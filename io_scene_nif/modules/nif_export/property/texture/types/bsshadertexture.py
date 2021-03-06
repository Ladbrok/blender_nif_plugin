"""This script contains helper methods to export shader property data."""

# ***** BEGIN LICENSE BLOCK *****
#
# Copyright © 2019, NIF File Format Library and Tools contributors.
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
from pyffi.formats.nif import NifFormat

from io_scene_nif.modules.nif_export.property.texture import TextureWriter, TextureSlotManager


class BSShaderTexture(TextureSlotManager):

    __instance = None

    @staticmethod
    def get():
        """ Static access method. """
        if BSShaderTexture.__instance is None:
            BSShaderTexture()
        return BSShaderTexture.__instance

    def __init__(self):
        """ Virtually private constructor. """
        if BSShaderTexture.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            super().__init__()
            BSShaderTexture.__instance = self

    def export_bs_effect_shader_prop_textures(self, bsshader):
        bsshader.texture_set = self._create_textureset()
        bsshader.source_texture = TextureWriter.export_texture_filename(self.b_diffuse_slot.texture)
        bsshader.greyscale_texture = TextureWriter.export_texture_filename(self.b_glow_slot.texture)

        # clamp Mode
        bsshader.texture_clamp_mode = 65283

    def export_bs_lighting_shader_prop_textures(self, bsshader):
        texset = self._create_textureset()
        bsshader.texture_set = texset

        # Add in extra texture slots
        texset.num_textures = 9
        texset.textures.update_size()

        if self.b_detail_slot:
            texset.textures[6] = TextureWriter.export_texture_filename(self.b_detail_slot.texture)

        if self.b_gloss_slot:
            texset.textures[7] = TextureWriter.export_texture_filename(self.b_gloss_slot.texture)

        # UV Offset
        if hasattr(bsshader, 'uv_offset'):
            self.export_uv_offset(bsshader)

        # UV Scale
        if hasattr(bsshader, 'uv_scale'):
            self.export_uv_scale(bsshader)

        # Texture Clamping mode
        if not self.b_diffuse_slot.texture.image.use_clamp_x:
            wrap_s = 2
        else:
            wrap_s = 0
        if not self.b_diffuse_slot.texture.image.use_clamp_y:
            wrap_t = 1
        else:
            wrap_t = 0
            
        bsshader.texture_clamp_mode = (wrap_s + wrap_t)

    def export_bs_shader_pp_lighting_prop_textures(self, bsshader):
        bsshader.texture_set = self._create_textureset()

    def _create_textureset(self):
        texset = NifFormat.BSShaderTextureSet()

        if self.b_diffuse_slot:
            texset.textures[0] = TextureWriter.export_texture_filename(self.b_diffuse_slot.texture)

        if self.b_normal_slot:
            texset.textures[1] = TextureWriter.export_texture_filename(self.b_normal_slot.texture)

        if self.b_glow_slot:
            texset.textures[2] = TextureWriter.export_texture_filename(self.b_glow_slot.texture)

        if self.b_detail_slot:
            texset.textures[3] = TextureWriter.export_texture_filename(self.b_detail_slot.texture)

        return texset

    def export_uv_offset(self, shader):
        shader.uv_offset.u = self.b_diffuse_slot.offset.x
        shader.uv_offset.v = self.b_diffuse_slot.offset.y

        return shader

    def export_uv_scale(self, shader):
        shader.uv_scale.u = self.b_diffuse_slot.scale.x
        shader.uv_scale.v = self.b_diffuse_slot.scale.y

        return shader
