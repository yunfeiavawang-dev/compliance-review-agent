"""Cost projection for scaled deployment scenarios.

Estimates monthly costs at different KYC volumes using actual per-case
token consumption from evaluation runs.
"""

from __future__ import annotations
from dataclasses import dataclass


# Doubao-seed-evolving pricing (per 1K tokens, in CNY)
DOUBAO_INPUT_PRICE_CNY = 0.004
DOUBAO_OUTPUT_PRICE_CNY = 0.004
CNY_TO_USD = 7.2

# Volcengine product suite costs (monthly, USD) for scaled deployment
VOLCENGINE_INFRA = {
    "ECS (2x ecs.g3i.xlarge)": 180,
    "VKE (Kubernetes)": 0,  # free control plane
    "TOS (Object Storage, 100GB)": 3,
    "RDS MySQL (basic)": 45,
    "Redis (1GB)": 15,
    "CDN (50GB)": 5,
    "CloudMonitor": 0,
    "VPC + NAT Gateway": 20,
}


@dataclass
class CostProjection:
    volume: int
    avg_tokens_per_case: int
    avg_input_tokens: int
    avg_output_tokens: int
    llm_cost_cny: float
    llm_cost_usd: float
    infra_cost_usd: float
    total_cost_usd: float
    cost_per_case_usd: float

    def summary(self) -> dict:
        return {
            "monthly_volume": self.volume,
            "avg_tokens_per_case": self.avg_tokens_per_case,
            "llm_cost_cny": round(self.llm_cost_cny, 2),
            "llm_cost_usd": round(self.llm_cost_usd, 2),
            "infra_cost_usd": round(self.infra_cost_usd, 2),
            "total_cost_usd": round(self.total_cost_usd, 2),
            "cost_per_case_usd": round(self.cost_per_case_usd, 4),
        }


def project_costs(
    avg_input_tokens: int,
    avg_output_tokens: int,
    volumes: list[int] = None,
) -> list[CostProjection]:
    if volumes is None:
        volumes = [500, 1000, 5000]

    infra_total = sum(VOLCENGINE_INFRA.values())
    results = []
    for vol in volumes:
        input_cost = vol * avg_input_tokens * DOUBAO_INPUT_PRICE_CNY / 1000
        output_cost = vol * avg_output_tokens * DOUBAO_OUTPUT_PRICE_CNY / 1000
        llm_cny = input_cost + output_cost
        llm_usd = llm_cny / CNY_TO_USD
        total = llm_usd + infra_total
        results.append(CostProjection(
            volume=vol,
            avg_tokens_per_case=avg_input_tokens + avg_output_tokens,
            avg_input_tokens=avg_input_tokens,
            avg_output_tokens=avg_output_tokens,
            llm_cost_cny=llm_cny,
            llm_cost_usd=llm_usd,
            infra_cost_usd=infra_total,
            total_cost_usd=total,
            cost_per_case_usd=total / vol,
        ))
    return results


def format_projection_table(projections: list[CostProjection]) -> str:
    lines = []
    lines.append("## Scaled Cost Projection (Volcengine Full Stack)\n")
    lines.append("| Monthly Volume | LLM Cost (CNY) | LLM Cost (USD) | Infra (USD) | Total (USD) | Per Case |")
    lines.append("|----------------|-----------------|----------------|-------------|-------------|----------|")
    for p in projections:
        lines.append(
            f"| {p.volume:,} cases | ¥{p.llm_cost_cny:.2f} | "
            f"${p.llm_cost_usd:.2f} | ${p.infra_cost_usd:.0f} | "
            f"${p.total_cost_usd:.2f} | ${p.cost_per_case_usd:.4f} |"
        )
    lines.append("")
    lines.append("**Infrastructure breakdown:**\n")
    for name, cost in VOLCENGINE_INFRA.items():
        lines.append(f"- {name}: ${cost}/mo")
    lines.append(f"- **Subtotal**: ${sum(VOLCENGINE_INFRA.values())}/mo\n")
    lines.append(f"*LLM: Doubao-seed-evolving @ ¥{DOUBAO_INPUT_PRICE_CNY}/1K input + ¥{DOUBAO_OUTPUT_PRICE_CNY}/1K output*")
    return "\n".join(lines)
