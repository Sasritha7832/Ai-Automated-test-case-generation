import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER

def create_enterprise_prd(filename):
    doc = SimpleDocTemplate(filename, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=18)
                            
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=24, spaceAfter=20, alignment=TA_CENTER)
    h1 = ParagraphStyle('H1', parent=styles['Heading1'], fontSize=16, spaceBefore=20, spaceAfter=10, textColor=colors.darkblue)
    h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=14, spaceBefore=15, spaceAfter=8, textColor=colors.black)
    h3 = ParagraphStyle('H3', parent=styles['Heading3'], fontSize=12, spaceBefore=10, spaceAfter=6)
    
    body = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, leading=14, alignment=TA_JUSTIFY, spaceAfter=8)
    body_bold = ParagraphStyle('BodyBold', parent=body, fontName='Helvetica-Bold')
    code = ParagraphStyle('Code', parent=styles['Code'], fontSize=9, leading=12, backColor=colors.whitesmoke, spaceAfter=8)
    
    story = []

    # --- COVER PAGE ---
    story.append(Spacer(1, 2*inch))
    story.append(Paragraph("PRODUCT REQUIREMENTS DOCUMENT (PRD)", title_style))
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("Project: GlobalTrade Brokerage Platform v2.0", h2))
    story.append(Paragraph("Document Version: 1.4.2 (Final Approved)", body))
    story.append(Paragraph("Status: Approved for Engineering", body))
    story.append(Paragraph("Target Release: Q4 2026", body))
    story.append(PageBreak())

    # --- 1. INTRODUCTION ---
    story.append(Paragraph("1. Executive Summary", h1))
    story.append(Paragraph("The GlobalTrade Brokerage Platform (v2.0) aims to revolutionize retail investing by introducing seamless fractional share trading, instant bank settlement, and an automated portfolio rebalancer. This PRD outlines the engineering requirements for the core trading execution engine, user authentication, and regulatory compliance logging. The system must support concurrent user loads of over 100,000 active sessions with sub-50ms execution latency.", body))
    
    # --- 2. AUTHENTICATION & SECURITY ---
    story.append(Paragraph("2. Authentication & Identity Verification (KYC)", h1))
    story.append(Paragraph("2.1 Multi-Factor Authentication (MFA)", h2))
    story.append(Paragraph("All user accounts must enforce MFA upon login. The system shall support SMS OTP, Email OTP, and Time-Based One-Time Passwords (TOTP) via apps like Google Authenticator. ", body))
    
    # List requirements
    mfa_reqs = [
        "REQ-SEC-01: The system MUST lock the user account after 5 consecutive failed login attempts.",
        "REQ-SEC-02: An automated email notification SHALL be dispatched to the user upon account lockout, providing a password reset link.",
        "REQ-SEC-03: The MFA session token MUST expire after 15 minutes of inactivity.",
        "REQ-SEC-04: API requests containing expired Bearer tokens must return a 401 Unauthorized response instantly."
    ]
    for r in mfa_reqs:
        story.append(Paragraph(r, body_bold))

    story.append(Paragraph("2.2 KYC & AML Compliance", h2))
    story.append(Paragraph("Before a user can deposit funds, they must pass Know Your Customer (KYC) checks. The system will integrate with the Jumio API for document scanning.", body))
    story.append(Paragraph("REQ-KYC-01: The platform MUST restrict all trading capabilities until the user's KYC status is flagged as 'VERIFIED'. If the status is 'PENDING', only browsing features are allowed.", body_bold))
    story.append(Paragraph("REQ-KYC-02: Any deposit exceeding $10,000 USD in a single transaction MUST trigger an automated Anti-Money Laundering (AML) audit log and be paused for manual review.", body_bold))

    # --- 3. TRADING ENGINE ---
    story.append(Paragraph("3. Core Trading & Order Execution", h1))
    story.append(Paragraph("The trading engine must handle market orders, limit orders, and fractional share allocations.", body))
    
    story.append(Paragraph("3.1 Order Types", h2))
    
    # Add a table
    data = [
        ['Order Type', 'Execution Condition', 'Expiration Options'],
        ['Market', 'Execute immediately at best available bid/ask', 'Day Only'],
        ['Limit', 'Execute only at specified price or better', 'Day, GTC (Good Till Cancelled)'],
        ['Stop-Loss', 'Convert to Market order if price drops below trigger', 'Day, GTC']
    ]
    t = Table(data, colWidths=[1.5*inch, 3*inch, 2*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN',      (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.beige),
        ('GRID',       (0,0), (-1,-1), 1, colors.black)
    ]))
    story.append(t)
    story.append(Spacer(1, 0.2*inch))

    story.append(Paragraph("REQ-TRD-01: An order MUST be rejected if the user has insufficient 'Settled Cash' available in their account.", body_bold))
    story.append(Paragraph("REQ-TRD-02: Market orders for highly volatile assets (Beta > 2.0) MUST prompt the user with a volatility warning before submission.", body_bold))
    story.append(Paragraph("REQ-TRD-03: The system SHALL support fractional trading down to 6 decimal places (e.g., 0.000001 BTC or 0.550123 AAPL).", body_bold))
    
    # --- 4. API SPECIFICATIONS ---
    story.append(PageBreak())
    story.append(Paragraph("4. External Integrations", h1))
    story.append(Paragraph("4.1 Plaid Bank Linking", h2))
    story.append(Paragraph("Users will link bank accounts using the Plaid Link widget. Once linked, the backend will exchange the public token for an access token.", body))
    story.append(Paragraph("REQ-INT-01: The system MUST securely encrypt the Plaid access token in the database using AES-256 encryption.", body_bold))
    story.append(Paragraph("REQ-INT-02: If a Plaid webhook fires indicating an 'ITEM_LOGIN_REQUIRED' error, the system MUST immediately disable outbound ACH transfers for that account and notify the user to re-link.", body_bold))

    story.append(Paragraph("4.2 Clearing House API", h2))
    story.append(Paragraph("Trade settlements will be routed to Apex Clearing.", body))
    story.append(Paragraph("REQ-INT-03: All executed trades MUST be batched and transmitted to the Apex SFTP server by 4:15 PM EST daily. Trades executed after 4:00 PM EST market close MUST be marked for next-day settlement.", body_bold))

    # --- 5. REPORTING ---
    story.append(Paragraph("5. Notifications & Reporting", h1))
    story.append(Paragraph("REQ-NOT-01: A trade confirmation email MUST be sent within 60 seconds of any order execution, containing the ticker, quantity, fill price, and transaction ID.", body_bold))
    story.append(Paragraph("REQ-NOT-02: Users MUST be able to download their monthly account statement as a PDF file no later than the 5th business day of the subsequent month.", body_bold))

    # --- 6. EDGE CASES ---
    story.append(Paragraph("6. Defined Edge Cases & Degradation Constraints", h1))
    story.append(Paragraph("REQ-EDG-01: Handling Stock Splits: If a stock split occurs while a user holds a GTC limit order, the system MUST automatically cancel the order and push a notification to the user.", body_bold))
    story.append(Paragraph("REQ-EDG-02: API Rate Limiting: The REST API MUST ratelimit incoming requests to 100 requests per minute per IP. Excess requests MUST yield a 429 Too Many Requests response.", body_bold))
    story.append(Paragraph("REQ-EDG-03: Circuit Breaker: If the S&P 500 index drops by 7% (Level 1 Market Wide Circuit Breaker), the system MUST halt all new equities order submissions for exactly 15 minutes.", body_bold))

    # Build PDF
    doc.build(story)
    print(f"Created Enterprise PRD at: {filename}")

if __name__ == "__main__":
    os.makedirs("sample_prds", exist_ok=True)
    create_enterprise_prd("sample_prds/Enterprise_GlobalTrade_Brokerage_PRD.pdf")
