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

from flask import Flask, jsonify
from flask.ext.restful import Api, Resource, reqparse
from nmc_probe.target import TargetManager
from nmc_probe.log import Log

import time
import sys
from pprint import pprint

import rtslib_fb
#from rtslib import BlockStorageObject, FabricModule, Target, TPG, NetworkPortal, NodeACL, LUN, MappedLUN, RTSRoot

app = Flask(__name__)
api = Api(app)

class BackstoreList(Resource):
    def get(self):
        dict = {}
        target = Target()

        for backstore in target.backstores:
            dict[backstore.name] = Target.backstoreDict(backstore)

        return jsonify(dict)

class iSCSIList(Resource):
    def get(self):
        dict = {}
        target = Target()
        
        for tgt in list(target.iscsi.targets):
            dict[target.wwn] = target.targetDict(tgt)

        return jsonify(dict)

class Target(Resource):
    def post(self):
        try:
            args = self.postParser.parse_args()
            mgr = TargetManager()
            mgr.create_iscsi_target(args)
        except (TypeError, ValueError), e:
            return {'status': str(e)}, 501

        return {'status': 'ok'}, 201

    def delete(self):
        args = self.deleteParser.parse_args()
        mgr = TargetManager()
        mgr.delete_target_and_block_store(args)
        try:
            args = self.deleteParser.parse_args()
            mgr = TargetManager()
            mgr.delete_target_and_block_store(args)
        except (TypeError, ValueError), e:
            return {'status': str(e)}, 501

        return {'status': 'ok'}, 201

    @property
    def postParser(self):
        if getattr(self, '_postParser', None) is None:
            self._postParser = reqparse.RequestParser()
            self._postParser.add_argument('wwn', type=str, location='json')
            self._postParser.add_argument('device', type=str, location='json')
            self._postParser.add_argument('initiators', type=list, location='json')

        return self._postParser

    @property
    def deleteParser(self):
        if getattr(self, '_deleteParser', None) is None:
            self._deleteParser = reqparse.RequestParser()
            self._deleteParser.add_argument('wwn', type=str, location='json')

        return self._deleteParser
