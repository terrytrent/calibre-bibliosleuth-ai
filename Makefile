PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
CALIBRE_CUSTOMIZE ?= /Applications/calibre.app/Contents/MacOS/calibre-customize
PLUGIN_ZIP := dist/BiblioSleuth-AI.zip
PLUGIN_CHECKSUM := $(PLUGIN_ZIP).sha256

.PHONY: help test test-debug test-searxng test-searxng-debug test-ollama test-ollama-debug test-openai-compatible test-openai-compatible-debug build verify install clean release

help:
	@echo "BiblioSleuth AI development commands"
	@echo "  make test     Run the automated test suite"
	@echo "  make test-debug  Run the automated suite with verbose live output"
	@echo "  make test-searxng  Run the disposable real-SearXNG integration test (Docker)"
	@echo "  make test-searxng-debug  Show the SearXNG container, results, and teardown"
	@echo "  make test-ollama  Test a disposable real Ollama service and tiny model"
	@echo "  make test-ollama-debug  Show Ollama lifecycle, response, usage, and teardown"
	@echo "  make test-openai-compatible  Test a disposable llama.cpp local server"
	@echo "  make test-openai-compatible-debug  Show local-server lifecycle and results"
	@echo "  make build    Build the deterministic plugin ZIP and checksum"
	@echo "  make verify   Build and validate the ZIP contents and checksum"
	@echo "  make install  Build and install the plugin into Calibre"
	@echo "  make clean    Remove generated packages and Python test caches"
	@echo "  make release  Run tests and all package verification"

test:
	$(PYTHON) -m pip install --disable-pip-version-check --require-hashes -r requirements-runtime.txt
	$(PYTHON) -m pytest -q

test-debug:
	$(PYTHON) -m pip install --disable-pip-version-check --require-hashes -r requirements-runtime.txt
	$(PYTHON) -m pytest -vv -s

test-searxng:
	PYTHON=$(PYTHON) bash scripts/test_searxng_integration.sh

test-searxng-debug:
	PYTHON=$(PYTHON) BIBLIOSLEUTH_TEST_DEBUG=1 bash scripts/test_searxng_integration.sh

test-ollama:
	PYTHON=$(PYTHON) bash scripts/test_local_model_integration.sh ollama

test-ollama-debug:
	PYTHON=$(PYTHON) BIBLIOSLEUTH_TEST_DEBUG=1 bash scripts/test_local_model_integration.sh ollama

test-openai-compatible:
	PYTHON=$(PYTHON) bash scripts/test_local_model_integration.sh openai-compatible

test-openai-compatible-debug:
	PYTHON=$(PYTHON) BIBLIOSLEUTH_TEST_DEBUG=1 bash scripts/test_local_model_integration.sh openai-compatible

build:
	$(PYTHON) scripts/build_plugin.py

verify: build
	unzip -t $(PLUGIN_ZIP)
	cd dist && shasum -a 256 -c BiblioSleuth-AI.zip.sha256

install: build
	"$(CALIBRE_CUSTOMIZE)" -a "$(abspath $(PLUGIN_ZIP))"

clean:
	rm -rf dist build .pytest_cache tests/__pycache__ src/bibliosleuth_ai/__pycache__

release: test verify
