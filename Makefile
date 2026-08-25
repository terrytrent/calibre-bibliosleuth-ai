PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
CALIBRE_CUSTOMIZE ?= /Applications/calibre.app/Contents/MacOS/calibre-customize
PLUGIN_ZIP := dist/BiblioSleuth-AI.zip
PLUGIN_CHECKSUM := $(PLUGIN_ZIP).sha256

.PHONY: help test build verify install clean release

help:
	@echo "BiblioSleuth AI development commands"
	@echo "  make test     Run the automated test suite"
	@echo "  make build    Build the deterministic plugin ZIP and checksum"
	@echo "  make verify   Build and validate the ZIP contents and checksum"
	@echo "  make install  Build and install the plugin into Calibre"
	@echo "  make clean    Remove generated packages and Python test caches"
	@echo "  make release  Run tests and all package verification"

test:
	$(PYTHON) -m pip install --disable-pip-version-check --require-hashes -r requirements-runtime.txt
	$(PYTHON) -m pytest -q

build:
	$(PYTHON) scripts/build_plugin.py

verify: build
	unzip -t $(PLUGIN_ZIP)
	cd dist && shasum -a 256 -c BiblioSleuth-AI.zip.sha256

install: build
	"$(CALIBRE_CUSTOMIZE)" -a "$(abspath $(PLUGIN_ZIP))"

clean:
	rm -rf dist build .pytest_cache tests/__pycache__ src/calibre_ai_plugin/__pycache__

release: test verify
