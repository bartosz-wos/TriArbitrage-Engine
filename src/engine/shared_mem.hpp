#pragma once

#include <atomic>
#include <cstdint>

constexpr int MAX_NODES = 500;
constexpr int MAX_EDGES = 5000;

struct Edge{
	int u,v;
	double log_w;
};

struct alignas(64) ShmStruct{
	std::atomic<uint64_t> seq;
	int64_t last_upd_edge_id;
	int64_t num_nodes;
	int64_t num_edges;
	Edge edges[MAX_EDGES];
};
