#!/bin/bash -x

host=`echo $1 | sed 's/^.*\.\([a-z\-]*\.[a-z]*\).*/\1/'`
fhost=`echo $1 | awk -F\/ '{print $3;}'`
req=`echo $1 | sed 's/^.*\/\([a-z]*\.[a-z]*\)$/\1/'`

if [ ! -z $3 ]; then
    url=https://$3/${req}
else
    url=$1
fi

x1=1000

for ns in `dig -4 +time=1 +tries=2 NS $host | grep IN | grep -v ";" | awk '{print $5;}'`; do
    x1=`dig -4 +norecurse +time=1 +tries=2 $fhost @$ns | grep "Query time" | awk '{print $4;}'`
    ip=`dig -4 +norecurse +time=1 +tries=2 +short $fhost @$ns`
    if [ $x1 -lt 1000 ]; then break; fi
done

dns=`printf %.3f $(echo "${x1}/1000" | bc -l)`

# if number of args > 0
if [ $# -gt 0 ]; then
    curl -4 \
        -A "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36" \
        --connect-timeout 3 \
        --max-time 5 \
        -w "DNS_TIME=${dns}&CURL_DNS=%{time_namelookup}&SSL_TIME=%{time_appconnect}&TRANSFER_TIME=%{time_total}&HTTP_CODE=%{http_code}&DOWNLOAD_SIZE=%{size_download}\n" \
        --max-redirs 5 \
        -skLo /dev/null ${url}
else
    echo "Error: Bad usage."
fi
