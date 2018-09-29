#!/usr/bin/env python
import eospy.cleos
import argparse
import datetime as dt
from threading import Thread
import re

dt_format = '%Y-%m-%d%H:%M'
out_format = '%Y%m%d%H%M'

parser = argparse.ArgumentParser(description='Create a snapshot')
parser.add_argument('--api-version','-v', type=str, default='v1', action='store', dest='api_version')
parser.add_argument('--url', '-u', type=str, action='store', default='http://localhost:8888', dest='url')
parser.add_argument('--acct-file', type=str, action='store', default='/opt/eosio/acct_snapshot.txt', dest='acct_file')
parser.add_argument('--time', type=str, action='store', default='', dest='time')
parser.add_argument('--out-file', type=str, help='%%Y-%%m-%%d%%H:%%M', action='store', required=True, dest='out_file')
parser.add_argument('--staked', action='store_true', dest='staked')
args = parser.parse_args()

global acct_age
acct_age = dt.datetime.now()
if args.time :
    acct_age = dt.datetime.strptime(args.time, dt_format)

print('Getting accounts older than: {}'.format(acct_age))

# connect to mongo
ce = eospy.cleos.Cleos(args.url, version=args.api_version)

global rslts
rslts = []


def check_delegated(name, get_staked=False) :
    delbw = ce.get_table('eosio', name, 'delband')
    for r in delbw['rows'] :
        try :
            cpu = float(r['cpu_weight'].split()[0])
            net = float(r['net_weight'].split()[0])
        except TypeError:
            cpu = 0
            net = 0
        rslts.append('{0},{1},{2},{3}'.format(r['from'],r['to'],cpu,net))

with open(args.acct_file) as ro:
    accounts = list(ro.readlines())
    
num_thds = 10
total = len(accounts)
print('Got {} accounts'.format(total))
cnt = 0
while cnt < total :
    threads = []
    cnt_thds = 0
    # resize num_thds
    if cnt + num_thds > total :
        num_thds = total - cnt
    proc_list = accounts[cnt:cnt+num_thds]
    for proc in proc_list :
        name = proc.strip('\n')
        t = Thread(target=check_delegated, args=(name,args.staked))
        t.start()
        threads.append(t)
    for thd in threads :
        thd.join()
    cnt += num_thds
    if cnt % 10240 == 0 :
        print('{} Processed {} out of {}'.format(dt.datetime.now(), cnt, total))

print('Rslts cnt: {0}'.format(len(rslts)))
with open(args.out_file,'w') as wb:
    wb.write('from,to,cpu,net\n')
    for line in rslts:
        wb.write('{}\n'.format(line))

