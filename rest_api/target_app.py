#!flask/bin/python

#api.add_resource(BackstoreList, '/target/api/v1.0/backstores',     endpoint='backstores')
#api.add_resource(iSCSIList,     '/target/api/v1.0/iscsi_targets',  endpoint='iscsi_targets')

api.add_resource(Target, '/target/api/v1.0/target', endpoint='target')

if __name__ == '__main__':
    app.run(debug=True)
