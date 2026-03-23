#include <iostream>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <atomic>

#include "shared_mem.hpp"
#include "ArbitrageLib.hpp"

int main(){
    std::cout << "init...\n";

    int fd = shm_open("/triarb_shm_v4", O_RDONLY, 0666);
    if(fd == -1){
        std::cerr << "failed to open shm\n";
        return 1;
    }

    void* ptr = mmap(0, sizeof(ShmStruct), PROT_READ, MAP_SHARED, fd, 0);
    if(ptr == MAP_FAILED){
        std::cerr << "mmap failed\n";
        return 1;
    }

    ShmStruct* shm = static_cast<ShmStruct*>(ptr);
    uint64_t seq = 0;
    uint64_t cnt = 0;
    uint64_t missed = 0;

    ArbitrageClass det(MAX_NODES);

    while(1){
        uint64_t seq1 = shm->seq.load(std::memory_order_acquire);

        if(seq1 == 0 || (seq1 & 1) || seq1 == seq)
            continue;

        int64_t last_id = std::atomic_ref<int64_t>(shm->last_upd_edge_id).load(std::memory_order_relaxed);

        if(last_id < 0 || last_id >= MAX_EDGES)
            continue;

        int u = std::atomic_ref<int>(shm->edges[last_id].u).load(std::memory_order_relaxed);
        int v = std::atomic_ref<int>(shm->edges[last_id].v).load(std::memory_order_relaxed);
        double w = std::atomic_ref<double>(shm->edges[last_id].log_w).load(std::memory_order_relaxed);

        std::atomic_thread_fence(std::memory_order_acquire);
        uint64_t seq2 = shm->seq.load(std::memory_order_acquire);

        if(seq1 != seq2)
            continue;

        if(seq > 0 && seq1 < seq){
            std::cout << "python restart, old, new" << seq << " -> " << seq1 << "\n";
            cnt = missed = 0;
        }else if(seq > 0 && seq1 > seq + 2)
            missed += (seq1 - seq - 2) / 2;

        seq = seq1;
        ++cnt;

	int num = std::atomic_ref<int64_t>(shm->num_nodes).load(std::memory_order_relaxed);
	det.set_n(num);

	ArbTriplet arb = det.update_and_check(u, v, w);

	if(arb.found){
		std::cout << "cycle " << arb.v << ' ' << arb.c << ' ' << arb.u << std::endl;
		std::cout << "profit " << std::fixed << std::setprecision(4) << arb.profit << std::endl;
	}

        if(cnt % 1000 == 0){
            std::cout << "read " << cnt << " updates, missed: " << missed << "\n";
        }
    }
    return 0;
}
