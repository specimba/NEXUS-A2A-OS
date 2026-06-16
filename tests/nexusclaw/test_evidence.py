from nexus_os.nexusclaw.evidence import EvidenceDisposition, default_nexusclaw_evidence_matrix


def test_default_evidence_matrix_contains_required_dispositions():
    matrix = default_nexusclaw_evidence_matrix()
    dispositions = {claim.disposition for claim in matrix}

    assert EvidenceDisposition.VERIFIED in dispositions
    assert EvidenceDisposition.REFRAMED in dispositions
    assert EvidenceDisposition.SUSPECT in dispositions
    assert EvidenceDisposition.REJECTED in dispositions
    assert EvidenceDisposition.DEFERRED in dispositions


def test_evidence_matrix_rejects_unverified_gross_remediation_claims():
    rejected = [
        claim
        for claim in default_nexusclaw_evidence_matrix()
        if claim.disposition is EvidenceDisposition.REJECTED
    ]

    assert any("self-remediation" in claim.claim for claim in rejected)


def test_evidence_matrix_is_secret_free():
    joined = "\n".join(str(claim.to_dict()) for claim in default_nexusclaw_evidence_matrix()).lower()

    assert "token=" not in joined
    assert "api_key" not in joined
    assert "bearer " not in joined


def test_evidence_matrix_preserves_native_nexusclaw_pivot():
    matrix = default_nexusclaw_evidence_matrix()

    assert any(
        claim.artifact == "archivist/NEXUS-CLAW-01.txt"
        and claim.disposition is EvidenceDisposition.REFRAMED
        and "native NEXUSCLAW" in claim.rationale
        for claim in matrix
    )


def test_evidence_matrix_rejects_credential_artifact_copying():
    matrix = default_nexusclaw_evidence_matrix()

    assert any(
        claim.artifact == "Downloads credential-shaped artifacts"
        and claim.disposition is EvidenceDisposition.REJECTED
        and "commits" in claim.rationale
        for claim in matrix
    )
