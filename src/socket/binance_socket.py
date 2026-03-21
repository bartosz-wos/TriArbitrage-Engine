import asyncio
import websockets
import json
import math
import posix_ipc
import mmap
import struct
import time

SHM_NAME = '/triarb_shm'
MAX_NODES = 500
MAX_EDGES = 5000
FEE = 0.001

OFFSET_SEQ = 0
OFFSET_LAST_EDGE = 8
OFFSET_NUM_NODES = 12
OFFSET_NUM_EDGES = 16
OFFSET_EDGES_ARRAY = 24
EDGE_STRUCT_SIZE = 16

node_to_id = {}
edge_to_id = {}
crypto = ['USDT', 'USDC', 'ETH', 'BTC', 'SOL', 'BNB']

def get_id(x):
    if x not in node_to_id:
        if len(node_to_id) >= MAX_NODES:
            return None
        node_to_id[x] = len(node_to_id)
    return node_to_id[x]

def split_pair(x):
    for c in crypto:
        if x.endswith(c):
            base = x[:-len(c)]
            return base, c
    return None, None

def setup_shm():
    shm_size = OFFSET_EDGES_ARRAY + MAX_EDGES * EDGE_STRUCT_SIZE

    try:
        shm = posix_ipc.SharedMemory(SHM_NAME, flags=posix_ipc.O_CREAT, size=shm_size)
    except posix_ipc.ExistentialError:
        shm = posix_ipc.SharedMemory(SHM_NAME)

    mm = mmap.mmap(shm.fd, shm.size)
    struct.pack_into('Q i i i 4x', mm, 0, 0, -1, 0, 0)
    return mm

async def binance_client():
    mm = setup_shm()
    url = 'wss://stream.binance.com:9443/ws/!miniTicker@arr'
    print('Connecting to binance websocket')

    async with websockets.connect(url) as ws:
        seq = 0

        while True:
            msg = await ws.recv()
            data = json.loads(msg)

            for ticker in data:
                symbol = ticker['s']
                price = float(ticker['c'])

                if price <= 0:
                    continue

                base, quote = split_pair(symbol)

                if not base:
                    continue

                u = get_id(base)
                v = get_id(quote)

                if u is None or v is None:
                    continue

                edge_id = 0
                if symbol not in edge_to_id:
                    if len(edge_to_id) >= MAX_EDGES:
                        continue
                    edge_id = len(edge_to_id)
                    edge_to_id[symbol] = len(edge_to_id)
                else:
                    edge_id = edge_to_id[symbol]

                log_w = -math.log(price * (1.0 - FEE))
                seq += 1

                struct.pack_into('Q', mm, OFFSET_SEQ, seq)
                
                edge_off = OFFSET_EDGES_ARRAY + edge_id * EDGE_STRUCT_SIZE
                struct.pack_into('i i d', mm, edge_off, u, v, log_w)

                struct.pack_into('i i i', mm, OFFSET_LAST_EDGE, edge_id, len(node_to_id), len(edge_to_id))

                seq += 1
                struct.pack_into('Q', mm, OFFSET_SEQ, seq)

                if seq % 2000 == 0:
                    print(f'processed {seq//2} updates')

if __name__ == '__main__':
    asyncio.run(binance_client())
