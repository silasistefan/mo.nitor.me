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
def curl_host (host, protocol):
    if protocol == "http":
        url=host[0].replace("https", "http")
    elif protocol == "https":
        url=host[0]
    else:
        # this is for PHP req
        url=host[0].replace("/index.html", "/index.php")

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
def work_curl (node, host, protocol):
    global conn, db
    str=host.split()
    val=curl_host(str, protocol)

    dns = float(get_value(val, "DNS_TIME"))
    curl_dns = float(get_value(val, "CURL_DNS"))
    http = float(get_value(val, "TRANSFER_TIME")) - curl_dns

    if protocol == "http":
        https = -1
    else:
        # SSL Handshake can be faster than 1ms, resulting in 0.000ms value
        https = float(get_value(val, "SSL_TIME"))
        if https == 0.000:
            https = 0.001
        else:
            https =  float(get_value(val, "SSL_TIME")) - curl_dns

    http_code = int(get_value(val, "HTTP_CODE"))
    download_size = int(get_value(val, "DOWNLOAD_SIZE"))
    fst_byte = float(get_value(val, "1ST_BYTE")) - curl_dns
    ping = float(get_value(val, "ping"))

    print "### URL: %s (%s)" %(str[0], str[1])
    print "# Result: %s" %(val)
    print "# Generated values => Node: '%s', CDN: '%s', DNS: %.3f, CURL_DNS: %.3f, HTTPs: %.3f, HTTP: %.3f, HTTP_CODE: %d, DOWNLOAD_SIZE: %d, 1ST_BYTE: %.3f, PING: %.3f" %(node, str[1], dns, curl_dns, https, http, http_code, download_size, fst_byte, ping)
    tmp="insert into curl_points(time, host, node, dns_time, https_time, http_time, code, size, 1st_byte, ping) values (from_unixtime(%.0f), '%s', '%s', %.3f, %.3f, %.3f, %d, %d, %.3f, %.3f)" %(time.time(), str[1], node, dns, https, http, http_code, download_size, fst_byte, ping)
    print "#"
    print tmp
    print "###\n"

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
                work_curl(node, body.rstrip('\n'), "http")
                work_curl(node, body.rstrip('\n'), "https")
    f.close()

    db.commit()
    conn.close()
    db.close()
