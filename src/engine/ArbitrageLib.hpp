#pragma once

#include <iostream>
#include <vector>
#include <cmath>
#include <iomanip>

#include "shared_mem.hpp"

constexpr double inf = 1e9;

struct ArbTriplet{
	int u;
	int v;
	int c;
	bool found;
	double profit;
};

class ArbitrageClass{
private:
	int n;
	double w[MAX_NODES][MAX_NODES];

public:
	ArbitrageClass(int n_ = MAX_NODES) : n(n_){
		for(int i = 0; i < MAX_NODES; ++i)
			for(int j = 0; j < MAX_NODES; ++j)
				w[i][j] = inf;
	}

	void set_n(int n_){
		n = n;
	}

	ArbTriplet update_and_check(int u, int v, double log_w){
		w[u][v]=log_w;
		for(int k = 0; k < n; ++k)
			if(w[v][k] != inf && w[k][u] != inf){
				double weight = log_w + w[v][k] + w[k][u];

				if(weight < 0.0){
					double mult = std::exp(-weight);
					double profit = (mult - 1.0) * 100.0;
					return {u, v, k, true, profit};
				}
			}
		return {-1, -1, -1, false, 0.0};
	}
};
