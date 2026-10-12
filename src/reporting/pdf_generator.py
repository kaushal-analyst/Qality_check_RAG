"""PDF report generation service using ReportLab."""
import io
from typing import Dict, Any, List, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.units import inch
from datetime import datetime

def generate_complaint_investigation_pdf(
    complaint: Dict[str, Any],
    evaluation: Optional[Dict[str, Any]] = None,
    criteria_results: Optional[List[Dict[str, Any]]] = None,
    risk: Optional[Dict[str, Any]] = None,
    hypotheses: Optional[List[Dict[str, Any]]] = None,
    capas: Optional[List[Dict[str, Any]]] = None
) -> bytes:
    """Generates a comprehensive PDF Quality Complaint Investigation Report."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom Corporate Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0F172A')
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569')
    )
    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=10,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155')
    )
    bold_style = ParagraphStyle(
        'BodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Italic'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#64748B')
    )

    story = []

    # 1. Header Banner
    story.append(Paragraph("CODE SPACE TECHLAB | QUALITY ASSURANCE SYSTEM", subtitle_style))
    story.append(Paragraph(f"Complaint Quality Investigation Report: {complaint.get('complaint_id')}", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC | Status: {complaint.get('current_status')}", subtitle_style))
    story.append(Spacer(1, 10))

    # 2. Case Overview Table
    overview_data = [
        [Paragraph("<b>Product Name:</b>", body_style), Paragraph(str(complaint.get("product_name", "N/A")), body_style),
         Paragraph("<b>SKU:</b>", body_style), Paragraph(str(complaint.get("sku", "N/A")), body_style)],
        [Paragraph("<b>Customer/Retailer:</b>", body_style), Paragraph(str(complaint.get("customer_name", "General")), body_style),
         Paragraph("<b>Reporter:</b>", body_style), Paragraph(str(complaint.get("reporter_type", "N/A")), body_style)],
        [Paragraph("<b>Order/Batch No:</b>", body_style), Paragraph(str(complaint.get("order_batch_number", "N/A")), body_style),
         Paragraph("<b>Date Received:</b>", body_style), Paragraph(str(complaint.get("date_received", "N/A")), body_style)],
        [Paragraph("<b>Severity / Urgency:</b>", body_style), Paragraph(f"{complaint.get('severity')} / {complaint.get('urgency')}", body_style),
         Paragraph("<b>Units Affected:</b>", body_style), Paragraph(str(complaint.get("quantity_affected", 1)), body_style)]
    ]
    t_overview = Table(overview_data, colWidths=[1.3*inch, 2.2*inch, 1.3*inch, 2.2*inch])
    t_overview.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_overview)
    story.append(Spacer(1, 10))

    # 3. Defect Description
    story.append(Paragraph("1. Complaint Defect Description", h2_style))
    story.append(Paragraph(complaint.get("description", "No description provided."), body_style))
    story.append(Spacer(1, 10))

    # 4. Evaluation Engine Outcomes
    if evaluation:
        story.append(Paragraph("2. Quality Evaluation & Scoring Results", h2_style))
        eval_summary = [
            [Paragraph("<b>Overall Quality Score:</b>", body_style), Paragraph(f"<b>{evaluation.get('quality_score', 'N/A')}%</b>", bold_style),
             Paragraph("<b>Scoring Outcome:</b>", body_style), Paragraph(f"<b>{evaluation.get('scoring_status', 'N/A')}</b>", bold_style)],
            [Paragraph("<b>Mandatory Failures:</b>", body_style), Paragraph(str(evaluation.get("mandatory_failures_count", 0)), body_style),
             Paragraph("<b>Evidence Completeness:</b>", body_style), Paragraph(f"{evaluation.get('evidence_completeness_pct', 0)}%", body_style)],
            [Paragraph("<b>Manager Sign-Off:</b>", body_style), Paragraph(str(evaluation.get("manager_approval_status", "Pending Review")), body_style),
             Paragraph("<b>Rule Version:</b>", body_style), Paragraph(str(evaluation.get("rule_version", "1.0")), body_style)]
        ]
        t_eval = Table(eval_summary, colWidths=[1.5*inch, 2.0*inch, 1.5*inch, 2.0*inch])
        t_eval.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F1F5F9')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#94A3B8')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t_eval)
        story.append(Spacer(1, 6))

    # 5. Criterion Breakdown
    if criteria_results:
        story.append(Paragraph("3. Detailed Quality Criteria Findings", h2_style))
        crit_rows = [[Paragraph("<b>Code</b>", bold_style), Paragraph("<b>Criterion</b>", bold_style), Paragraph("<b>Observed vs Expected</b>", bold_style), Paragraph("<b>Outcome</b>", bold_style)]]
        for c in criteria_results:
            crit_rows.append([
                Paragraph(c.get("criterion_code", ""), body_style),
                Paragraph(c.get("criterion_name", ""), body_style),
                Paragraph(f"Obs: {c.get('observed_value', 'N/A')}<br/>Exp: {c.get('expected_value', 'N/A')}", body_style),
                Paragraph(f"<b>{c.get('outcome', 'N/A')}</b>", bold_style)
            ])
        t_crit = Table(crit_rows, colWidths=[1.1*inch, 2.2*inch, 2.7*inch, 1.0*inch])
        t_crit.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E2E8F0')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t_crit)
        story.append(Spacer(1, 10))

    # 6. Risk Assessment
    if risk:
        story.append(Paragraph("4. Risk Assessment & Safety Evaluation", h2_style))
        risk_text = f"<b>Overall Risk Level: {risk.get('overall_risk_level', 'N/A')}</b> (Score: {risk.get('risk_score', 'N/A')})<br/>"
        risk_text += f"Recurrence incidents on SKU: {risk.get('repeat_incident_count', 0)} | Safety Flag: {'YES (Safety Critical)' if risk.get('safety_flag') else 'No'}<br/>"
        risk_text += f"<i>Rationale:</i> {risk.get('rationale', '')}"
        story.append(Paragraph(risk_text, body_style))
        story.append(Spacer(1, 10))

    # 7. Root Cause Hypotheses
    if hypotheses:
        story.append(Paragraph("5. AI-Assisted Root Cause Hypotheses", h2_style))
        for idx, h in enumerate(hypotheses, 1):
            h_text = f"<b>Hypothesis {idx} [{h.get('category')}]:</b> {h.get('hypothesis_statement')}<br/>"
            h_text += f"• <i>Supporting:</i> {h.get('supporting_evidence', 'N/A')}<br/>"
            h_text += f"• <i>Missing info:</i> {h.get('missing_information', 'N/A')} | <i>Status:</i> <b>{h.get('verification_status')}</b>"
            story.append(Paragraph(h_text, body_style))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 6))

    # 8. CAPA Actions
    if capas:
        story.append(Paragraph("6. Corrective and Preventive Actions (CAPA)", h2_style))
        capa_rows = [[Paragraph("<b>Type</b>", bold_style), Paragraph("<b>Title & Description</b>", bold_style), Paragraph("<b>Department</b>", bold_style), Paragraph("<b>Status</b>", bold_style)]]
        for cp in capas:
            capa_rows.append([
                Paragraph(cp.get("capa_type", ""), bold_style),
                Paragraph(f"<b>{cp.get('title')}</b><br/>{cp.get('description')}", body_style),
                Paragraph(cp.get("department", ""), body_style),
                Paragraph(cp.get("status", ""), bold_style)
            ])
        t_capa = Table(capa_rows, colWidths=[1.1*inch, 3.8*inch, 1.2*inch, 0.9*inch])
        t_capa.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E2E8F0')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t_capa)
        story.append(Spacer(1, 10))

    # 9. Manager Sign-Off
    story.append(Paragraph("7. Quality Manager Sign-Off & Approvals", h2_style))
    sign_data = [
        [Paragraph(f"<b>Manager Decision:</b> {evaluation.get('manager_approval_status', 'Pending') if evaluation else 'Pending'}", body_style),
         Paragraph("<b>Authorized Signature:</b> ___________________________", body_style)],
        [Paragraph(f"<b>Manager Notes:</b> {evaluation.get('manager_notes', 'N/A') if evaluation else 'N/A'}", body_style),
         Paragraph("<b>Date of Final Sign-Off:</b> ___________________________", body_style)]
    ]
    t_sign = Table(sign_data, colWidths=[3.5*inch, 3.5*inch])
    t_sign.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#94A3B8')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('PADDING', (0,0), (-1,-1), 6)
    ]))
    story.append(t_sign)
    story.append(Spacer(1, 15))

    # Disclaimer
    story.append(Paragraph(
        "CONFIDENTIAL & PROPRIETARY — CODE SPACE TECHLAB QUALITY ASSURANCE SYSTEM.<br/>"
        "AI-generated hypotheses and recommendations serve as decision support metrics only and do not replace certified physical testing or regulatory lab compliance declarations.",
        disclaimer_style
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
