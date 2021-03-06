"""This script contains helper methods to export object data properties."""

# ***** BEGIN LICENSE BLOCK *****
#
# Copyright © 2013, NIF File Format Library and Tools contributors.
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


import bpy

from pyffi.formats.nif import NifFormat

from io_scene_nif.modules.nif_import.object import PRN_DICT
from io_scene_nif.modules.nif_export.block_registry import block_store
from io_scene_nif.utils import util_math
from io_scene_nif.utils.util_global import NifOp
from io_scene_nif.utils.util_logging import NifLog


class ObjectProperty:

    def export_vertex_color_property(self, block_parent, flags=1, vertex_mode=0, lighting_mode=1):
        """Create a vertex color property, and attach it to an existing block
        (typically, the root of the nif tree).

        @param block_parent: The block to which to attach the new property.
        @param flags: The C{flags} of the new property.
        @param vertex_mode: The C{vertex_mode} of the new property.
        @param lighting_mode: The C{lighting_mode} of the new property.
        @return: The new property block.
        """
        # create new vertex color property block
        vcol_prop = block_store.create_block("NiVertexColorProperty")

        # make it a property of the parent
        block_parent.add_property(vcol_prop)

        # and now export the parameters
        vcol_prop.flags = flags
        vcol_prop.vertex_mode = vertex_mode
        vcol_prop.lighting_mode = lighting_mode

        return vcol_prop

    def export_z_buffer_property(self, block_parent, flags=15, func=3):
        """Create a z-buffer property, and attach it to an existing block
        (typically, the root of the nif tree).

        @param block_parent: The block to which to attach the new property.
        @param flags: The C{flags} of the new property.
        @param func: The C{function} of the new property.
        @return: The new property block.
        """
        # create new z-buffer property block
        zbuf = block_store.create_block("NiZBufferProperty")

        # make it a property of the parent
        block_parent.add_property(zbuf)

        # and now export the parameters
        zbuf.flags = flags
        zbuf.function = func

        return zbuf

    def get_matching_block(self, block_type, **kwargs):
        """Try to find a block matching block_type. Keyword arguments are a dict of parameters and required attributes of the block"""
        # go over all blocks of block_type

        NifLog.debug(f"Looking for {block_type} block. Kwargs: {kwargs}")
        for block in block_store.block_to_obj:
            # if isinstance(block, block_type):
            if block_type in str(type(block)):
                # skip blocks that don't match additional conditions
                for param, attribute in kwargs.items():
                    # now skip this block if any of the conditions does not match
                    if attribute is not None:
                        ret_attr = getattr(block, param, None)
                        if ret_attr != attribute:
                            NifLog.debug(f"break, {param} != {attribute}, returns {ret_attr}")
                            break
                else:
                    # we did not break out of the loop, so all checks went through, so we can use this block
                    NifLog.debug(f"Found existing {block_type} block matching all criteria!")
                    return block
        # we are still here, so we must create a block of this type and set all attributes accordingly
        NifLog.debug(f"Created new {block_type} block because none matched the required criteria!")
        block = block_store.create_block(block_type)
        for param, attribute in kwargs.items():
            if attribute is not None:
                setattr(block, param, attribute)
        return block

    # TODO [material][property] Move this to new form property processing
    def export_alpha_property(self, b_mat):
        """Return existing alpha property with given flags, or create new one
        if an alpha property with required flags is not found."""
        if b_mat.niftools_alpha.alphaflag != 0:
            # todo [material] reconstruct flag from material alpha settings
            flags = b_mat.niftools_alpha.alphaflag
            threshold = b_mat.alpha_threshold * 255
        elif NifOp.props.game == 'SID_MEIER_S_RAILROADS':
            flags = 0x32ED
            threshold = 150
        elif NifOp.props.game == 'EMPIRE_EARTH_II':
            flags = 0x00ED
            threshold = 0
        else:
            flags = 0x12ED
            threshold = 0
        return self.get_matching_block("NiAlphaProperty", flags=flags, threshold=int(threshold))

    def export_specular_property(self, flags=0x0001):
        """Return existing specular property with given flags, or create new one
        if a specular property with required flags is not found."""
        # search for duplicate
        return self.get_matching_block("NiSpecularProperty", flags=flags)

    def export_wireframe_property(self, flags=0x0001):
        """Return existing wire property with given flags, or create new one
        if an wire property with required flags is not found."""
        return self.get_matching_block("NiWireframeProperty", flags=flags)

    def export_stencil_property(self, flags=None):
        """Return existing stencil property with given flags, or create new one
        if an identical stencil property."""
        if NifOp.props.game == 'FALLOUT_3':
            flags = 19840
        # search for duplicate
        return self.get_matching_block("NiStencilProperty", flags=flags)


# TODO [object][property][extradata] doesn't account for mult-root
class ObjectDataProperty:

    @staticmethod
    def has_collision():
        """Helper function that determines if a blend file contains a collider."""
        for b_obj in bpy.data.objects:
            if b_obj.display_type == "BOUNDS":
                return b_obj

    # TODO [object][property] Move to object property
    @staticmethod
    def export_inventory_marker(n_root, root_objects):
        if NifOp.props.game in ('SKYRIM',):
            for root_object in root_objects:
                if root_object.niftools_bs_invmarker:
                    for extra_item in n_root.extra_data_list:
                        if isinstance(extra_item, NifFormat.BSInvMarker):
                            raise util_math.NifError("Multiple Items have Inventory marker data only one item may contain this data")
                    else:
                        n_extra_list = NifFormat.BSInvMarker()
                        n_extra_list.name = root_object.niftools_bs_invmarker[0].name.encode()
                        n_extra_list.rotation_x = root_object.niftools_bs_invmarker[0].bs_inv_x
                        n_extra_list.rotation_y = root_object.niftools_bs_invmarker[0].bs_inv_y
                        n_extra_list.rotation_z = root_object.niftools_bs_invmarker[0].bs_inv_z
                        n_extra_list.zoom = root_object.niftools_bs_invmarker[0].bs_inv_zoom
                        n_root.add_extra_data(n_extra_list)

    # TODO [object][property] Move to new object type
    def export_weapon_location(self, n_root, root_obj):
        # export weapon location
        if NifOp.props.game in ('OBLIVION', 'FALLOUT_3', 'SKYRIM'):
            loc = root_obj.niftools.prn_location
            if loc != "NONE":
                # add string extra data
                prn = block_store.create_block("NiStringExtraData")
                prn.name = 'Prn'
                prn.string_data = PRN_DICT[loc]
                n_root.add_extra_data(prn)

    # TODO [object][property] Move to object property
    def export_bsxflags_upb(self, root_block):
        # TODO [object][property] Fixme
        NifLog.info("Checking collision")
        # activate oblivion/Fallout 3 collision and physics
        if NifOp.props.game in ('OBLIVION', 'FALLOUT_3', 'SKYRIM'):
            b_obj = self.has_collision()
            if b_obj:
                # enable collision
                bsx = block_store.create_block("BSXFlags")
                bsx.name = 'BSX'
                bsx.integer_data = b_obj.niftools.bsxflags
                root_block.add_extra_data(bsx)

                # many Oblivion nifs have a UPB, but export is disabled as
                # they do not seem to affect anything in the game
                if b_obj.niftools.upb:
                    upb = block_store.create_block("NiStringExtraData")
                    upb.name = 'UPB'
                    if b_obj.niftools.upb == '':
                        upb.string_data = 'Mass = 0.000000\r\nEllasticity = 0.300000\r\nFriction = 0.300000\r\nUnyielding = 0\r\nSimulation_Geometry = 2\r\nProxy_Geometry = <None>\r\nUse_Display_Proxy = 0\r\nDisplay_Children = 1\r\nDisable_Collisions = 0\r\nInactive = 0\r\nDisplay_Proxy = <None>\r\n'
                    else:
                        upb.string_data = b_obj.niftools.upb.encode()
                    root_block.add_extra_data(upb)
