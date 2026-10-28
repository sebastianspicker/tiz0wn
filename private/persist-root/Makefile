PYTHON ?= python3

.PHONY: help lint test offline busybox repro ledger-verify ledger-chain check all

help:
	@printf '%s\n' \
	  'make test           - offline unit/contract suite (no TV, no network)' \
	  'make offline        - end-to-end repro through the pinned sink (loopback only)' \
	  'make busybox        - apply/revert under busybox ash in a container' \
	  'make lint           - shellcheck + python compile' \
	  'make ledger-verify  - verify ledger chain + out-of-band anchor' \
	  'make ledger-chain   - verify the chain only (anchor may be stale)' \
	  'make check          - lint + test + offline + ledger-verify'

lint:
	# repro/mount.smb.sh is the unmodified vendor fixture; only our script is linted.
	# SC2115: ROOT is deliberately empty on the TV (${ROOT:?} aborted the revert
	# there), so the explicit slash join is required. SC2012: `ls -lZ` is the
	# portable way to read a SMACK label.
	shellcheck -e SC2115,SC2012 root_setup.sh
	$(PYTHON) -m py_compile \
	  ledger.py payload.py prelude.py sha512crypt.py serve.py \
	  test_persist_root.py test_sha512crypt.py test_serve.py test_ledger.py \
	  test_regressions.py repro/run_offline.py repro/busybox_check.py

test:
	$(PYTHON) -m unittest discover -s . -p 'test_*.py' -v

offline:
	$(PYTHON) repro/run_offline.py

busybox:
	$(PYTHON) repro/busybox_check.py

repro: offline

ledger-verify:
	$(PYTHON) ledger.py --verify

ledger-chain:
	$(PYTHON) ledger.py --verify-chain

check: lint test offline busybox ledger-chain
	@printf '\nall persist-root checks passed; no TV was contacted\n'

all: check
