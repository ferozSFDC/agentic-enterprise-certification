"""
Monte Carlo simulation to validate CAT engine behavior.

Generates simulated candidates with known theta values, runs them through
the CAT algorithm, and reports:
- Classification accuracy (should be > 95% for alpha=beta=0.05)
- Average test length for clearly passing/failing/borderline candidates
- Domain coverage proportional to blueprint weights

Usage:
    python -m scripts.simulate_cat --n-candidates 1000 --theta-c 0.0
"""

import argparse
import random
import numpy as np
from dataclasses import dataclass

from app.irt.models import probability_2pl
from app.irt.estimation import estimate_theta_eap
from app.irt.sprt import sprt_update, Decision
from app.services.item_selection import ItemCandidate, select_next_item
from app.services.stopping_rule import evaluate_stopping_with_theta_c
from app.services.cat_engine import EngineState, SessionConfig, ResponseRecord, process_response


# Blueprint domain weights
DOMAIN_WEIGHTS = {
    "1": 0.15, "2": 0.12, "3": 0.20, "4": 0.15,
    "5": 0.12, "6": 0.10, "7": 0.10, "8": 0.06,
}


def generate_item_bank(n_items: int = 180, seed: int = 42) -> list[ItemCandidate]:
    """Generate a synthetic item bank with realistic parameters."""
    rng = np.random.default_rng(seed)

    items = []
    items_per_domain = {
        1: 27, 2: 22, 3: 36, 4: 27,
        5: 22, 6: 18, 7: 18, 8: 10,
    }

    item_idx = 0
    for domain_id, count in items_per_domain.items():
        for i in range(count):
            # CC3 items are harder (25% of items)
            is_cc3 = rng.random() < 0.25
            if is_cc3:
                difficulty = rng.normal(0.5, 0.8)
            else:
                difficulty = rng.normal(-0.2, 0.8)

            difficulty = np.clip(difficulty, -3.5, 3.5)
            discrimination = rng.uniform(0.6, 2.0)

            items.append(ItemCandidate(
                item_id=f"item-{item_idx:04d}",
                domain_id=domain_id,
                discrimination=float(discrimination),
                difficulty=float(difficulty),
                sympson_hetter_k=1.0,  # No exposure control for simulation
            ))
            item_idx += 1

    return items


def simulate_candidate(
    true_theta: float,
    item_bank: list[ItemCandidate],
    config: SessionConfig,
) -> dict:
    """
    Simulate one candidate taking the CAT.

    The candidate's responses are generated probabilistically based on
    their true theta and each item's parameters.
    """
    state = EngineState.new_session(config)
    eligible = list(item_bank)

    # Select first item
    from app.services.item_selection import select_next_item
    current_item = select_next_item(
        eligible_items=eligible,
        theta_hat=state.current_theta,
        domain_counts=state.domain_counts,
        total_administered=0,
        domain_weights=config.domain_weights,
        w_info=config.w_info,
        w_content=config.w_content,
    )

    items_administered = 0
    decision = None

    while current_item and items_administered < config.max_items:
        # Generate response based on true theta
        p_correct = probability_2pl(
            true_theta, current_item.discrimination, current_item.difficulty
        )
        is_correct = random.random() < p_correct

        # Process through engine
        remaining = [i for i in eligible if i.item_id not in state.administered_item_ids]
        result = process_response(
            state=state,
            item=current_item,
            response_index=0 if is_correct else 1,  # Simulate correct=0, incorrect=1
            correct_index=0,  # All items have correct at index 0 for simulation
            eligible_items=remaining,
        )

        items_administered += 1

        if result.stop_decision.should_stop:
            decision = result.decision
            break

        current_item = result.next_item

    # If we ran out of items without a decision
    if decision is None:
        decision = Decision.PASS if state.current_theta > config.theta_c else Decision.FAIL

    return {
        "true_theta": true_theta,
        "estimated_theta": state.current_theta,
        "items_administered": items_administered,
        "decision": decision.value if isinstance(decision, Decision) else decision,
        "correct_decision": (
            (decision == Decision.PASS and true_theta >= config.theta_c) or
            (decision == Decision.FAIL and true_theta < config.theta_c)
        ),
        "domain_counts": dict(state.domain_counts),
        "cumulative_lr": state.cumulative_lr,
    }


def run_simulation(
    n_candidates: int = 1000,
    theta_c: float = 0.0,
    delta: float = 0.2,
    alpha: float = 0.05,
    beta: float = 0.05,
    max_items: int = 40,
    seed: int = 42,
):
    """Run the full Monte Carlo simulation."""
    random.seed(seed)
    np.random.seed(seed)

    config = SessionConfig(
        theta_c=theta_c,
        delta=delta,
        alpha=alpha,
        beta=beta,
        max_items=max_items,
        min_items=5,
        w_info=0.7,
        w_content=0.3,
        starting_theta=0.0,
        domain_weights=DOMAIN_WEIGHTS,
        max_exposure_rate=0.25,
        time_limit_minutes=120,
    )

    item_bank = generate_item_bank()
    print(f"Generated item bank: {len(item_bank)} items across 8 domains")
    print(f"Config: theta_c={theta_c}, delta={delta}, alpha={alpha}, beta={beta}, max_items={max_items}")
    print(f"Simulating {n_candidates} candidates...\n")

    # Generate candidates across the ability spectrum
    # 40% clearly passing, 40% clearly failing, 20% borderline
    thetas = []
    for _ in range(int(n_candidates * 0.4)):
        thetas.append(np.random.normal(theta_c + 1.5, 0.5))  # Clearly passing
    for _ in range(int(n_candidates * 0.4)):
        thetas.append(np.random.normal(theta_c - 1.5, 0.5))  # Clearly failing
    for _ in range(n_candidates - len(thetas)):
        thetas.append(np.random.normal(theta_c, 0.3))  # Borderline

    results = []
    for i, true_theta in enumerate(thetas):
        if (i + 1) % 100 == 0:
            print(f"  Simulated {i + 1}/{n_candidates}...")
        result = simulate_candidate(true_theta, item_bank, config)
        results.append(result)

    # Analyze results
    print("\n" + "=" * 60)
    print("SIMULATION RESULTS")
    print("=" * 60)

    # Overall accuracy
    correct_decisions = sum(1 for r in results if r["correct_decision"])
    accuracy = correct_decisions / n_candidates
    print(f"\n1. CLASSIFICATION ACCURACY: {accuracy:.1%} ({correct_decisions}/{n_candidates})")
    print(f"   Target: > {1 - max(alpha, beta):.0%}")
    print(f"   {'PASS' if accuracy >= 1 - max(alpha, beta) else 'FAIL'}")

    # Test length by group
    clearly_passing = [r for r in results if r["true_theta"] >= theta_c + 1.0]
    clearly_failing = [r for r in results if r["true_theta"] <= theta_c - 1.0]
    borderline = [r for r in results if theta_c - 1.0 < r["true_theta"] < theta_c + 1.0]

    print(f"\n2. AVERAGE TEST LENGTH:")
    if clearly_passing:
        avg_pass = np.mean([r["items_administered"] for r in clearly_passing])
        print(f"   Clearly passing (theta > {theta_c + 1.0}): {avg_pass:.1f} items (n={len(clearly_passing)})")
    if clearly_failing:
        avg_fail = np.mean([r["items_administered"] for r in clearly_failing])
        print(f"   Clearly failing (theta < {theta_c - 1.0}): {avg_fail:.1f} items (n={len(clearly_failing)})")
    if borderline:
        avg_border = np.mean([r["items_administered"] for r in borderline])
        print(f"   Borderline ({theta_c - 1.0} < theta < {theta_c + 1.0}): {avg_border:.1f} items (n={len(borderline)})")

    avg_all = np.mean([r["items_administered"] for r in results])
    print(f"   Overall average: {avg_all:.1f} items")

    # Domain coverage
    print(f"\n3. DOMAIN COVERAGE (target vs actual):")
    all_domain_counts = {}
    total_items = 0
    for r in results:
        for d, count in r["domain_counts"].items():
            all_domain_counts[d] = all_domain_counts.get(d, 0) + count
            total_items += count

    for d in sorted(DOMAIN_WEIGHTS.keys()):
        target = DOMAIN_WEIGHTS[d]
        actual = all_domain_counts.get(d, 0) / total_items if total_items > 0 else 0
        deficit = target - actual
        status = "OK" if abs(deficit) < 0.05 else "DRIFT"
        print(f"   Domain {d}: target={target:.0%}, actual={actual:.0%}, deficit={deficit:+.1%} [{status}]")

    # Error analysis
    print(f"\n4. ERROR ANALYSIS:")
    false_passes = [r for r in results if r["decision"] == "pass" and r["true_theta"] < theta_c]
    false_fails = [r for r in results if r["decision"] == "fail" and r["true_theta"] >= theta_c]
    print(f"   False PASS (Type I): {len(false_passes)} ({len(false_passes)/n_candidates:.1%})")
    print(f"   False FAIL (Type II): {len(false_fails)} ({len(false_fails)/n_candidates:.1%})")
    print(f"   Target Type I (alpha): {alpha:.0%}")
    print(f"   Target Type II (beta): {beta:.0%}")

    # Theta estimation accuracy
    print(f"\n5. THETA ESTIMATION:")
    theta_errors = [r["estimated_theta"] - r["true_theta"] for r in results]
    print(f"   Mean bias: {np.mean(theta_errors):.3f}")
    print(f"   RMSE: {np.sqrt(np.mean(np.array(theta_errors)**2)):.3f}")
    print(f"   Correlation(true, estimated): {np.corrcoef([r['true_theta'] for r in results], [r['estimated_theta'] for r in results])[0,1]:.3f}")

    print(f"\n{'=' * 60}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monte Carlo CAT simulation")
    parser.add_argument("--n-candidates", type=int, default=1000)
    parser.add_argument("--theta-c", type=float, default=0.0)
    parser.add_argument("--delta", type=float, default=0.2)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--beta", type=float, default=0.05)
    parser.add_argument("--max-items", type=int, default=40)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    run_simulation(
        n_candidates=args.n_candidates,
        theta_c=args.theta_c,
        delta=args.delta,
        alpha=args.alpha,
        beta=args.beta,
        max_items=args.max_items,
        seed=args.seed,
    )
