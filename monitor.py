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

logging.basicConfig()

node=''.join(sys.argv[1:]) or 'undefined'

def get_value(line, search):
    x=line.split("&")
    for i in range(len(x)):
        tmp=x[i].split("=")
        if tmp[0] == search:
            return tmp[1]

def curl_host (host):
    if len(host) == 2:
        p=subprocess.Popen(["/root/curl.sh", host[0], host[1]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        p=subprocess.Popen(["/root/curl.sh", host[0], host[1], host[2]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out,err = p.communicate()
    val=out.rstrip()
    return val

def work_curl (node,host):
    global conn, db
    str=host.split()
    val=curl_host(str)

    dns=float(get_value(val, "DNS_TIME"))
    https=float(get_value(val, "SSL_TIME")) - float(get_value(val, "CURL_DNS"))
    http=float(get_value(val, "TRANSFER_TIME")) - float(get_value(val, "CURL_DNS"))

    tmp="insert into curl_points(time, host, node, dns_time, https_time, http_time, code, size) values (from_unixtime(%.0f), '%s', '%s', %.3f, %.3f, %.3f, %d, %d)" %(time.time(), str[1], node, dns, https, http, int(get_value(val, "HTTP_CODE")), int(get_value(val, "DOWNLOAD_SIZE")))
    print tmp

    conn.execute (tmp)
    db.commit()

node=''.join(sys.argv[1:]) or "localhost"

while True:
    db = MySQLdb.connect(host="127.0.0.1", user="username", passwd="password", db="database")
    conn=db.cursor()

    with open ("/root/curl.list") as f:
        for body in  f:
            if body == "\n":
                print "Sleeping 3..."
                time.sleep(3)
            else:
                work_curl(node, body.rstrip('\n'))
    f.close()

    db.commit()
    conn.close()
    db.close()
