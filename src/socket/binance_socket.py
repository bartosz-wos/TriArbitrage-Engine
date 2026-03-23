import asyncio
import websockets
import json
import math
import posix_ipc
import mmap
import struct

SHM_NAME = '/triarb_shm_v4'
MAX_NODES = 500
MAX_EDGES = 5000
FEE = 0.001

OFFSET_SEQ = 0
OFFSET_LAST_EDGE = 8
OFFSET_NUM_NODES = 16
OFFSET_NUM_EDGES = 24
OFFSET_EDGES_ARRAY = 32
EDGE_STRUCT_SIZE = 16

node_to_id = {}
edge_to_id = {}
crypto = ['USDT', 'USDC', 'ETH', 'BTC', 'SOL', 'BNB']

def setup_shm():
    shm_size = OFFSET_EDGES_ARRAY + MAX_EDGES * EDGE_STRUCT_SIZE
    try:
        shm = posix_ipc.SharedMemory(SHM_NAME, flags=posix_ipc.O_CREAT | posix_ipc.O_EXCL, size=shm_size)
        is_new = True
    except posix_ipc.ExistentialError:
        shm = posix_ipc.SharedMemory(SHM_NAME)
        is_new = False

    mm = mmap.mmap(shm.fd, shm.size)
    if is_new:
        struct.pack_into('<Q q q q', mm, 0, 0, 0, 0, 0)
    else:
        print('connected to existing ram')
    return mm

def get_id(x):
    if x not in node_to_id:
        if len(node_to_id) >= MAX_NODES: return None
        node_to_id[x] = len(node_to_id)
    return node_to_id[x]

def split_pair(x):
    for c in crypto:
        if x.endswith(c):
            return x[:-len(c)], c
    return None, None

async def binance_client():
    mm = setup_shm()
    url = 'wss://stream.binance.com:9443/ws/!miniTicker@arr'
    f_log = open("python_dump.csv", "w")

    while True:
        print('connecting to websocket')
        try:
            async with websockets.connect(url) as ws:
                seq = 0
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)

                    for ticker in data:
                        symbol = ticker['s']
                        price = float(ticker['c'])
                        if price <= 0: continue
                        
                        base, quote = split_pair(symbol)
                        if not base: continue
                        
                        u = get_id(base)
                        v = get_id(quote)
                        if u is None or v is None: continue

                        edge_id = edge_to_id.get(symbol)
                        if edge_id is None:
                            if len(edge_to_id) >= MAX_EDGES: continue
                            edge_id = len(edge_to_id)
                            edge_to_id[symbol] = edge_id

                        log_w = -math.log(price * (1.0 - FEE))

                        seq += 1
                        struct.pack_into('<Q', mm, OFFSET_SEQ, seq)

                        edge_off = OFFSET_EDGES_ARRAY + edge_id * EDGE_STRUCT_SIZE
                        struct.pack_into('<i i d', mm, edge_off, u, v, log_w)
                        struct.pack_into('<q', mm, OFFSET_LAST_EDGE, edge_id)
                        struct.pack_into('<q q', mm, OFFSET_NUM_NODES, len(node_to_id), len(edge_to_id))

                        seq += 1
                        struct.pack_into('<Q', mm, OFFSET_SEQ, seq)

                        f_log.write(f"{seq},{u},{v},{log_w:.8f}\n")

                        if seq % 2000 == 0:
                            f_log.flush()
                            print(f'processed {seq//2}, edge {u} -> {v}, weight {log_w}')

        except Exception as e:
            print(f"lost connection: {e}")
            await asyncio.sleep(2)

if __name__ == '__main__':
    asyncio.run(binance_client())
