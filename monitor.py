#!/usr/bin/env python
import pika
import subprocess
import time
import random
import MySQLdb
import ConfigParser

with open ("/root/node", "r") as myfile:
    node=myfile.read().replace('\n', '')

config = ConfigParser.ConfigParser()
config.readfp(open(r'/root/monitor.cfg'))

# reading mysql credentials
hostname = config.get('mysql', 'hostname')
username = config.get('mysql', 'username')
password = config.get('mysql', 'password')
database = config.get('mysql', 'database')

# reading rabbitmq credentials
rabbit_hostname = config.get('rabbitmq', 'hostname')
rabbit_username = config.get('rabbitmq', 'username')
rabbit_password = config.get('rabbitmq', 'password')
# reading rabbitmq backup credentials
rabbit_hostname_backup = config.get('rabbitmq', 'hostname_backup')
rabbit_username_backup = config.get('rabbitmq', 'username_backup')
rabbit_password_backup = config.get('rabbitmq', 'password_backup')

db = MySQLdb.connect(host=hostname, user=username, passwd=password, db=database)
conn=db.cursor()

try:
    credentials = pika.PlainCredentials(rabbit_username, rabbit_password)
    connection = pika.BlockingConnection(pika.ConnectionParameters(rabbit_hostname, 5672, '/', credentials))
except Exception:
    credentials = pika.PlainCredentials(rabbit_username_backup, rabbit_password_backup)
    connection = pika.BlockingConnection(pika.ConnectionParameters(rabbit_hostname_backup, 5672, '/', credentials))

channel = connection.channel()
channel.exchange_declare(exchange='urls', type='fanout')
result = channel.queue_declare(exclusive=True)
queue_name = result.method.queue
channel.queue_bind(exchange='urls', queue=queue_name)

print ' [*] Waiting for urls. To exit press CTRL+C'

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
# callback - executes the curl call and saves data to mysql
#
def callback(ch, method, properties, body):
    global conn, db
    print " [x] %r" % (body,)
    url = body.split()
    # url[0] = url to fetch
    # url[1] = CDN monitored
    # url[2] = if present, hostname to be sent to curl

    protocols = ['http://', 'https://']

    for protocol in protocols:
        # i want to have different random values for http and https
        if url[1] == "cdnsun.com":
            requests = ['/mo.nitor.me.jpg', '/mo.nitor.me.txt']
        else:
            requests  = ['/index.html', '/index.php?rand=' + str(random.random()*10000), '/image.jpg']

        for req in requests:
            if len(url) == 2:
                p=subprocess.Popen(["/root/curl.sh", protocol + url[0] + req, url[1]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            else:
                p=subprocess.Popen(["/root/curl.sh", protocol + url[0] + req, url[1], url[2]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            out,err = p.communicate()
            val=out.rstrip()

            if req.find("/index.php") == -1:
                table = "curl_points"
            else:
                table = "dynamic_points"

            dns = float(get_value(val, "DNS_TIME"))
            curl_dns = float(get_value(val, "CURL_DNS"))
            http = float(get_value(val, "TRANSFER_TIME")) - curl_dns

            # SSL Handshake can be faster than 1ms, resulting in 0.000ms value
            if protocol == "http://":
                https = -1
            else:
                https = float(get_value(val, "SSL_TIME")) - curl_dns
                if https == 0.000:
                    https = 0.001

            http_code = int(get_value(val, "HTTP_CODE"))
            download_size = int(get_value(val, "DOWNLOAD_SIZE"))
            fst_byte = float(get_value(val, "1ST_BYTE")) - curl_dns
            ping = float(get_value(val, "ping"))

            print "### URL: %s%s%s (%s)" %(protocol,url[0],req, url[1])
            print "# Result: %s" %(val)
            print "# Generated values => Node: '%s', CDN: '%s', DNS: %.3f, CURL_DNS: %.3f, HTTPs: %.3f, HTTP: %.3f, HTTP_CODE: %d, DOWNLOAD_SIZE: %d, 1ST_BYTE: %.3f, PING: %.3f" %(node, url[1], dns, curl_dns, https, http, http_code, download_size, fst_byte, ping)
            tmp="insert into " + table + " (time, host, node, dns_time, https_time, http_time, code, size, 1st_byte, ping) values (from_unixtime(%.0f), '%s', '%s', %.3f, %.3f, %.3f, %d, %d, %.3f, %.3f)" %(time.time(), url[1], node, dns, https, http, http_code, download_size, fst_byte, ping)
            print "#"
            print tmp

            # write data to MySQL
            conn.execute (tmp)
            db.commit()

            print "###\n"

channel.basic_consume(callback, queue=queue_name, no_ack=True)
channel.start_consuming()
