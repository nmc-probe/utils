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

import json,httplib,datetime,urllib
from nmc_probe.log import Log
from nmc_probe.bladeutilsconfig import BladeUtilsConfig

class CouchDB:
    """
    CouchDB connector that provides methods for getting, putting
    and saving documents
    """
    db = None
    host = None
    port = None

    def __init__(self, host, port, db):
        """
        Constructor

        Params
        ------
        host : string
               The host name where the CouchDB instance resides
        port : int
               The port to use
        db   : string
               The name of the database
        """
        self.host = host
        self.port = port
        self.db = db

    @classmethod
    def withConfigFile(cls, file = None):
        config = None

        if file:
            config = BladeUtilsConfig(file)
        else:
            config = BladeUtilsConfig()

        return cls(config.options['couch']['host'],
                   config.options['couch']['port'],
                   config.options['couch']['db'])
        
    def putDocument(self, docId, params):
        """
        PUT a document on the CouchDB server. If the document
        already exists, you will need to pass in a _rev param
        with the revision you would like to update. The
        saveDocument() method handles this for you, if all
        you want to do is save a document, regardless of whether
        or not it already exists.

        Params
        ------
        docId  : string
                 The unique ID of the document
        params : dictionary
                 A dictionary of parameters that define the document
        """
        path = '/%s/%s' % (self.db, docId.replace(' ', '+'))
        Log.debug(100, 'Putting %s' % path)
        connection = httplib.HTTPConnection(self.host, self.port)
        connection.connect()
        params['updatedAt'] = CouchDB.now()
        connection.request('PUT', path,
                           json.dumps(params),
                           {
                               'Content-Type': 'application/json'
                           })

        result = json.loads(connection.getresponse().read())

        if result.has_key(u'error'):
            Log.error('PUT %s: %s' % (path, result))

        return result

    def getDocument(self, docId):
        """
        GET a document from the server

        Params
        ------
        docId : string
                The unique ID of the document
        """
        path = '/%s/%s' % (self.db, docId.replace(' ', '+'))
        connection = httplib.HTTPConnection(self.host, self.port)
        connection.connect()
        connection.request('GET', path)
        result = json.loads( connection.getresponse().read())

        if result.has_key(u'error'):
            if result[u'error'] != u'not_found':
                Log.error('GET %s: %s' % (path, result))

        return result

    @classmethod
    def now(self):
        return datetime.datetime.now().isoformat()

    def saveDocument(self, docId, params):
        """                                                                     
        PUT a document on the CouchDB server. If the document                   
        already exists, it will be updated. You most likely want                
        to use this method and not putDocument()                                
                                                                                
        Params                                                                  
        ------                                                                  
        docId  : string                                                         
                 The unique ID of the document                                  
        params : dictionary                                                     
                 A dictionary of parameters that define the document            
        """
        results = self.getDocument(docId)
        needsPut = None

        # Document already exists, merge the param sets
        if results.has_key(u'_rev'):
            for key in params:
                # Check to see if the document was updated
                if key != '_id' and key != '_rev' and key != 'updatedAt' and key != 'createdAt':
                    if results.has_key(key):
                        if results[key] != params[key]:
                            needsPut = 1
                    else:
                        needsPut = 1
                        

                results[key] = params[key]
        else:
            needsPut = 1
            results = params
            results['createdAt'] = CouchDB.now()

        # Put document, if needed
        if needsPut:
            self.putDocument(docId, results)

    def delete(self, params):
        """
        Delete a document. Params must have an _id and _rev param
        """
        path = '/%s/%s?rev=%s' % (self.db, params['_id'].replace(' ', '+'), params['_rev'].replace(' ', '+'))
        Log.debug(10, 'DELETE %s' % path)
        connection = httplib.HTTPConnection(self.host, self.port)
        connection.connect()
        connection.request('DELETE', path)
        result = json.loads(connection.getresponse().read())

        if result.has_key(u'error'):
            if result[u'error'] != u'not_found':
                Log.error('GET %s: %s' % (path, result))

        return result
        
    def getView(self, design, view, key = None):
        """
        Get a view

        Params
        ------
        design:  string
                 The design document name
        view:    string
                 The view name
        key:     string (optional)
                 a key to select

        Returns
        -------
        A dictionary of view key/value pairs. If no results were returned, then
        None is returned
        """
        path = '_design/%s/_view/%s' % (design, view)

        if key:
            path = '%s?key="%s"' % (path, key)

        output = self.getDocument(path)
        results = {}

        if output.has_key(u'total_rows'):
            Log.debug(10, '%s returned %s rows' % (path, output[u'total_rows']))

        if output.has_key(u'rows'):
            for row in output[u'rows']:
                value = row[u'value']
                key   = row[u'key']

                if results.has_key(key):
                    storedValue = results[key]

                    # If the stored value is a dict, change to an array of dicts
                    if isinstance(storedValue, (frozenset, list, set, tuple)):
                        storedValue.append(value)
                        value = storedValue
                    else:
                        value = [storedValue, value]

                results[key] = value

        # If no results, then return a None object
        if len(results) <= 0:
            results = {}

        return results

    def getViewPath(self, design, view, params = None):
        """
        Internal function for building the path portion of 
        the URL to get a view. This is used by both getViewTuple
        and getViewDict
        
        Params
        ------
        design:  string
                 The design document name
        view:    string
                 The view name
        params:  dict
                 Dictionary of parameters:
                   key: The key to which results will be limited
                   start: The starting key for the range to which results will be
                             limited
                   end:   The ending key for the range to which results will be limited
                   includeDocs: Set this to anything, and the entire document will
                                be returned

        Returns
        -------
        The path
        """
        path = '_design/%s/_view/%s' % (design, view)

        if params is None or len(params) == 0:
            return path

        urlParams = {}

        key         = params.get('key', None)
        start       = params.get('start', None)
        end         = params.get('end', None)
        includeDocs = params.get('includeDocs', None)

        if key:
            urlParams['key'] = '"%s"' % key

        if start:
            urlParams['startkey'] = '"%s"' % start

        if end:
            urlParams['endkey'] = '"%s"' % end

        if includeDocs:
            urlParams['include_docs'] = 'true'

        if urlParams:
            path = '%s?%s' % (path, urllib.urlencode(urlParams))

        return path

    def getViewTuple(self, design, view, params = None):
        """
        Get a view, return a list of key/value tuples

        Params
        ------
        design:  string
                 The design document name
        view:    string
                 The view name
        key:     string (optional)
                 a key to select

        Returns
        -------
        An array of 2-tuples. The first element in the tuple is the key,
        the second element is the value. If no results were returned, then
        the array will be empty
        """
        path = self.getViewPath(design, view, params)
        Log.debug(10, 'Getting view path %s' % path)

        output = self.getDocument(path)
        results = []

        if output.has_key(u'total_rows'):
            Log.debug(10, '%s returned %s rows' % (path, output[u'total_rows']))

        if output.has_key(u'rows'):
            for row in output[u'rows']:
                key   = row[u'key']
                value = row.get(u'value', None)
                if params.has_key('includeDocs'):
                    value = row.get(u'doc', None)
                results.append((key, value))

        return results

    def getViewDict(self, design, view, params = {}):
        """
        Get a view, return the results as a dictionary of key => values.
        If the particular key occurs multiple times, then the value will 
        be an array of values for that key

        Params
        ------
        design:  string
                 The design document name
        view:    string
                 The view name
        params:  dictv
                 Dictionary of parameters:
                   key: The key to which results will be limited
                   start: The starting key for the range to which results will be
                             limited
                   end:   The ending key for the range to which results will be limited
                   includeDocs: Set this to anything, and the entire document will
                                be returned as the value

        Returns
        -------
        A dictionary of view key/value pairs. If no results were returned, then
        None is returned
        """
        path = self.getViewPath(design, view, params)
        Log.debug(10, 'Getting view path %s' % path)
        output = self.getDocument(path)
        results = {}

        if output.has_key(u'total_rows'):
            Log.debug(10, '%s returned %s rows' % (path, output[u'total_rows']))

        if output.has_key(u'rows'):
            for row in output[u'rows']:
                key   = row[u'key']
                value = row.get(u'value', None)
                if params.has_key('includeDocs'):
                    value = row.get(u'doc', None)

                # If this key is already in the results, then append this value
                # to the list
                if results.has_key(key):
                    storedValue = results[key]

                    # If the stored value is a dict, change to an array of dicts
                    if isinstance(storedValue, (frozenset, list, set, tuple)):
                        storedValue.append(value)
                        value = storedValue
                    else:
                        value = [storedValue, value]

                results[key] = value

        # If no results, then return a None object
        if len(results) <= 0:
            results = {}

        return results

class CouchDoc (object):
    """
    Base class for CouchDB documents
    """
    def __init__(self, params):
        """
        Constructor

        Parameters
        ----------
        params : dictionary
             Set of attributes
        """
        if params:
            for attr in self.persistentAttributes:
                if params.has_key(attr):
                    setattr(self, attr, params[attr])

    def persist(self, couch):
        """
        Persist this object to CouchDB
        """
        params = {'type': self.type}
        for attr in self.persistentAttributes:
            if hasattr(self, attr):
                params[attr] = getattr(self, attr)

        couch.saveDocument(self.docId, params)