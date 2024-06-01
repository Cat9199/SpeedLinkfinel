from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def create_shipping_pdf(user_info, shipping_info, filename):
    c = canvas.Canvas(filename, pagesize=letter)

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "Shipping Document")

    # User Information
    c.setFont("Helvetica", 12)
    y_position = 720
    for key, value in user_info.items():
        c.drawString(50, y_position, f"{key}: {value}")
        y_position -= 20

    # Shipping Information
    c.setFont("Helvetica", 12)
    y_position -= 20
    c.drawString(50, y_position, "Shipping Information:")
    y_position -= 20
    for key, value in shipping_info.items():
        c.drawString(70, y_position, f"{key}: {value}")
        y_position -= 20

    c.save()

# Example user info and shipping info
user_info = {
    "First Name": "John",
    "Last Name": "Doe",
    "Email": "john@example.com",
    "Phone": "123-456-7890"
}

shipping_info = {
    "City": "New York",
    "Address": "123 Shipping St",
    "Zip Code": "10001",
    "Delivery Date": "2024-06-01"
}

filename = "shipping_document.pdf"
create_shipping_pdf(user_info, shipping_info, filename)
