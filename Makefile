CXX ?= g++
CXXFLAGS ?= -std=c++20 -O3 -march=native -Wall -Wextra -pedantic
LDFLAGS ?=

.PHONY: all clean test

all: build/organic_v0

build/organic_v0: native/organic_v0.cpp
	@mkdir -p build
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDFLAGS)

test: build/organic_v0
	./build/organic_v0 --phase self-test

clean:
	rm -rf build
