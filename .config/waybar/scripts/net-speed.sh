#!/bin/bash

INTERFACE=$(ip route | awk '/default/ {print $5; exit}')

RX1=$(cat /sys/class/net/$INTERFACE/statistics/rx_bytes)
TX1=$(cat /sys/class/net/$INTERFACE/statistics/tx_bytes)

sleep 1

RX2=$(cat /sys/class/net/$INTERFACE/statistics/rx_bytes)
TX2=$(cat /sys/class/net/$INTERFACE/statistics/tx_bytes)

RX=$((RX2 - RX1))
TX=$((TX2 - TX1))

format() {
    VALUE=$1

    if [ $VALUE -lt 1024 ]; then
        echo "${VALUE} B/s"
    elif [ $VALUE -lt 1048576 ]; then
        echo "$((VALUE / 1024)) KB/s"
    elif [ $VALUE -lt 1073741824 ]; then
        echo "$(echo "scale=2; $VALUE/1024/1024" | bc) MB/s"
    else
        echo "$(echo "scale=2; $VALUE/1024/1024/1024" | bc) GB/s"
    fi
}

DOWN=$(format $RX)
UP=$(format $TX)

echo " $UP  $DOWN"