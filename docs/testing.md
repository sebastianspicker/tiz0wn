publish

# Testing

The five `exploits/tiz0wn-root/tests/test_*.py` files are public synthetic
contracts. They create their own temporary files and block images. The only checked-in
fixture is the public 776-byte vendor carrier, used to keep the exact-carrier
patch contract; there is no firmware image. They do not contact a TV or require
`evidence/`, `runs/`, local configuration, or a real device. The CI job runs them
with Python 3.13:

```sh
python3 -m unittest discover -s exploits/tiz0wn-root/tests -p 'test_*.py' -v
```

The tests run with Python's standard library and local shell tools. Cases that
rehearse BusyBox in Docker use the already-local `python:3.11-alpine` image,
`--pull never`, and `--network none`. They skip when Docker or that image is
absent. They are not a substitute for the separate block-file loopbacks or a
device-specific validation. To run the broader offline checks locally, use:

```sh
make -C exploits/tiz0wn-root verify
```

That target also runs shell/Python lint, the synthetic security controls, and
the carrier and account loopbacks. Docker is optional for the loopbacks. CI
runs the Python suite separately from the security controls; the general lint
step in `.github/workflows/security.yml` retains its existing event condition.

`evidence/`, `runs/`, the ledger, and local handoff notes remain ignored. No
device identifiers, private values, or generated image files are published as
test fixtures.
