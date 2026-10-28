"""
Executive-Grade 16:9 Presentation PDF using ReportLab with proper PageTemplate background rendering.
"""

from reportlab.lib import colors
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

PAGE_WIDTH = 960
PAGE_HEIGHT = 540

# Colors
BG_DARK = colors.HexColor("#0A1128")       # Dark Navy
CARD_BG = colors.HexColor("#131E3A")       # Slate Card
CARD_BORDER = colors.HexColor("#2B4C7E")   # Border
ACCENT_CYAN = colors.HexColor("#00D2FF")   # Cyan
ACCENT_BLUE = colors.HexColor("#4299E1")   # Blue
TEXT_WHITE = colors.HexColor("#F8FAFC")    # White text
TEXT_MUTED = colors.HexColor("#A0AEC0")    # Muted Slate
ACCENT_GREEN = colors.HexColor("#48BB78")  # Green
ACCENT_RED = colors.HexColor("#F56565")    # Red
ACCENT_AMBER = colors.HexColor("#ED8936")  # Amber
ACCENT_PURPLE = colors.HexColor("#9F7AEA") # Purple


def draw_background(canvas, doc):
    """Draws background and headers BEFORE flowables are drawn."""
    canvas.saveState()
    w, h = PAGE_WIDTH, PAGE_HEIGHT

    # Dark background
    canvas.setFillColor(BG_DARK)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)

    # Top accent line
    canvas.setFillColor(ACCENT_CYAN)
    canvas.rect(0, h - 5, w, 5, fill=1, stroke=0)

    # Header on pages >= 2
    if doc.page > 1:
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(ACCENT_CYAN)
        canvas.drawString(40, h - 22, "PBL-III (AIM3170) • MENTOR PRESENTATION")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(TEXT_MUTED)
        canvas.drawRightString(w - 40, h - 22, "AI-POWERED UPI SCAM DETECTION")

        canvas.setStrokeColor(colors.HexColor("#1E293B"))
        canvas.setLineWidth(0.8)
        canvas.line(40, h - 26, w - 40, h - 26)

    # Footer
    canvas.setStrokeColor(colors.HexColor("#1E293B"))
    canvas.setLineWidth(0.8)
    canvas.line(40, 26, w - 40, 26)

    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(TEXT_MUTED)
    canvas.drawString(40, 15, "Dept. of Artificial Intelligence & Machine Learning  |  Manipal University Jaipur")
    canvas.drawRightString(w - 40, 15, f"Slide {doc.page} of 9")

    canvas.restoreState()


def build_executive_pdf():
    pdf_filename = "UPI_Scam_Detection_Executive_Presentation.pdf"

    frame = Frame(40, 32, PAGE_WIDTH - 80, PAGE_HEIGHT - 66, id='normal', leftPadding=0, topPadding=0, rightPadding=0, bottomPadding=0)
    template = PageTemplate(id='Executive', frames=frame, onPage=draw_background)
    
    doc = BaseDocTemplate(
        pdf_filename,
        pagesize=(PAGE_WIDTH, PAGE_HEIGHT),
        pageTemplates=[template]
    )

    styles = getSampleStyleSheet()

    # Typography
    slide_title_style = ParagraphStyle(
        'SlideTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=TEXT_WHITE,
        spaceAfter=2
    )

    slide_subtitle_style = ParagraphStyle(
        'SlideSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=ACCENT_BLUE,
        spaceAfter=10
    )

    card_h_style = ParagraphStyle(
        'CardHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=ACCENT_CYAN,
        spaceAfter=4
    )

    bullet_style = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12.5,
        textColor=TEXT_MUTED,
        leftIndent=10,
        firstLineIndent=-8,
        spaceAfter=3
    )

    story = []

    def make_card(content_list, width, border_color=CARD_BORDER, bg_color=CARD_BG, padding=8):
        t = Table([[content_list]], colWidths=[width])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg_color),
            ('BOX', (0, 0), (-1, -1), 1.2, border_color),
            ('TOPPADDING', (0, 0), (-1, -1), padding),
            ('BOTTOMPADDING', (0, 0), (-1, -1), padding),
            ('LEFTPADDING', (0, 0), (-1, -1), padding + 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), padding + 2),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        return t

    # =========================================================================
    # SLIDE 1: TITLE SLIDE
    # =========================================================================
    story.append(Spacer(1, 15))
    s1_badge = Paragraph("<font color='#00D2FF'><b>PBL-III (AIM3170) • MENTOR PRESENTATION</b></font>", ParagraphStyle('B1', alignment=1, fontSize=9.5, fontName='Helvetica-Bold'))
    s1_title = Paragraph("AI-Powered UPI Scam & Fraud Detection", ParagraphStyle('T1', alignment=1, fontSize=26, leading=32, fontName='Helvetica-Bold', textColor=TEXT_WHITE, spaceBefore=6, spaceAfter=4))
    s1_sub = Paragraph("Behavioral Anomaly Detection & Multi-Hop Graph Layering Analytics", ParagraphStyle('TS1', alignment=1, fontSize=13, leading=16, fontName='Helvetica', textColor=ACCENT_BLUE, spaceAfter=16))
    
    meta_1 = Paragraph("<font color='#00D2FF'><b>PROJECT DOMAIN</b></font><br/><font color='#A0AEC0'>• FinTech Cybersecurity<br/>• Unsupervised Anomaly Detection<br/>• Directed Graph NetworkX</font>", ParagraphStyle('M1', fontSize=8.5, leading=12))
    meta_2 = Paragraph("<font color='#00D2FF'><b>CORE ML ENGINE</b></font><br/><font color='#A0AEC0'>• Isolation Forest Model<br/>• StandardScaler Normalization<br/>• Exact 30 Model Features</font>", ParagraphStyle('M2', fontSize=8.5, leading=12))
    meta_3 = Paragraph("<font color='#00D2FF'><b>ACADEMIC INSTITUTION</b></font><br/><font color='#A0AEC0'>• Manipal University Jaipur<br/>• Dept. of AIML (2026)<br/>• Application-Based Project</font>", ParagraphStyle('M3', fontSize=8.5, leading=12))
    
    t_meta = Table([[
        make_card([meta_1], 260),
        make_card([meta_2], 260),
        make_card([meta_3], 260)
    ]], colWidths=[280, 280, 280])
    t_meta.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))

    s1_content = [
        s1_badge,
        s1_title,
        s1_sub,
        HRFlowable(width="60%", thickness=1.5, color=ACCENT_CYAN, spaceAfter=16, hAlign='CENTER'),
        t_meta
    ]
    story.append(make_card(s1_content, 875, border_color=ACCENT_CYAN, bg_color=colors.HexColor("#0E1730"), padding=18))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 2: PROBLEM STATEMENT & MOTIVATION
    # =========================================================================
    story.append(Paragraph("1. Problem Statement & Industry Motivation", slide_title_style))
    story.append(Paragraph("Why traditional payment fraud rules fail in real-time UPI ecosystems", slide_subtitle_style))

    c2_1 = [
        Paragraph("<b>The Modern UPI Scam Challenge</b>", card_h_style),
        Paragraph("• <font color='#00D2FF'><b>Massive Velocity & Irreversibility:</b></font> Instant settlements give victims zero rollback window.", bullet_style),
        Paragraph("• <font color='#00D2FF'><b>Social Engineering Scams:</b></font> Phishing QR codes, fake refund links, and remote access tools coerce authorized debits.", bullet_style),
        Paragraph("• <font color='#00D2FF'><b>Account Takeover Bursts:</b></font> Unrecognized devices draining 100% balance during nocturnal hours (22:00 – 06:00).", bullet_style),
        Paragraph("• <font color='#00D2FF'><b>Mule Layering Networks:</b></font> Stolen money is split across multiple intermediary accounts within minutes to prevent fund freezing.", bullet_style),
    ]

    c2_2 = [
        Paragraph("<b>Why Traditional Rule Engines Fail</b>", ParagraphStyle('CH2', parent=card_h_style, textColor=ACCENT_AMBER)),
        Paragraph("• <font color='#ED8936'><b>High False Positive Rates:</b></font> Static rules (Amount > $50k) block genuine users while missing sophisticated micro-layering.", bullet_style),
        Paragraph("• <font color='#ED8936'><b>Siloed Per-Transaction View:</b></font> Evaluating transfers individually fails to detect multi-transfer bursts and rapid forwarding chains.", bullet_style),
        Paragraph("• <font color='#ED8936'><b>Lack of Explainability:</b></font> Black-box fraud scores lack interpretable behavioral context required for fast triage.", bullet_style),
        Paragraph("• <font color='#ED8936'><b>Our Core Approach:</b></font> Unsupervised Isolation Forest + 30 chronological behavioral features + NetworkX graph topology.", bullet_style),
    ]

    t2 = Table([[make_card(c2_1, 430), make_card(c2_2, 430, border_color=ACCENT_AMBER)]], colWidths=[440, 440])
    story.append(t2)
    story.append(Spacer(1, 8))

    bot_text = Paragraph("🎯 <b>Objective:</b> Build an interactive batch investigation system that ingests monthly transaction datasets, computes 30 leak-free behavioral features, ranks suspicious transactions by anomaly score, and provides actionable triage evidence.", ParagraphStyle('B2', fontName='Helvetica-Bold', fontSize=9, textColor=TEXT_WHITE))
    story.append(make_card([bot_text], 875, border_color=ACCENT_CYAN, bg_color=colors.HexColor("#0E1730"), padding=6))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 3: PBL-II RECAP & TRANSITION
    # =========================================================================
    story.append(Paragraph("2. Previous Semester (PBL-II) Recap & Transition", slide_title_style))
    story.append(Paragraph("Building upon proven competencies in machine learning, user interfaces, and persistence", slide_subtitle_style))

    c3_1 = [
        Paragraph("<b>PBL-II Foundation (AI Health Assistant)</b>", ParagraphStyle('CH3_1', parent=card_h_style, textColor=ACCENT_GREEN)),
        Paragraph("• <font color='#48BB78'><b>Supervised Classification:</b></font> Trained multi-label classification models on user symptom vectors.", bullet_style),
        Paragraph("• <font color='#48BB78'><b>Fuzzy Dietary Recommendation:</b></font> Token-sort fuzzy matching on structured food knowledge bases.", bullet_style),
        Paragraph("• <font color='#48BB78'><b>Multi-Tab Streamlit UI:</b></font> Responsive web dashboards with authentication and session states.", bullet_style),
        Paragraph("• <font color='#48BB78'><b>Dual Data Persistence:</b></font> MongoDB database with structured local JSON fallback.", bullet_style),
        Paragraph("• <font color='#48BB78'><b>Core Competency:</b></font> Model serialization, validation, and full-stack Python deployment.", bullet_style),
    ]

    c3_2 = [
        Paragraph("<b>PBL-III Evolution (UPI Scam Detection)</b>", card_h_style),
        Paragraph("• <font color='#00D2FF'><b>Supervised ➔ Unsupervised:</b></font> Replaced static class labels with Isolation Forest to detect zero-day attacks without ground truth bias.", bullet_style),
        Paragraph("• <font color='#00D2FF'><b>Single Input ➔ Full Batch Analytics:</b></font> Ingesting full monthly transaction datasets rather than single form inputs.", bullet_style),
        Paragraph("• <font color='#00D2FF'><b>Leak-Free Feature Engineering:</b></font> Engineered 30 temporal, rolling-window, and expanding statistics strictly prior to each event.", bullet_style),
        Paragraph("• <font color='#00D2FF'><b>Relational Graph Modeling:</b></font> Added NetworkX graph layer to trace multi-hop layering chains (A ➔ B ➔ C ➔ D).", bullet_style),
        Paragraph("• <font color='#00D2FF'><b>Investigative Decision Support:</b></font> Tiered risk classifications and feature vector inspection.", bullet_style),
    ]

    t3 = Table([[make_card(c3_1, 430, border_color=ACCENT_GREEN), make_card(c3_2, 430)]], colWidths=[440, 440])
    story.append(t3)
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 4: SYSTEM ARCHITECTURE (6-STAGE PIPELINE)
    # =========================================================================
    story.append(Paragraph("3. End-to-End System Architecture", slide_title_style))
    story.append(Paragraph("Reproducible, data-leak-free batch processing and inference pipeline", slide_subtitle_style))

    stages_top = [
        Paragraph("<b>01. BATCH UPLOAD</b><br/><font color='#A0AEC0'>• 14 Raw Columns<br/>• Monthly Datasets<br/>• Format Validation</font>", ParagraphStyle('S1', fontSize=8, leading=11, textColor=ACCENT_BLUE)),
        Paragraph("<b>02. DATA VALIDATION</b><br/><font color='#A0AEC0'>• Nulls & Duplicate IDs<br/>• Non-negative Values<br/>• Datetime Parsing</font>", ParagraphStyle('S2', fontSize=8, leading=11, textColor=ACCENT_CYAN)),
        Paragraph("<b>03. FEATURE ENGINE</b><br/><font color='#A0AEC0'>• Chronological Sorting<br/>• 30 ML Features<br/>• No Future Leakage</font>", ParagraphStyle('S3', fontSize=8, leading=11, textColor=ACCENT_PURPLE))
    ]

    stages_bot = [
        Paragraph("<b>04. PREPROCESSING</b><br/><font color='#A0AEC0'>• np.log1p (11 features)<br/>• Scaler transform()<br/>• Never refitted</font>", ParagraphStyle('S4', fontSize=8, leading=11, textColor=ACCENT_AMBER)),
        Paragraph("<b>05. ISOLATION FOREST</b><br/><font color='#A0AEC0'>• Decision Score Output<br/>• Predict: Normal/Anomaly<br/>• Zero Retraining</font>", ParagraphStyle('S5', fontSize=8, leading=11, textColor=ACCENT_RED)),
        Paragraph("<b>06. STREAMLIT UI</b><br/><font color='#A0AEC0'>• KPIs & Ranked Table<br/>• 30-Feature Deep-Dive<br/>• Scored CSV Export</font>", ParagraphStyle('S6', fontSize=8, leading=11, textColor=ACCENT_GREEN))
    ]

    t_arch_top = Table([[
        make_card([stages_top[0]], 270, border_color=ACCENT_BLUE),
        make_card([stages_top[1]], 270, border_color=ACCENT_CYAN),
        make_card([stages_top[2]], 270, border_color=ACCENT_PURPLE)
    ]], colWidths=[293, 293, 293])

    t_arch_bot = Table([[
        make_card([stages_bot[0]], 270, border_color=ACCENT_AMBER),
        make_card([stages_bot[1]], 270, border_color=ACCENT_RED),
        make_card([stages_bot[2]], 270, border_color=ACCENT_GREEN)
    ]], colWidths=[293, 293, 293])

    story.append(t_arch_top)
    story.append(Spacer(1, 6))
    story.append(t_arch_bot)
    story.append(Spacer(1, 8))

    foot_arch = Paragraph("🔒 <b>Architectural Rule:</b> Pre-trained Isolation Forest and StandardScaler are completely immutable artifacts. No refitting or retraining occurs during inference.", ParagraphStyle('AF', fontName='Helvetica-Bold', fontSize=8.5, textColor=ACCENT_CYAN))
    story.append(make_card([foot_arch], 875, border_color=CARD_BORDER, bg_color=colors.HexColor("#0E1730"), padding=5))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 5: THE 30 MODEL FEATURES
    # =========================================================================
    story.append(Paragraph("4. Feature Engineering: The 30 Model Features", slide_title_style))
    story.append(Paragraph("Vectorized extraction strictly prior to current transaction to avoid future leakage", slide_subtitle_style))

    f1 = Paragraph("<b>1. Direct & Temporal Features (10)</b><br/><font color='#A0AEC0'>• amount, transaction_step, sender_old_balance, sender_new_balance<br/>• receiver_old_balance, receiver_new_balance<br/>• device_change_flag, new_device_flag<br/>• transaction_hour (0–23), is_night (22:00–06:00)</font>", ParagraphStyle('F1', fontSize=8, leading=11, textColor=ACCENT_BLUE))
    f2 = Paragraph("<b>2. Historical Interaction Counts (6)</b><br/><font color='#A0AEC0'>• sender_txn_count_before (Prior sent txns)<br/>• same_step_txn_count_before (Txns in same step)<br/>• sender_receiver_txn_count_before (Pair history)<br/>• sender_unique_recipients_before, receiver_txn_count_before, receiver_unique_senders_before</font>", ParagraphStyle('F2', fontSize=8, leading=11, textColor=ACCENT_CYAN))
    f3 = Paragraph("<b>3. Expanding Statistics & Ratios (6)</b><br/><font color='#A0AEC0'>• sender_balance_ratio (amount / [sender_old_balance + 1])<br/>• time_since_previous_sender_txn (Hours, -1 if 1st txn)<br/>• sender_amount_mean_before & sender_amount_std_before<br/>• amount_deviation & amount_zscore (Normalized deviation)</font>", ParagraphStyle('F3', fontSize=8, leading=11, textColor=ACCENT_AMBER))
    f4 = Paragraph("<b>4. Rolling Velocity & Chains (8)</b><br/><font color='#A0AEC0'>• txns_last_1h, txns_last_6h, txns_last_24h (Rolling searchsorted)<br/>• rapid_transaction_flag (Burst indicator: time <= 6min)<br/>• hop_number (Position in transfer money flow chain)<br/>• chain_length & chain_duration_steps, transaction_frequency</font>", ParagraphStyle('F4', fontSize=8, leading=11, textColor=ACCENT_PURPLE))

    t_f_top = Table([[make_card([f1], 430, border_color=ACCENT_BLUE), make_card([f2], 430, border_color=ACCENT_CYAN)]], colWidths=[440, 440])
    t_f_bot = Table([[make_card([f3], 430, border_color=ACCENT_AMBER), make_card([f4], 430, border_color=ACCENT_PURPLE)]], colWidths=[440, 440])

    story.append(t_f_top)
    story.append(Spacer(1, 6))
    story.append(t_f_bot)
    story.append(Spacer(1, 8))

    foot_f = Paragraph("⚡ <b>Data Leakage Guarantee:</b> Transactions are sorted chronologically. Every rolling window and cumulative count only evaluates events strictly prior to current event ($t_{prior} < t_{current}$).", ParagraphStyle('FF', fontName='Helvetica-Bold', fontSize=8.5, textColor=ACCENT_GREEN))
    story.append(make_card([foot_f], 875, border_color=CARD_BORDER, bg_color=colors.HexColor("#0E1730"), padding=5))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 6: STREAMLIT DASHBOARD (6 SECTIONS)
    # =========================================================================
    story.append(Paragraph("5. Interactive Batch Dashboard (Streamlit UI)", slide_title_style))
    story.append(Paragraph("Operational investigation interface organized into 6 functional sections", slide_subtitle_style))

    d_sec1 = Paragraph("<b>Section 1: Upload & Validation</b><br/><font color='#A0AEC0'>• Drag-and-drop CSV uploader<br/>• Schema check on 14 raw columns<br/>• 1-click Demo Dataset loader</font>", ParagraphStyle('D1', fontSize=8, leading=11, textColor=ACCENT_BLUE))
    d_sec2 = Paragraph("<b>Section 2: Overview KPIs</b><br/><font color='#A0AEC0'>• Total Volume & Anomaly Rate (%)<br/>• Min/Max Decision Scores<br/>• Highest-Risk Transaction ID</font>", ParagraphStyle('D2', fontSize=8, leading=11, textColor=ACCENT_CYAN))
    d_sec3 = Paragraph("<b>Section 3: Suspicious Table</b><br/><font color='#A0AEC0'>• Sorted by Anomaly Score ascending<br/>• Filters: Risk Tier, Prediction, Type<br/>• Limits: Top 10, 25, 50, 100, All</font>", ParagraphStyle('D3', fontSize=8, leading=11, textColor=ACCENT_PURPLE))
    d_sec4 = Paragraph("<b>Section 4: Visual Analytics</b><br/><font color='#A0AEC0'>• Normal vs. Anomaly breakdown<br/>• Continuous score histogram<br/>• Step trends & Transaction types</font>", ParagraphStyle('D4', fontSize=8, leading=11, textColor=ACCENT_AMBER))
    d_sec5 = Paragraph("<b>Section 5: Feature Inspector</b><br/><font color='#A0AEC0'>• Single transaction deep-dive<br/>• Full 30-feature vector viewer<br/>• Raw vs. Transformed values</font>", ParagraphStyle('D5', fontSize=8, leading=11, textColor=ACCENT_GREEN))
    d_sec6 = Paragraph("<b>Section 6: Scored Exports</b><br/><font color='#A0AEC0'>• Complete Scored Dataset CSV<br/>• Anomalies-Only Filtered CSV<br/>• Audit-ready data structures</font>", ParagraphStyle('D6', fontSize=8, leading=11, textColor=ACCENT_RED))

    t_d_top = Table([[
        make_card([d_sec1], 270, border_color=ACCENT_BLUE),
        make_card([d_sec2], 270, border_color=ACCENT_CYAN),
        make_card([d_sec3], 270, border_color=ACCENT_PURPLE)
    ]], colWidths=[293, 293, 293])

    t_d_bot = Table([[
        make_card([d_sec4], 270, border_color=ACCENT_AMBER),
        make_card([d_sec5], 270, border_color=ACCENT_GREEN),
        make_card([d_sec6], 270, border_color=ACCENT_RED)
    ]], colWidths=[293, 293, 293])

    story.append(t_d_top)
    story.append(Spacer(1, 6))
    story.append(t_d_bot)
    story.append(Spacer(1, 8))

    foot_d = Paragraph("📊 <b>Risk Tiers:</b> <font color='#F56565'><b>High Risk</b></font> (Score < -0.05) | <font color='#ED8936'><b>Medium Risk</b></font> (-0.05 ≤ Score < 0.00) | <font color='#48BB78'><b>Normal / Low Risk</b></font> (Score ≥ 0.00)", ParagraphStyle('DF', fontName='Helvetica-Bold', fontSize=8.5, textColor=TEXT_WHITE))
    story.append(make_card([foot_d], 875, border_color=CARD_BORDER, bg_color=colors.HexColor("#0E1730"), padding=5))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 7: AUTOMATED VERIFICATION & TEST RESULTS
    # =========================================================================
    story.append(Paragraph("6. Automated Verification & Pipeline Reliability", slide_title_style))
    story.append(Paragraph("Rigorous test suite verifying zero model drift, exact feature sequence, and export stability", slide_subtitle_style))

    c7_1 = [
        Paragraph("<b>15/15 Verification Suite (test_batch_app.py)</b>", ParagraphStyle('CH7_1', parent=card_h_style, textColor=ACCENT_GREEN)),
        Paragraph("✓ <b>Test 1 & 2:</b> 500-transaction benchmark loaded & 14 columns validated.", bullet_style),
        Paragraph("✓ <b>Test 3, 4 & 5:</b> Exactly 30 features generated matching configuration order.", bullet_style),
        Paragraph("✓ <b>Test 6:</b> Exact 11 log features transformed using np.log1p().", bullet_style),
        Paragraph("✓ <b>Test 7 & 8:</b> StandardScaler.transform() executed; scaler was <b>NOT refitted</b>.", bullet_style),
        Paragraph("✓ <b>Test 9 & 10:</b> Isolation Forest loaded; model was <b>NOT retrained</b>.", bullet_style),
        Paragraph("✓ <b>Test 11 & 12:</b> 100% of transactions scored with decision score & discrete prediction.", bullet_style),
        Paragraph("✓ <b>Test 13, 14 & 15:</b> Original columns preserved; complete and filtered CSVs exported.", bullet_style),
    ]

    c7_2 = [
        Paragraph("<b>Live Detection Scenarios & Scoring</b>", card_h_style),
        Paragraph("<font color='#48BB78'><b>• Normal Daytime Payment:</b></font><br/><font color='#A0AEC0'>Transfer $1,200 during daytime from primary device.<br/>➔ <b>Score: +0.0237</b> | <b>Prediction: +1 (Normal / Low Risk)</b></font>", ParagraphStyle('SC1', fontSize=8, leading=11, spaceAfter=6)),
        Paragraph("<font color='#F56565'><b>• Nocturnal Account Takeover:</b></font><br/><font color='#A0AEC0'>Transfer $850k at 03:15 AM from new device draining 100% balance.<br/>➔ <b>Score: -0.1428</b> | <b>Prediction: -1 (High Risk)</b></font>", ParagraphStyle('SC2', fontSize=8, leading=11, spaceAfter=6)),
        Paragraph("<font color='#ED8936'><b>• Rapid Mule Layering Hop:</b></font><br/><font color='#A0AEC0'>Account receives transfer and forwards $79k downstream within 6 min.<br/>➔ <b>Score: -0.0969</b> | <b>Prediction: -1 (High Risk)</b></font>", ParagraphStyle('SC3', fontSize=8, leading=11)),
    ]

    t7 = Table([[make_card(c7_1, 430, border_color=ACCENT_GREEN), make_card(c7_2, 430)]], colWidths=[440, 440])
    story.append(t7)
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 8: POST-MIDTERM ROADMAP
    # =========================================================================
    story.append(Paragraph("7. Post-Midterm Roadmap & Upcoming Milestones", slide_title_style))
    story.append(Paragraph("Advancing from tabular behavioral anomaly detection to relational graph analysis", slide_subtitle_style))

    miles_cards = [
        Paragraph("<b>Milestone 1: NetworkX Directed Graph Engine</b> <font color='#00D2FF'><b>[IN PROGRESS]</b></font><br/><font color='#A0AEC0'>Construct directed money-flow graphs where accounts represent nodes and fund transfers form weighted edges with timestamp metadata.</font>", ParagraphStyle('M1_C', fontSize=8.5, leading=11.5, textColor=TEXT_WHITE)),
        Paragraph("<b>Milestone 2: Multi-Hop Scam Chain Detection</b> <font color='#4299E1'><b>[UPCOMING]</b></font><br/><font color='#A0AEC0'>Implement cycle detection and path search algorithms to identify rapid layering chains (A ➔ B ➔ C ➔ D) and fund dispersal syndicates.</font>", ParagraphStyle('M2_C', fontSize=8.5, leading=11.5, textColor=TEXT_WHITE)),
        Paragraph("<b>Milestone 3: Combined Multi-Signal Risk Engine</b> <font color='#9F7AEA'><b>[UPCOMING]</b></font><br/><font color='#A0AEC0'>Synthesize behavioral Isolation Forest scores (60%) with graph topology centralities (40%) into a unified 0–100 composite risk score.</font>", ParagraphStyle('M3_C', fontSize=8.5, leading=11.5, textColor=TEXT_WHITE)),
        Paragraph("<b>Milestone 4: Interactive Network Visualizer</b> <font color='#ED8936'><b>[UPCOMING]</b></font><br/><font color='#A0AEC0'>Develop interactive node-link visualizers in the Streamlit UI to display money flow subgraphs for suspicious accounts.</font>", ParagraphStyle('M4_C', fontSize=8.5, leading=11.5, textColor=TEXT_WHITE)),
        Paragraph("<b>Milestone 5: MongoDB Persistence & Final Benchmark</b> <font color='#48BB78'><b>[UPCOMING]</b></font><br/><font color='#A0AEC0'>Integrate MongoDB cloud storage for audit trails, case notes, and comprehensive precision/recall evaluation against synthetic fraud benchmarks.</font>", ParagraphStyle('M5_C', fontSize=8.5, leading=11.5, textColor=TEXT_WHITE)),
    ]

    for m_p in miles_cards:
        story.append(make_card([m_p], 875, border_color=CARD_BORDER, padding=6))
        story.append(Spacer(1, 4))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 9: SUMMARY & MENTOR DISCUSSION
    # =========================================================================
    story.append(Paragraph("8. Project Summary & Mentor Discussion", slide_title_style))
    story.append(Paragraph("Recap of progress achieved and open discussion points with mentor", slide_subtitle_style))

    c9_1 = [
        Paragraph("<b>Key Achievements Till Mid-Term</b>", card_h_style),
        Paragraph("✓ <font color='#48BB78'><b>Working Batch Engine:</b></font> Built high-performance feature engineering calculating 30 ML features from raw monthly CSV batches without future data leakage.", bullet_style),
        Paragraph("✓ <font color='#48BB78'><b>Strict Model Integrity:</b></font> Integrated pre-trained Isolation Forest and StandardScaler as immutable artifacts with zero refitting or retraining.", bullet_style),
        Paragraph("✓ <font color='#48BB78'><b>Streamlit Dashboard:</b></font> Complete 6-section UI with KPIs, suspicious transaction filters, charts, deep-dive inspectors, and exports.", bullet_style),
        Paragraph("✓ <font color='#48BB78'><b>100% Automated Test Suite:</b></font> Passed all 15 operational test assertions validating pipeline correctness.", bullet_style),
    ]

    c9_2 = [
        Paragraph("<b>Discussion Points for Mentor Guidance</b>", ParagraphStyle('CH9_2', parent=card_h_style, textColor=ACCENT_AMBER)),
        Paragraph("❓ <font color='#ED8936'><b>Graph Topology Scaling:</b></font> Best practices for constructing dynamic transaction subgraphs in NetworkX when batch sizes scale past 100,000 nodes.", bullet_style),
        Paragraph("❓ <font color='#ED8936'><b>Composite Risk Weighting:</b></font> Refining weighting formulas between tabular Isolation Forest anomaly scores (60%) and graph degree centralities (40%).", bullet_style),
        Paragraph("❓ <font color='#ED8936'><b>Evaluation Benchmarks:</b></font> Feedback on synthetic fraud injection scenarios (layering, account takeover, fan-out dispersal) for benchmarking.", bullet_style),
        Paragraph("❓ <font color='#ED8936'><b>Live Demonstration:</b></font> Ready to demonstrate the interactive Streamlit batch application during review.", bullet_style),
    ]

    t9 = Table([[make_card(c9_1, 430), make_card(c9_2, 430, border_color=ACCENT_AMBER)]], colWidths=[440, 440])
    story.append(t9)

    doc.build(story)
    print(f"Executive Presentation PDF successfully generated: {pdf_filename}")


if __name__ == "__main__":
    build_executive_pdf()
