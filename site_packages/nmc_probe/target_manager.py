# Copyright (c) 2015 The New Mexico Consortium
# 
# {{{NMC-LICENSE
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
# OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF
# THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
# DAMAGE.
#
# }}}

import re, subprocess
import rtslib_fb
from rtslib_fb import FabricModule, Target, TPG, BlockStorageObject, NetworkPortal, NodeACL, LUN, MappedLUN, RTSRoot

from nmc_probe.log import Log

class TargetManager:
    'Manages ZVOL based iSCSI targets for Emulab diskless booting'
    block_store = {}
    target      = {}
    root        = rtslib_fb.RTSRoot()
    iscsi       = FabricModule("iscsi")
    mapped_luns = {}

    # Constructor
    def __init__(self):
        self.get_block_store_objects()
        self.get_targets()

    # Get list of block storage objects
    def get_block_store_objects(self):
        for storage_object in self.root.storage_objects:
            if storage_object.plugin == "block":
                self.block_store[storage_object.name] = storage_object

    # Get a list of iscsi targets and associated luns, acls and portals
    # This builds a data structure that is a hash that hash other hashes
    # as values, and then other hashes, etc. To see what the data structure
    # looks like, run targetcli from the command line and issue the ls command.
    #
    # This data structure mimics that list for fast lookup for creating
    # shares for lots of nodes.
    #
    # This code is really confusing, in case you couldn't tell.
    #
    # target 0..N -> target.wwn
    # |
    # +---tpgs         List of target portal groups, this code assumes only one
    #      |            self.target[wwn]['tpg'][tpg.tag]['acl'][initiator_name'] = mapped_lun
    #      |
    #      +--acls     List of initiator names that can log into this iscsi target
    #      |             self.target[wwn]['tpg'][tpg.tag]['acl'] = { initiator_name : acl }
    #      |
    #      +--luns     List of LUNS for this TPG
    #      |             self.target[wwn]['lun'][lun.storage_object.name] = lun
    #      |
    #      +--portals  List of portals for this TPG
    #                    self.target[wwn]['portal'][portal.ip_address:portal.port] = portal

    # There can be any number of targets, each uniquely identified by its wwn (World Wide Name)
    #   which is also known as the initiator name. This is the unique name assigned to each client.
    #   The client knows about this name either by looking at its kernel parameters, the initiator
    #   name stored in the BIOS, but usually in /etc/iscsi/initiatorname.iscsi
    #
    # self.target[wwn]['tpg']    [tpg.tag]  ['acl'] [initiator_name] = MappedLUN object
    # self.target[wwn]['lun']    [lun_storage_object.name] = LUN object
    # self.target[wwn]['portal'] [portal_id] = Portal object
    # 
    def get_targets(self):
        for target in list(self.iscsi.targets):
            wwn = target.wwn
            self.target[wwn] = {'target': target, 'tpg': {} }

            for tpg in target.tpgs:
                self.target[wwn]['tpg'][tpg.tag] = {'tpg': tpg, 'acl': {}, 'lun': {}, 'portal': {} }
                tpg_tag = self.target[wwn]['tpg'][tpg.tag]

                for acl in tpg.node_acls:
                    tpg_tag['acl'][acl.node_wwn] = acl

                for lun in tpg.luns:
                    tpg_tag['lun'][lun.storage_object.name] = lun

                for portal in tpg.network_portals:
                    portal_id = portal.ip_address + ":" + str(portal.port)
                    tpg_tag['portal'][portal_id] = portal

    # Create a share
    def create_iscsi_target(self, params):
        """Create an iSCSI target

        Parameters
        ----------
        params : dict
            Dictionary of parameters
            wwn: The World Wide Name of the share, eg, the IQN
            device: the backing device
            initiators: list of initiators
        """
        wwn = params.get('wwn', None)
        device = params.get('device', None)
        initiators = params.get('initiators', None)
        ip = params.get('ip', '0.0.0.0')
        port = params.get('port', 3260)

        # Create blockstore, if needed
        blockstore = self.create_block_store(wwn, device)

        # Create target
        target = self.create_target(wwn)

        # Create TPG
        tpg = self.create_tpg(target, 1)

        # Create LUN
        lun = self.create_lun(tpg, blockstore)

        Log.info('lun: %s' % repr(lun))

        # Create portal
        portal = self.create_portal(tpg, ip, port)

        # Set up ACLs and mapped LUNs
        for initiator in initiators:
            # Create ACL
            acl = self.create_acl(tpg, initiator)

            # Map LUN
            mapped_lun = self.create_mapped_lun(acl, 0, lun)

    def delete_target_and_block_store(self, params):
        """Delete an iSCSI target and block store. This does not delete the underlying storage
        
        Parameters
        ----------
        wwn : string
            The world wide name of the share to remove
        """
        wwn = params.get('wwn', None)

        if wwn is None:
            raise ValueError('No wwn specified')

        # Delete target
        self.delete_target(wwn)

        # Delete blockstore
        self.delete_block_store(wwn)

    def create_block_store(self, wwn, device):
        """Create a blockstore with the given wwn, if it does not exist.
        TODO: check that existing wwns are connected to the specified device. If not, raise an exception
        Parameters
        ----------
        wwn : string
            World Wide Name for the block store
        device : string
            Path to a block device
        """
        storage = None

        # Check to see if the block storage has been set up
        if self.block_store.has_key(wwn):
            storage = self.block_store[wwn]
        else:
            Log.info('creating block backstore %s for device %s' % (wwn, device))
            storage = BlockStorageObject(wwn, device, wwn)
            self.block_store[wwn] = storage

        return storage

    # Delete blockstore, if it exists
    def delete_block_store(self, name):
        store = self.block_store.get(name)

        # If blockstore doesn't exist, do not proceed
        if store is None:
            Log.info('No block store %s. Not deleting' % name)
            return

        Log.info('deleting block store %s' % (name))

        # Delete the block store. The backing device, file, etc,  still exists
        store.delete()
        del self.block_store[name]

    # Delete target, if it exists
    def delete_target(self, wwn):
        # See if the target exists
        targetDict = self.target.get(wwn, None)

        # Doesn't exist, don't proceed
        if targetDict is None:
            Log.info('No target %s. Not deleting' % wwn)
            return

        target = targetDict.get('target', None)

        # Surprising, but possible, because processes can die
        # and the state can strange
        if target is None:
            return

        Log.info('deleting target %s' % (wwn))

        # Delete the target
        target.delete()
        del self.target[wwn]
    
    # Create target, if needed
    def create_target(self, wwn):
        target = None

        if self.target.has_key(wwn):
            target = self.target[wwn]['target']
        else:
            target = Target(self.iscsi, wwn)
            # Add target to data structure, initialize empty child nodes
            self.target[wwn] = {'target': target, 'tpg': {} }

        return target

    # Create TPG, if needed
    def create_tpg(self, target, tag):
        tpg = None
        tpg_list = self.target[target.wwn]['tpg']

        if tpg_list.has_key(tag):
            tpg = tpg_list[tag]['tpg']
        else:
            Log.info('creating tpg (%s, %s)' % (target, tag))
            tpg = TPG(target,tag)
            tpg_list[tag] = {'tpg': tpg, 'acl': { 'mapped_lun': {} }, 'lun': {}, 'portal': {} }

        if tpg is None:
            Log.error('tpg for %s not created' % target.wwn)
        else:
            tpg.set_attribute("authentication", 0)
            tpg.enable = 1

        return tpg

    # Create LUN, if needed
    def create_lun(self, tpg, blockstore):
        lun = None

        wwn = tpg.parent_target.wwn
        lun_list = self.target[wwn]['tpg'][tpg.tag]['lun']

        if lun_list.has_key(blockstore.name):
            # LUN already exists
            lun = lun_list[blockstore.name]
        else:
            Log.info('creating lun %s, blockstore %s' % (tpg, blockstore))
            # Create the LUN
            lun = LUN(tpg, 0, blockstore)
            # Add it to the local data structure for tracking LUNs
            lun_list[blockstore.name] = lun

        return lun

    # Create portal, if needed
    def create_portal(self, tpg, ip, port):
        portal      = None
        portal_id   = ip + ":" + str(port)
        wwn         = tpg.parent_target.wwn
        portal_list = self.target[wwn]['tpg'][tpg.tag]['portal']

        if portal_list.has_key(portal_id):
            portal = portal_list[portal_id]
        else:
            Log.info('creating portal (%s, %s, %s)' % (tpg, ip, port))
            portal = NetworkPortal(tpg, ip, port)
            portal_list[portal_id] = portal
            
        return portal

    # Create ACL, if needed
    def create_acl(self, tpg, initiator_name):
        acl     = None
        wwn     = tpg.parent_target.wwn
        acl_list = self.target[wwn]['tpg'][tpg.tag]['acl']
        
        if acl_list.has_key(initiator_name):
            acl = acl_list[initiator_name]
        else:
            Log.info('creating acl (%s, %s)' % (tpg, initiator_name))
            acl = NodeACL(tpg, initiator_name)
            acl_list[initiator_name] = acl

        return acl

    # Create mapped lun, if needed
    def create_mapped_lun(self, acl, num, lun):
        mapped_lun = None
        if not list(acl.mapped_luns):
            try:
                Log.info('creating mapped lun (%s, %s, %s)' % (acl, num, lun))
                mapped_lun = MappedLUN(acl, num, lun)
            except (rtslib_fb.utils.RTSLibError) as e:
                Log.error(str(e))

        return mapped_lun
