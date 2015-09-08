# REST API

Provides a RESTful API using python and flask to creating
and sharing iSCSI LUNs from ZFS clones and preparing them 
for use


# Install lun_clone

## CentOS 7

Clone the repository
```bash
mkdir -p /usr/src/nmc-probe
cd /usr/src/nmc-probe
git clone git@github.com:nmc-probe/utils.git
```

Create the virtualenv

```bash
yum install python-virtualenv
yum groupinstall "Development Tools"
mkdir /home/lun_clone
cd /home/lun_clone
virtualenv env
./env/bin/pip install Flask-RESTful-extend rtslib_fb uwsgi
```

Populate virtualenv with required nmc-probe/utils/ files and directories

```bash
cd /home/lun_clone
ln -s /usr/src/nmc-probe/utils/rest_api/lun_clone/app .
ln -s /usr/src/nmc-probe/utils/rest_api/lun_clone/wsgi.py .
ln -s /usr/src/nmc-probe/utils/rest_api/lun_clone/config.ini .
ln -s /usr/src/nmc-probe/utils/site-packages/nmc_probe env/lib/python2.7/site-packages/nmc_probe
ln -s /usr/src/nmc-probe/utils/site-packages/nmc_probe_rest env/lib/python2.7/site-packages/nmc_probe_rest
```

Install systemd unit for lun_clone
```bash
cat << EOF > /etc/systemd/system/lun_clone.service
[Unit]
Description=uWSGI instance to serve lun_clone
After=network.target

[Service]
User=root
Group=root
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/root/bin"
WorkingDirectory=/home/lun_clone
ExecStart=/home/lun_clone/env/bin/uwsgi --ini=./config.ini

[Install]
WantedBy=multi-user.target
EOF
```

Start and enable lun_clone

```bash
systemctl start lun_clone
systemctl enable lun_clone
```

Verify that the lun_clone is running
```bash
systemctl status lun_clone -l
```

Install and configure nginx

```bash
yum install nginx
mv /etc/nginx/nginx.conf /etc/nginx.conf.orig
cat << EOF > /etc/nginx/nginx.conf
# For more information on configuration, see:
#   * Official English Documentation: http://nginx.org/en/docs/
#   * Official Russian Documentation: http://nginx.org/ru/docs/

user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';

    access_log  /var/log/nginx/access.log  main;

    sendfile            on;
    tcp_nopush          on;
    tcp_nodelay         on;
    keepalive_timeout   65;
    types_hash_max_size 2048;

    include             /etc/nginx/mime.types;
    default_type        application/octet-stream;

    # Load modular configuration files from the /etc/nginx/conf.d directory.
    # See http://nginx.org/en/docs/ngx_core_module.html#include
    # for more information.
    include /etc/nginx/conf.d/*.conf;

}
EOF


cat << EOF > /etc/nginx/conf.d/lun_clone.conf
server {
    server_name _;
    listen       443 default_server;
    listen       [::]:443 default_server;
    root         /usr/share/nginx/html;

    ssl on;
    ssl_certificate        /etc/nginx/ssl/lun_clone.crt;
    ssl_certificate_key    /etc/nginx/ssl/lun_clone.key;
    ssl_client_certificate /etc/nginx/ssl/ca.crt;
    ssl_verify_client      on;

    location / {
        include uwsgi_params;
        uwsgi_pass unix:/var/run/lun_clone.sock;
    }

    error_page 404 /404.html;
        location = /40x.html {
    }

    error_page 500 502 503 504 /50x.html;
        location = /50x.html {
    }
}
EOF
```
Create self signed server cert for web front end. Or go buy one. 

```bash
mkdir /etc/nginx/ssl
cd /etc/nginx/ssl

export SERVER_SUBJECT="/C=US/ST=New Mexico/L=Los Alamos/CN=server.domain"
export CLIENT_SUBJECT="/C=US/ST=New Mexico/L=Los Alamos/CN=client.domain"
export DAYS=1865
export BITS=2048

# Create certificate authority:
# Create private key for CA
openssl genrsa -des3 -out ca.key 4096
# Create cert for CA
openssl req -new -x509 -days $DAYS -key ca.key -out ca.crt -subj "$SERVER_SUBJECT"
  
# Create the Server Key
openssl genrsa -des3 -out lun_clone_enc.key $BITS

# Remove encryption from private key
openssl rsa -in lun_clone_enc.key -out lun_clone.key

# Create the CSR
openssl req -new -key lun_clone.key -out lun_clone.csr -subj "$SERVER_SUBJECT"

# Sign the CSR with the newly created CA
openssl x509 -req -days $DAYS -in lun_clone.csr -CA ca.crt -CAkey ca.key -set_serial 01 -out lun_clone.crt

# Create the client key
openssl genrsa -des3 -out client_enc.key $BITS

# Remove encryption from client key, since you'll likely be
# consuming this REST service from a piece of software
openssl rsa -in client_enc.key -out client.key

# Create CSR for client
openssl req -new -key client.key -out client.csr -subj "$CLIENT_SUBJECT"

# Sign the CSR
openssl x509 -req -days $DAYS -in client.csr -CA ca.crt -CAkey ca.key -set_serial 02 -out client.crt
```

Start and enable nginx

```bash
systemctl enable nginx
systemctl start nginx
```

Test

```bash
curl -s -k --key /etc/nginx/ssl/client.key --cert /etc/nginx/ssl/client.crt https://localhost/lun/api/v1.0/clone_test
```

You should see

```json
{"status": "ok", "message": "test"}
```

# API

The API was designed for a ZFS + iSCSI backend.

## Endpoint: `/lun/api/v1.0/clone`

### Method: POST

Creates an iSCSI target by creating a clone of a ZFS snapshot, then shares it over iSCSI. It is assumed that the source snapshot is a snapshot of a volume. 
If the destination clone already exists, then that existing volume will be used for the iSCSI share

<table>
<tr> <th> Parameter    </th> <th> Required </th> <th> Description </th> </tr>
<tr> <td> src          </td> <td> yes      </td> <td> Source snapshot for the volume </td> </tr>
<tr> <td> dst          </td> <td> yes      </td> <td> Destination volume to create </td> </tr>
<tr> <td> wwn          </td> <td> yes      </td> <td> WWN for the iSCSI target </td> </tr>
<tr> <td> initiators   </td> <td> yes      </td> <td> Array of WWNs of initiators that are allowed to </td> </tr>
<tr> <td> createParent </td> <td> no       </td> <td> If set, any parent datasets for the destination will be created, if needed. </td> </tr>
<tr> <td> properties   </td> <td> no       </td> <td> ZFS properties for the destination clone. If not provided, then the properties will be taken from t </td> </tr>
</table>

Example

```bash
curl -s -k \
   --key /etc/emulab/ssl/client.key \
   --cert /etc/emulab/ssl/client.crt \
    -X POST 
    -H 'Content-Type: application/json' \
    -d '{"initiators":
           ["iqn.2014-11.nmc-probe.org:2da412368f",
            "iqn.2014-11.nmc-probe.org:bf537c5b3f8"],
         "src": "ns-host/projects/testbed/images/centos70-probe@0001",
         "dst": "ns-host/projects/myproject/myexperiment/nodes/ns0001/centos70-probe.0001",
         "createParent": 1,
         "wwn": "iqn.2014-11.nmc-probe.org:myproject.myexperiment.ns0001.centos70-probe.0001"
         }' 
    https://10.57.0.5/lun/api/v1.0/clone
```

### Method: DELETE

Removes an iSCSI share and optionally deletes the supporting volume.

<table>
<tr> <th> Parameter    </th> <th> Required </th> <th> Description </th> </tr>
<tr> <td> dst          </td> <td> yes      </td> <td> Destination volume to delete </td> </tr>
<tr> <td> wwn          </td> <td> yes      </td> <td> WWN for the target to unshare </td> </tr>
<tr> <td> deleteClones </td> <td> no       </td> <td> If set, the underlying clone will be deleted </td> </tr>
</table>


Example:

```bash
curl -s -k \
   --key /etc/emulab/ssl/client.key \
   --cert /etc/emulab/ssl/client.crt \
   -X DELETE \
   -H 'Content-Type: application/json' \
   -d '{"dst": "ns-host/projects/myproject/myexperiment/nodes/ns0001/centos70-probe.0001",
        "deleteClones": 1,
        "wwn": "iqn.2014-11.nmc-probe.org:myproject.myexperiment.ns0001.centos70-probe.0001"}' \ 
   https://10.57.0.5/lun/api/v1.0/clone
```

## Endpoint: /lun/api/v1.0/clone_test

### Method: POST

Used to check to see if the API stack is up and running. This endpoint does not take any parameters

Example:

```bash
curl -s -k --key /etc/nginx/ssl/client.key --cert /etc/nginx/ssl/client.crt https://localhost/lun/api/v1.0/clone_test
```