# Overview

REST API to iSCSI LUN preparation. This expects the iSCSI LUN FS to have /usr/local/bin/lun_prep

TODO: document purpose of the LUN-specific LUN prep

# Install: CentOS 7

Disable selinux
```bash
sed -i s/SELINUX=enforcing/SELINUX=disabled/g /etc/selinux/config
reboot
```

Clone the repository
```bash
mkdir -p /usr/src/nmc-probe
cd /usr/src/nmc-probe
git clone git@github.com:nmc-probe/utils.git
```

Create the virtualenv

```bash
yum groupinstall "Development Tools"
yum install python-virtualenv pcre-devel
mkdir /home/lun_prep
cd /home/lun_prep
virtualenv env
./env/bin/pip install Flask-RESTful-extend uwsgi
```

Populate virtualenv with required nmc-probe/utils/ files and directories

```bash
cd /home/lun_prep
ln -s /usr/src/nmc-probe/utils/rest_api/lun_prep/app .
ln -s /usr/src/nmc-probe/utils/rest_api/lun_prep/wsgi.py .
ln -s /usr/src/nmc-probe/utils/rest_api/lun_prep/config.ini .
ln -s /usr/src/nmc-probe/utils/site-packages/nmc_probe env/lib/python2.7/site-packages/nmc_probe
ln -s /usr/src/nmc-probe/utils/site-packages/nmc_probe_rest env/lib/python2.7/site-packages/nmc_probe_rest
```

Install systemd unit for lun_prep
```bash
cat << EOF > /etc/systemd/system/lun_prep.service
[Unit]
Description=uWSGI instance to serve lun_prep
After=network.target

[Service]
User=root
Group=root
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/root/bin"
WorkingDirectory=/home/lun_prep
ExecStart=/home/lun_prep/env/bin/uwsgi --ini=./config.ini

[Install]
WantedBy=multi-user.target
EOF
```

Install and configure nginx

```bash
yum install epel-release
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


cat << EOF > /etc/nginx/conf.d/lun_prep.conf
server {
    server_name _;
    listen       443 default_server;
    listen       [::]:443 default_server;
    root         /usr/share/nginx/html;

    ssl on;
    ssl_certificate        /etc/nginx/ssl/lun_prep.crt;
    ssl_certificate_key    /etc/nginx/ssl/lun_prep.key;
    ssl_client_certificate /etc/nginx/ssl/ca.crt;
    ssl_verify_client      on;

    location / {
        include uwsgi_params;
        uwsgi_pass unix:/var/run/lun_prep.sock;
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
openssl genrsa -des3 -out lun_prep_enc.key $BITS

# Remove encryption from private key
openssl rsa -in lun_prep_enc.key -out lun_prep.key

# Create the CSR
openssl req -new -key lun_prep.key -out lun_prep.csr -subj "$SERVER_SUBJECT"

# Sign the CSR with the newly created CA
openssl x509 -req -days $DAYS -in lun_prep.csr -CA ca.crt -CAkey ca.key -set_serial 01 -out lun_prep.crt

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
Start and enable lun_prep

```bash
systemctl enable lun_prep
systemctl start lun_prep
```

Verify that the lun_prep is running
```bash
systemctl status lun_prep -l
```


Start and enable nginx

```bash
systemctl enable nginx
systemctl start nginx
```

Test

```bash
curl -s -k --key /etc/nginx/ssl/client.key --cert /etc/nginx/ssl/client.crt https://localhost/lun/api/v1.0/prep_test
```

You should see

```json
{"status": "ok", "message": "test"}
```

## Troubleshooting

```
systemctl statux nginx -l
...
Aug 25 16:14:04 hostname.domain uwsgi[3218]: ImportError: No module named nmc_probe_rest.lun_clone
```
Verify that the git repo site-packages/nmc_probe and site-packages/nmc_probe_rest directories are linked:

```bash
ls -l /home/lun_prep/env/lib/python2.7/site-packages/ | grep nmc
lrwxrwxrwx.  1 root root     48 Aug 25 16:21 nmc_probe -> /usr/src/nmc-probe/utils/site-packages/nmc_probe
lrwxrwxrwx.  1 root root     53 Aug 25 16:21 nmc_probe_rest -> /usr/src/nmc-probe/utils/site-packages/nmc_probe_rest
```

If those links are broken, try remaking them. If they are still broken, verify that you successfully cloned the git repo

### Can't connect to socket
```
connect() to unix:/var/run/lun_clone.sock failed (2: No such file or directory) while connecting to upstream, client: ::1, server: _, request: "GET /lun/api/v1.0/test HTTP/1.1", upstream: "uwsgi://unix:/var/run/lun_clone.sock:", host: "localhost"
```

You may have followed the directions for lun_clone. Verify that /etc/nginx/conf.d/lun_prep.conf points to unix:/var/run/lun_prep.conf

### Permission denied while connecting to upstream 
```
connect() to unix:/var/run/lun_prep.sock failed (13: Permission denied) while connecting to upstream
```
 * Make sure your config.ini sets the ownership of the socket to root:nginx.
 * ls -l /var/run/lun_prep.sock, make sure it is owned by root:nginx
 * Disable SELINUX
 
