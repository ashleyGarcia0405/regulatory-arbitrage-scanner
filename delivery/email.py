"""
Email delivery via Resend API.
Sends a digest of the top N high-opportunity regulatory briefs.
"""

import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
import resend

load_dotenv()


def _plain_text(briefs: list[dict]) -> str:
    lines = [
        "REGULATORY ARBITRAGE SCANNER — WEEKLY DIGEST",
        f"Generated: {datetime.now(timezone.utc).strftime('%B %d, %Y')}",
        "=" * 60,
        "",
    ]

    for i, reg in enumerate(briefs, 1):
        opp = reg.get("opportunity") or {}
        lines += [
            f"{i}. {reg.get('title', '')}",
            f"   Source: {reg.get('source', '')} | Published: {reg.get('published_at', '')}",
            f"   Urgency: {opp.get('urgency', '')} | Score: {opp.get('total_score', 0)}/20",
            "",
            f"   SUMMARY: {opp.get('rule_summary', '')}",
            "",
            f"   OPPORTUNITY: {opp.get('opportunity_hypothesis', '')}",
            "",
            f"   WHO WINS: {opp.get('who_wins', '')}",
            "",
            f"   PRECEDENT: {opp.get('historical_precedent', '')}",
            "",
            f"   COMPLIANCE PRODUCT: {opp.get('compliance_product_opportunity', '')}",
            "",
            f"   URGENCY REASON: {opp.get('urgency_reason', '')}",
            "",
            f"   SOURCE: {reg.get('url', '')}",
            "",
            "-" * 60,
            "",
        ]

    lines.append("To unsubscribe or change preferences, reply to this email.")
    return "\n".join(lines)


def _html_body(briefs: list[dict]) -> str:
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")

    urgency_colors = {
        "High": "#dc2626",
        "Medium": "#d97706",
        "Low": "#16a34a",
    }

    cards = []
    for reg in briefs:
        opp = reg.get("opportunity") or {}
        urgency = opp.get("urgency", "Low")
        color = urgency_colors.get(urgency, "#16a34a")
        sectors = ", ".join(opp.get("sectors", []))
        total_score = opp.get("total_score", 0)

        cards.append(f"""
        <div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;padding:24px;margin-bottom:20px;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">
            <div>
              <p style="margin:0 0 4px;font-size:11px;color:#9ca3af;text-transform:uppercase;letter-spacing:0.05em;">
                {reg.get('source', '')} &middot; {reg.get('published_at', '')}
              </p>
              <h2 style="margin:0;font-size:16px;font-weight:600;color:#111827;">{reg.get('title', '')}</h2>
            </div>
            <span style="flex-shrink:0;margin-left:12px;background:{color}1a;color:{color};border:1px solid {color}40;
                         padding:2px 10px;border-radius:9999px;font-size:12px;font-weight:600;">
              {urgency}
            </span>
          </div>

          <p style="margin:0 0 12px;font-size:13px;color:#6b7280;">Sectors: {sectors}</p>

          <p style="margin:0 0 12px;font-size:14px;color:#374151;">
            <strong>Summary:</strong> {opp.get('rule_summary', '')}
          </p>

          <div style="background:#eef2ff;border:1px solid #c7d2fe;border-radius:8px;padding:12px;margin-bottom:12px;">
            <p style="margin:0 0 6px;font-size:13px;font-weight:600;color:#4338ca;">Opportunity Hypothesis</p>
            <p style="margin:0;font-size:13px;color:#4f46e5;">{opp.get('opportunity_hypothesis', '')}</p>
          </div>

          <table style="width:100%;border-collapse:collapse;margin-bottom:12px;">
            <tr>
              <td style="width:50%;vertical-align:top;padding-right:8px;">
                <div style="background:#f9fafb;border-radius:8px;padding:10px;">
                  <p style="margin:0 0 4px;font-size:12px;font-weight:600;color:#374151;">Who Wins</p>
                  <p style="margin:0;font-size:12px;color:#6b7280;">{opp.get('who_wins', '')}</p>
                </div>
              </td>
              <td style="width:50%;vertical-align:top;padding-left:8px;">
                <div style="background:#f9fafb;border-radius:8px;padding:10px;">
                  <p style="margin:0 0 4px;font-size:12px;font-weight:600;color:#374151;">Historical Precedent</p>
                  <p style="margin:0;font-size:12px;color:#6b7280;">{opp.get('historical_precedent', '')}</p>
                </div>
              </td>
            </tr>
          </table>

          <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:10px;margin-bottom:12px;">
            <p style="margin:0 0 4px;font-size:12px;font-weight:600;color:#92400e;">Compliance Product Opportunity</p>
            <p style="margin:0;font-size:12px;color:#78350f;">{opp.get('compliance_product_opportunity', '')}</p>
          </div>

          <div style="display:flex;justify-content:space-between;align-items:center;">
            <p style="margin:0;font-size:12px;color:#9ca3af;">
              Score: <strong style="color:#111827;">{total_score}/20</strong>
            </p>
            <a href="{reg.get('url', '#')}" style="font-size:13px;color:#4f46e5;font-weight:500;">
              View Source →
            </a>
          </div>
        </div>""")

    cards_html = "\n".join(cards)

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="max-width:640px;margin:0 auto;padding:32px 16px;">
    <div style="text-align:center;margin-bottom:32px;">
      <h1 style="margin:0 0 4px;font-size:24px;font-weight:700;color:#111827;">
        Regulatory Arbitrage Scanner
      </h1>
      <p style="margin:0;font-size:14px;color:#6b7280;">
        Weekly digest &middot; {date_str} &middot; {len(briefs)} brief{"s" if len(briefs) != 1 else ""}
      </p>
    </div>

    {cards_html}

    <div style="text-align:center;margin-top:24px;padding-top:24px;border-top:1px solid #e5e7eb;">
      <p style="margin:0;font-size:12px;color:#9ca3af;">
        Powered by Claude &middot; Regulatory Arbitrage Scanner
      </p>
    </div>
  </div>
</body>
</html>"""


def send_digest(briefs: list[dict], top_n: int = 5):
    """Send a digest of the top N briefs via Resend."""
    api_key = os.environ.get("RESEND_API_KEY")
    recipient = os.environ.get("RECIPIENT_EMAIL")

    if not api_key:
        print("[Email] RESEND_API_KEY not set — skipping email.")
        return False
    if not recipient:
        print("[Email] RECIPIENT_EMAIL not set — skipping email.")
        return False

    resend.api_key = api_key

    top = briefs[:top_n]
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    subject = f"Regulatory Arbitrage Digest — {date_str} ({len(top)} new opportunities)"

    try:
        response = resend.Emails.send(
            {
                "from": "Regulatory Scanner <onboarding@resend.dev>",
                "to": [recipient],
                "subject": subject,
                "text": _plain_text(top),
                "html": _html_body(top),
            }
        )
        print(f"[Email] Sent digest to {recipient} — ID: {response.get('id', 'unknown')}")
        return True
    except Exception as e:
        print(f"[Email] Failed to send: {e}")
        return False


if __name__ == "__main__":
    # Smoke test with dummy data
    dummy = [
        {
            "source": "Federal Register",
            "title": "Final Rule: Mandatory Safety Standards for Lithium-Ion Batteries",
            "published_at": "2026-04-10",
            "url": "https://federalregister.gov/example",
            "opportunity": {
                "rule_summary": "Requires all consumer lithium-ion batteries to meet UL 9540 standards by 2027.",
                "sectors": ["Energy", "Consumer Electronics", "Manufacturing"],
                "opportunity_hypothesis": "A compliance certification SaaS could help small manufacturers navigate the new standard quickly. First movers can capture the SMB market before larger players build in-house solutions.",
                "who_wins": "Battery importers and consumer electronics OEMs with under 500 employees",
                "urgency": "High",
                "urgency_reason": "18-month compliance window creates an immediate certification rush",
                "historical_precedent": "Similar to how UL certification services boomed after CPSC safety mandates in 2008",
                "compliance_product_opportunity": "Automated compliance gap analysis tool for battery manufacturers",
                "urgency_score": 5,
                "market_size_score": 4,
                "defensibility_score": 3,
                "regulatory_certainty_score": 4,
                "total_score": 16,
            },
        }
    ]
    send_digest(dummy, top_n=1)