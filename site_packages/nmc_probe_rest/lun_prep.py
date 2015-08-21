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
from  nmc_probe.lun_prep import LUNPrep
from nmc_probe.log import Log

from subprocess import CalledProcessError
import traceback

class LUNPrepREST(Resource):
    def post(self):
        try:
            # Parse the arguments
            args = self.post_parser.parse_args()

            if args.get('lun', None) is None:
                args['lun'] = 0

            if args.get('part', None) is None:
                args['part'] = 1

            if args.get('port', None) is None:
                args['port'] = 3260


            # Make sure required arguments are present
            missing_args = []
            required_args = ['ip', 'wwn', 'initiator_name', 'fqdn', 'ctrl_iface', 'ctrl_mac', 'console_port', 'console_speed', 'console_params', 'lun', 'part', 'port']
            
            for required_arg in required_args:
                if args[required_arg] is None:
                    missing_args.append(required_arg)

            if len(missing_args) > 0:
                Log.error(message)
                message = 'Missing parameters: %s' % ', '.join(missing_args)
                return {'status': message}, 404
            else:
                LUNPrep(args)
                return {'status': 'ok'}, 201

        except (TypeError, ValueError), e:
            Log.error(str(e))
            return {'status': str(e),
                    'stacktrace': traceback.format_exc(),
                }, 501

        except (CalledProcessError), e:
            cmd = ' '.join(e.cmd)
            Log.error(' '.join(e.cmd))
            return {'status': 'failed',
                    'cmd':    ' '.join(e.cmd),
                    'stacktrace': traceback.format_exc(),
                    'output': str(e.output)}, 501

        except (Exception), e:
            return {'status': 'fail',
                    'stacktrace': traceback.format_exc(),
                    'message': str(e)}, 501

    @property
    def post_parser(self):
        if getattr(self, '_post_parser', None) is None:
            self._post_parser = reqparse.RequestParser()
            self._post_parser.add_argument('initiator_name',  type=str, location='json')
            self._post_parser.add_argument('wwn',             type=str, location='json')
            self._post_parser.add_argument('lun',             type=int, location='json')
            self._post_parser.add_argument('part',            type=int, location='json')
            self._post_parser.add_argument('ip',              type=str, location='json')
            self._post_parser.add_argument('fqdn',            type=str, location='json')
            self._post_parser.add_argument('ctrl_iface',      type=str, location='json')
            self._post_parser.add_argument('ctrl_mac',        type=str, location='json')
            self._post_parser.add_argument('console_port',    type=str, location='json')
            self._post_parser.add_argument('console_speed',   type=str, location='json')
            self._post_parser.add_argument('console_params',  type=str, location='json')
            

        return self._post_parser