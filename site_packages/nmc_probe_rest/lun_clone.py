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

# Flask imports
from flask import Flask, jsonify
from flask.ext.restful import Api, Resource, reqparse

# nmc_probe imports
from nmc_probe.target_manager import TargetManager
from nmc_probe.zfs import ZFS
from nmc_probe.log import Log

class LUNClone(Resource):
    def post(self):
        try:
            # Parse the arguments
            args = self.post_parser.parse_args()

            # Make sure required arguments are present
            missing_args = []
            required_args = ['snapshot', 'dest', 'wwn', 'device', 'initiators']
            
            for required_arg in required_args:
                if args[required_arg] is None:
                    missing_args.append(required_arg)

            if len(missing_args) > 0:
                Log.error(message)
                message = 'Missing parameters: %s' % ', '.join(missing_args)
                return {'status': message}, 404
            else:
                # Set up ZFS and Target management
                zfs = ZFS()
                mgr = TargetManager()
                # Create the ZFS clone
                zfs.clone(args)
                # Create the iSCSI target
                mgr.create_iscsi_target(args)
                return {'status': 'ok'}, 201

        except (TypeError, ValueError), e:
            Log.error(str(e))
            return {'status': str(e)}, 501

    def delete(self):
        try:
            args = self.delete_parser.parse_args()

            missing_args = []
            required_args = ['name', 'wwn']
            
            for required_arg in required_args:
                if args[required_arg] is None:
                    missing_args.append(required_arg)

            if len(missing_args) > 0:
                message = 'Missing parameters: %s' % ', '.join(missing_args)
                return {'status': message}, 404
            else:
                mgr = TargetManager()
                mgr.delete_target_and_block_store(args)

                if args['deleteClones'] is not None:
                    zfs = ZFS()
                    zfs.destroy(args)

                return {'status': 'ok'}, 201

        except (TypeError, ValueError), e:
            Log.error(str(e))
            return {'status': str(e)}, 501

    @property
    def post_parser(self):
        if getattr(self, '_post_parser', None) is None:
            self._post_parser = reqparse.RequestParser()
            self._post_parser.add_argument('snapshot', type=str, location='json')
            self._post_parser.add_argument('dest', type=str, location='json')
            self._post_parser.add_argument('properties', type=dict, location='json')
            self._post_parser.add_argument('createParent', type=bool, location='json')
            self._post_parser.add_argument('wwn', type=str, location='json')
            self._post_parser.add_argument('device', type=str, location='json')
            self._post_parser.add_argument('initiators', type=list, location='json')

        return self._post_parser

    @property
    def delete_parser(self):
        if getattr(self, '_delete_parser', None) is None:
            self._delete_parser = reqparse.RequestParser()
            self._delete_parser.add_argument('name', type=str, location='json')
            self._delete_parser.add_argument('wwn', type=str, location='json')
            self._delete_parser.add_argument('deleteClones', type=str, location='json')
        return self._delete_parser
