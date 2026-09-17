PYTHON ?= python
CXX ?= g++
CXXFLAGS = -std=c++17 -Wall -Wextra -Werror -Wpedantic
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
