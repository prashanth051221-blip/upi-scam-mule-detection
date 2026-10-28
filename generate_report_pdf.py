"""
Generate high quality academic PDF for PBL-III Progress Report using ReportLab.
Follows the exact structure of PBL-III Progress Report Format.
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and display total page count in footer.
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
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#4A5568"))

        # Header (pages >= 1)
        self.drawString(
            54, letter[1] - 36,
            "PBL-III (AIM3170) Progress Report  |  AI-Powered UPI Scam & Fraud Detection"
        )
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.6)
        self.line(54, letter[1] - 42, letter[0] - 54, letter[1] - 42)

        # Footer
        self.line(54, 45, letter[0] - 54, 45)
        self.drawString(
            54, 32,
            "Dept. of Artificial Intelligence & Machine Learning  |  Manipal University Jaipur"
        )
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 54, 32, page_str)
        self.restoreState()


def create_pbl_report():
    pdf_filename = "PBL_III_Progress_Report_UPI_Scam_Detection.pdf"
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    primary_color = colors.HexColor("#1A365D")   # Deep navy
    secondary_color = colors.HexColor("#2B6CB0") # Slate blue
    text_dark = colors.HexColor("#2D3748")       # Charcoal
    bg_light = colors.HexColor("#F7FAFC")        # Soft grey

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=primary_color,
        spaceAfter=4,
        alignment=0
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=secondary_color,
        spaceAfter=12,
        alignment=0
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=secondary_color,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=text_dark,
        spaceAfter=5
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=text_dark,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=3
    )

    callout_style = ParagraphStyle(
        'Callout_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11.5,
        textColor=colors.HexColor("#1A202C")
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10.5,
        textColor=colors.white,
        alignment=1
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=text_dark
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=10,
        textColor=text_dark
    )

    story = []

    # Title & Subtitle banner
    story.append(Paragraph("AI-POWERED UPI SCAM & FRAUD DETECTION SYSTEM", title_style))
    story.append(Paragraph(
        "<b>Course Code:</b> AIM3170 (PBL-III)  |  <b>Domain:</b> FinTech Cybersecurity, Anomaly Detection & Graph Analytics  |  <b>Type:</b> Application-Based",
        subtitle_style
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=10))

    # =========================================================================
    # I. ABSTRACT (SUMMARY)
    # =========================================================================
    story.append(Paragraph("I. Abstract (Summary)", h1_style))
    abstract_text = (
        "This progress report outlines the architecture, implementation, and mid-term progress of an "
        "<b>AI-Powered UPI Scam and Fraud Detection System</b>. With the widespread adoption of the Unified "
        "Payments Interface (UPI) and real-time digital payment channels, financial cyber-fraud has rapidly evolved "
        "from isolated unauthorized debits into coordinated multi-stage attacks, including social engineering scams, "
        "nocturnal account takeover bursts, and rapid money mule layering chains. Traditional static rule engines "
        "struggle to identify these behavioral shifts without imposing high false-positive rates on legitimate users. "
        "Building upon our previous semester (PBL-II) foundation in machine learning pipelines and interactive user "
        "interfaces, this project implements a batch anomaly detection prototype. In this phase of "
        "PBL-III, we established a 14-column UPI transaction schema and engineered a vectorized batch feature extraction "
        "engine that computes exactly 30 behavioral, temporal, and sequential features strictly before each transaction event, "
        "completely preventing future data leakage. Leveraging a pre-trained <b>Isolation Forest</b> model and pre-fitted "
        "<b>StandardScaler</b> with selective log transformations (<code>np.log1p</code>), the system scores multi-thousand "
        "transaction datasets, generating continuous anomaly scores and tiered risk classifications (High Risk, Medium Risk, "
        "Normal/Low Risk). An interactive Streamlit investigation dashboard was built featuring data quality validation, KPI "
        "overviews, multi-filter suspicious transaction ranking, interactive visualizations, deep-dive feature vector inspection, "
        "and complete CSV export capabilities. Automated tests verified 15 pipeline checks (artifact loading, feature alignment, no refitting, exports); detection accuracy was not yet measured at this stage."
    )
    story.append(Paragraph(abstract_text, body_style))
    story.append(Spacer(1, 4))

    # =========================================================================
    # II. INTRODUCTION TO PROBLEM
    # =========================================================================
    story.append(Paragraph("II. Introduction to Problem (What, Why, How)", h1_style))
    story.append(Paragraph("<b>Project Category:</b> Application-Based System with Machine Learning & Graph Analytics", bullet_style))
    story.append(Spacer(1, 2))

    story.append(Paragraph("1. Problem Description (What)", h2_style))
    what_text = (
        "Digital payment ecosystems—predominantly UPI in India—handle billions of low-latency transactions every month. "
        "However, their instant settlement and irreversibility make them primary targets for cyber-fraud. Common attack patterns include: "
        "<br/>• <b>Social Engineering & Phishing:</b> Deceiving victims into transferring funds via fraudulent QR codes or payment links. "
        "<br/>• <b>Account Takeover Bursts:</b> Rapid drainage of account balances to external accounts from unrecognized devices during unusual hours. "
        "<br/>• <b>Mule Account Layering:</b> Routing illicit funds through multiple intermediary accounts in rapid succession to obstruct recovery. "
        "<br/>In isolation, each transaction appears legitimate, but analyzing historical sequences, balance drainage ratios, and network connectivity reveals distinct anomalous footprints."
    )
    story.append(Paragraph(what_text, body_style))

    story.append(Paragraph("2. Motivation and Significance (Why)", h2_style))
    why_text = (
        "• <b>High False Positive Burden:</b> Rigid rule-based systems generate excessive alerts, causing alert fatigue and friction for genuine customers. "
        "<br/>• <b>Lack of Multi-Hop Visibility:</b> Traditional transaction-level filters evaluate transactions in silos, failing to detect organized mule syndicates. "
        "<br/>• <b>Need for Prioritized Decision Support:</b> Fraud analysts require continuous risk rankings and explainable indicators to triage urgent cases effectively."
    )
    story.append(Paragraph(why_text, body_style))

    story.append(Paragraph("3. Proposed Solution & Architecture (How)", h2_style))
    how_text = (
        "The application ingests monthly transaction batches and executes an automated validation and processing pipeline: "
        "<br/>1. <b>Batch Schema Validation:</b> Validates all 14 required raw columns, checking for nulls, duplicate IDs, and numeric validity. "
        "<br/>2. <b>Leak-Free Feature Engineering:</b> Chronologically computes 30 ML features capturing velocity, expanding sender/receiver statistics, and hop metrics strictly using prior data. "
        "<br/>3. <b>Unsupervised Anomaly Inference:</b> Applies exact saved log transformations and scaling, followed by Isolation Forest scoring to assign continuous anomaly scores and risk tiers. "
        "<br/>4. <b>Graph Layer & Dashboard:</b> Delivers a multi-section investigation interface with visual analytics, individual transaction inspection, and report downloads."
    )
    story.append(Paragraph(how_text, body_style))
    story.append(Spacer(1, 4))

    # =========================================================================
    # III. WORK DONE IN PREVIOUS SEMESTER (PBL-II RECAP)
    # =========================================================================
    story.append(Paragraph("III. Work Done in Previous Semester (PBL-II Recap)", h1_style))
    recap_text = (
        "In PBL-II, our team developed an <b>AI Health Assistant & Disease-Specific Dietary Recommendation Platform</b>. "
        "That project established core competencies in training and deploying machine learning models, creating interactive "
        "Streamlit user interfaces, managing dual data persistence (MongoDB with local JSON fallback), and implementing input validation."
    )
    story.append(Paragraph(recap_text, body_style))

    story.append(Paragraph("• Literature Survey Highlights (Major Works Studied)", h2_style))
    lit_text = (
        "• <b>Isolation-Based Anomaly Detection:</b> Studied tree-partitioning algorithms (Isolation Forest) that isolate anomalies through random splits, achieving linear computational complexity suitable for high-dimensional financial data without requiring labeled fraud datasets. "
        "<br/>• <b>Mobile Money Benchmarking:</b> Evaluated synthetic financial logs (e.g. PaySim dataset) to study transaction step dynamics, balance continuity, and synthetic fraud injection methodologies. "
        "<br/>• <b>Graph Modeling in Fraud:</b> Analyzed graph-based architectures where accounts represent nodes and transfers represent directed edges, showing that network degrees, path lengths, and cycle detection significantly boost detection of mule networks. "
        "<br/>• <b>Temporal Behavioral Profiling:</b> Researched sliding-window velocity metrics, confirming that expanding historical averages, deviation z-scores, and short-term transaction counts provide strong discriminating signals for compromised accounts."
    )
    story.append(Paragraph(lit_text, body_style))

    story.append(Paragraph("• Comparative Study Table", h2_style))
    comp_data = [
        [
            Paragraph("<b>Approach / Paradigm</b>", table_header_style),
            Paragraph("<b>Detection Logic</b>", table_header_style),
            Paragraph("<b>Graph Awareness</b>", table_header_style),
            Paragraph("<b>Interpretability</b>", table_header_style),
            Paragraph("<b>Complexity</b>", table_header_style),
            Paragraph("<b>Suitability for UPI</b>", table_header_style)
        ],
        [
            Paragraph("<b>Static Threshold Rules</b>", table_cell_bold),
            Paragraph("Heuristic limits (e.g. Amount > Rs. 50,000)", table_cell_style),
            Paragraph("None (Siloed)", table_cell_style),
            Paragraph("High (Rule Triggered)", table_cell_style),
            Paragraph("O(1)", table_cell_style),
            Paragraph("Low (High false alarms, easily bypassed)", table_cell_style)
        ],
        [
            Paragraph("<b>Supervised Classifiers</b><br/>(Random Forest / XGBoost)", table_cell_bold),
            Paragraph("Supervised learning on historical labels", table_cell_style),
            Paragraph("Low (Requires manual feature engineering)", table_cell_style),
            Paragraph("Medium (Feature importances / SHAP)", table_cell_style),
            Paragraph("O(N log N)", table_cell_style),
            Paragraph("Moderate (Requires massive labeled fraud data; weak on zero-day attacks)", table_cell_style)
        ],
        [
            Paragraph("<b>Isolation Forest</b><br/>(Our Base ML Engine)", table_cell_bold),
            Paragraph("Unsupervised subspace isolation", table_cell_style),
            Paragraph("Moderate (Via engineered chain & hop features)", table_cell_style),
            Paragraph("High (Continuous Decision Score)", table_cell_style),
            Paragraph("O(N · t · log ψ)", table_cell_style),
            Paragraph("<b>High (Detects zero-day anomalies without ground truth labels)</b>", table_cell_style)
        ],
        [
            Paragraph("<b>Hybrid Behavioral + Graph Engine</b><br/>(Our Proposed PBL-III Target)", table_cell_bold),
            Paragraph("Unsupervised ML + Directed Graph Topology", table_cell_style),
            Paragraph("<b>High (Direct multi-hop cycle & path tracing)</b>", table_cell_style),
            Paragraph("<b>High (Risk Tier + Feature Vector + Graph Evidence)</b>", table_cell_style),
            Paragraph("O(N log N + V + E)", table_cell_style),
            Paragraph("<b>Optimal (Combines individual account profiling with network syndicate detection)</b>", table_cell_style)
        ]
    ]

    comp_table = Table(comp_data, colWidths=[85, 80, 80, 75, 55, 129])
    comp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#F7FAFC"), colors.white]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(comp_table)
    story.append(Spacer(1, 4))

    story.append(Paragraph("• Objectives Set in PBL-II & Planned Methodology", h2_style))
    obj_text = (
        "1. Transition from supervised classification to unsupervised behavioral anomaly detection in financial streams. "
        "<br/>2. Build scalable batch pipelines that process multi-thousand transactions without temporal data leakage. "
        "<br/>3. Design an investigative dashboard tailored for operational fraud triage and audit reporting."
    )
    story.append(Paragraph(obj_text, body_style))
    story.append(Spacer(1, 4))

    # =========================================================================
    # IV. PROGRESS MADE TILL NOW (PBL-III WORK)
    # =========================================================================
    story.append(Paragraph("IV. Progress Made Till Now (PBL-III Work)", h1_style))

    story.append(Paragraph("• Implementation Steps Completed So Far", h2_style))
    steps_text = (
        "1. <b>Schema Standardization & Input Validation:</b> Established the 14-column raw format (<code>transaction_id</code>, "
        "<code>sender_id</code>, <code>receiver_id</code>, <code>amount</code>, <code>transaction_type</code>, <code>transaction_step</code>, "
        "<code>sender_old_balance</code>, <code>sender_new_balance</code>, <code>receiver_old_balance</code>, <code>receiver_new_balance</code>, "
        "<code>transaction_time</code>, <code>device_id</code>, <code>device_change_flag</code>, <code>new_device_flag</code>). "
        "Built validation checks in <code>feature_engineering.py</code> verifying column presence, unique IDs, non-negative amounts, and datetime formats. "
        "<br/>2. <b>Leak-Free Feature Engineering (30 Features):</b> Implemented a chronological computation engine ensuring expanding statistics "
        "(historical counts, expanding means, sample variances, z-scores) and rolling windows (1h, 6h, 24h via <code>np.searchsorted</code>) only aggregate prior events ($t_{prior} < t_{current}$). "
        "<br/>3. <b>Exact Preprocessing & Inference:</b> Applied <code>np.log1p</code> strictly to the 11 features specified in <code>preprocessing_config.pkl</code>, "
        "normalized data via <code>scaler.transform()</code> from <code>scaler.pkl</code>, and generated predictions and decision scores via <code>isolation_forest.pkl</code>. "
        "<br/>4. <b>Interactive Streamlit Dashboard:</b> Developed <code>fraud_detection_app/app.py</code> with 6 dedicated sections: Upload, Overview KPIs, Ranked Suspicious Table, "
        "Visual Analytics, 30-Feature Deep-Dive Inspector, and Scored/Anomalies CSV Downloads."
    )
    story.append(Paragraph(steps_text, body_style))

    story.append(Paragraph("• Tools and Technologies Used", h2_style))
    tools_data = [
        [Paragraph("<b>Category</b>", table_header_style), Paragraph("<b>Technology / Tool</b>", table_header_style), Paragraph("<b>Role in Project</b>", table_header_style)],
        [Paragraph("Core Backend", table_cell_bold), Paragraph("Python 3.10+ / NumPy & Pandas", table_cell_style), Paragraph("Vectorized batch feature engineering, statistical expanding windows, and rolling velocity counters.", table_cell_style)],
        [Paragraph("Web Application", table_cell_bold), Paragraph("Streamlit", table_cell_style), Paragraph("Batch file upload, real-time KPI metrics, interactive filtering, charts, and report exports.", table_cell_style)],
        [Paragraph("Machine Learning", table_cell_bold), Paragraph("Scikit-Learn (Isolation Forest)", table_cell_style), Paragraph("Pre-trained tree-based anomaly isolation and continuous decision scoring.", table_cell_style)],
        [Paragraph("Graph Analytics", table_cell_bold), Paragraph("NetworkX (In Progress)", table_cell_style), Paragraph("Directed account-to-account graph modeling and multi-hop layering cycle detection.", table_cell_style)],
        [Paragraph("Serialization", table_cell_bold), Paragraph("Pickle", table_cell_style), Paragraph("Dynamic loading of frozen model artifacts, scaler parameters, and feature configurations.", table_cell_style)]
    ]
    tools_table = Table(tools_data, colWidths=[100, 130, 274])
    tools_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#F7FAFC"), colors.white]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(tools_table)
    story.append(Spacer(1, 4))

    story.append(Paragraph("• Partial Results, Prototypes & Automated Verification", h2_style))
    results_text = (
        "An automated test suite (<code>test_batch_app.py</code>) was developed and executed on a 500-transaction benchmark dataset (<code>sample_transactions.csv</code>), "
        "and all 15 pipeline checks passed. These checks cover plumbing, not detection accuracy: "
        "<br/>✓ <b>Artifact Integrity:</b> Successfully loaded all 4 pickle files without modification. "
        "<br/>✓ <b>Feature Dimensionality:</b> Produced exactly 30 features strictly matching <code>feature_config.pkl</code>. "
        "<br/>✓ <b>Immutability Verification:</b> Proved that <code>scaler.mean_</code>, <code>scaler.scale_</code>, and <code>model.offset_</code> were never refitted or retrained. "
        "<br/>✓ <b>Inference Validation:</b> Scored all 500 transactions into High Risk (score < -0.05), Medium Risk (-0.05 to 0.0), and Normal (score ≥ 0.0). "
        "<br/>✓ <b>Export Functionality:</b> Generated complete enriched CSVs and filtered anomalies-only exports successfully."
    )
    story.append(Paragraph(results_text, body_style))

    story.append(Paragraph("• Challenges Faced and Addressed", h2_style))
    chal_text = (
        "• <b>Preventing Data Leakage:</b> Sorted transactions chronologically prior to computation so that counts and variances only aggregate historical transactions. "
        "<br/>• <b>Distribution Skewness:</b> Applied <code>np.log1p</code> to 11 highly skewed features (amounts, balances, stats) to preserve linear scaling fidelity. "
        "<br/>• <b>Computational Efficiency:</b> Replaced slow iterative loops with vectorized <code>groupby</code> operations and binary search (<code>np.searchsorted</code>) for rolling time windows."
    )
    story.append(Paragraph(chal_text, body_style))
    story.append(Spacer(1, 4))

    # =========================================================================
    # V. WORK IN PROGRESS / PENDING WORK
    # =========================================================================
    story.append(Paragraph("V. Work in Progress / Pending Work", h1_style))

    story.append(Paragraph("• Tasks Being Worked On", h2_style))
    wip_text = (
        "1. <b>NetworkX Directed Graph Engine:</b> Constructing directed money-flow graphs where accounts form nodes and transactions form weighted edges with timestamp metadata. "
        "<br/>2. <b>Scam-Chain & Mule Ring Detection:</b> Developing topological algorithms to detect rapid multi-hop chains (A → B → C → D) and fund aggregation/dispersal hubs. "
        "<br/>3. <b>Signal Explainability Module:</b> Creating human-readable risk attribution badges highlighting contributing factors (e.g. nocturnal transfer, new device, extreme balance ratio)."
    )
    story.append(Paragraph(wip_text, body_style))

    story.append(Paragraph("• Next Milestones", h2_style))
    miles_data = [
        [Paragraph("<b>Milestone</b>", table_header_style), Paragraph("<b>Target Deliverable</b>", table_header_style), Paragraph("<b>Expected Output</b>", table_header_style)],
        [Paragraph("<b>Milestone 1</b>", table_cell_bold), Paragraph("NetworkX Graph Layer", table_cell_style), Paragraph("Account node creation, degree centralities, and mule path detection.", table_cell_style)],
        [Paragraph("<b>Milestone 2</b>", table_cell_bold), Paragraph("Multi-Signal Risk Engine", table_cell_style), Paragraph("Combined scoring synthesizing behavioral anomaly score with graph topology risk.", table_cell_style)],
        [Paragraph("<b>Milestone 3</b>", table_cell_bold), Paragraph("Interactive Network Visualizer", table_cell_style), Paragraph("Interactive node-link UI visualizing suspicious money flow paths.", table_cell_style)],
        [Paragraph("<b>Milestone 4</b>", table_cell_bold), Paragraph("Database & Case Management", table_cell_style), Paragraph("Persistent storage for batch audit history and flagged accounts.", table_cell_style)],
        [Paragraph("<b>Milestone 5</b>", table_cell_bold), Paragraph("Evaluation & Final Report", table_cell_style), Paragraph("Precision/recall benchmark evaluations and final project documentation.", table_cell_style)]
    ]
    miles_table = Table(miles_data, colWidths=[80, 160, 264])
    miles_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#F7FAFC"), colors.white]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(miles_table)
    story.append(Spacer(1, 4))

    # =========================================================================
    # VI. BIBLIOGRAPHY / REFERENCES
    # =========================================================================
    story.append(Paragraph("VI. Bibliography / References", h1_style))
    refs_text = (
        "1. F. T. Liu, K. M. Ting, and Z.-H. Zhou, 'Isolation Forest,' in <i>Proc. IEEE Int. Conf. on Data Mining (ICDM)</i>, 2008, pp. 413–422.<br/>"
        "2. E. A. Lopez-Rojas, A. Elmir, and S. Axelsson, 'PaySim: A financial mobile money simulator for fraud detection,' in <i>Proc. 28th European Modeling and Simulation Symp. (EMSS)</i>, 2016, pp. 249–255.<br/>"
        "3. T. Pourhabibi, K.-L. Ong, B. H. Kam, and Y. L. Boo, 'Fraud detection: A systematic literature review of graph-based anomaly detection approaches,' <i>Decision Support Systems</i>, vol. 133, Art. no. 113303, 2020.<br/>"
        "4. A. Correa Bahnsen, D. Aouada, A. Stojanovic, and B. Ottersten, 'Feature engineering strategies for credit card fraud detection,' <i>Expert Systems with Applications</i>, vol. 51, pp. 134–142, 2016.<br/>"
        "5. V. Chandola, A. Banerjee, and V. Kumar, 'Anomaly detection: A survey,' <i>ACM Comput. Surv.</i>, vol. 41, no. 3, pp. 1–58, 2009."
    )
    story.append(Paragraph(refs_text, body_style))

    # Build document with NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully generated: {pdf_filename}")


if __name__ == "__main__":
    create_pbl_report()
