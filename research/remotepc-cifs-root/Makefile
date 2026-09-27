PYTHON ?= python3
HOST := host/one_shot_proof.py
TEST := host/test_one_shot_proof.py

.PHONY: dry-run syntax test lab-test help

help:
	@printf '%s\n' \
	  'make dry-run  - pinned local rootfs audit; no config or network' \
	  'make test     - offline unit/contract tests' \
	  'make lab-test - Docker RDP+SMB test on 127.0.0.1 only'

dry-run:
	$(PYTHON) $(HOST)

syntax:
	$(PYTHON) -m py_compile $(HOST) $(TEST)
	$(PYTHON) -m py_compile lab/client.py lab/server.py
	sh -n lab/entrypoint.sh lab/client.sh lab/healthcheck.sh lab/startwm.sh

test: syntax
	$(PYTHON) -m unittest discover -s host -p 'test_one_shot_proof.py' -v

lab-test: test
	$(PYTHON) $(HOST) --local-selftest
