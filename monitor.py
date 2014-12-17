#!/usr/bin/env python
import logging
import subprocess
import sys
import json
import Queue
import threading
import random
import time
import MySQLdb
import ConfigParser

logging.basicConfig()

#
# get_value - returns the search value. All fields are separated by & and are looking like field_name=field_value
#
def get_value(line, search):
    x=line.split("&")
    for i in range(len(x)):
        tmp=x[i].split("=")
        if tmp[0] == search:
            return tmp[1]

#
# curl_host - calls the external curl.sh script
#
def curl_host (host, https):
    if https == 0:
        url=host[0].replace("https", "http")
    else:
        url=host[0]

    if len(host) == 2:
        p=subprocess.Popen(["/root/curl.sh", url, host[1]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        p=subprocess.Popen(["/root/curl.sh", url, host[1], host[2]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out,err = p.communicate()
    val=out.rstrip()
    return val

#
# work_curl - makes the HTTP request, saving -1 for the https_time
#
def work_curl (node, host):
    global conn, db
    str=host.split()
    val=curl_host(str, 0)

    dns = float(get_value(val, "DNS_TIME"))
    curl_dns = float(get_value(val, "CURL_DNS"))
    http = float(get_value(val, "TRANSFER_TIME")) - curl_dns
    https = -1
    http_code = int(get_value(val, "HTTP_CODE"))
    download_size = int(get_value(val, "DOWNLOAD_SIZE"))
    fst_byte = float(get_value(val, "1ST_BYTE")) - curl_dns

    print "# Generated values => Node: '%s', CDN: '%s', DNS: %.3f, CURL_DNS: %.3f, HTTPs: %.3f, HTTP: %.3f, HTTP_CODE: %d, DOWNLOAD_SIZE: %d, 1ST_BYTE: %.3f" %(node, str[1], dns, curl_dns, https, http, http_code, download_size, fst_byte)
    tmp="insert into curl_points(time, host, node, dns_time, https_time, http_time, code, size, 1st_byte) values (from_unixtime(%.0f), '%s', '%s', %.3f, %.3f, %.3f, %d, %d, %.3f)" %(time.time(), str[1], node, dns, https, http, http_code, download_size, fst_byte)
    print tmp

    conn.execute (tmp)
    db.commit()

#
# work_curls - makes the HTTPs request
#
def work_curls (node,host):
    global conn, db
    str=host.split()
    val=curl_host(str, 1)

    dns = float(get_value(val, "DNS_TIME"))
    curl_dns = float(get_value(val, "CURL_DNS"))
    https = float(get_value(val, "SSL_TIME")) - curl_dns
    http = float(get_value(val, "TRANSFER_TIME")) - curl_dns - https
    http_code = int(get_value(val, "HTTP_CODE"))
    download_size = int(get_value(val, "DOWNLOAD_SIZE"))
    fst_byte = float(get_value(val, "1ST_BYTE")) - curl_dns

    print "# Generated values => Node: '%s', CDN: '%s', DNS: %.3f, CURL_DNS: %.3f, HTTPs: %.3f, HTTP: %.3f, HTTP_CODE: %d, DOWNLOAD_SIZE: %d, 1ST_BYTE: %.3f" %(node, str[1], dns, curl_dns, https, http, http_code, download_size, fst_byte)
    tmp="insert into curl_points(time, host, node, dns_time, https_time, http_time, code, size, 1st_byte) values (from_unixtime(%.0f), '%s', '%s', %.3f, %.3f, %.3f, %d, %d, %.3f)" %(time.time(), str[1], node, dns, https, http, http_code, download_size, fst_byte)
    print tmp

    conn.execute (tmp)
    db.commit()

node=''.join(sys.argv[1:]) or "localhost"
version='0.2'

config = ConfigParser.ConfigParser()
config.readfp(open(r'/root/monitor.cfg'))

hostname = config.get('mysql', 'hostname')
username = config.get('mysql', 'username')
password = config.get('mysql', 'password')
database = config.get('mysql', 'database')

while True:
    db = MySQLdb.connect(host=hostname, user=username, passwd=password, db=database)
    conn=db.cursor()

    with open ("/root/curl.list") as f:
        for body in  f:
            if body == "\n":
                print "# Found sleeping signal => sleeping 3 seconds..."
                time.sleep(3)
            else:
                work_curl(node, body.rstrip('\n'))
                work_curls(node, body.rstrip('\n'))
    f.close()

    db.commit()
    conn.close()
    db.close()
