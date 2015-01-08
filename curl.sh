#!/bin/bash

host=`echo $1 | awk -F \/ '{print $3;}' | awk -F. '{ print $(NF-1) "." $(NF) ; }'`
#echo "Root host: $host"
fhost=`echo $1 | awk -F\/ '{print $3;}'`
#echo "Full hostname: $fhost"
req=`echo $1 | awk -F\/ '{print $(NF);}'`
#echo "Requested resource: $req"

if [ ! -z $3 ]; then
    url="https://${3}/${req}"
else
    url=$1
fi

x1=1000

# The NS record is not present only for v2cdn.net (EdgeCast) so I'm hardcoding their NS
# This will speed up the script a lot

if [ "$host" == "v2cdn.net" ]; then dns='ns1.v2cdn.net ns2.v2cdn.net';
else dns=`dig -4 +time=3 +tries=2 +short NS $host`;
fi

for ns in $dns; do
    x1=`dig -4 +norecurse +time=3 +tries=2 $fhost @$ns | grep "Query time" | awk '{print $4;}'`
    
    # It happens with the edgecast CDN that the NS responds in under 1ms. I can't graph that.
    if [ $x1 -eq 0 ]; then x1=1; fi

    if [ $x1 -lt 1000 ]; then break; fi
done

ip=`host $fhost | grep "has address" | awk '{print $4;}' | head -1`
dns=`printf %.3f $(echo "${x1}/1000" | bc -l)`

# check 443 or 80 depending on URL
if [ `echo $1 | grep "https://" | wc -l` -eq 1 ]; then
    tcp_ping_tmp=`/root/tcp-ping ${ip} 443 | awk '{print $1;}'`
else
    tcp_ping_tmp=`/root/tcp-ping ${ip} 80 | awk '{print $1;}'`
fi

ping=`printf %.3f $(echo "${tcp_ping_tmp}/1000" | bc -l)`

# if number of args > 0
if [ $# -gt 0 ]; then
    curl -4 \
        -A "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36" \
        --connect-timeout 5 \
        --max-time 7 \
        -w "DNS_TIME=${dns}&CURL_DNS=%{time_namelookup}&SSL_TIME=%{time_appconnect}&TRANSFER_TIME=%{time_total}&HTTP_CODE=%{http_code}&DOWNLOAD_SIZE=%{size_download}&1ST_BYTE=%{time_starttransfer}&ping=${ping}\n" \
        --max-redirs 5 \
        -skLo /dev/null ${url}
else
    echo "Error: Bad usage."
fi
