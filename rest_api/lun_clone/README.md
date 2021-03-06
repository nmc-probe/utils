# REST API for Creating Clones

Provides a RESTful API using python and flask to creating
and sharing iSCSI LUNs from ZFS clones and preparing them 
for use.

# Install and configure nginx

```bash
yum install epel-release nginx python-flask-sqlalchemy python-pip
pip install sqlalchemy-utils

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
If needed, create self signed server cert for web front end.

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

# Install lun_clone

## CentOS 7

Clone the repository
```bash
mkdir -p /usr/src/nmc-probe
cd /usr/src/nmc-probe
git clone https://github.com/nmc-probe/utils.git
```

Create the virtualenv

```bash
  679  yum install python-flask-sqlalchemy
  747  pip install sqlalchemy-utils
  748  yum install python-sqlalchemy-utils
  749  yum install pip
  751  yum install python-pip
  752  pip install sqlalchemy-utils

yum install python-virtualenv
yum groupinstall "Development Tools"
mkdir /home/lun_clone
cd /home/lun_clone
virtualenv env
./env/bin/pip install Flask-RESTful-extend rtslib_fb uwsgi sqlalchemy-utils python-flask-sqlalchemy
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
Environment="SQLITE_DB=/var/lun_clone/queue.db"
WorkingDirectory=/home/lun_clone
ExecStart=/home/lun_clone/env/bin/uwsgi --ini=./config.ini

[Install]
WantedBy=multi-user.target
EOF
```

Start and enable lun_clone

```bash
mkdir -p /var/lun_clone
systemctl start lun_clone
systemctl enable lun_clone
```

Verify that the lun_clone is running
```bash
systemctl status lun_clone -l
```

# Test

```bash
curl -s -k --key /etc/nginx/ssl/client.key --cert /etc/nginx/ssl/client.crt https://localhost/lun/api/v1.0/clone_test
```

You should see

```json
{"status": "ok", "message": "test"}
```

Watch the log:

```bash
systemctl restart lun_clone && journalctl -l -u lun_clone -f
```

Troubleshoot independent of nginx:

```
export SQLITE_DB=/var/lun_clone/queue.db
cd /home/lun_clone
./env/bin/python ./wsgi.py
```

# Install queue processing service

Install support packages:

```bash
mkdir /home/lun_queue
cd /home/lun_queue
virtualenv env
ln -s /usr/src/nmc-probe/utils/site-packages/nmc_probe env/lib/python2.7/site-packages/nmc_probe
ln -s /usr/src/nmc-probe/utils/site-packages/nmc_probe_rest env/lib/python2.7/site-packages/nmc_probe_rest
env/bin/pip install sqlalchemy-utils Flask-SQLAlchemy
```

Install systemd unit for lun_queue
```bash
cat << EOF > /etc/systemd/system/lun_queue.service
[Unit]
Description=LUN clone queue processing
After=network.target

[Service]
User=root
Group=root
Environment=VIRTUAL_ENV="/home/lun_queue/env"
Environment="PATH=$VIRTUAL_ENV/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/root/bin"
Environment="SQLITE_DB=/var/lun_clone/queue.db"
ExecStart=/home/lun_queue/lun_queue

[Install]
WantedBy=multi-user.target
EOF
```

Start and enable lun_queue

```bash
systemctl start lun_queue
systemctl enable lun_queue
```
Verify that the process_queue is running
```bash
systemctl status lun_queue -l
```

Restart and watch the log:
```bash
systemctl restart lun_queue && journalctl -l -u lun_queue -f
```

Troubleshoot from command line:

```bash
export SQLITE_DB=/var/lun_clone/queue.db
/usr/src/nmc-probe/utils/bin/lun_queue
```
