import pytest
def test_gmr_import():
    from nexus_os.monitoring.gmr import GMREngine
    assert GMREngine is not None
