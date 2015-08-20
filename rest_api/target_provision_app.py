#!flask/bin/python
from flask import Flask, jsonify
from flask.ext.restful import Api, Resource, reqparse
from nmc.target import TargetManager
from nmc.zfs import ZFS
from nmc.log import Log

import time
import sys
from pprint import pprint

app = Flask(__name__)
api = Api(app)

class LUN(Resource):
    def post(self):
        try:
            args = self.postParser.parse_args()

            missing_args = []
            required_args = ['snapshot', 'dest', 'wwn', 'device', 'initiators']
            
            for required_arg in required_args:
                if args[required_arg] is None:
                    missing_args.append(required_arg)

            if len(missing_args) > 0:
                message = 'Missing parameters: %s' % ', '.join(missing_args)
                return {'status': message}, 404
            else:
                zfs = ZFS()
                mgr = TargetManager()
                zfs.clone(args)
                mgr.create_iscsi_target(args)
                return {'status': 'ok'}, 201

        except (TypeError, ValueError), e:
            Log.error(str(e))
            return {'status': str(e)}, 501


    def delete(self):
        try:
            args = self.deleteParser.parse_args()

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
    def postParser(self):
        if getattr(self, '_postParser', None) is None:
            self._postParser = reqparse.RequestParser()
            self._postParser.add_argument('snapshot', type=str, location='json')
            self._postParser.add_argument('dest', type=str, location='json')
            self._postParser.add_argument('properties', type=dict, location='json')
            self._postParser.add_argument('createParent', type=bool, location='json')
            self._postParser.add_argument('wwn', type=str, location='json')
            self._postParser.add_argument('device', type=str, location='json')
            self._postParser.add_argument('initiators', type=list, location='json')

        return self._postParser

    @property
    def deleteParser(self):
        if getattr(self, '_deleteParser', None) is None:
            self._deleteParser = reqparse.RequestParser()
            self._deleteParser.add_argument('name', type=str, location='json')
            self._deleteParser.add_argument('wwn', type=str, location='json')
            self._deleteParser.add_argument('deleteClones', type=str, location='json')
        return self._deleteParser


api.add_resource(LUN, '/lun/api/v1.0/clone', endpoint='clone')

if __name__ == '__main__':
    app.run(debug=True)
