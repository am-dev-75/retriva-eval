"""Generate a 100-message email dataset exercising all addressing combinations.

Each message has:
- A unique message_id
- A subject and body resembling typical business content across fields
  (finance, engineering, sales, manufacturing, HR, legal, IT, logistics, etc.)
- A question and expected_answer for query verification
- A recipient address that exercises one of these addressing patterns:
  1. Plain prefix (no plus sign): retriva@server.com
  2. Prefix + collection only: retriva+coll@server.com
  3. Prefix + collection + kb: retriva+coll+kb@server.com
  4. Prefix + collection + kb + one tag: retriva+coll+kb+priority=high@server.com
  5. Prefix + collection + kb + multiple tags: retriva+coll+kb+prio=high+proj=alpha@server.com
  6. Prefix + collection + kb + many tags (3+): retriva+coll+kb+t1=a+t2=b+t3=c@server.com
  7. Prefix + kb only (no collection): retriva++kb@server.com  (empty collection segment)
  8. Prefix + tags only (no collection, no kb): retriva+++tag=val@server.com (two empty segments)

Run: python suites/email_ingestion/generate_dataset.py
Output: suites/email_ingestion/data/emails.jsonl
"""

from __future__ import annotations

import json
import os
import random
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Business content templates by field
# Each entry is (subject, body, question, expected_answer)
# ---------------------------------------------------------------------------

_FIELDS = {
    "finance": [
        (
            "Q3 Financial Results Summary",
            "The Q3 revenue reached $4.2M, a 12% increase year-over-year. "
            "Operating margins improved to 28% due to reduced cloud infrastructure costs. "
            "We recommend increasing the R&D allocation by 5% for the next quarter.",
            "What was the Q3 revenue and year-over-year growth?",
            "Q3 revenue was $4.2M with a 12% increase year-over-year.",
        ),
        (
            "Budget Approval Request — Marketing Department",
            "Please review the attached budget proposal for the marketing department. "
            "Total requested allocation is $850K, covering digital campaigns, events, "
            "and content production. Approval needed by July 15th to meet Q3 planning.",
            "What is the total budget requested for the marketing department and by when is approval needed?",
            "The total requested allocation is $850K, and approval is needed by July 15th.",
        ),
        (
            "Cash Flow Forecast Update",
            "Updated cash flow projections indicate a runway of 18 months at current "
            "burn rate. Accounts receivable improved by 8% following the new collection "
            "policy. Recommend maintaining the $2M reserve for operational continuity.",
            "How long is the cash flow runway and what reserve is recommended?",
            "The runway is 18 months at current burn rate, and a $2M reserve is recommended.",
        ),
        (
            "Quarterly Earnings Call Preparation",
            "The earnings call is scheduled for August 12th at 2PM EST. Key talking "
            "points include revenue growth, margin expansion, and the strategic "
            "acquisition of DataFlow Inc. Legal has cleared all forward-looking "
            "statements.",
            "When is the earnings call scheduled and what are the key talking points?",
            "The earnings call is on August 12th at 2PM EST, covering revenue growth, margin expansion, and the DataFlow Inc. acquisition.",
        ),
    ],
    "engineering": [
        (
            "Architecture Review — Microservices Migration",
            "The microservices migration is 60% complete. The order service and "
            "inventory service have been successfully decoupled. Next priority is "
            "the payment service, which has complex transactional dependencies. "
            "Estimated completion: end of Q3.",
            "What percentage of the microservices migration is complete and what is the next priority?",
            "The migration is 60% complete, and the next priority is the payment service.",
        ),
        (
            "Postmortem: Production Outage June 28",
            "Root cause analysis for the June 28 outage (14:32–15:08 UTC): a "
            "misconfigured health check caused the load balancer to drain all "
            "backend instances. Fix deployed in v3.1.4. Action item: add circuit "
            "breaker pattern to prevent cascading failures.",
            "What was the root cause of the June 28 outage and what fix was deployed?",
            "A misconfigured health check caused the load balancer to drain all backend instances. The fix was deployed in v3.1.4.",
        ),
        (
            "Sprint 47 Retrospective Notes",
            "Sprint 47 delivered 38 story points out of 42 committed. Key "
            "achievements: user authentication refactor, performance optimization "
            "reducing p95 latency by 40%. Carry-over: the reporting dashboard "
            "needs additional API endpoints.",
            "How many story points were delivered in Sprint 47 and what was the latency improvement?",
            "38 story points were delivered out of 42 committed, and p95 latency was reduced by 40%.",
        ),
        (
            "API Rate Limiting Implementation Plan",
            "The rate limiting implementation will use a token bucket algorithm "
            "with Redis as the backing store. Default limits: 100 req/min per "
            "user, 1000 req/min per IP. Burst allowance of 20% above the steady "
            "rate. Rollout planned in three phases starting July 10th.",
            "What algorithm and backing store will be used for rate limiting, and what are the default per-user limits?",
            "A token bucket algorithm with Redis as the backing store. Default limit is 100 req/min per user.",
        ),
    ],
    "sales": [
        (
            "Proposal Follow-up — Acme Corp",
            "Following up on the proposal sent to Acme Corp on June 20th. "
            "The procurement team indicated they need additional information "
            "about our SLA terms and data residency options for EU compliance. "
            "I've scheduled a call for Thursday to address their concerns.",
            "What additional information does Acme Corp's procurement team need?",
            "They need additional information about SLA terms and data residency options for EU compliance.",
        ),
        (
            "Pipeline Review — July 2026",
            "The July pipeline stands at $2.8M across 47 opportunities. "
            "Weighted forecast is $1.1M. Three deals are in the final negotiation "
            "stage: Acme Corp ($180K), Stark Industries ($340K), and Wayne "
            "Enterprises ($95K). Expected close by month-end.",
            "What is the total July pipeline value and how many opportunities are there?",
            "The July pipeline stands at $2.8M across 47 opportunities.",
        ),
        (
            "Contract Renewal — Globex Industries",
            "Globex Industries' contract expires in 90 days. Current ARR is "
            "$240K. They've requested a 15% reduction for renewal. I propose "
            "counter-offering with a 8% reduction tied to a 2-year commitment "
            "and expanded usage of the analytics module.",
            "What is Globex Industries' current ARR and what reduction did they request?",
            "Current ARR is $240K, and they requested a 15% reduction for renewal.",
        ),
    ],
    "manufacturing": [
        (
            "Production Schedule Update — Line 3",
            "Production Line 3 will undergo scheduled maintenance from July 8th "
            "to July 12th. During this period, output capacity is reduced by 35%. "
            "We've pre-built inventory for high-demand SKUs to minimize customer "
            "impact. Alternative routing available on Lines 1 and 5.",
            "When is the Line 3 maintenance and by how much is capacity reduced?",
            "Maintenance is from July 8th to July 12th, and output capacity is reduced by 35%.",
        ),
        (
            "Quality Incident Report — Batch #2026-0714",
            "Batch #2026-0714 failed quality inspection due to dimensional "
            "tolerance deviation on component A-7. Root cause identified as "
            "tool wear on CNC machine 12. Affected quantity: 480 units. "
            "Rework estimated at 16 labor hours. Corrective action: tool "
            "replacement schedule shortened from 2000 to 1500 cycles.",
            "What was the root cause of the quality failure in batch 2026-0714 and how many units were affected?",
            "The root cause was tool wear on CNC machine 12, and 480 units were affected.",
        ),
        (
            "Supplier Delay Notification — Raw Materials",
            "Supplier TechMaterials Inc. has notified a 2-week delay on the "
            "aluminum alloy shipment (PO-4471). This impacts production of "
            "the X-Series starting July 18th. We're sourcing alternative "
            "material from MetroMetals, pending quality certification.",
            "Which supplier delayed the shipment and what alternative source is being considered?",
            "TechMaterials Inc. delayed the shipment, and MetroMetals is being considered as an alternative source.",
        ),
    ],
    "hr": [
        (
            "Open Enrollment — Benefits 2026",
            "Annual benefits open enrollment runs from July 1st to July 31st. "
            "All employees must review and select their health, dental, and "
            "vision plans. New this year: expanded mental health coverage and "
            "a dependent care FSA option. Information sessions scheduled for "
            "July 5th and 8th.",
            "When does benefits open enrollment run and what is new this year?",
            "Open enrollment runs from July 1st to July 31st. New this year: expanded mental health coverage and a dependent care FSA option.",
        ),
        (
            "New Hire Onboarding Schedule — July Cohort",
            "The July onboarding cohort includes 12 new hires across Engineering, "
            "Sales, and Operations. Day 1 covers HR orientation and IT setup. "
            "Days 2-5 are department-specific training. Please ensure all "
            "managers have confirmed their buddy assignments.",
            "How many new hires are in the July onboarding cohort and what does Day 1 cover?",
            "There are 12 new hires, and Day 1 covers HR orientation and IT setup.",
        ),
        (
            "Performance Review Cycle — Mid-Year",
            "Mid-year performance reviews are due by July 20th. Managers should "
            "complete self-assessments first, then schedule 1:1 meetings with "
            "each direct report. Focus areas: goal progress, blockers, and "
            "development plans. Calibration sessions will be held the week of "
            "July 24th.",
            "When are mid-year performance reviews due and what are the focus areas?",
            "Reviews are due by July 20th, and focus areas are goal progress, blockers, and development plans.",
        ),
    ],
    "legal": [
        (
            "Contract Review — SaaS Agreement v2.1",
            "Please review the updated SaaS agreement (v2.1). Key changes: "
            "revised limitation of liability clause (Section 11), new data "
            "breach notification timeline (72 hours), and updated termination "
            "for convenience terms (30-day notice). Redlines attached for "
            "your review.",
            "What are the key changes in the SaaS agreement v2.1?",
            "Key changes include a revised limitation of liability clause (Section 11), a new 72-hour data breach notification timeline, and updated 30-day notice termination terms.",
        ),
        (
            "NDA Execution — Strategic Partnership",
            "The mutual NDA with DataFlow Inc. has been executed by both "
            "parties. Effective date: July 1, 2026. Term: 3 years. This "
            "enables the technical evaluation and due diligence for the "
            "proposed strategic partnership. Please ensure all shared "
            "materials are marked 'Confidential'.",
            "What is the effective date and term of the NDA with DataFlow Inc.?",
            "The effective date is July 1, 2026, and the term is 3 years.",
        ),
        (
            "Litigation Update — Patent Dispute",
            "The patent dispute with Competitor X has been scheduled for "
            "mediation on August 15th. Our outside counsel recommends "
            "preparing the prior art documentation and expert witness "
            "testimony. Estimated legal costs for Q3: $180K. Settlement "
            "authority requested up to $500K.",
            "When is the patent dispute mediation scheduled and what settlement authority is requested?",
            "Mediation is scheduled for August 15th, and settlement authority up to $500K is requested.",
        ),
    ],
    "it": [
        (
            "System Upgrade — VPN Infrastructure",
            "The VPN infrastructure will be upgraded to OpenVPN 2.6 on July "
            "14th, 2AM-4AM EST. Brief connectivity interruptions expected. "
            "All users must re-authenticate after the upgrade. New features: "
            "multi-factor authentication enforcement and split-tunneling "
            "support. Instructions will be sent separately.",
            "When is the VPN upgrade and what new features will be available?",
            "The upgrade is on July 14th, 2AM-4AM EST. New features include multi-factor authentication enforcement and split-tunneling support.",
        ),
        (
            "Phishing Simulation Results — June",
            "June phishing simulation results: 14% click rate (down from 22% "
            "in May). 3 users submitted credentials on the fake login page. "
            "All have been enrolled in mandatory security awareness training. "
            "Recommend increasing simulation frequency to bi-weekly.",
            "What was the phishing simulation click rate in June and how many users submitted credentials?",
            "The click rate was 14% (down from 22% in May), and 3 users submitted credentials.",
        ),
        (
            "Access Request — New Contractor",
            "Access request for contractor John Smith (DataFlow Inc.): needs "
            "read-only access to the analytics dashboard and Jira project "
            "ENG. Contract duration: 6 months. Manager approval received "
            "from Sarah Chen. Please provision by July 5th.",
            "What access does contractor John Smith need and what is the contract duration?",
            "He needs read-only access to the analytics dashboard and Jira project ENG, with a 6-month contract duration.",
        ),
    ],
    "logistics": [
        (
            "Shipment Delay — Port Congestion Rotterdam",
            "Port congestion at Rotterdam has caused a 5-day delay on "
            "shipment MAEU-784512. ETA revised from July 8th to July 13th. "
            "Affected containers: 4x40ft. We're working with the freight "
            "forwarder to prioritize unloading. Customer notifications have "
            "been sent.",
            "What caused the shipment delay and what is the revised ETA?",
            "Port congestion at Rotterdam caused a 5-day delay. The revised ETA is July 13th (from July 8th).",
        ),
        (
            "Warehouse Capacity Alert — DC-East",
            "DC-East is at 94% capacity, approaching the 95% threshold. "
            "Recommend expediting the inventory transfer of 1,200 SKUs to "
            "DC-Central. Additionally, 3 inbound containers from Asia can "
            "be diverted to DC-South at minimal cost increase.",
            "What is the current capacity of DC-East and how many SKUs should be transferred?",
            "DC-East is at 94% capacity, and 1,200 SKUs should be transferred to DC-Central.",
        ),
        (
            "Carrier Performance Review — Q2",
            "Q2 carrier performance: on-time delivery rate of 94.2% across "
            "all lanes. Top performer: FedEx (97.8%). Below target: Regional "
            "Express (87.1%). Recommend renegotiating the Regional Express "
            "contract or shifting 30% volume to DHL for the underperforming "
            "lanes.",
            "What was the Q2 on-time delivery rate and which carrier was below target?",
            "The on-time delivery rate was 94.2%. Regional Express was below target at 87.1%.",
        ),
    ],
}


# ---------------------------------------------------------------------------
# Addressing patterns to exercise
# ---------------------------------------------------------------------------

_ADDRESS_PATTERNS = [
    # (description, address_template, expected_tags_dict)
    # 1. Plain prefix — no plus sign
    ("plain_prefix", "retriva@retriva-server.com", {}),
    # 2. Prefix + collection only
    ("collection_only", "retriva+emails@retriva-server.com", {}),
    # 3. Prefix + collection + kb
    ("coll_plus_kb", "retriva+emails+eval_kb@retriva-server.com", {}),
    # 4. Prefix + collection + kb + one tag
    ("one_tag", "retriva+emails+eval_kb+priority=high@retriva-server.com",
     {"priority": "high"}),
    # 5. Prefix + collection + kb + two tags
    ("two_tags", "retriva+emails+eval_kb+priority=high+project=alpha@retriva-server.com",
     {"priority": "high", "project": "alpha"}),
    # 6. Prefix + collection + kb + three tags
    ("three_tags", "retriva+emails+eval_kb+priority=medium+project=beta+status=review@retriva-server.com",
     {"priority": "medium", "project": "beta", "status": "review"}),
    # 7. Prefix + collection + kb + four tags
    ("four_tags", "retriva+emails+eval_kb+priority=low+project=gamma+status=draft+dept=ops@retriva-server.com",
     {"priority": "low", "project": "gamma", "status": "draft", "dept": "ops"}),
    # 8. Prefix + kb only (empty collection segment)
    ("kb_only", "retriva++eval_kb@retriva-server.com", {}),
    # 9. Prefix + kb + tags (empty collection, with tags)
    ("kb_only_with_tags", "retriva++eval_kb+priority=urgent+category=incident@retriva-server.com",
     {"priority": "urgent", "category": "incident"}),
    # 10. Prefix + tags only (empty collection and kb)
    ("tags_only", "retriva+++priority=normal+source=external@retriva-server.com",
     {"priority": "normal", "source": "external"}),
]


def generate_dataset(output_path: str, seed: int = 42, count: int = 100):
    """Generate the email dataset JSONL file."""
    rng = random.Random(seed)

    # Flatten all field entries into (field, subject, body, question, answer) tuples
    all_entries = []
    for field, entries in _FIELDS.items():
        for subject, body, question, answer in entries:
            all_entries.append((field, subject, body, question, answer))

    base_date = datetime(2026, 7, 1, 9, 0, 0)

    messages = []
    for i in range(count):
        field, subject, body, question, expected_answer = rng.choice(all_entries)

        # Cycle through address patterns to ensure all are exercised
        pattern_desc, address, expected_tags = _ADDRESS_PATTERNS[i % len(_ADDRESS_PATTERNS)]

        # Vary the sender
        sender_names = [
            "john.doe", "jane.smith", "m.brown", "alex.wilson", "pat.lee",
            "k.tanaka", "s.garcia", "r.muller", "l.rossi", "d.kowalski",
        ]
        sender_domains = ["company.com", "corp.net", "enterprise.io", "firm.org"]
        sender = f"{rng.choice(sender_names)}@{rng.choice(sender_domains)}"

        # Stagger dates
        msg_date = base_date + timedelta(hours=i * 3, minutes=rng.randint(0, 59))
        date_str = msg_date.strftime("%a, %d %b %Y %H:%M:%S +0000")

        message_id = f"<email-{i+1:04d}-{field}@retriva-eval.local>"

        messages.append({
            "id": f"email_{i+1:04d}",
            "message_id": message_id,
            "from": sender,
            "to": address,
            "cc": "",
            "subject": f"[{field.upper()}] {subject}",
            "body": body,
            "date": date_str,
            "field": field,
            "address_pattern": pattern_desc,
            "expected_tags": expected_tags,
            "expected_kb": "eval_kb" if "eval_kb" in address else "",
            "expected_collection": "emails" if "emails" in address.split("+") else "",
            "question": question,
            "expected_answer": expected_answer,
        })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for msg in messages:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")

    print(f"Generated {len(messages)} messages → {output_path}")

    # Print pattern distribution
    from collections import Counter
    pattern_counts = Counter(m["address_pattern"] for m in messages)
    print("\nAddress pattern distribution:")
    for pattern, count in sorted(pattern_counts.items()):
        print(f"  {pattern:25s} {count:3d}")

    field_counts = Counter(m["field"] for m in messages)
    print("\nField distribution:")
    for field, count in sorted(field_counts.items()):
        print(f"  {field:15s} {count:3d}")


if __name__ == "__main__":
    output = os.path.join(os.path.dirname(__file__), "data", "emails.jsonl")
    generate_dataset(output, seed=42, count=100)
