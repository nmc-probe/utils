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

# nmc_probe imports
from nmc_probe.lun_clone_details import LUNCloneDetails
from nmc_probe.log import Log

# other imports
import traceback

class LUNCloneQueue:
    '''Processes the LUN clone queue'''
    def create_zfs(self, zfs, args):
        created_clone = None
        # Create the ZFS clone
        created_clone = zfs.clone(args)

        if created_clone is not None:
            return True
        return None

    def create_target(self, mgr, args):
        created = None
        # Create the iSCSI target
        args['device'] = '/dev/zvol/%s' % args['dst']
        created = mgr.create_iscsi_target(args)

        if created is not None:
            return True
        return None

    def remove_target(self, mgr, args):
        mgr.delete_target_and_block_store(args)

    def remove_zfs(self, zfs, args):
        # If deleteClones = true, then the dst parameter is also required.
        deleteClones = args.get('deleteClones', None)
        
        if deleteClones:
            if args.get('dst', None) is None:
                message = {'message': 'deleteClones parameter requires dst parameter'}
                return {'status': message}, 404

            zfs.destroy(args)

    def process_queue(self):
        
    def post(self):
        try:
            # Parse the arguments
            args = self.array_parser.parse_args()
            lun_clone = LUNCloneDetails(details = args)

        except (Exception), e:
            Log.error('%s:\n%s' % (str(e), traceback.format_exc()))
            return {'status': str(e),
                    'stacktrace': traceback.format_exc()}, 501
        
        return {'status': 'ok', 'created': created}, 201

    def post_old(self):
        try:
            # Parse the arguments
            args = self.array_parser.parse_args()

            # Set up ZFS and Target management
            zfs = ZFS()
            mgr = TargetManager()
            created = []

            for arg in args['clones']:
                if self.create_zfs(zfs, arg):
                    created.append(arg['dst'])

            # This can take quite some time. One would hope
            # that it would take less than a second, but if there
            # are hundreds of zvol devices, then this can take 
            # minutes to complete. But udevd has to finish before
            # the targets can be created
            if len(created) > 0:
                zfs.udevd_settle_down()

            for arg in args['clones']:
                self.create_target(mgr, arg)

        except (Exception), e:
            Log.error('%s:\n%s' % (str(e), traceback.format_exc()))
            return {'status': str(e),
                    'stacktrace': traceback.format_exc()}, 501
        
        return {'status': 'ok', 'created': created}, 201

    def delete_old(self):
        try:
            args = self.array_parser.parse_args()

            # Set up ZFS and Target management
            zfs = ZFS()
            mgr = TargetManager()

            for arg in args['clones']:
                self.remove_target(mgr, arg)

            for arg in args['clones']:
                self.remove_zfs(zfs, arg)

        except (Exception), e:
            Log.error('%s:\n%s' % (str(e), traceback.format_exc()))
            return {'status': str(e),
                    'stacktrace': traceback.format_exc()}, 501

        return {'status': 'ok'}, 201

