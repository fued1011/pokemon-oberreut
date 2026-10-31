# Keep ENGINE, UPSTREAM and EXPORT outside this public source repository.
PYTHON ?= python3
ENGINE ?=
UPSTREAM ?=
EXPORT ?=
JOBS ?= 4
.PHONY: verify install regenerate test build export
verify:
	$(PYTHON) verify_distribution.py
install: verify
	@test -n "$(ENGINE)" || (echo 'Set ENGINE to a new private directory'; exit 1)
	PHASE1_PYTHON="$(PYTHON)" bash install.sh "$(ENGINE)" $(if $(UPSTREAM),"$(UPSTREAM)")
regenerate:
	@test -n "$(ENGINE)"
	PHASE1_PYTHON="$(PYTHON)" bash scripts/regenerate.sh "$(ENGINE)"
test:
	@test -n "$(ENGINE)"
	cd "$(ENGINE)" && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 "$(PYTHON)" -m pytest tests_phase0 -q
build:
	@test -n "$(ENGINE)"
	$(MAKE) -C "$(ENGINE)" -j$(JOBS)
export:
	@test -n "$(ENGINE)" && test -n "$(UPSTREAM)" && test -n "$(EXPORT)"
	$(PYTHON) scripts/export_overlay.py "$(ENGINE)" "$(UPSTREAM)" "$(EXPORT)"
