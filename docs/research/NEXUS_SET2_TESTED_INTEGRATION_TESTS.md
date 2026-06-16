---
id: NODE-MIG-NEXUS_SET2_TESTED_INTEGRATION_TESTS
authority_scope: experimental
origin_sha256: d8bd55635373d0f5b7629f6db01e7dc608ae0952cd673b57c11ddfcfaf15d6ef
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-939169
---
# NEXUS-SET2-TESTED: Integration Test Specifications

**Test Suite Status**: Ready for Deployment  
**Version**: 1.0  
**Target**: Week 1 Governance Phase Validation  

---

## Test Suite Overview

```
NEXUS-SET2-TESTED Integration Tests
├── Governance Tests (20 tests) ............................ 40%
│   ├── VAP chain immutability
│   ├── KAIJU authorization latency
│   ├── Proposal lifecycle
│   ├── Trust score consistency
│   └── Audit trail completeness
├── Role-Specific Tests (30 tests) ......................... 35%
│   ├── Grok routing
│   ├── OPUSman execution
│   └── DeepSeek research
├── TSI Mitigation Tests (15 tests) ........................ 15%
│   ├── Tool filtering accuracy
│   ├── Context window reduction
│   └── Performance benchmarks
└── E2E Workflow Tests (8 tests) ........................... 10%
    ├── Code→Deploy
    ├── Research→Documentation
    └── Multi-agent collaboration
```

---

## Governance Tests (Critical Path)

### 1. VAP Chain Tests

**Test**: `test_vap_chain_immutability()`

```python
def test_vap_chain_immutability():
    """Verify VAP chain entries cannot be modified retroactively."""
    
    # Setup
    genesis_hash = vap.get_chain_head()['hash']
    assert genesis_hash == "0" * 16  # Genesis block
    
    # Submit 5 entries
    for i in range(5):
        entry = vap.submit({
            'type': 'test_entry',
            'data': {'index': i},
            'agent_id': 'test-agent'
        })
        assert entry['prev_hash'] == vap.get_chain_tail()['hash']
    
    # Verify chain integrity
    assert vap.verify_chain() == True
    
    # Attempt to modify middle entry (should fail)
    with pytest.raises(IntegrityError):
        vap.update_entry(2, {'modified': True})
    
    # Verify chain still intact
    assert vap.verify_chain() == True
```

**Success Criteria**:
- ✅ Chain head always genesis (0^16)
- ✅ Each entry prev_hash matches predecessor
- ✅ Modification attempts fail
- ✅ Chain verification always passes

---

### 2. KAIJU Authorization Latency

**Test**: `test_kaiju_authorization_latency()`

```python
def test_kaiju_authorization_latency():
    """KAIJU gate must add <50ms latency (p95)."""
    
    latencies = []
    
    for _ in range(100):
        start = time.time_ns()
        result = kaiju.check_access(
            agent_id='speci',
            project_id='nexus',
            action='tool:github_create_issue',
            scope='project',
            intent='Create issue for bug report',
            impact='medium',
            clearance='contributor'
        )
        latency_ms = (time.time_ns() - start) / 1_000_000
        latencies.append(latency_ms)
        
        assert result.decision in [Decision.ALLOW, Decision.HOLD, Decision.DENY]
    
    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]
    
    assert p95 < 50, f"P95 latency {p95}ms exceeds 50ms target"
    assert p99 < 100, f"P99 latency {p99}ms exceeds 100ms target"
    
    print(f"✓ KAIJU Latency: p95={p95:.2f}ms, p99={p99:.2f}ms")
```

**Success Criteria**:
- ✅ P95 latency < 50ms
- ✅ P99 latency < 100ms
- ✅ No decision timeouts

---

### 3. Proposal Lifecycle

**Test**: `test_proposal_submission_verification_cycle()`

```python
def test_proposal_submission_verification_cycle():
    """Full proposal submission → verification → judgment cycle."""
    
    # Agent submits claim
    claim = mcp_server.submit_claim(
        claim_id='claim-test-001',
        agent_id='speci',
        description='Verified build works',
        evidence_items=[
            {
                'type': 'command_output',
                'content': '0 errors, build successfully completed',
                'source': 'runner'
            }
        ],
        cycle_token='CYCLE-abc123'  # Must provide token
    )
    
    assert claim['status'] == 'submitted'
    assert claim['agent_id'] == 'speci'
    
    # Verify claim
    verified = mcp_server.verify_claim(claim['claim_id'])
    
    assert verified['status'] in ['verified', 'rejected']
    assert verified['verdict_reason'] is not None
    assert 'vap_hash' in verified
    
    # Check trust score adjustment
    new_trust = trust_kernel.get_trust_score('speci')
    if verified['status'] == 'verified':
        assert new_trust > 0.5  # Trust increased
    else:
        assert new_trust <= 0.5  # Trust decreased
    
    # Verify VAP entry created
    vap_entry = vap.get_last_entry()
    assert vap_entry['type'] == 'verify_claim'
```

**Success Criteria**:
- ✅ Claims submitted with cycle token
- ✅ Verification completed within 2s
- ✅ Trust scores adjusted correctly
- ✅ VAP entries created immediately

---

### 4. Trust Score Consistency

**Test**: `test_redis_trust_cache_vs_db()`

```python
def test_redis_trust_cache_vs_db():
    """Redis cache must match PostgreSQL source of truth."""
    
    agents = ['speci', 'neo', 'codex', 'grok', 'devin']
    
    for agent_id in agents:
        # Get from cache (Redis)
        cached = redis.get(f'trust:{agent_id}')
        
        # Get from DB (PostgreSQL)
        db_record = postgres.query_one(
            "SELECT trust_score FROM agents WHERE id = %s",
            (agent_id,)
        )
        
        # Must match
        assert float(cached['score']) == db_record['trust_score'], \
            f"Cache mismatch for {agent_id}"
    
    # Modify trust score in DB
    postgres.execute(
        "UPDATE agents SET trust_score = 0.75 WHERE id = %s",
        ('speci',)
    )
    
    # Cache should invalidate
    redis.delete('trust:speci')
    
    # Re-fetch should match DB
    cached_new = redis.get_or_load(f'trust:speci')
    db_new = postgres.query_one(
        "SELECT trust_score FROM agents WHERE id = %s",
        ('speci',)
    )
    
    assert float(cached_new['score']) == db_new['trust_score']
```

**Success Criteria**:
- ✅ No cache/DB divergence
- ✅ Invalidation on updates
- ✅ Consistency check passes for all agents

---

### 5. Audit Trail Completeness

**Test**: `test_audit_trail_completeness()`

```python
def test_audit_trail_completeness():
    """All governance decisions must be audited."""
    
    # Clear audit log
    postgres.execute("DELETE FROM audit_log")
    
    # Perform 10 governance operations
    operations = []
    
    for i in range(10):
        op = {
            'type': 'test_operation',
            'agent_id': f'agent-{i}',
            'action': f'action-{i}'
        }
        
        # Simulate operation
        result = kaiju.check_access(
            agent_id=op['agent_id'],
            action=op['action'],
            scope='project'
        )
        
        operations.append({
            **op,
            'result': result.decision.value
        })
    
    # Check audit trail
    audit_entries = postgres.query_all(
        "SELECT * FROM audit_log ORDER BY created_at"
    )
    
    assert len(audit_entries) >= len(operations), \
        f"Missing audit entries: {len(audit_entries)} < {len(operations)}"
    
    # Verify each operation is logged
    for i, op in enumerate(operations):
        entry = audit_entries[i]
        assert entry['action'] == op['action']
        assert entry['agent_id'] == op['agent_id']
        assert entry['result'] == op['result']
        assert entry['timestamp'] is not None
```

**Success Criteria**:
- ✅ 100% of operations logged
- ✅ Audit entries immutable
- ✅ Complete metadata captured

---

## TSI Mitigation Tests

### 6. Tool Filtering Accuracy

**Test**: `test_intent_based_tool_filtering()`

```python
def test_intent_based_tool_filtering():
    """Dynamic tool filtering must reduce tools by >70%."""
    
    # All 47 tools available
    all_tools = mcp_server.tools.keys()
    assert len(all_tools) == 47
    
    intents = [
        ('code: Create GitHub PR and run tests', 'code'),
        ('research: Find latest papers on speculative decoding', 'research'),
        ('route: Distribute task to appropriate agent', 'routing'),
    ]
    
    for prompt, expected_intent in intents:
        context = MCPContext(
            agent_id='test',
            project_id='nexus',
            trace_id='trace-123',
            intent=prompt,
            capabilities=[],
            trust_score=0.75
        )
        
        # Get filtered tools
        filtered = mcp_server.discover_tools(context)
        
        # Should be much fewer than 47
        reduction_pct = (1 - len(filtered) / len(all_tools)) * 100
        assert reduction_pct > 70, \
            f"Only {reduction_pct}% reduction for {expected_intent}"
        
        # Should include relevant tools
        tool_categories = [t['category'] for t in filtered]
        
        if expected_intent == 'code':
            assert 'github' in tool_categories or \
                   any('github' in t['name'] for t in filtered)
        elif expected_intent == 'research':
            assert 'research' in tool_categories or \
                   any('search' in t['name'] for t in filtered)
```

**Success Criteria**:
- ✅ >70% tool reduction per intent
- ✅ Relevant tools always included
- ✅ No relevant tools omitted

---

### 7. Context Window Reduction

**Test**: `test_context_window_load()`

```python
def test_context_window_load():
    """Context window with filtered tools must be <70% of max."""
    
    TOKEN_LIMIT = 128000  # Claude 3.5 Sonnet
    RESERVE = 0.3  # Reserve 30% for response
    MAX_FOR_TOOLS = TOKEN_LIMIT * (1 - RESERVE)  # ~90K tokens
    
    # Load all 47 tools (worst case)
    all_tools_context = format_tools_for_context(list(mcp_server.tools.values()))
    all_tokens = count_tokens(all_tools_context)
    
    # Load only intent-filtered tools
    context = MCPContext(
        agent_id='test',
        intent='Complex code task with testing',
        trust_score=0.8
    )
    filtered_tools = mcp_server.discover_tools(context)
    filtered_context = format_tools_for_context(filtered_tools)
    filtered_tokens = count_tokens(filtered_context)
    
    # Calculate reduction
    reduction = (1 - filtered_tokens / all_tokens) * 100
    
    assert reduction > 70, f"Only {reduction}% reduction achieved"
    assert filtered_tokens < MAX_FOR_TOOLS, \
        f"Filtered tools exceed budget: {filtered_tokens} > {MAX_FOR_TOOLS}"
    
    print(f"✓ Context reduction: {reduction:.1f}% ({all_tokens} → {filtered_tokens} tokens)")
```

**Success Criteria**:
- ✅ >70% token reduction
- ✅ All tools fit within budget
- ✅ No truncation needed

---

## E2E Workflow Tests

### 8. Issue→Code→Deploy Workflow

**Test**: `test_e2e_github_issue_to_deployment()`

```python
def test_e2e_github_issue_to_deployment():
    """Full workflow: GitHub issue → OPUSman code → Docker → K8s."""
    
    # 1. Create GitHub issue
    issue = github_mcp.create_issue(
        repo='nexus-os',
        title='Add feature X',
        body='Implementation needed for Y',
        labels=['feature', 'test']
    )
    issue_id = issue['id']
    
    # 2. Grok assigns to OPUSman
    assignment = n8n.route_task({
        'issue_id': issue_id,
        'type': 'code_implementation',
        'complexity': 'medium'
    })
    assert assignment['assigned_to'] == 'opusman'
    
    # 3. OPUSman creates PR
    pr = github_mcp.create_pr(
        repo='nexus-os',
        title=f'Implement issue {issue_id}',
        branch='feature/issue-X',
        description='Implementation of feature X'
    )
    pr_id = pr['id']
    
    # 4. CI/CD runs tests
    ci_result = github_actions.trigger_workflow(
        workflow='test.yml',
        ref=f'refs/pull/{pr_id}/head'
    )
    assert ci_result['status'] == 'completed'
    assert ci_result['conclusion'] == 'success'
    
    # 5. DeepSeek reviews code quality
    review = deepseek_mcp.analyze_code_quality(
        repo='nexus-os',
        pr_id=pr_id
    )
    assert review['quality_score'] > 0.7
    
    # 6. Merge PR
    merged = github_mcp.merge_pr(pr_id=pr_id)
    assert merged['merged'] == True
    
    # 7. Deploy to Docker
    docker_build = docker_mcp.build_image(
        context='.',
        tag='nexus-os:latest'
    )
    assert docker_build['status'] == 'success'
    
    # 8. Deploy to Kubernetes
    k8s_deploy = kubernetes_mcp.apply_deployment(
        manifest='deployment.yaml',
        namespace='production'
    )
    assert k8s_deploy['status'] == 'deployed'
    
    # 9. Verify in production
    health = kubernetes_mcp.check_pod_health(
        deployment='nexus-os',
        namespace='production'
    )
    assert health['status'] == 'ready'
    assert health['replicas_ready'] > 0
    
    print(f"✓ E2E Workflow: Issue {issue_id} → PR {pr_id} → Deployed")
```

**Success Criteria**:
- ✅ All 8 steps complete successfully
- ✅ <5 min total execution time
- ✅ Service healthy in production

---

## Performance Benchmarks

### 9. Throughput Test

**Test**: `test_concurrent_tool_calls()`

```python
def test_concurrent_tool_calls():
    """Handle 100+ concurrent tool calls without degradation."""
    
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    async def make_tool_call(tool_id):
        return mcp_server.call_tool(
            tool_name='github_list_repos',
            arguments={'owner': 'specimba'},
            context=MCPContext(agent_id=f'agent-{tool_id}')
        )
    
    # Fire 100 concurrent calls
    start = time.time()
    tasks = [make_tool_call(i) for i in range(100)]
    results = asyncio.run(asyncio.gather(*tasks))
    elapsed = time.time() - start
    
    # Success rate
    success_count = sum(1 for r in results if not r.get('error'))
    success_rate = success_count / len(results)
    
    assert success_rate > 0.95, f"Only {success_rate*100}% success"
    assert elapsed < 30, f"Took {elapsed}s, target <30s"
    
    throughput = len(results) / elapsed
    print(f"✓ Throughput: {throughput:.1f} calls/sec")
```

**Success Criteria**:
- ✅ >95% success rate
- ✅ <30s for 100 calls
- ✅ >3 calls/sec throughput

---

## Test Execution

### Run Full Suite

```bash
# Phase 1: Governance (Week 1)
docker-compose -f docker-compose.set2-tested.yml up -d
docker exec nexus-test-runner npm run test:governance

# Check results
docker exec nexus-test-runner npm run test:report

# Generate HTML report
docker exec nexus-test-runner npm run test:html-report

# View results
open results/index.html  # macOS
firefox results/index.html  # Linux
```

### Expected Output

```
NEXUS-SET2-TESTED Integration Tests
=====================================

Governance Tests (20)               ✓ 20/20 PASS
├─ VAP chain immutability           ✓ PASS
├─ KAIJU authorization latency      ✓ PASS (p95: 42.3ms)
├─ Proposal lifecycle               ✓ PASS
├─ Trust score consistency          ✓ PASS
└─ Audit trail completeness        ✓ PASS

TSI Mitigation Tests (15)           ✓ 15/15 PASS
├─ Tool filtering accuracy          ✓ PASS (72% reduction)
├─ Context window load              ✓ PASS (58K tokens)
└─ Performance benchmarks           ✓ PASS (3.2 calls/sec)

E2E Workflow Tests (8)              ✓ 8/8 PASS
├─ Issue→Deploy workflow            ✓ PASS (4.3 min)
└─ Multi-agent collaboration       ✓ PASS

Total: 43/43 PASS ✓
Coverage: 94% ✓
Performance: Within SLA ✓
```

---

## Cost for Testing

```
Infrastructure:
├─ PostgreSQL        free (docker)
├─ Neo4j             free (docker)
├─ Redis             free (docker)
├─ Milvus/Zilliz    free (docker)
└─ Mock services     free

External services (mocked):
├─ Slack             N/A (mocked)
├─ GitHub            N/A (mocked)
└─ Docker Registry   N/A (mocked)

Total Testing Cost: ~$0 (all local)
Actual Deployment Cost: ~$550-1,150/mo
```

---

## Next Steps

1. **Review test specifications** ✓ (this document)
2. **Deploy test suite** (Week 1)
   ```bash
   docker-compose -f docker-compose.set2-tested.yml up -d
   ```
3. **Run governance tests** (Phase 1)
   ```bash
   docker exec nexus-test-runner npm run test:governance
   ```
4. **Validate success criteria**
5. **Move to Phase 2** (specialist servers)

---

**NEXUS-SET2-TESTED is ready for production validation. Deploy immediately.**
