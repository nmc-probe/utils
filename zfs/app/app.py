#!flask/bin/python
from flask import Flask, jsonify
from flask.ext.restful import Api, Resource, reqparse
from nmc.zfs import ZFS, CommandError
from nmc.log import Log

import time
import sys

app = Flask(__name__)
api = Api(app)

zfs = ZFS()


class SnapshotList(Resource):
    def get(self):
        return jsonify(zfs.snapshots)

class VolumeList(Resource):
    def get(self):
        return jsonify(zfs.volumes)

class FilesystemList(Resource):
    def get(self):
        return jsonify(zfs.filesystems)

class AttributeList(Resource):
    def get(self):
        return jsonify(zfs.attributes)

class ZFSResource(Resource):
    def post(self):
        try:
            args = self.postParser.parse_args()
            self.postHandler(args)
        except (TypeError, ValueError, CommandError), e:
            return {'status': str(e)}, 501

        return {'status': 'ok'}, 201

    def delete(self):
        try:
            args = self.deleteParser.parse_args()
            self.deleteHandler(args)
        except (TypeError, ValueError, CommandError), e:
            return {'status': str(e)}, 501

        return {'status': 'ok'}, 201

    def postHandler(self, args):
        zfs.create(args)

    def deleteHandler(self, args):
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
        zfs.snapshot(args)

class Clone(ZFSResource):
    def postHandler(self, args):
        zfs.clone(args)

    def deleteHandler(self, args):
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

api.add_resource(SnapshotList,   '/zfs/api/v1.0/snapshots',   endpoint='snapshots')
api.add_resource(VolumeList,     '/zfs/api/v1.0/volumes',     endpoint='volumes')
api.add_resource(FilesystemList, '/zfs/api/v1.0/filesystems', endpoint='filesystems')
api.add_resource(AttributeList,  '/zfs/api/v1.0/attributes',  endpoint='attributes')

api.add_resource(Filesystem, '/zfs/api/v1.0/filesystem',  endpoint='filesystem')
api.add_resource(Volume,     '/zfs/api/v1.0/volume',      endpoint='volume')
api.add_resource(Snapshot,   '/zfs/api/v1.0/snapshot',    endpoint='snapshot')
api.add_resource(Clone,      '/zfs/api/v1.0/clone',       endpoint='clone')

if __name__ == '__main__':
    app.run(debug=True)
