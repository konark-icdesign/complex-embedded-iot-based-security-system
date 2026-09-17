PYTHON ?= python
CXX ?= g++
CXXFLAGS = -std=c++17 -Wall -Wextra -Werror -Wpedantic
CC ?= cc
CFLAGS = -std=c11 -Wall -Wextra -Werror -Wpedantic
.PHONY: simulate test embedded sanitize
simulate:
	$(PYTHON) run_simulation.py --seeds 10
test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v
embedded:
	$(CXX) $(CXXFLAGS) tests/embedded_test.cpp -o embedded-tests
	./embedded-tests
sanitize:
	$(CXX) $(CXXFLAGS) -fsanitize=address,undefined -fno-omit-frame-pointer -g tests/embedded_test.cpp -o embedded-tests-sanitized
	./embedded-tests-sanitized

.PHONY: incident-build c-sanitize incidents
incident-build:
	mkdir -p build
	$(CXX) $(CXXFLAGS) tests/board_stream.cpp -o build/board-stream
	$(CC) $(CFLAGS) -O2 -fPIC -shared csrc/detection.c -lm -o build/libdetection.so

c-sanitize:
	mkdir -p build
	$(CC) $(CFLAGS) -fsanitize=address,undefined -fno-omit-frame-pointer -g tests/c_core_test.c csrc/detection.c -lm -o build/c-core-test
	./build/c-core-test

incidents: incident-build
	$(PYTHON) run_incidents.py --c-library build/libdetection.so
