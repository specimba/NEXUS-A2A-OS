import pytest
def test_gmr_import():
    from nexus_os.gmr.rotator import GeniusModelRotator
    assert GeniusModelRotator is not None
