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
from nmc_probe.zfs import ZFS, CommandError
from nmc_probe.log import Log

import time
import sys

class SnapshotList(Resource):
    def get(self):
        zfs = ZFS()
        return jsonify(zfs.snapshots)

class VolumeList(Resource):
    def get(self):
        zfs = ZFS()
        return jsonify(zfs.volumes)

class FilesystemList(Resource):
    def get(self):
        zfs = ZFS()
        return jsonify(zfs.filesystems)

class AttributeList(Resource):
    def get(self):
        zfs = ZFS()
        return jsonify(zfs.attributes)

class ZFSResource(Resource):
    def post(self):
        try:
            zfs = ZFS()
            args = self.postParser.parse_args()
            self.postHandler(args)
        except (TypeError, ValueError, CommandError), e:
            return {'status': str(e)}, 501

        return {'status': 'ok'}, 201

    def delete(self):
        try:
            zfs = ZFS()
            args = self.deleteParser.parse_args()
            self.deleteHandler(args)
        except (TypeError, ValueError, CommandError), e:
            return {'status': str(e)}, 501

        return {'status': 'ok'}, 201

    def postHandler(self, args):
        zfs = ZFS()
        zfs.create(args)

    def deleteHandler(self, args):
        zfs = ZFS()
        zfs.destroy(args)

    @property
    def deleteParser(self):
        if getattr(self, '_deleteParser', None) is None:
            self._deleteParser = reqparse.RequestParser()
            self._deleteParser.add_argument('name', type=str, location='json')
        return self._deleteParser

    @property
    def postParser(self):
        if getattr(self, '_postParser', None) is None:
            self._postParser = reqparse.RequestParser()
            self._postParser.add_argument('name', type=str, location='json')
        return self._postParser

class Volume(ZFSResource):
    @property
    def postParser(self):
        if getattr(self, '_postParser', None) is None:
            self._postParser = reqparse.RequestParser()
            self._postParser.add_argument('name', type=str, location='json')
            self._postParser.add_argument('createParent', type=bool, location='json')
            self._postParser.add_argument('properties', type=dict, location='json')
            self._postParser.add_argument('volume', type=dict, location='json')

        return self._postParser

class Filesystem(ZFSResource):
    @property
    def postParser(self):
        if getattr(self, '_postParser', None) is None:
            self._postParser = reqparse.RequestParser()
            self._postParser.add_argument('name', type=str, location='json')
            self._postParser.add_argument('createParent', type=bool, location='json')
            self._postParser.add_argument('properties', type=dict, location='json')

        return self._postParser

class Snapshot(ZFSResource):
    def postHandler(self, args):
        zfs = ZFS()
        zfs.snapshot(args)

class Clone(ZFSResource):
    def postHandler(self, args):
        zfs = ZFS()
        zfs.clone(args)

    def deleteHandler(self, args):
        zfs = ZFS()
        zfs.destroy(args)

    @property
    def postParser(self):
        if getattr(self, '_postParser', None) is None:
            self._postParser = reqparse.RequestParser()
            self._postParser.add_argument('snapshot', type=str, location='json')
            self._postParser.add_argument('dest', type=str, location='json')
            self._postParser.add_argument('properties', type=dict, location='json')
            self._postParser.add_argument('createParent', type=bool, location='json')

        return self._postParser
