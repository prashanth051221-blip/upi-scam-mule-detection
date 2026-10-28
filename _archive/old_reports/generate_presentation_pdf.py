"""
Generate a professional, mentor-ready Landscape Presentation PDF for PBL-III
AI-Powered UPI Scam & Fraud Detection System.
"""

import os
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas


class PresentationCanvas(canvas.Canvas):
    """
    Two-pass canvas for presentation slides with header accent bar and footer slide numbering.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_slide_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_slide_decorations(self, page_count):
        self.saveState()
        w, h = landscape(letter)

        if self._pageNumber > 1:
            # Top accent line
            self.setFillColor(colors.HexColor("#1A365D"))
            self.rect(0, h - 8, w, 8, fill=1, stroke=0)

            # Running header text
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor("#718096"))
            self.drawString(36, h - 24, "PBL-III MENTOR PRESENTATION  |  AI-POWERED UPI SCAM & FRAUD DETECTION")
            
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.8)
            self.line(36, h - 28, w - 36, h - 28)

        # Footer
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.8)
        self.line(36, 32, w - 36, 32)

        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#718096"))
        self.drawString(36, 20, "Department of Artificial Intelligence & Machine Learning  |  Manipal University Jaipur")

        slide_str = f"Slide {self._pageNumber} of {page_count}"
        self.drawRightString(w - 36, 20, slide_str)
        self.restoreState()


def create_presentation_pdf():
    pdf_filename = "UPI_Scam_Detection_Mentor_Presentation.pdf"
    
    # 792 x 612 pt (11 x 8.5 inches landscape)
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=landscape(letter),
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Color Palette
    c_primary = colors.HexColor("#1A365D")   # Deep Navy
    c_secondary = colors.HexColor("#2B6CB0") # Slate Blue
    c_accent = colors.HexColor("#3182CE")    # Blue
    c_dark = colors.HexColor("#2D3748")      # Charcoal Text
    c_card_bg = colors.HexColor("#F7FAFC")   # Soft Grey Background
    c_card_border = colors.HexColor("#E2E8F0")

    # Typography Styles
    slide_title_style = ParagraphStyle(
        'SlideTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=c_primary,
        spaceAfter=2
    )

    slide_subtitle_style = ParagraphStyle(
        'SlideSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=13,
        textColor=c_secondary,
        spaceAfter=10
    )

    card_heading_style = ParagraphStyle(
        'CardHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=c_primary,
        spaceAfter=4
    )

    card_text_style = ParagraphStyle(
        'CardText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=c_dark
    )

    bullet_style = ParagraphStyle(
        'BulletText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12.5,
        textColor=c_dark,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=1
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=c_dark
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=c_dark
    )

    story = []

    # =========================================================================
    # SLIDE 1: TITLE SLIDE
    # =========================================================================
    story.append(Spacer(1, 40))
    title_main = ParagraphStyle(
        'TitleMain',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=26,
        leading=32,
        textColor=c_primary,
        alignment=1,
        spaceAfter=8
    )
    title_sub = ParagraphStyle(
        'TitleSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=14,
        leading=18,
        textColor=c_secondary,
        alignment=1,
        spaceAfter=20
    )
    title_meta = ParagraphStyle(
        'TitleMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=15,
        textColor=c_dark,
        alignment=1
    )

    story.append(Paragraph("AI-POWERED UPI SCAM & FRAUD DETECTION", title_main))
    story.append(Paragraph("Behavioral Anomaly Detection & Graph Analytics Platform", title_sub))
    story.append(HRFlowable(width="60%", thickness=2, color=c_accent, spaceAfter=25, hAlign='CENTER'))
    
    meta_box = [
        [
            Paragraph("<b>Course:</b> PBL-III (AIM3170)<br/><b>Category:</b> Application-Based", title_meta),
            Paragraph("<b>Domain:</b> FinTech Cybersecurity & ML<br/><b>Core Model:</b> Isolation Forest", title_meta),
            Paragraph("<b>Institution:</b> Manipal University Jaipur<br/><b>Department:</b> Dept. of AIML", title_meta)
        ]
    ]
    t_meta = Table(meta_box, colWidths=[240, 240, 240])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), c_card_bg),
        ('BOX', (0, 0), (-1, -1), 1, c_card_border),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(t_meta)
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 2: PROBLEM STATEMENT & MOTIVATION
    # =========================================================================
    story.append(Paragraph("1. Problem Statement & Industry Motivation", slide_title_style))
    story.append(Paragraph("Why traditional payment fraud rules fail in real-time UPI ecosystems", slide_subtitle_style))

    p2_c1 = [
        Paragraph("<b>The Growing UPI Scam Landscape</b>", card_heading_style),
        Paragraph("• <b>Massive Volume & Instant Settlement:</b> UPI processes billions of transactions monthly; irreversible transfers make immediate detection critical.", bullet_style),
        Paragraph("• <b>Social Engineering Scams:</b> Victims are tricked via fake refund links, remote access tools, or phishing QR codes into authorizing payments.", bullet_style),
        Paragraph("• <b>Account Takeovers:</b> Sudden nocturnal balance drainage from unrecognised devices to newly created beneficiary accounts.", bullet_style),
        Paragraph("• <b>Mule Account Networks:</b> Illicit funds are split and rapidly hopped across multiple intermediary accounts to evade freezing.", bullet_style),
    ]

    p2_c2 = [
        Paragraph("<b>Limitations of Existing Systems</b>", card_heading_style),
        Paragraph("• <b>Static Rules & High False Positives:</b> Simple limits (e.g. amount > $50k) block genuine users while missing sophisticated multi-transfer frauds.", bullet_style),
        Paragraph("• <b>Siloed Per-Transaction View:</b> Traditional systems evaluate single transactions in isolation, blind to temporal bursts and money-flow chains.", bullet_style),
        Paragraph("• <b>Lack of Explainability:</b> Black-box fraud scores lack interpretable behavioral context required for fast investigation triage.", bullet_style),
        Paragraph("• <b>Our Core Solution:</b> An unsupervised batch detection engine combining 30 behavioral signals with graph topology to score and prioritize suspicious activity.", bullet_style),
    ]

    t_p2 = Table([[p2_c1, p2_c2]], colWidths=[355, 355])
    t_p2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), c_card_bg),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor("#EBF8FF")),
        ('BOX', (0, 0), (0, 0), 1, c_card_border),
        ('BOX', (1, 0), (1, 0), 1, colors.HexColor("#BEE3F8")),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t_p2)
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 3: PBL-II RECAP & FOUNDATION
    # =========================================================================
    story.append(Paragraph("2. Previous Semester (PBL-II) Recap & Transition", slide_title_style))
    story.append(Paragraph("Building upon proven competencies in machine learning, user interfaces, and persistence", slide_subtitle_style))

    p3_c1 = [
        Paragraph("<b>PBL-II Project Summary (AI Health Assistant)</b>", card_heading_style),
        Paragraph("• <b>Supervised Disease Prediction:</b> Multi-label ML classification mapping user symptom vectors to potential diagnoses.", bullet_style),
        Paragraph("• <b>Fuzzy Dietary Recommendation:</b> Automated dietary guidance using token-sort fuzzy matching on medical dietary knowledge bases.", bullet_style),
        Paragraph("• <b>Interactive Dashboard & Dual Storage:</b> Multi-tab Streamlit dashboard with MongoDB persistence and local JSON fallback.", bullet_style),
        Paragraph("• <b>Key Competency Acquired:</b> End-to-end model serialization, input validation, and interactive web dashboard development.", bullet_style),
    ]

    p3_c2 = [
        Paragraph("<b>Evolution to PBL-III (UPI Scam Detection)</b>", card_heading_style),
        Paragraph("• <b>From Supervised to Unsupervised:</b> Shifting from static symptom classification to unsupervised financial anomaly detection (Isolation Forest) to catch zero-day scam patterns.", bullet_style),
        Paragraph("• <b>From Single Input to Batch Analytics:</b> Ingesting full monthly transaction datasets rather than single form inputs.", bullet_style),
        Paragraph("• <b>Leak-Free Feature Engineering:</b> Developing strict chronological historical profiling to calculate 30 features without future data leakage.", bullet_style),
        Paragraph("• <b>Relational Graph Analysis:</b> Introducing NetworkX graph topology to track multi-hop money flow chains and mule account syndicates.", bullet_style),
    ]

    t_p3 = Table([[p3_c1, p3_c2]], colWidths=[355, 355])
    t_p3.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), c_card_bg),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor("#F0FFF4")),
        ('BOX', (0, 0), (0, 0), 1, c_card_border),
        ('BOX', (1, 0), (1, 0), 1, colors.HexColor("#C6F6D5")),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t_p3)
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 4: SYSTEM ARCHITECTURE & PIPELINE
    # =========================================================================
    story.append(Paragraph("3. End-to-End System Architecture", slide_title_style))
    story.append(Paragraph("Reproducible, data-leak-free batch processing and inference pipeline", slide_subtitle_style))

    arch_box = [
        [
            Paragraph("<b>1. Raw Batch Ingestion</b><br/>• 14 Raw Columns<br/>• Full Monthly Datasets<br/>• Automated Format Check", card_text_style),
            Paragraph("➔", ParagraphStyle('Arr', parent=styles['Normal'], alignment=1, fontSize=16, textColor=c_accent)),
            Paragraph("<b>2. Data Quality & Validation</b><br/>• Nulls & Duplicate IDs<br/>• Non-negative Values<br/>• Datetime Parsing", card_text_style),
            Paragraph("➔", ParagraphStyle('Arr', parent=styles['Normal'], alignment=1, fontSize=16, textColor=c_accent)),
            Paragraph("<b>3. Feature Engineering</b><br/>• Chronological Sorting<br/>• 30 ML Features<br/>• No Future Leakage", card_text_style),
        ],
        [
            Paragraph("<b>4. Preprocessing</b><br/>• np.log1p (11 log features)<br/>• StandardScaler transform()<br/>• Never refitted", card_text_style),
            Paragraph("➔", ParagraphStyle('Arr', parent=styles['Normal'], alignment=1, fontSize=16, textColor=c_accent)),
            Paragraph("<b>5. Isolation Forest ML</b><br/>• Decision Score Output<br/>• Predict: Normal vs Anomaly<br/>• Zero Retraining", card_text_style),
            Paragraph("➔", ParagraphStyle('Arr', parent=styles['Normal'], alignment=1, fontSize=16, textColor=c_accent)),
            Paragraph("<b>6. Streamlit Dashboard</b><br/>• Overview KPIs & Filters<br/>• 30-Feature Deep-Dive<br/>• Scored CSV Export", card_text_style),
        ]
    ]

    t_arch = Table(arch_box, colWidths=[200, 30, 200, 30, 240])
    t_arch.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), c_card_bg),
        ('BOX', (0, 0), (-1, -1), 1, c_card_border),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_arch)
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Key Pipeline Design Principle:</b> The pre-trained Isolation Forest and StandardScaler are completely decoupled and treated as immutable artifacts. Preprocessing strictly reproduces the Jupyter training configuration without modifying the models.", card_text_style))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 5: THE 30 MODEL FEATURES & LEAKAGE PREVENTION
    # =========================================================================
    story.append(Paragraph("4. Feature Engineering: The 30 Model Features", slide_title_style))
    story.append(Paragraph("Vectorized extraction strictly prior to current transaction to avoid future leakage", slide_subtitle_style))

    feat_data = [
        [
            Paragraph("<b>Category</b>", table_header_style),
            Paragraph("<b>Features Included</b>", table_header_style),
            Paragraph("<b>Computation Logic & Prevention of Leakage</b>", table_header_style)
        ],
        [
            Paragraph("<b>Direct & Temporal</b>", table_cell_bold),
            Paragraph("amount, transaction_step, sender_old_balance, sender_new_balance, receiver_old_balance, receiver_new_balance, device_change_flag, new_device_flag, transaction_hour, is_night", table_cell_style),
            Paragraph("Extracted directly from CSV or parsed from transaction timestamp (night: 22:00–06:00).", table_cell_style)
        ],
        [
            Paragraph("<b>Historical Interaction Counts</b>", table_cell_bold),
            Paragraph("sender_txn_count_before, same_step_txn_count_before, sender_receiver_txn_count_before, sender_unique_recipients_before, receiver_txn_count_before, receiver_unique_senders_before", table_cell_style),
            Paragraph("Vectorized <code>groupby.cumcount()</code> and cumulative unique recipient sets strictly counting events <i>prior</i> to current transaction.", table_cell_style)
        ],
        [
            Paragraph("<b>Expanding Statistics & Ratios</b>", table_cell_bold),
            Paragraph("sender_balance_ratio, time_since_previous_sender_txn, sender_amount_mean_before, sender_amount_std_before, amount_deviation, amount_zscore", table_cell_style),
            Paragraph("Expanding mean, variance, and Z-score calculated over previous transactions only. Sentinel -1 for first transaction.", table_cell_style)
        ],
        [
            Paragraph("<b>Rolling Velocity & Chains</b>", table_cell_bold),
            Paragraph("txns_last_1h, txns_last_6h, txns_last_24h, rapid_transaction_flag, hop_number, chain_length, chain_duration_steps, transaction_frequency", table_cell_style),
            Paragraph("O(N log N) rolling count using binary search (<code>np.searchsorted</code>) over epoch timestamps. Multi-hop money flow tracking.", table_cell_style)
        ]
    ]

    t_feat = Table(feat_data, colWidths=[120, 260, 330])
    t_feat.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('GRID', (0, 0), (-1, -1), 0.5, c_card_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [c_card_bg, colors.white]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t_feat)
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 6: STREAMLIT DASHBOARD & CORE SECTIONS
    # =========================================================================
    story.append(Paragraph("5. Interactive Batch Dashboard (Streamlit)", slide_title_style))
    story.append(Paragraph("Operational investigation interface organized into 6 functional sections", slide_subtitle_style))

    dash_box = [
        [
            Paragraph("<b>Section 1: Upload & Validation</b><br/>• Drag-and-drop CSV uploader<br/>• Automated schema checks (14 cols)<br/>• 1-click Demo Dataset loader", card_text_style),
            Paragraph("<b>Section 2: Dataset Overview</b><br/>• Total Volume & Anomaly Rate<br/>• Min/Max Anomaly Scores<br/>• Highest-Risk Transaction ID", card_text_style),
            Paragraph("<b>Section 3: Suspicious Table</b><br/>• Sorted by Anomaly Score ascending<br/>• Filters: Risk Level, Prediction, Type<br/>• Limits: Top 10, 25, 50, 100, All", card_text_style),
        ],
        [
            Paragraph("<b>Section 4: Visual Analytics</b><br/>• Normal vs. Anomaly breakdown<br/>• Continuous score histogram<br/>• Step trends & Transaction types", card_text_style),
            Paragraph("<b>Section 5: Transaction Inspector</b><br/>• Single transaction deep-dive<br/>• Full 30-feature vector viewer<br/>• Raw vs. Transformed values", card_text_style),
            Paragraph("<b>Section 6: Scored Exports</b><br/>• Complete Scored Dataset CSV<br/>• Anomalies-Only Filtered CSV<br/>• Audit-ready data structures", card_text_style),
        ]
    ]

    t_dash = Table(dash_box, colWidths=[235, 235, 240])
    t_dash.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), c_card_bg),
        ('BOX', (0, 0), (-1, -1), 1, c_card_border),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t_dash)
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>Risk Level Tiers:</b> <font color='#991B1B'><b>High Risk</b></font> (Score < -0.05) | <font color='#92400E'><b>Medium Risk</b></font> (-0.05 ≤ Score < 0.0) | <font color='#166534'><b>Normal / Low Risk</b></font> (Score ≥ 0.0)", card_text_style))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 7: AUTOMATED TESTING & VERIFICATION
    # =========================================================================
    story.append(Paragraph("6. Automated Verification & Technical Integrity", slide_title_style))
    story.append(Paragraph("Rigorous test suite verifying zero model drift, exact feature sequence, and export stability", slide_subtitle_style))

    p7_c1 = [
        Paragraph("<b>15/15 Verification Suite Results (test_batch_app.py)</b>", card_heading_style),
        Paragraph("✓ <b>Test 1 & 2:</b> 500-transaction benchmark loaded and all 14 required columns validated.", bullet_style),
        Paragraph("✓ <b>Test 3, 4 & 5:</b> Exactly 30 features generated matching feature_config.pkl in sequence.", bullet_style),
        Paragraph("✓ <b>Test 6:</b> Exact 11 log features transformed using np.log1p().", bullet_style),
        Paragraph("✓ <b>Test 7 & 8:</b> StandardScaler.transform() executed; scaler was <b>NOT refitted</b>.", bullet_style),
        Paragraph("✓ <b>Test 9 & 10:</b> Isolation Forest loaded; model was <b>NOT retrained</b>.", bullet_style),
        Paragraph("✓ <b>Test 11 & 12:</b> 100% of transactions scored and assigned discrete predictions.", bullet_style),
        Paragraph("✓ <b>Test 13, 14 & 15:</b> Original columns preserved; complete and filtered CSVs exported.", bullet_style),
    ]

    p7_c2 = [
        Paragraph("<b>Sample Test Scenarios & Model Outputs</b>", card_heading_style),
        Paragraph("• <b>Normal Daytime Payment:</b> Standard volume, matching primary device, low balance ratio<br/>➔ <b>Score:</b> +0.0237 | <b>Prediction:</b> +1 (Normal / Low Risk)", bullet_style),
        Paragraph("• <b>Suspicious Nocturnal Takeover:</b> Unrecognized new device at 03:00 AM draining 100% of balance to new recipient<br/>➔ <b>Score:</b> -0.1428 | <b>Prediction:</b> -1 (High Risk)", bullet_style),
        Paragraph("• <b>Rapid Multi-Hop Layering:</b> Large transfer received and forwarded downstream within 6 minutes<br/>➔ <b>Score:</b> -0.0969 | <b>Prediction:</b> -1 (High Risk)", bullet_style),
    ]

    t_p7 = Table([[p7_c1, p7_c2]], colWidths=[360, 350])
    t_p7.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), c_card_bg),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor("#F0FFF4")),
        ('BOX', (0, 0), (0, 0), 1, c_card_border),
        ('BOX', (1, 0), (1, 0), 1, colors.HexColor("#C6F6D5")),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t_p7)
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 8: WORK IN PROGRESS & ROADMAP
    # =========================================================================
    story.append(Paragraph("7. Ongoing Work & Post-Midterm Roadmap", slide_title_style))
    story.append(Paragraph("Advancing from tabular behavioral anomaly detection to relational graph analysis", slide_subtitle_style))

    miles_data = [
        [Paragraph("<b>Milestone</b>", table_header_style), Paragraph("<b>Target Deliverable</b>", table_header_style), Paragraph("<b>Technical Focus</b>", table_header_style), Paragraph("<b>Status</b>", table_header_style)],
        [Paragraph("<b>Milestone 1</b>", table_cell_bold), Paragraph("NetworkX Graph Layer", table_cell_style), Paragraph("Account node creation, degree centralities, and mule path cycle detection.", table_cell_style), Paragraph("<font color='#2B6CB0'><b>In Progress</b></font>", table_cell_style)],
        [Paragraph("<b>Milestone 2</b>", table_cell_bold), Paragraph("Combined Multi-Signal Risk Engine", table_cell_style), Paragraph("Synthesizing behavioral anomaly scores with graph topology metrics into a unified 0-100 score.", table_cell_style), Paragraph("<font color='#D69E2E'><b>Upcoming</b></font>", table_cell_style)],
        [Paragraph("<b>Milestone 3</b>", table_cell_bold), Paragraph("Interactive Network Visualizer", table_cell_style), Paragraph("Interactive node-link visualizer rendering suspicious money flow paths and hubs.", table_cell_style), Paragraph("<font color='#D69E2E'><b>Upcoming</b></font>", table_cell_style)],
        [Paragraph("<b>Milestone 4</b>", table_cell_bold), Paragraph("MongoDB Database Persistence", table_cell_style), Paragraph("Storing uploaded datasets, investigation audit history, and flagged account registries.", table_cell_style), Paragraph("<font color='#D69E2E'><b>Upcoming</b></font>", table_cell_style)],
        [Paragraph("<b>Milestone 5</b>", table_cell_bold), Paragraph("Benchmark Evaluation & Report", table_cell_style), Paragraph("Comprehensive precision/recall analysis, false-positive benchmarking, and final documentation.", table_cell_style), Paragraph("<font color='#D69E2E'><b>Upcoming</b></font>", table_cell_style)]
    ]

    t_miles = Table(miles_data, colWidths=[80, 170, 360, 100])
    t_miles.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('GRID', (0, 0), (-1, -1), 0.5, c_card_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [c_card_bg, colors.white]),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t_miles)
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 9: SUMMARY & MENTOR DISCUSSION POINTS
    # =========================================================================
    story.append(Paragraph("8. Project Summary & Key Takeaways", slide_title_style))
    story.append(Paragraph("Recap of progress achieved and open discussion points with mentor", slide_subtitle_style))

    p9_c1 = [
        Paragraph("<b>Key Achievements Till Mid-Term</b>", card_heading_style),
        Paragraph("• <b>Production-Ready Batch Engine:</b> Built high-performance, leak-free feature engineering calculating 30 ML features from raw monthly data.", bullet_style),
        Paragraph("• <b>Model Integrity:</b> Successfully integrated pre-trained Isolation Forest and StandardScaler without drift or refitting.", bullet_style),
        Paragraph("• <b>Rich Streamlit Dashboard:</b> Delivered interactive triage UI with KPI metrics, filters, charts, deep-dive inspectors, and exports.", bullet_style),
        Paragraph("• <b>100% Test Validation:</b> Verified end-to-end reliability across 15 automated validation checks.", bullet_style),
    ]

    p9_c2 = [
        Paragraph("<b>Discussion Points with Mentor</b>", card_heading_style),
        Paragraph("• <b>Graph Scalability:</b> Tuning NetworkX graph construction parameters for large-scale multi-thousand transaction networks.", bullet_style),
        Paragraph("• <b>Risk Weighting Formula:</b> Defining optimal weighting between behavioral Isolation Forest scores (60%) and graph centrality metrics (40%).", bullet_style),
        Paragraph("• <b>Evaluation Metrics:</b> Finalizing benchmark evaluation strategy on synthetic fraud scenarios.", bullet_style),
        Paragraph("• <b>Next Demonstration:</b> Live demonstration of the interactive Streamlit batch application.", bullet_style),
    ]

    t_p9 = Table([[p9_c1, p9_c2]], colWidths=[355, 355])
    t_p9.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), c_card_bg),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor("#EBF8FF")),
        ('BOX', (0, 0), (0, 0), 1, c_card_border),
        ('BOX', (1, 0), (1, 0), 1, colors.HexColor("#BEE3F8")),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t_p9)

    doc.build(story, canvasmaker=PresentationCanvas)
    print(f"Presentation PDF successfully generated: {pdf_filename}")


if __name__ == "__main__":
    create_presentation_pdf()
