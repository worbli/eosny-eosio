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

def getKeys(acct_info):
    permissions = acct_info['permissions']
    active_key = 'None'
    owner_key = 'None'
    for p in permissions:
        if p['perm_name'] == 'active':
            keys = p['required_auth']['keys']
            if len(keys) == 1:
                active_key = keys[0]['key']
            else:
                active_key = 'count {0}'.format(len(keys))
        if p['perm_name'] == 'owner':
            keys = p['required_auth']['keys']
            if len(keys) == 1:
                owner_key = keys[0]['key']
            else:
                owner_key = 'count {0}'.format(len(keys))
    return(owner_key, active_key)

def check_account(name, get_staked=False) :
    acct_info = ce.get_account(name)
    created_time = dt.datetime.strptime(acct_info['created'], '%Y-%m-%dT%H:%M:%S.%f')
    if created_time < acct_age :
        # get liquid balance
        try :
            liquid = float(acct_info['core_liquid_balance'].split()[0])
        except KeyError :
            liquid = 0
        # cpu/net balance
        try :
            cpu = float(acct_info['self_delegated_bandwidth']['cpu_weight'].split()[0])
            net = float(acct_info['self_delegated_bandwidth']['net_weight'].split()[0])
        except TypeError:
            cpu = 0
            net = 0
        # get refund amount
        try :
            refund_cpu = float(acct_info["refund_request"]['cpu_amount'].split()[0])
            refund_net = float(acct_info["refund_request"]['net_amount'].split()[0])
        except TypeError :
            refund_cpu = 0.0
            refund_net = 0.0
        staked_total = cpu + net
        refund_total = refund_cpu + refund_net
        keys = getKeys(acct_info)
        if get_staked :
            rslts.append('{0},{1},{4},{5},{2:.4f},{3:.4f}'.format(created_time, name, liquid + staked_total + refund_total, staked_total, keys[0], keys[1]))
        else :
            rslts.append('{0},{1},{3},{4},{2:.4f}'.format(created_time, name, liquid + staked_total + refund_total, keys[0], keys[1]))

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
        t = Thread(target=check_account, args=(name,args.staked))
        t.start()
        threads.append(t)
    for thd in threads :
        thd.join()
    cnt += num_thds
    if cnt % 10240 == 0 :
        print('{} Processed {} out of {}'.format(dt.datetime.now(), cnt, total))

print('Rslts cnt: {0}'.format(len(rslts)))
with open(args.out_file,'w') as wb:
    if args.staked :
        wb.write('creation_time,account_name,owner_key,active_key,total_eos,total_staked\n')
    else :
        wb.write('creation_time,account_name,owner_key,active_key,total_eos\n')
    for line in rslts:
        wb.write('{}\n'.format(line))
