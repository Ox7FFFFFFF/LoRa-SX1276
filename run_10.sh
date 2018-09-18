#!/bin/bash

for i in {1..100};
do
    python send_otaa_retry.py --pa 55
    sleep 5s
done
