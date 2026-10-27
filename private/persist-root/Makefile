PYTHON ?= python3

.PHONY: help lint test offline repro ledger-verify check all

help:
	@printf '%s\n' \
	  'make test           - offline unit/contract suite (no TV, no network)' \
	  'make offline        - end-to-end repro through the pinned sink (loopback only)' \
	  'make lint           - shellcheck + python compile' \
	  'make ledger-verify  - verify the hash-chained work ledger' \
	  'make check          - lint + test + offline + ledger-verify'

lint:
	# repro/mount.smb.sh is the unmodified vendor fixture; only our script is linted
	shellcheck root_setup.sh
	$(PYTHON) -m py_compile \
	  ledger.py payload.py prelude.py sha512crypt.py serve.py \
	  test_persist_root.py test_sha512crypt.py test_serve.py repro/run_offline.py

test:
	$(PYTHON) -m unittest discover -s . -p 'test_*.py' -v

offline:
	$(PYTHON) repro/run_offline.py

repro: offline

ledger-verify:
	$(PYTHON) ledger.py --verify

check: lint test offline ledger-verify
	@printf '\nall persist-root checks passed; no TV was contacted\n'

all: check
