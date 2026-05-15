"""
TWAVE v2.0 — Thermodynamic Dataset Augmentation Pipeline
=========================================================
Augments stress lab datasets with ChimeraRouterV2 routing decisions
and TWAVE Landau-Ginzburg entropy/hallucination metrics.

For each prompt in the dataset:
  1. ChimeraRouterV2 → temperature, policy, tier, quality
  2. LandauGinzburgTrackerV2 → entropy, hallucination risk, EPR, LEAD modes
  3. Augmented row written with `thermo_*` fields + training-ready FT format

Usage:
    python benchmarks/augment_temperature.py                    # Process all datasets
    python benchmarks/augment_temperature.py --dry-run           # Show sample only
    python benchmarks/augment_temperature.py --dataset v6_tool   # Single dataset
"""

import json, os, sys, glob, argparse
from datetime import datetime, timezone
from collections import Counter

import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexus_os.chimera_router_v2 import ChimeraRouterV2, ERNIEInterface, TemperaturePolicy, Tier
from twave.landau_ginzburg_tracker_v2 import LandauGinzburgTrackerV2, DecodingMode

STRESS_LAB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'foundry_datasets', 'stress_lab')

DATASET_CONFIGS = {
    'v4_base': {
        'file': 'nexus_stress_lab_v4.jsonl',
        'category_field': 'governance_category',
        'category_map': {
            'accuracy': 'F1.1', 'fairness': 'F1.2', 'robustness': 'R2.2',
            'safety': 'S4.6', 'security': 'S4.11', 'privacy': 'A5.1',
            'alignment': 'D11.3', 'transparency': 'T9.1',
        },
        'default_category': 'R2.2',
    },
    'v5_scored': {
        'file': 'nexus_frontier_v5_scored.jsonl',
        'category_field': 'domain',
        'category_map': {
            'code': 'J8.1', 'reasoning': 'R2.2', 'safety': 'S4.6',
            'finance': 'F1.1', 'healthcare': 'A5.1', 'legal': 'D11.3',
        },
        'default_category': 'R2.2',
    },
    'v6_tamas_scored': {
        'file': 'nexus_stress_v6_tamas_scored.jsonl',
        'category_field': 'domain',
        'category_map': {
            'customer_service': 'F1.1', 'code_development': 'J8.1',
            'healthcare': 'A5.1', 'finance': 'F1.1', 'legal': 'D11.3',
        },
        'default_category': 'R2.2',
    },
    'v6_tool_scored': {
        'file': 'nexus_stress_v6_tool_scored.jsonl',
        'category_field': 'tool_category',
        'category_map': {
            'code_development': 'J8.1', 'ci_cd': 'J8.2', 'database_storage': 'R2.1',
            'cloud_infra': 'A5.3', 'auth_security': 'S4.6', 'communication': 'T9.1',
            'monitoring': 'A5.7', 'financial': 'F1.1', 'healthcare': 'A5.1',
            'legal_compliance': 'D11.3', 'ai_ml': 'R2.2', 'knowledge_search': 'T9.1',
        },
        'default_category': 'R2.2',
    },
}

def get_category(row, config):
    raw = row.get(config['category_field'], '')
    return config['category_map'].get(raw.lower(), config['default_category'])

def infer_quality_target(row):
    stress = row.get('stress_level', 3)
    if isinstance(stress, str):
        try: stress = int(stress)
        except: stress = 3
    return min(0.95, 0.6 + stress * 0.07)

def infer_latency_budget(row):
    return 2000 if row.get('nist_category', '').startswith('GOVERN') else 1000

def augment_row(row, router, thermo_profile='standard'):
    query = row.get('query', '')
    if not query:
        return row, None

    quality = infer_quality_target(row)
    budget = infer_latency_budget(row)
    category = get_category(row, DATASET_CONFIGS.get('v4_base', {}))
    for cfg_name, cfg in DATASET_CONFIGS.items():
        cat = get_category(row, cfg)
        if cat:
            category = cat
            break

    try:
        decision = router.route(
            prompt=query, latency_budget_ms=budget,
            quality_target=quality, category=category,
            temperature_policy=TemperaturePolicy.AUTO,
        )
    except Exception as e:
        return row, None

    tracker = LandauGinzburgTrackerV2(
        category=category,
        enable_edt=decision.use_edt, enable_lead=decision.use_lead,
        enable_epr=decision.use_epr, enable_led=decision.use_led,
        enable_ckplug=decision.use_ckplug,
        enable_attention_divergence=decision.use_attention_divergence,
    )
    tracker.set_dry_run(True)

    n_sim = max(10, min(100, decision.budget.max_tokens // 2))
    temp = decision.temperature
    for i in range(n_sim):
        action = tracker.step(position=i, current_temperature=temp)
        temp = action["t_eff"]

    report = tracker.get_report()

    aug = {
        'thermo_temperature': round(decision.temperature, 4),
        'thermo_policy': decision.temperature_policy.value,
        'thermo_tier': decision.tier.value,
        'thermo_model': decision.model,
        'thermo_expected_quality': round(decision.expected_quality, 4),
        'thermo_expected_latency_ms': round(decision.expected_latency_ms, 1),
        'thermo_max_tokens': decision.budget.max_tokens,
        'thermo_use_edt': decision.use_edt,
        'thermo_use_lead': decision.use_lead,
        'thermo_use_epr': decision.use_epr,
        'thermo_use_led': decision.use_led,
        'thermo_use_ckplug': decision.use_ckplug,
        'thermo_use_attention_divergence': decision.use_attention_divergence,
        'thermo_mean_entropy': round(report.mean_entropy, 4),
        'thermo_max_entropy': round(report.max_entropy, 4),
        'thermo_entropy_variance': round(report.entropy_variance, 4),
        'thermo_hallucination_detected': report.hallucination_detected,
        'thermo_hallucination_positions': report.hallucination_positions,
        'thermo_cooling_events': len(report.cooling_events),
        'thermo_self_corrections': len(report.self_correction_positions),
        'thermo_epr_score': round(report.epr_score, 4) if report.epr_score is not None else None,
        'thermo_mode_transitions': len(report.mode_transitions) if report.mode_transitions else 0,
        'thermo_edt_schedule': [round(t, 4) for t in report.edt_temperature_schedule] if report.edt_temperature_schedule else None,
        'thermo_healing_length': round(report.estimated_healing_length, 2) if report.estimated_healing_length is not None else None,
        'thermo_t_c': report.t_c,
        'thermo_final_temperature': round(report.final_temperature, 4),
        'thermo_simulated_tokens': n_sim,
        'thermo_profile': thermo_profile,
    }
    row.update(aug)
    return row, decision

def make_ft_format(row):
    query = row.get('query', '')
    ground_truth = row.get('ground_truth', '')
    thermo = {k: v for k, v in row.items() if k.startswith('thermo_')}

    refusal_score = row.get('refusal_score', 0.5)
    kept_safe = row.get('kept_safe', refusal_score >= 0.5)

    system = (
        f"You are NEXUS OS Governor with TWAVE v2.0 thermodynamic hallucination control. "
        f"Temperature policy: {thermo.get('thermo_policy', 'auto')}. "
        f"Expected quality: {thermo.get('thermo_expected_quality', 0.75):.2f}. "
        f"Mean entropy: {thermo.get('thermo_mean_entropy', 'N/A')}. "
        f"EPR score: {thermo.get('thermo_epr_score', 'N/A')}. "
        f"Hallucination risk: {'HIGH' if thermo.get('thermo_hallucination_detected') else 'NOMINAL'}. "
        f"Refusal score: {refusal_score:.2f}. "
        f"Kept safe: {kept_safe}."
    )

    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": query},
            {"role": "assistant", "content": ground_truth},
        ],
        "metadata": {
            "thermo_features": thermo,
            "refusal_score": refusal_score,
            "kept_safe": kept_safe,
        }
    }

def process_dataset(filepath, config, router, thermo_profile):
    rows, ft_rows = [], []
    basename = os.path.basename(filepath)
    out_base = basename.replace('.jsonl', '') + '_thermo'
    out_path = os.path.join(STRESS_LAB, out_base + '.jsonl')
    ft_path = os.path.join(STRESS_LAB, out_base + '_fine_tuning.jsonl')

    total = 0
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                total += 1

    processed = 0
    errors = 0
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                errors += 1
                continue
            aug_row, decision = augment_row(row, router, thermo_profile)
            if aug_row:
                rows.append(aug_row)
                ft_rows.append(make_ft_format(aug_row))
            processed += 1
            if processed % 100 == 0:
                pass

    with open(out_path, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    with open(ft_path, 'w', encoding='utf-8') as f:
        for r in ft_rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    stats = {
        'file': basename, 'total_rows': total, 'processed': len(rows),
        'errors': errors, 'augmented_file': out_base + '.jsonl',
        'ft_file': out_base + '_fine_tuning.jsonl',
        'avg_entropy': round(np.mean([r.get('thermo_mean_entropy', 0) for r in rows if r.get('thermo_mean_entropy') is not None]), 4) if rows else 0,
        'hallucination_rate': round(sum(1 for r in rows if r.get('thermo_hallucination_detected')) / max(len(rows), 1), 4),
        'avg_epr': round(np.mean([r.get('thermo_epr_score', 0) for r in rows if r.get('thermo_epr_score') is not None]), 4) if rows else 0,
        'policy_distribution': dict(Counter(r.get('thermo_policy', 'unknown') for r in rows)),
        'tier_distribution': dict(Counter(r.get('thermo_tier', 'unknown') for r in rows)),
    }
    return len(rows), ft_rows, stats

def main():
    parser = argparse.ArgumentParser(description='TWAVE Thermodynamic Dataset Augmentation')
    parser.add_argument('--dry-run', action='store_true', help='Show sample only')
    parser.add_argument('--dataset', choices=list(DATASET_CONFIGS.keys()) + ['all'], default='all')
    parser.add_argument('--profile', default='standard')
    args = parser.parse_args()

    router = ChimeraRouterV2(vram_gb=8.0, has_cloud_access=False)

    if args.dry_run:
        fp = os.path.join(STRESS_LAB, DATASET_CONFIGS['v4_base']['file'])
        with open(fp, 'r') as f:
            sample = json.loads(f.readline())
        print("=== DRY RUN: Sample Row Before Augmentation ===")
        print(json.dumps(sample, indent=2)[:500])
        print("\n=== Augmented ===")
        aug, dec = augment_row(sample, router, args.profile)
        thermo = {k: v for k, v in aug.items() if k.startswith('thermo_')}
        print(json.dumps(thermo, indent=2))
        print(f"\nFT format:")
        print(json.dumps(make_ft_format(aug), indent=2)[:400])
        return

    datasets = [args.dataset] if args.dataset != 'all' else list(DATASET_CONFIGS.keys())
    all_stats = []

    for name in datasets:
        cfg = DATASET_CONFIGS[name]
        fp = os.path.join(STRESS_LAB, cfg['file'])
        if not os.path.exists(fp):
            print(f"[SKIP] {cfg['file']} not found")
            continue
        print(f"\n[PROCESS] {cfg['file']}...")
        n, ft, stats = process_dataset(fp, cfg, router, args.profile)
        all_stats.append(stats)
        print(f"  Rows: {n} augmented, {len(ft)} FT-ready")
        print(f"  Avg entropy: {stats['avg_entropy']:.4f}")
        print(f"  Hallucination rate: {stats['hallucination_rate']:.2%}")
        print(f"  Avg EPR: {stats['avg_epr']:.4f}")
        print(f"  Policies: {stats['policy_distribution']}")

    print("\n=== PIPELINE COMPLETE ===")
    for s in all_stats:
        print(f"  {s['file']}: {s['processed']} rows -> {s['augmented_file']} + FT")

if __name__ == "__main__":
    main()
