"""Static honesty checks for the ModelRelay dashboard score rendering."""
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
HTML_PATH = REPO / "nexus_os" / "monitoring" / "dashboard.html"
JS_PATH = REPO / "nexus_os" / "monitoring" / "dashboard.js"


def _html() -> str:
    return HTML_PATH.read_text(encoding="utf-8")


def _js() -> str:
    return JS_PATH.read_text(encoding="utf-8")


def test_unscored_models_are_not_rendered_as_zero_percent() -> None:
    js = _js()

    assert "function benchmarkValue(model, dimension)" in js
    assert "UNSCORED" in js
    assert "No benchmark evidence" in js
    assert "((intell || 0) * 100)" not in js
    assert "benchmarks?.catalogue_score" not in js
    assert ">CAT</span>" not in js
    assert "CATALOGUE ONLY" in js
    assert "formatBenchmark(model, 'quality')" in js


def test_only_evidence_backed_scores_drive_quality_ranking_and_matrix() -> None:
    js = _js()

    assert "hasBenchmarkEvidence(model)" in js
    assert ".filter(hasBenchmarkEvidence)" in js
    assert "benchmarkValue(model, 'quality')" in js
    assert "policy_prior_is_not_benchmark" in js


def test_evidence_column_exposes_metadata_gaps_without_fabricating_sources() -> None:
    html = _html()
    js = _js()

    assert "<th>Evidence</th>" in html
    assert "Catalogue only" in js
    assert "benchmarks.sources" in js
    assert "benchmarks.as_of" in js
    assert 'colspan="10"' in js


def test_dashboard_defaults_to_canonical_routes_but_keeps_provider_offers_available() -> None:
    html = _html()
    js = _js()

    assert '<span class="filter-chip" id="chipOnline"' not in html
    assert '<select id="presentationMode"' in html
    assert '<option value="canonical">Canonical CLI routes</option>' in html
    assert '<option value="offers">Provider offers</option>' in html
    assert '<option value="unverified">Unverified / not probed</option>' in html
    assert '<option value="healthy">Observed healthy</option>' in html
    assert 'id="tableSummary"' in html
    assert 'function presentationModels()' in js
    assert "return selectedPresentationMode() === 'offers' ? allModels : canonicalCliRoutes()" in js
    assert "Provider offers" in html


def test_route_posture_keeps_primary_health_and_quality_claims_separate() -> None:
    html = _html()
    js = _js()

    assert "Primary lock" in html
    assert "Manifest live route" in html
    assert "Evidence quality leader" in html
    assert 'id="primaryRoute"' in html
    assert 'id="freshLiveLead"' in html
    assert 'id="evidenceQualityLead"' in html
    assert "function primaryLockedRoute()" in js
    assert "function freshLiveLead()" in js
    assert "function evidenceQualityLeader()" in js
    assert "Quality does not prove availability." in js
    assert "not a health or fallback claim." in js
    assert "function topCliRoute()" not in js
    assert "Route lead" not in js


def test_manifest_route_is_named_with_its_selection_basis_not_a_universal_best() -> None:
    html = _html()
    js = _js()

    assert "fetch('/api/client-manifest')" in js
    assert "function manifestRecommendationCard()" in js
    assert "Client-manifest recommendation:" in js
    assert "not benchmark proof." in js
    assert "Health-first route order" in html
    assert "Best Available" not in html


def test_dashboard_consumes_same_origin_canonical_projection() -> None:
    html = _html()
    js = _js()

    assert '<script src="/dashboard.js"></script>' in html
    assert "fetch('/api/model-cards')" in js
    assert "projection.summary" in js
    assert "CLI-visible Model IDs" in html
    assert "Health Unverified" in html
    assert "Evidence-backed" in html
    assert "Observed Healthy" in html


def test_optional_dashboard_elements_cannot_discard_a_valid_projection() -> None:
    """A partial operator embed must retain successfully fetched model cards."""
    js = _js()

    assert "setText('lastUpdate', new Date().toLocaleTimeString())" in js
    assert "document.getElementById('lastUpdate').textContent" not in js
    assert "if (!plot || !tooltip) return" in js
    assert "if (!tbody) return" in js
    assert "if (!select) return" in js


def test_task_conditioned_benchmark_columns_are_independent() -> None:
    html = _html()
    js = _js()

    for heading in ("Quality", "Code", "SWE", "Evidence"):
        assert f">{heading}<" in html
    assert "reasoning" in js
    assert "speed" in js
    assert "cost_efficiency" in js


def test_latency_kpi_filters_the_same_canonical_routes_it_measures() -> None:
    js = _js()

    assert ".filter((model) => model.health?.state === 'healthy')" in js
    assert ".filter((_, index) => allModels[index]?.health?.state === 'healthy')" not in js


def test_matrix_deduplicates_provider_aliases_and_explains_runtime_evidence_state() -> None:
    html = _html()
    js = _js()

    assert "const displayModels = canonicalCliRoutes()" in js
    assert "One dot per canonical CLI route" in html
    assert "function runtimeRefreshSummary()" in js
    assert "Runtime evidence refresh failed" in js
    assert 'id="evidenceRuntimeStatus"' in html


def test_health_pill_shows_observation_state_and_latest_http_evidence() -> None:
    js = _js()

    assert "OBSERVED HEALTHY" in js
    assert "UNAVAILABLE" in js
    assert "health.latest_http_code" in js
    assert "HTTP ${health.latest_http_code}" in js
