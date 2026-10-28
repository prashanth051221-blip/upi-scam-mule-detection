"""
Build an executive-grade 16:9 widescreen presentation (both .pptx and .pdf)
for PBL-III AI-Powered UPI Scam & Fraud Detection.
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# -----------------------------------------------------------------------------
# CONSTANTS & COLOR PALETTE (Executive Navy / Cyan Theme)
# -----------------------------------------------------------------------------
BG_COLOR = RGBColor(10, 17, 40)          # Dark Executive Navy (#0A1128)
CARD_BG = RGBColor(19, 30, 58)           # Slate Card Background (#131E3A)
CARD_BORDER = RGBColor(43, 76, 126)      # Subtle Border (#2B4C7E)
ACCENT_CYAN = RGBColor(0, 210, 255)      # Luminous Cyan (#00D2FF)
ACCENT_BLUE = RGBColor(66, 153, 225)     # Sky Blue (#4299E1)
TEXT_WHITE = RGBColor(248, 250, 252)     # Off-white (#F8FAFC)
TEXT_MUTED = RGBColor(160, 174, 192)     # Muted Slate (#A0AEC0)
ACCENT_GREEN = RGBColor(72, 187, 120)    # Success Green (#48BB78)
ACCENT_RED = RGBColor(245, 101, 101)     # Alert Red (#F56565)
ACCENT_AMBER = RGBColor(237, 137, 54)    # Amber Warning (#ED8936)
ACCENT_PURPLE = RGBColor(159, 122, 234)  # Purple (#9F7AEA)


def create_pptx_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    def add_slide_background(slide, title_text="", category_text="PBL-III (AIM3170) | MENTOR PRESENTATION"):
        # Full slide background
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = BG_COLOR
        bg.line.fill.background()

        # Top banner accent line
        top_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(0.08))
        top_bar.fill.solid()
        top_bar.fill.fore_color.rgb = ACCENT_CYAN
        top_bar.line.fill.background()

        if title_text:
            # Category pill tag
            tag_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.35), Inches(11.7), Inches(0.35))
            tf_tag = tag_box.text_frame
            tf_tag.word_wrap = True
            p_tag = tf_tag.paragraphs[0]
            p_tag.text = category_text.upper()
            p_tag.font.name = "Arial"
            p_tag.font.size = Pt(9)
            p_tag.font.bold = True
            p_tag.font.color.rgb = ACCENT_CYAN

            # Title
            title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.65), Inches(11.7), Inches(0.75))
            tf_title = title_box.text_frame
            tf_title.word_wrap = True
            p_title = tf_title.paragraphs[0]
            p_title.text = title_text
            p_title.font.name = "Arial"
            p_title.font.size = Pt(22)
            p_title.font.bold = True
            p_title.font.color.rgb = TEXT_WHITE

        # Footer
        footer_box = slide.shapes.add_textbox(Inches(0.8), Inches(7.0), Inches(11.7), Inches(0.35))
        tf_foot = footer_box.text_frame
        p_foot = tf_foot.paragraphs[0]
        p_foot.text = "Dept. of Artificial Intelligence & Machine Learning  |  Manipal University Jaipur  |  AI-Powered UPI Scam Detection"
        p_foot.font.name = "Arial"
        p_foot.font.size = Pt(8.5)
        p_foot.font.color.rgb = TEXT_MUTED

    def add_card(slide, left, top, width, height, heading="", border_color=CARD_BORDER, fill_color=CARD_BG):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
        card.fill.solid()
        card.fill.fore_color.rgb = fill_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1.2)
        card.adjustments[0] = 0.04  # Slight corner roundness

        if heading:
            tb = slide.shapes.add_textbox(Inches(left + 0.2), Inches(top + 0.15), Inches(width - 0.4), Inches(0.45))
            tf = tb.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = heading
            p.font.name = "Arial"
            p.font.size = Pt(13)
            p.font.bold = True
            p.font.color.rgb = ACCENT_CYAN
        return card

    # =========================================================================
    # SLIDE 1: TITLE SLIDE
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    add_slide_background(s1)

    # Hero Banner Card
    add_card(s1, 0.8, 1.0, 11.733, 5.5, border_color=ACCENT_CYAN, fill_color=RGBColor(14, 23, 48))

    # Pill badge
    pill = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.3), Inches(1.5), Inches(3.8), Inches(0.38))
    pill.fill.solid()
    pill.fill.fore_color.rgb = RGBColor(12, 74, 110)
    pill.line.color.rgb = ACCENT_CYAN
    pill.line.width = Pt(1)
    tf_pill = pill.text_frame
    p_pill = tf_pill.paragraphs[0]
    p_pill.text = "PBL-III (AIM3170) • MENTOR PRESENTATION"
    p_pill.font.name = "Arial"
    p_pill.font.size = Pt(9.5)
    p_pill.font.bold = True
    p_pill.font.color.rgb = ACCENT_CYAN
    p_pill.alignment = PP_ALIGN.CENTER

    # Main Title
    t_box = s1.shapes.add_textbox(Inches(1.3), Inches(2.05), Inches(10.5), Inches(1.5))
    tf_t = t_box.text_frame
    tf_t.word_wrap = True
    p1 = tf_t.paragraphs[0]
    p1.text = "AI-Powered UPI Scam & Fraud Detection"
    p1.font.name = "Arial"
    p1.font.size = Pt(30)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_WHITE

    p2 = tf_t.add_paragraph()
    p2.text = "Behavioral Anomaly Detection & Multi-Hop Graph Layering Analytics"
    p2.font.name = "Arial"
    p2.font.size = Pt(15)
    p2.font.color.rgb = ACCENT_BLUE
    p2.space_before = Pt(8)

    # 3 Metadata Columns
    cols_data = [
        ("PROJECT DOMAIN", "FinTech Cybersecurity\nUnsupervised Anomaly Detection\nDirected Graph NetworkX"),
        ("CORE ML ENGINE", "Isolation Forest Model\nStandardScaler Normalization\nExact 30 Model Features"),
        ("ACADEMIC INSTITUTION", "Manipal University Jaipur\nDept. of AIML (2026)\nApplication-Based Project")
    ]
    for i, (head, desc) in enumerate(cols_data):
        c_left = 1.3 + (i * 3.65)
        add_card(s1, c_left, 3.8, 3.4, 2.2, heading=head, border_color=CARD_BORDER, fill_color=CARD_BG)
        tb_c = s1.shapes.add_textbox(Inches(c_left + 0.2), Inches(4.35), Inches(3.0), Inches(1.5))
        tf_c = tb_c.text_frame
        tf_c.word_wrap = True
        for line in desc.split('\n'):
            p = tf_c.add_paragraph()
            p.text = f"• {line}"
            p.font.name = "Arial"
            p.font.size = Pt(10)
            p.font.color.rgb = TEXT_MUTED
            p.space_after = Pt(4)

    # =========================================================================
    # SLIDE 2: PROBLEM STATEMENT & MOTIVATION
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_slide_background(s2, "Problem Statement & Industry Motivation")

    # Left Card: The Challenge
    add_card(s2, 0.8, 1.45, 5.7, 4.2, heading="The Modern UPI Scam Challenge")
    tb2_1 = s2.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.3), Inches(3.4))
    tf2_1 = tb2_1.text_frame
    tf2_1.word_wrap = True
    p_items_1 = [
        ("Massive Velocity & Irreversibility: ", "UPI processes billions of transactions monthly. Instant settlements give victims zero rollback window."),
        ("Social Engineering Scams: ", "Phishing QR codes, fake customer care refunds, and remote-screen-share tools coerce authorized debits."),
        ("Account Takeover Bursts: ", "Unrecognized devices draining 100% balance during nocturnal hours (22:00 – 06:00)."),
        ("Mule Layering Networks: ", "Stolen money is split across multiple intermediary accounts within minutes to prevent fund freezing.")
    ]
    for bold_prefix, text in p_items_1:
        p = tf2_1.add_paragraph()
        p.text = f"• "
        p.font.name = "Arial"
        p.font.size = Pt(10)
        p.font.color.rgb = TEXT_WHITE
        run_b = p.add_run()
        run_b.text = bold_prefix
        run_b.font.bold = True
        run_b.font.color.rgb = ACCENT_CYAN
        run_t = p.add_run()
        run_t.text = text
        run_t.font.color.rgb = TEXT_MUTED
        p.space_after = Pt(8)

    # Right Card: Why Existing Rule Systems Fail
    add_card(s2, 6.8, 1.45, 5.7, 4.2, heading="Why Traditional Rule Engines Fail")
    tb2_2 = s2.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(3.4))
    tf2_2 = tb2_2.text_frame
    tf2_2.word_wrap = True
    p_items_2 = [
        ("High False Positive Rates: ", "Static rules (e.g. Amount > ₹50,000) trigger false alarms on genuine high-value users while missing micro-layering."),
        ("Siloed Per-Transaction Analysis: ", "Evaluating transfers individually fails to detect multi-transfer bursts and rapid forwarding chains."),
        ("Black-Box Opacity: ", "Investigators receive raw flags without actionable risk levels or supporting behavioral evidence."),
        ("Our Core Approach: ", "Unsupervised Isolation Forest + 30 chronological behavioral features + NetworkX graph topology.")
    ]
    for bold_prefix, text in p_items_2:
        p = tf2_2.add_paragraph()
        p.text = f"• "
        p.font.name = "Arial"
        p.font.size = Pt(10)
        p.font.color.rgb = TEXT_WHITE
        run_b = p.add_run()
        run_b.text = bold_prefix
        run_b.font.bold = True
        run_b.font.color.rgb = ACCENT_AMBER
        run_t = p.add_run()
        run_t.text = text
        run_t.font.color.rgb = TEXT_MUTED
        p.space_after = Pt(8)

    # Bottom summary pill
    add_card(s2, 0.8, 5.8, 11.7, 0.95, border_color=ACCENT_CYAN, fill_color=RGBColor(14, 23, 48))
    tb2_bot = s2.shapes.add_textbox(Inches(1.0), Inches(5.85), Inches(11.3), Inches(0.85))
    tf2_bot = tb2_bot.text_frame
    tf2_bot.word_wrap = True
    p_bot = tf2_bot.paragraphs[0]
    p_bot.text = "🎯 Objective: Build an interactive batch investigation system that ingests monthly transaction datasets, computes 30 leak-free behavioral features, ranks suspicious transactions by anomaly score, and provides actionable triage evidence."
    p_bot.font.name = "Arial"
    p_bot.font.size = Pt(10.5)
    p_bot.font.bold = True
    p_bot.font.color.rgb = TEXT_WHITE

    # =========================================================================
    # SLIDE 3: PBL-II RECAP & FOUNDATION
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_slide_background(s3, "PBL-II Recap & Transition to PBL-III")

    # Left: PBL-II Recap
    add_card(s3, 0.8, 1.45, 5.7, 5.2, heading="PBL-II Foundation (AI Health Assistant)")
    tb3_1 = s3.shapes.add_textbox(Inches(1.0), Inches(2.05), Inches(5.3), Inches(4.3))
    tf3_1 = tb3_1.text_frame
    tf3_1.word_wrap = True
    recap_pts = [
        ("Supervised ML Classification: ", "Trained supervised models on multi-symptom vectors to predict clinical disease categories."),
        ("Fuzzy Dietary Recommendation: ", "Implemented token-sort fuzzy matching (rapidfuzz) on structured food knowledge bases."),
        ("Multi-Tab Streamlit UI: ", "Built responsive multi-page user interfaces with authentication and session states."),
        ("Dual Data Persistence: ", "Integrated MongoDB cloud database with structured local JSON fallback."),
        ("Key Competencies Acquired: ", "Model serialization (pickle), web application deployment, input validation, and user experience workflows.")
    ]
    for bold_prefix, text in recap_pts:
        p = tf3_1.add_paragraph()
        p.text = f"• "
        p.font.name = "Arial"
        p.font.size = Pt(10)
        p.font.color.rgb = TEXT_WHITE
        run_b = p.add_run()
        run_b.text = bold_prefix
        run_b.font.bold = True
        run_b.font.color.rgb = ACCENT_GREEN
        run_t = p.add_run()
        run_t.text = text
        run_t.font.color.rgb = TEXT_MUTED
        p.space_after = Pt(8)

    # Right: PBL-III Evolution
    add_card(s3, 6.8, 1.45, 5.7, 5.2, heading="PBL-III Evolution (UPI Scam Detection)")
    tb3_2 = s3.shapes.add_textbox(Inches(7.0), Inches(2.05), Inches(5.3), Inches(4.3))
    tf3_2 = tb3_2.text_frame
    tf3_2.word_wrap = True
    evol_pts = [
        ("Supervised ➔ Unsupervised Anomaly Detection: ", "Replaced static class labels with Isolation Forest to detect unknown and zero-day scam behaviors without ground truth bias."),
        ("Single Input ➔ Full Batch Analytics: ", "Shifted from single-form user prediction to monthly batch transaction dataset processing."),
        ("Strict Leak-Free Feature Engineering: ", "Engineered 30 temporal, rolling-window, and expanding statistics strictly prior to each event (t_prior < t_current)."),
        ("Relational Graph Modeling: ", "Added NetworkX graph analysis layer to trace multi-hop layering chains (A ➔ B ➔ C ➔ D)."),
        ("Investigative Decision Support: ", "Tiered risk classifications (High/Medium/Low) and feature vector inspection for security analysts.")
    ]
    for bold_prefix, text in evol_pts:
        p = tf3_2.add_paragraph()
        p.text = f"• "
        p.font.name = "Arial"
        p.font.size = Pt(10)
        p.font.color.rgb = TEXT_WHITE
        run_b = p.add_run()
        run_b.text = bold_prefix
        run_b.font.bold = True
        run_b.font.color.rgb = ACCENT_CYAN
        run_t = p.add_run()
        run_t.text = text
        run_t.font.color.rgb = TEXT_MUTED
        p.space_after = Pt(8)

    # =========================================================================
    # SLIDE 4: SYSTEM ARCHITECTURE (6-STAGE PIPELINE)
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_slide_background(s4, "End-to-End System Architecture & Pipeline")

    stages = [
        ("01. BATCH UPLOAD", "Accepts raw monthly transaction CSV with 14 mandatory attributes.", ACCENT_BLUE),
        ("02. DATA VALIDATION", "Validates columns, nulls, unique transaction IDs, non-negative amounts.", ACCENT_CYAN),
        ("03. FEATURE ENGINE", "Vectorized chronological calculation of exactly 30 ML features without data leakage.", ACCENT_PURPLE),
        ("04. PREPROCESSING", "Selective np.log1p on 11 log features + StandardScaler.transform() (never refitted).", ACCENT_AMBER),
        ("05. ISOLATION FOREST", "Inference via pre-trained isolation_forest.pkl generating continuous decision anomaly scores.", ACCENT_RED),
        ("06. STREAMLIT UI", "6-section dashboard: KPIs, ranked suspicious table, charts, inspector, and CSV downloads.", ACCENT_GREEN)
    ]

    for idx, (title, desc, color) in enumerate(stages):
        r = idx // 3
        c = idx % 3
        c_left = 0.8 + (c * 3.98)
        c_top = 1.5 + (r * 2.5)

        add_card(s4, c_left, c_top, 3.75, 2.25, heading=title, border_color=color, fill_color=CARD_BG)
        
        # Badge
        b_box = s4.shapes.add_textbox(Inches(c_left + 0.15), Inches(c_top + 0.55), Inches(3.45), Inches(1.5))
        tf_b = b_box.text_frame
        tf_b.word_wrap = True
        p = tf_b.paragraphs[0]
        p.text = desc
        p.font.name = "Arial"
        p.font.size = Pt(10)
        p.font.color.rgb = TEXT_MUTED
        p.space_before = Pt(4)

    # Footer note
    add_card(s4, 0.8, 6.0, 11.7, 0.75, border_color=CARD_BORDER, fill_color=RGBColor(14, 23, 48))
    tb4_foot = s4.shapes.add_textbox(Inches(1.0), Inches(6.05), Inches(11.3), Inches(0.65))
    tf4_foot = tb4_foot.text_frame
    p_f = tf4_foot.paragraphs[0]
    p_f.text = "🔒 Architectural Rule: Pre-trained Isolation Forest and StandardScaler are completely immutable artifacts. No refitting or retraining occurs during inference."
    p_f.font.name = "Arial"
    p_f.font.size = Pt(9.5)
    p_f.font.bold = True
    p_f.font.color.rgb = ACCENT_CYAN

    # =========================================================================
    # SLIDE 5: THE 30 MODEL FEATURES BREAKDOWN
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_slide_background(s5, "Feature Engineering: The 30 Model Features")

    feat_cats = [
        ("1. Direct & Temporal Features (10)", [
            "amount (Transferred sum in $)",
            "transaction_step (Timeline hour index)",
            "sender_old_balance / sender_new_balance",
            "receiver_old_balance / receiver_new_balance",
            "device_change_flag / new_device_flag",
            "transaction_hour (0–23 extracted from timestamp)",
            "is_night (Binary: 1 if 22:00–06:00, else 0)"
        ], ACCENT_BLUE),
        ("2. Historical Interaction Counts (6)", [
            "sender_txn_count_before (Prior transactions sent)",
            "same_step_txn_count_before (Txns in same step)",
            "sender_receiver_txn_count_before (Pair history)",
            "sender_unique_recipients_before (Unique recipients)",
            "receiver_txn_count_before (Prior transactions received)",
            "receiver_unique_senders_before (Unique senders)"
        ], ACCENT_CYAN),
        ("3. Expanding Statistics & Ratios (6)", [
            "sender_balance_ratio (amount / [sender_old_balance + 1])",
            "time_since_previous_sender_txn (Hours, -1 if 1st txn)",
            "sender_amount_mean_before (Expanding mean)",
            "sender_amount_std_before (Expanding sample std)",
            "amount_deviation (abs[amount - mean_before])",
            "amount_zscore (Standardized deviation score)"
        ], ACCENT_AMBER),
        ("4. Rolling Velocity & Chains (8)", [
            "txns_last_1h (Rolling 1h count via searchsorted)",
            "txns_last_6h (Rolling 6h count via searchsorted)",
            "txns_last_24h (Rolling 24h count via searchsorted)",
            "rapid_transaction_flag (Burst indicator: time <= 6min)",
            "hop_number (Position in transfer money flow chain)",
            "chain_length (Total length of money laundering chain)",
            "chain_duration_steps (Duration from chain root)",
            "transaction_frequency (Baseline observation rate)"
        ], ACCENT_PURPLE)
    ]

    for i, (cat_title, f_list, color) in enumerate(feat_cats):
        r = i // 2
        c = i % 2
        c_left = 0.8 + (c * 5.95)
        c_top = 1.45 + (r * 2.6)

        add_card(s5, c_left, c_top, 5.75, 2.45, heading=cat_title, border_color=color, fill_color=CARD_BG)
        tb = s5.shapes.add_textbox(Inches(c_left + 0.15), Inches(c_top + 0.45), Inches(5.45), Inches(1.9))
        tf = tb.text_frame
        tf.word_wrap = True
        for f_item in f_list:
            p = tf.add_paragraph()
            p.text = f"• {f_item}"
            p.font.name = "Arial"
            p.font.size = Pt(8.5)
            p.font.color.rgb = TEXT_MUTED
            p.space_after = Pt(1.5)

    add_card(s5, 0.8, 6.15, 11.7, 0.65, border_color=CARD_BORDER, fill_color=RGBColor(14, 23, 48))
    tb5_foot = s5.shapes.add_textbox(Inches(1.0), Inches(6.18), Inches(11.3), Inches(0.55))
    tf5_foot = tb5_foot.text_frame
    p_f5 = tf5_foot.paragraphs[0]
    p_f5.text = "⚡ Data Leakage Guarantee: Transactions are sorted chronologically (timestamp + step + index). Every rolling window and cumulative count only evaluates events prior to current event."
    p_f5.font.name = "Arial"
    p_f5.font.size = Pt(9.0)
    p_f5.font.bold = True
    p_f5.font.color.rgb = ACCENT_GREEN

    # =========================================================================
    # SLIDE 6: STREAMLIT BATCH DASHBOARD
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_slide_background(s6, "Interactive Batch Dashboard (Streamlit UI)")

    dash_sections = [
        ("Section 1: Upload & Validator", "Drag-and-drop CSV uploader validating 14 raw columns, duplicate IDs, null values, and negative amounts with 1-click demo dataset loading.", ACCENT_BLUE),
        ("Section 2: Executive Overview KPIs", "High-level metrics: total transaction volume, normal vs. anomaly breakdown, anomaly rate (%), highest-risk transaction ID, and minimum anomaly score.", ACCENT_CYAN),
        ("Section 3: Ranked Suspicious Table", "Prioritized data table sorted by anomaly score ascending. Interactive filtering by Risk Tier (High/Medium/Low), Prediction, Type, and Display Limits (Top 10 to All).", ACCENT_PURPLE),
        ("Section 4: Visual Anomaly Analytics", "Interactive charting tabs: Class distributions, anomaly score histograms, temporal step trends, transaction type breakdowns, and top-10 extreme score rankings.", ACCENT_AMBER),
        ("Section 5: 30-Feature Deep-Dive Inspector", "Select any transaction ID to view all 14 raw input attributes alongside the complete 30-feature vector before and after log transformations and scaling.", ACCENT_GREEN),
        ("Section 6: Scored & Filtered CSV Export", "One-click export of complete scored dataset (original columns + score + prediction + risk_level) or anomalies-only CSV for audit teams.", ACCENT_RED)
    ]

    for idx, (title, desc, color) in enumerate(dash_sections):
        r = idx // 3
        c = idx % 3
        c_left = 0.8 + (c * 3.98)
        c_top = 1.45 + (r * 2.3)

        add_card(s6, c_left, c_top, 3.75, 2.15, heading=title, border_color=color, fill_color=CARD_BG)
        tb_s = s6.shapes.add_textbox(Inches(c_left + 0.15), Inches(c_top + 0.45), Inches(3.45), Inches(1.55))
        tf_s = tb_s.text_frame
        tf_s.word_wrap = True
        p = tf_s.paragraphs[0]
        p.text = desc
        p.font.name = "Arial"
        p.font.size = Pt(9)
        p.font.color.rgb = TEXT_MUTED
        p.space_before = Pt(3)

    # Risk Tier Banner
    add_card(s6, 0.8, 5.85, 11.7, 0.95, border_color=CARD_BORDER, fill_color=RGBColor(14, 23, 48))
    tb6_foot = s6.shapes.add_textbox(Inches(1.0), Inches(5.9), Inches(11.3), Inches(0.85))
    tf6_foot = tb6_foot.text_frame
    tf6_foot.word_wrap = True
    p_f6 = tf6_foot.paragraphs[0]
    p_f6.text = "📊 Risk Classification Framework:\n• High Risk: Anomaly Score < -0.05 (Immediate investigation priority)\n• Medium Risk: -0.05 ≤ Anomaly Score < 0.00 (Secondary review)\n• Normal / Low Risk: Anomaly Score ≥ 0.00 (Conforms to expected behavioral baseline)"
    p_f6.font.name = "Arial"
    p_f6.font.size = Pt(9)
    p_f6.font.color.rgb = TEXT_WHITE

    # =========================================================================
    # SLIDE 7: AUTOMATED VERIFICATION & TEST RESULTS
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    add_slide_background(s7, "Automated Verification & Pipeline Reliability")

    # Left: 15/15 Tests
    add_card(s7, 0.8, 1.45, 5.7, 5.2, heading="15/15 Automated Test Suite (100% Pass)", border_color=ACCENT_GREEN)
    tb7_1 = s7.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.3), Inches(4.3))
    tf7_1 = tb7_1.text_frame
    tf7_1.word_wrap = True
    test_items = [
        "✓ Test 1 & 2: Benchmark loaded (500 txns) & 14 required columns validated.",
        "✓ Test 3, 4 & 5: Exactly 30 features generated matching saved configuration order.",
        "✓ Test 6: Exact 11 log features transformed using np.log1p().",
        "✓ Test 7 & 8: StandardScaler.transform() executed; scaler was NOT refitted.",
        "✓ Test 9 & 10: Isolation Forest loaded; model was NOT retrained.",
        "✓ Test 11 & 12: 100% of transactions scored with continuous decision score & discrete prediction.",
        "✓ Test 13: All 14 original columns preserved alongside anomaly outputs.",
        "✓ Test 14 & 15: Complete scored CSV and filtered anomalies-only CSV exported successfully."
    ]
    for t_str in test_items:
        p = tf7_1.add_paragraph()
        p.text = t_str
        p.font.name = "Arial"
        p.font.size = Pt(9.5)
        p.font.color.rgb = TEXT_WHITE
        p.space_after = Pt(5)

    # Right: Sample Scenario Results
    add_card(s7, 6.8, 1.45, 5.7, 5.2, heading="Live Detection Scenarios & Scoring", border_color=ACCENT_CYAN)
    tb7_2 = s7.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.3))
    tf7_2 = tb7_2.text_frame
    tf7_2.word_wrap = True
    scenarios = [
        ("Scenario 1: Normal Daytime Payment", "Transfer $1,200 during daytime (14:30) from registered device with consistent historical balance ratio.\n➔ Anomaly Score: +0.0237 | Prediction: +1 (Normal / Low Risk)", ACCENT_GREEN),
        ("Scenario 2: Nocturnal Account Takeover", "Transfer $850,000 at 03:15 AM from an unrecognized new device draining 100% of sender's balance to a newly created account.\n➔ Anomaly Score: -0.1428 | Prediction: -1 (High Risk)", ACCENT_RED),
        ("Scenario 3: Rapid Mule Layering Hop", "Account receives large transfer and immediately forwards $79,000 downstream within 6 minutes to third-party node.\n➔ Anomaly Score: -0.0969 | Prediction: -1 (High Risk)", ACCENT_AMBER)
    ]
    for s_title, s_desc, s_color in scenarios:
        p_t = tf7_2.add_paragraph()
        p_t.text = s_title
        p_t.font.name = "Arial"
        p_t.font.size = Pt(10.5)
        p_t.font.bold = True
        p_t.font.color.rgb = s_color
        p_t.space_before = Pt(6)

        p_d = tf7_2.add_paragraph()
        p_d.text = s_desc
        p_d.font.name = "Arial"
        p_d.font.size = Pt(9)
        p_d.font.color.rgb = TEXT_MUTED
        p_d.space_after = Pt(6)

    # =========================================================================
    # SLIDE 8: POST-MIDTERM ROADMAP & MILESTONES
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    add_slide_background(s8, "Post-Midterm Roadmap & Upcoming Milestones")

    milestones = [
        ("Milestone 1: NetworkX Directed Graph Engine", "In Progress", "Construct directed money-flow graphs where accounts represent nodes and fund transfers form weighted edges with timestamp metadata.", ACCENT_CYAN),
        ("Milestone 2: Multi-Hop Scam Chain Detection", "Upcoming", "Implement cycle detection and path search algorithms to identify rapid layering chains (A ➔ B ➔ C ➔ D) and fund dispersal syndicates.", ACCENT_BLUE),
        ("Milestone 3: Combined Multi-Signal Risk Engine", "Upcoming", "Synthesize behavioral Isolation Forest scores (60%) with graph topology centralities (40%) into a unified 0–100 composite risk score.", ACCENT_PURPLE),
        ("Milestone 4: Interactive Network Visualizer", "Upcoming", "Develop interactive node-link visualizers in the Streamlit UI to display money flow subgraphs for suspicious accounts.", ACCENT_AMBER),
        ("Milestone 5: Evaluation & Final Report", "Upcoming", "Precision/recall evaluation on labelled UPI data, ablation study, and final report. (Database storage dropped from scope.)", ACCENT_GREEN)
    ]

    for i, (m_title, m_status, m_desc, m_color) in enumerate(milestones):
        c_top = 1.45 + (i * 1.05)
        add_card(s8, 0.8, c_top, 11.733, 0.95, border_color=m_color, fill_color=CARD_BG)
        
        # Text
        tb_m = s8.shapes.add_textbox(Inches(1.0), Inches(c_top + 0.1), Inches(11.3), Inches(0.75))
        tf_m = tb_m.text_frame
        tf_m.word_wrap = True
        
        p = tf_m.paragraphs[0]
        run_title = p.add_run()
        run_title.text = f"{m_title}  "
        run_title.font.name = "Arial"
        run_title.font.size = Pt(11)
        run_title.font.bold = True
        run_title.font.color.rgb = TEXT_WHITE

        run_stat = p.add_run()
        run_stat.text = f"[{m_status.upper()}]\n"
        run_stat.font.name = "Arial"
        run_stat.font.size = Pt(9.5)
        run_stat.font.bold = True
        run_stat.font.color.rgb = m_color

        run_desc = p.add_run()
        run_desc.text = m_desc
        run_desc.font.name = "Arial"
        run_desc.font.size = Pt(9)
        run_desc.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 9: SUMMARY & MENTOR DISCUSSION POINTS
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    add_slide_background(s9, "Project Summary & Mentor Discussion")

    # Left: Midterm Achievements
    add_card(s9, 0.8, 1.45, 5.7, 5.2, heading="Key Achievements Till Mid-Term", border_color=ACCENT_CYAN)
    tb9_1 = s9.shapes.add_textbox(Inches(1.0), Inches(2.05), Inches(5.3), Inches(4.3))
    tf9_1 = tb9_1.text_frame
    tf9_1.word_wrap = True
    achievements = [
        ("Working Batch Engine: ", "Built high-performance feature engineering calculating 30 ML features from raw monthly CSV batches without future data leakage."),
        ("Strict Model Integrity: ", "Integrated pre-trained Isolation Forest and StandardScaler as immutable artifacts with zero refitting or retraining."),
        ("Comprehensive Streamlit Dashboard: ", "Developed complete 6-section UI featuring dataset overview KPIs, suspicious transaction filters, analytics charts, feature deep-dive, and exports."),
        ("100% Automated Test Suite: ", "Passed all 15 operational test assertions validating pipeline correctness.")
    ]
    for bold_prefix, text in achievements:
        p = tf9_1.add_paragraph()
        p.text = "✓ "
        p.font.name = "Arial"
        p.font.size = Pt(10)
        p.font.color.rgb = TEXT_WHITE
        run_b = p.add_run()
        run_b.text = bold_prefix
        run_b.font.bold = True
        run_b.font.color.rgb = ACCENT_GREEN
        run_t = p.add_run()
        run_t.text = text
        run_t.font.color.rgb = TEXT_MUTED
        p.space_after = Pt(10)

    # Right: Mentor Discussion Points
    add_card(s9, 6.8, 1.45, 5.7, 5.2, heading="Discussion Points for Mentor Guidance", border_color=ACCENT_AMBER)
    tb9_2 = s9.shapes.add_textbox(Inches(7.0), Inches(2.05), Inches(5.3), Inches(4.3))
    tf9_2 = tb9_2.text_frame
    tf9_2.word_wrap = True
    mentor_topics = [
        ("Graph Topology Scaling: ", "Best practices for constructing dynamic transaction subgraphs in NetworkX when batch sizes scale past 100,000 nodes."),
        ("Composite Risk Weighting: ", "Refining weighting formulas between tabular Isolation Forest anomaly scores (60%) and graph degree centralities (40%)."),
        ("Evaluation Benchmarks: ", "Feedback on synthetic fraud injection scenarios (layering, account takeover, fan-out dispersal) for precision/recall benchmarking."),
        ("Live Demonstration: ", "Ready to demonstrate the interactive Streamlit batch application during review.")
    ]
    for bold_prefix, text in mentor_topics:
        p = tf9_2.add_paragraph()
        p.text = "❓ "
        p.font.name = "Arial"
        p.font.size = Pt(10)
        p.font.color.rgb = TEXT_WHITE
        run_b = p.add_run()
        run_b.text = bold_prefix
        run_b.font.bold = True
        run_b.font.color.rgb = ACCENT_AMBER
        run_t = p.add_run()
        run_t.text = text
        run_t.font.color.rgb = TEXT_MUTED
        p.space_after = Pt(10)

    pptx_filename = "UPI_Scam_Detection_Presentation.pptx"
    prs.save(pptx_filename)
    print(f"PowerPoint Presentation successfully generated: {pptx_filename}")


if __name__ == "__main__":
    create_pptx_deck()
