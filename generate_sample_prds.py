import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def create_pdf(filename, title, content):
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Custom heading styles
    h1 = ParagraphStyle('H1', parent=styles['Heading1'], spaceAfter=14)
    h2 = ParagraphStyle('H2', parent=styles['Heading2'], spaceAfter=10)
    body = ParagraphStyle('Body', parent=styles['Normal'], spaceAfter=8, leading=14)
    
    story = []
    story.append(Paragraph(title, h1))
    story.append(Spacer(1, 0.2 * inch))
    
    for section in content:
        if section.startswith('# '):
            story.append(Paragraph(section[2:], h1))
            story.append(Spacer(1, 0.1 * inch))
        elif section.startswith('## '):
            story.append(Paragraph(section[3:], h2))
            story.append(Spacer(1, 0.05 * inch))
        elif section.strip() == "":
            story.append(Spacer(1, 0.1 * inch))
        else:
            story.append(Paragraph(section, body))
            
    doc.build(story)
    print(f"Created: {filename}")

# --- HEALTHCARE PORTAL PRD ---
healthcare_content = [
    "# 1. Introduction",
    "The HealthConnect Patient Portal is a secure web application that allows patients to manage their medical profiles, schedule appointments, and view lab results. It must comply with HIPAA regulations.",
    "",
    "# 2. User Authentication",
    "## 2.1 Login & Security",
    "The system must allow patients to log in using a verified email address and password. The system must enforce two-factor authentication (2FA) via SMS or authenticator app for all user accounts. If a user fails to log in 5 consecutive times, the account must be locked for 30 minutes.",
    "",
    "# 3. Appointment Scheduling",
    "## 3.1 Booking Flow",
    "Patients must be able to view available time slots for doctors based on specialty. The system should allow users to book an appointment at least 24 hours in advance. The system must send an email confirmation upon successful booking.",
    "## 3.2 Cancellations",
    "Users must be able to cancel an appointment free of charge if doing so more than 48 hours in advance. If cancelled within 48 hours, the system must prompt the user with a late-cancellation warning.",
    "",
    "# 4. Lab Results Viewer",
    "## 4.1 Secure Access",
    "The system shall display lab results only after the primary physician has digitally signed and approved them. Users must be able to download their lab results as an encrypted PDF document."
]

# --- FINTECH PAYMENT APP PRD ---
fintech_content = [
    "# 1. Application Overview",
    "PaySwift is a mobile-first peer-to-peer (P2P) payment application designed to allow users to split bills, send money internationally, and manage low-balance alerts.",
    "",
    "# 2. Wallet Funding",
    "## 2.1 Linked Accounts",
    "Users must be able to link up to 3 external bank accounts via Plaid integration. The system must validate the routing number before allowing deposits. Users shall be able to fund their wallet instantly using a debit card, subject to a 1.5% processing fee.",
    "",
    "# 3. P2P Transactions",
    "## 3.1 Sending Money",
    "The application must allow users to send money to other registered users via their phone number or unique @handle. The system shall block any transaction that exceeds the user's available wallet balance. A transaction must process within 3 seconds, or a timeout error should be displayed.",
    "## 3.2 International Transfers",
    "The system must automatically calculate and display the live currency exchange rate before the user confirms an international transfer.",
    "",
    "# 4. Notifications",
    "## 4.1 Low Balance Alerts",
    "The App should dispatch a push notification immediately if the user's wallet balance drops below $20.00."
]

# --- ECOMMERCE DASHBOARD PRD ---
saas_content = [
    "# 1. Product Scope",
    "The Vendor Admin Dashboard is a centralized hub for e-commerce sellers to track inventory, manage active orders, and view sales analytics.",
    "",
    "# 2. Inventory Management",
    "## 2.1 Product Catalog",
    "The dashboard must allow vendors to add new products by uploading up to 5 images, a title, a description, and a price. The system shall reject any product pricing set to $0.00 or negative values. Vendors must be able to bulk-update inventory counts via CSV upload.",
    "",
    "# 3. Order Processing",
    "## 3.1 Fulfillment Workflow",
    "When a customer places an order, the system must change the order status to 'Pending Fulfillment'. The vendor must be able to generate and print a shipping label directly from the order details page. Once the label is printed, the system shall automatically update the status to 'Shipped'.",
    "",
    "# 4. Analytics & Reporting",
    "## 4.1 Sales Dashboard",
    "The dashboard must render a line chart showing daily revenue over the last 30 days. The system must allow the user to export the 30-day sales data as an Excel file."
]

if __name__ == "__main__":
    os.makedirs("sample_prds", exist_ok=True)
    create_pdf("sample_prds/Healthcare_Portal_PRD.pdf", "HealthConnect Patient Portal PRD", healthcare_content)
    create_pdf("sample_prds/FinTech_Payment_App_PRD.pdf", "PaySwift P2P Payment App PRD", fintech_content)
    create_pdf("sample_prds/Ecommerce_Vendor_Dashboard_PRD.pdf", "Vendor Admin Dashboard PRD", saas_content)
