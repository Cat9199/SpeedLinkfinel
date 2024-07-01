# Imports
import random
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash, send_file, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from flask_migrate import Migrate
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image, Spacer
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Frame, PageTemplate
from io import BytesIO
import pandas as pd
import openpyxl

from honeybadger.contrib import FlaskHoneybadger
# Initialize Flask app
app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///speedlink.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'SpeedLink'
app.config['API_URL'] = 'http://speedlink-delivery.com'
app.config['API_VERSION'] = 'v1'
app.config['API_NAME'] = 'speedlink'
app.config['HONEYBADGER_ENVIRONMENT'] = 'production'
app.config['HONEYBADGER_API_KEY'] = 'hbp_hchIlpnfKJmHUAb8sxgQ71G9xqlvVV0qpcn0'
app.config['HONEYBADGER_PARAMS_FILTERS'] = 'password, secret, credit-card'
FlaskHoneybadger(app, report_exceptions=True)
app.permanent_session_lifetime = timedelta(days=30)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
# Database Models (User, Shipment, ShipmentTracking, ShippingPrice, SystemSetting, SystemCity)...
class User(db.Model):
      id = db.Column(db.Integer, primary_key=True)
      first_name = db.Column(db.String(80), nullable=False)
      last_name = db.Column(db.String(80), nullable=False)
      username = db.Column(db.String(80), nullable=False, unique=True)
      password = db.Column(db.String(80), nullable=False)
      email = db.Column(db.String(120), nullable=False, unique=True)
      phone = db.Column(db.String(80), nullable=False)
      address = db.Column(db.String(80), nullable=False)
      city = db.Column(db.String(80), nullable=False)
      user_type = db.Column(db.String(80), nullable=False)  # Admin, shipper, delivery
      created_at = db.Column(db.DateTime, server_default=db.func.now())

# Shipment Database
class Shipment(db.Model):
      id = db.Column(db.Integer, primary_key=True)
      user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
      shipment_code = db.Column(db.String(80), nullable=False)
      sender = db.Column(db.String(80), nullable=False)
      receiver = db.Column(db.String(80), nullable=False)
      receiver_phone1 = db.Column(db.String(80), nullable=False)
      receiver_phone2 = db.Column(db.String(80), nullable=False)
      receiver_city = db.Column(db.String(80), nullable=False)
      receiver_address = db.Column(db.String(1800), nullable=False)
      status = db.Column(db.String(80), nullable=False)  # Pending, Processing, Delivered, Cancelled, Returned
      price = db.Column(db.String(80), nullable=False)
      shipment_date = db.Column(db.DateTime, server_default=db.func.now())
      delivery_date = db.Column(db.DateTime, server_default=db.func.now())
      shipment_price = db.Column(db.String(80), nullable=False)
      payment_status = db.Column(db.String(80), nullable=False)
      created_at = db.Column(db.DateTime, server_default=db.func.now())
class ShipmentTracking(db.Model):
      id = db.Column(db.Integer, primary_key=True)
      shipment_id = db.Column(db.Integer, db.ForeignKey('shipment.id'), nullable=False)
      status = db.Column(db.String(80), nullable=False)
      created_at = db.Column(db.DateTime, server_default=db.func.now())
class ShippingPrice(db.Model):
      id = db.Column(db.Integer, primary_key=True)
      user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
      city = db.Column(db.String(80), nullable=False)
      price = db.Column(db.String(80), nullable=False)
      created_at = db.Column(db.DateTime, server_default=db.func.now())

class SystemSetting(db.Model):
      id = db.Column(db.Integer, primary_key=True)
      key = db.Column(db.String(80), nullable=False)
      value = db.Column(db.String(80), nullable=False)
      created_at = db.Column(db.DateTime, server_default=db.func.now())

class SystemCity(db.Model):
      id = db.Column(db.Integer, primary_key=True)
      city = db.Column(db.String(80), nullable=False, unique=True)
      default_price = db.Column(db.String(80), nullable=False)
      created_at = db.Column(db.DateTime, server_default=db.func.now())

def shipment_code_generator():
      prefix = 'SL-'
      suffix = ''.join(random.choices('0123456789', k=6))
      return prefix + suffix

def shipping_price_extractor(city, user_id):
      shipping_price = ShippingPrice.query.filter_by(city=city, user_id=user_id).first()
      if shipping_price:
            return shipping_price.price
      else:
            system_city = SystemCity.query.filter_by(city=city).first()
            if system_city:
                  return system_city.default_price
            else:
                  return 60

def getattr_filter(obj, attr):
    return getattr(obj, attr)

# Register the filter with Jinja2 environment
app.jinja_env.filters['getattr'] = getattr_filter
# App Routes
# Main Pages
@app.route('/dashboard')
def dashboard():
      if not session.get('logged_in'):
            return redirect(url_for('admin_login'))

      user_id = session.get('user_id')
      user_role = session.get('role')
      user = User.query.get(user_id)
      if user.user_type == 'Admin':
            shipments_query = Shipment.query
      else:
            shipments_query = Shipment.query.filter_by(sender=user_id)
      all_shipment_list = shipments_query.order_by(Shipment.created_at.desc()).limit(100).all()
      all_shipment_count = shipments_query.count()
      pending_shipment_count = shipments_query.filter_by(status='Pending').count()
      delivered_shipment_count = shipments_query.filter_by(status='Delivered').count()
      cancelled_shipment_count = shipments_query.filter_by(status='Cancelled').count()

      context = {
            'title': "Dashboard",
            'all_shipment_list': all_shipment_list,
            'all_shipment_count': all_shipment_count,
            'pending_shipment_count': pending_shipment_count,
            'delivered_shipment_count': delivered_shipment_count,
            'cancelled_shipment_count': cancelled_shipment_count
      }

      return render_template('index.html', **context)


MODEL_MAPPING = {
    'user': User,
    'shipment': Shipment,
    'shipmenttracking': ShipmentTracking,
    'shippingprice': ShippingPrice,
    'systemsetting': SystemSetting,
    'systemcity': SystemCity
}

def get_model_by_name(name):
    return MODEL_MAPPING.get(name.lower())
@app.route('/')
def index():
      return redirect('/login')
@app.route('/e/<table>/<int:id>', methods=['GET', 'POST'])
def edit_record(table, id):
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))

    model = get_model_by_name(table)
    if not model:
        return f"Table '{table}' not found", 404

    record = model.query.get_or_404(id)

    if request.method == 'POST':
        for field in record.__table__.columns:
            value = request.form.get(field.name)
            if value:
                if isinstance(field.type, db.DateTime):  # Check if the field is DateTime type
                    try:
                        value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')  # Adjust format as needed
                    except ValueError:
                        flash(f'Invalid date format for {field.name}. Expected format: YYYY-MM-DD HH:MM:SS', 'error')
                        return redirect(request.url)
                setattr(record, field.name, value)
        db.session.commit()
        flash(f'{table.capitalize()} record updated successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('edit_record.html', record=record, table=table.capitalize())
@app.route('/users')
def users():
      if not session.get('logged_in'):
            return redirect(url_for('admin_login'))

      users = User.query.all()
      context = {
            'title': "Users",
            'users': users
      }

      return render_template('users.html', **context)

@app.route('/config')
def config():
      if not session.get('logged_in'):
            return redirect(url_for('admin_login'))

      settings = SystemSetting.query.all()
      cities = SystemCity.query.all()
      context = {
            'title': "Config",
            'settings': settings,
            'cities': cities
      }

      return render_template('config.html', **context)

# Functional Pages
@app.route('/add_shipment')
def add_shipment():
      if not session.get('logged_in'):
            return redirect(url_for('admin_login'))

      users = User.query.all()
      syscity = SystemCity.query.all()
      context = {
            'title': "Add Shipment",
            'shipment_code': shipment_code_generator(),
            'syscity': syscity,
            'users': users
      }

      return render_template('add_shipment.html', **context)

@app.route('/all_shipment')
def all_shipment():
      if not session.get('logged_in'):
            return redirect(url_for('admin_login'))

      user_id = session.get('user_id')
      user_role = session.get('role')

      if user_role == 'admin':
            shipments_query = Shipment.query
      else:
            shipments_query = Shipment.query.filter_by(sender=user_id)

      all_shipment_list = shipments_query.all()
      context = {
            'title': "All Shipments",
            'all_shipment_list': all_shipment_list
      }

      return render_template('all_shipment.html', **context)

@app.route('/add_shipment', methods=['POST'])
def add_shipment_post():
      if not session.get('logged_in'):
            return redirect(url_for('admin_login'))

      user_id = session.get('user_id')
      shipment_code = request.form['shipment_code']
      sender = request.form['sender']
      receiver = request.form['receiver']
      receiver_phone1 = request.form['receiver_phone1']
      receiver_phone2 = request.form['receiver_phone2']
      receiver_city = request.form['receiver_city']
      receiver_address = request.form['receiver_address']
      status = request.form['status']
      price = request.form['price']
      shipment_price = shipping_price_extractor(city=receiver_city, user_id=user_id)
      payment_status = request.form['payment_status']

      # Create a new Shipment object
      new_shipment = Shipment(
            user_id=user_id,
            shipment_code=shipment_code,
            sender=sender,
            receiver=receiver,
            receiver_phone1=receiver_phone1,
            receiver_phone2=receiver_phone2,
            receiver_city=receiver_city,
            receiver_address=receiver_address,
            status=status,
            price=price,
            shipment_price=shipment_price,
            payment_status=payment_status
      )
      # Add the new shipment to the database
      db.session.add(new_shipment)
      db.session.commit()

      return render_template('add_shipment.html', message='Shipment added successfully', message_type='success', shipment_code=shipment_code_generator())
@app.route('/shipmentprice/<int:id>')
def shipmentprice(id):
      if not session.get('logged_in'):
            return redirect(url_for('admin_login'))
      user = User.query.get_or_404(id)
      shipmentprice = ShippingPrice.query.filter_by(user_id=id).all()
      context = {
            'title': "Shipment Price",
            'user': user,
            'cities': shipmentprice
      }
      return render_template('shipmentprice.html', **context)

@app.route('/print/<int:id>')
def print_shipment(id):
    user = User.query.get_or_404(id)
    shipments = Shipment.query.filter_by(user_id=id, status='Pending').all()

    # Create a BytesIO object to store the PDF content
    pdf_bytes = BytesIO()

    # Create PDF using ReportLab
    doc = SimpleDocTemplate(pdf_bytes, pagesize=letter)

    # Create a PageTemplate for each page
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)  # Define a frame
    page = PageTemplate(frames=[frame])
    doc.addPageTemplates([page])

    elements = []

    # Calculate the height for each shipment label
    box_height = doc.height / 3

    # Define styles for the table
    styles = getSampleStyleSheet()
    table_style = TableStyle([
        ('BOX', (-2, -2), (1, 1), -1, colors.black),  # Add a border around the entire table
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ])

    # Add shipments data
    for i in range(0, len(shipments), 3):
        # Add shipments data for each label
        for j in range(i, min(i + 3, len(shipments))):
            shipment = shipments[j]

            # Create a table for shipment information
            data = [
                  ['Shipment Code:', shipment.shipment_code, 'Logo:', ''],
                  ['User:', f"{user.first_name} {user.last_name}", 'Total Price:', (shipment.shipment_price + shipment.price)],
                  ['Sender:', shipment.sender, 'Receiver:', shipment.receiver],
                  ['Phone:', shipment.receiver_phone1, 'Phone2:', shipment.receiver_phone2],
                  ['City:', shipment.receiver_city, 'Address:', shipment.receiver_address],
                  ['Price:', shipment.price, 'Delivery Price:', shipment.shipment_price],
                  ['Code:', shipment.shipment_code, 'Date:', shipment.created_at.strftime('%Y-%m-%d')],
            ]

            # Add logo
            logo_path = './static/images/Logo-dark.png'  # Change this to the path of your logo file
            logo = Image(logo_path, width=80, height=80)
            data[0][3] = logo
            # size of hedder and footer
            doc.topMargin = 0.5 
            doc.bottomMargin = 0.5 

            table_width = doc.width - doc.leftMargin - doc.rightMargin  # Calculate table width
            table = Table(data, colWidths=[table_width / 2] * 4, style=table_style)  # Divide the width into 4 columns
            elements.append(table)

            # Add space between shipment labels
            if j < min(i + 2, len(shipments) - 1):
                elements.append(Spacer(1, box_height / 6))  # Reduce the spacer size

    # Build PDF document
    doc.build(elements)

    # Reset the pointer of the BytesIO object to the beginning
    pdf_bytes.seek(0)

    # Return the PDF as a file attachment with manual Content-Disposition header
    headers = {
        'Content-Disposition': f'attachment; filename=shipment_{id}_date={datetime.now()}.pdf'
    }
    for shipment in shipments:
        shipment.status = 'Processing'
        db.session.commit()
    return Response(pdf_bytes, mimetype='application/pdf', headers=headers)

@app.route('/download_shipment/<int:id>')
def download_shipment(id):
      shipment = Shipment.query.filter_by(id=id).first()
      user = User.query.get_or_404(shipment.sender)

      # Create a BytesIO object to store the PDF content
      pdf_bytes = BytesIO()

      # Create PDF using ReportLab
      doc = SimpleDocTemplate(pdf_bytes, pagesize=letter)

      # Create a PageTemplate for each page
      frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)  # Define a frame
      page = PageTemplate(frames=[frame])
      doc.addPageTemplates([page])

      elements = []

      # Calculate the height for each shipment label
      box_height = doc.height / 3

      # Define styles for the table
      styles = getSampleStyleSheet()
      table_style = TableStyle([
            ('BOX', (-2, -2), (1, 1), -1, colors.black),  # Add a border around the entire table
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
      ])

      # Add shipments data
      data = [
                  ['Shipment Code:', shipment.shipment_code, 'Logo:', ''],
                  ['User:', f"{user.first_name} {user.last_name}", 'Total Price:', f'{(int(shipment.shipment_price) + int(shipment.price))}L.E'],
                  ['Sender:', shipment.sender, 'Receiver:', shipment.receiver],
                  ['Phone:', shipment.receiver_phone1, 'Phone2:', shipment.receiver_phone2],
                  ['City:', shipment.receiver_city, 'Address:', shipment.receiver_address],
                  ['Price:', shipment.price, 'Delivery Price:', shipment.shipment_price],
                  ['Code:', shipment.shipment_code, 'Date:', shipment.created_at.strftime('%Y-%m-%d')],
      ]
      # Add logo
      logo_path = './static/images/Logo-dark.png'  # Change this to the path of your logo file
      logo = Image(logo_path, width=80, height=80)
      data[0][3] = logo

      table_width = doc.width - doc.leftMargin - doc.rightMargin  # Calculate table width
      table = Table(data, colWidths=[table_width / 2] * 4, style=table_style)  # Divide the width into 4 columns
      elements.append(table)

      # Build PDF document
      doc.build(elements)

      # Reset the pointer of the BytesIO object to the beginning
      pdf_bytes.seek(0)

      # Return the PDF as a file attachment with manual Content-Disposition header
      headers = {
            'Content-Disposition': f'attachment; filename=shipment_{id}_date={datetime.now()}.pdf'
      }
      return Response(pdf_bytes, mimetype='application/pdf', headers=headers)
@app.route('/login')
def admin_login():
      if session.get('logged_in'):
            return redirect('/dashboard')
      return render_template('login.html')

@app.route('/login', methods=['POST'])
def admin_login_post():
      username = request.form.get('username')
      password = request.form.get('password')
      user = User.query.filter(or_(User.email == username, User.username == username, User.phone == username), User.password == password).first()

      if not user:
            return render_template('login.html', message='Invalid Credentials')

      # Setting session data
      session['logged_in'] = True
      session['user_id'] = user.id
      session['email'] = user.email
      session['role'] = user.user_type
      session['name'] = user.first_name + ' ' + user.last_name
      session.permanent = True

      return redirect('/dashboard')

@app.route('/edit_shipment/<int:id>')
def edit_shipment(id):
      if not session.get('logged_in'):
            return redirect(url_for('admin_login'))

      shipment = Shipment.query.get_or_404(id)
      users = User.query.all()
      syscity = SystemCity.query.all()
      context = {
            'title': "Edit Shipment",
            'shipment': shipment,
            'syscity': syscity,
            'users': users
      }
      return render_template('edit_shipment.html', **context)
# /edit_shipment/{{ shipment.id }} route
@app.route('/edit_shipment/<int:id>', methods=['POST'])
def edit_shipment_post(id):
      if not session.get('logged_in'):
            return redirect(url_for('admin_login'))

      shipment = Shipment.query.get_or_404(id)
      shipment.sender = request.form['sender']
      shipment.receiver = request.form['receiver']
      shipment.receiver_phone1 = request.form['receiver_phone1']
      shipment.receiver_phone2 = request.form['receiver_phone2']
      shipment.receiver_city = request.form['receiver_city']
      shipment.receiver_address = request.form['receiver_address']
      shipment.status = request.form['status']
      shipment.price = request.form['price']
      shipment.shipment_price = shipping_price_extractor(city=shipment.receiver_city, user_id=shipment.user_id)


      db.session.commit()

      return redirect('/all_shipment')

@app.route('/add_client', methods=['POST'])
def add_client():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))

    first_name = request.form['first_name']
    last_name = request.form['last_name']
    username = request.form['username']
    password = request.form['password']
    email = request.form['email']
    phone = request.form['phone']
    address = request.form['address']
    city = request.form['city']
    user_type = request.form['user_type']

    new_user = User(
        first_name=first_name,
        last_name=last_name,
        username=username,
        password=password,
        email=email,
        phone=phone,
        address=address,
        city=city,
        user_type=user_type
    )

    db.session.add(new_user)
    db.session.commit()  # Commit the new user to generate the user_id

    system_cities = SystemCity.query.all()
    for c in system_cities:
        new_shipmentprice = ShippingPrice(
            user_id=new_user.id,
            city=c.city,
            price=c.default_price
        )
        db.session.add(new_shipmentprice)
    
    db.session.commit()  # Commit the new shipment prices

    flash('Client added successfully!', 'success')
    return redirect(url_for('users'))

@app.route('/add_city', methods=['POST'])
def add_city():
      if not session.get('logged_in'):
            return redirect(url_for('admin_login'))

      city = request.form['city']
      default_price = request.form['default_price']

      new_city = SystemCity(
            city=city,
            default_price=default_price
      )

      db.session.add(new_city)
      db.session.commit()

      flash('City added successfully!', 'success')
      return redirect(url_for('config'))

@app.route('/user/<int:id>')
def user(id):
      if not session.get('logged_in'):
            return redirect(url_for('admin_login'))

      shipment = Shipment.query.filter_by(user_id=id).all()
      shipmentcount = Shipment.query.filter_by(user_id=id).count()
      user = User.query.get_or_404(id)
      context = {
            'title': "User",
            'user': user,
            'shipment': shipment,
            'shipmentcount': shipmentcount
      }

      return render_template('user-profile.html', **context)

@app.route('/add_key', methods=['POST'])
def add_key():
      if not session.get('logged_in'):
            return redirect(url_for('admin_login'))

      key = request.form['key']
      value = request.form['value']

      new_key = SystemSetting(
            key=key,
            value=value
      )

      db.session.add(new_key)
      db.session.commit()

      flash('Key added successfully!', 'success')
      return redirect(url_for('config'))
@app.route('/download_shipment_excel/<int:id>')
def download_shipment_excel(id):
      if not session.get('logged_in'):
            return redirect(url_for('admin_login'))

      user = User.query.get_or_404(id)
      shipments = Shipment.query.filter_by(user_id=id).all()

      # Create a BytesIO object to store the Excel content
      excel_bytes = BytesIO()

      # Create Excel file using Pandas


      # Create a DataFrame from the shipments data
      data = []
      for shipment in shipments:
            data.append({
                  'Shipment Code': shipment.shipment_code,
                  'Sender': shipment.sender,
                  'Receiver': shipment.receiver,
                  'Receiver Phone1': shipment.receiver_phone1,
                  'Receiver Phone2': shipment.receiver_phone2,
                  'Receiver City': shipment.receiver_city,
                  'Receiver Address': shipment.receiver_address,
                  'Status': shipment.status,
                  'Price': shipment.price,
                  'Shipment Date': shipment.shipment_date,
                  'Delivery Date': shipment.delivery_date,
                  'Shipment Price': shipment.shipment_price,
                  'Payment Status': shipment.payment_status,
                  'Created At': shipment.created_at
            })

      df = pd.DataFrame(data)
      df.to_excel(excel_bytes, index=False)

      # Reset the pointer of the BytesIO object to the beginning
      excel_bytes.seek(0)

      # Return the Excel as a file attachment with manual Content-Disposition header
      headers = {
            'Content-Disposition': f'attachment; filename=shipment_{id}_date={datetime.now()}.xlsx'
      }
      return Response(excel_bytes, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers=headers)
@app.route('/edit_client/<int:id>', methods=['POST'])
def edit_client(id):
      if not session.get('logged_in'):
            return redirect(url_for('admin_login'))

      user = User.query.get_or_404(id)
      user.first_name = request.form['first_name']
      user.last_name = request.form['last_name']
      user.username = request.form['username']

      if request.form['password']:
            user.password = request.form['password']

      user.email = request.form['email']
      user.phone = request.form['phone']
      user.address = request.form['address']
      user.city = request.form['city']
      user.user_type = request.form['user_type']

      db.session.commit()

      flash('Client updated successfully!', 'success')
      return redirect(url_for('users'))

@app.route('/delete_client/<int:id>', methods=['GET'])
def delete_client(id):
      if not session.get('logged_in'):
            return redirect(url_for('admin_login'))

      user = User.query.get_or_404(id)
      db.session.delete(user)
      db.session.commit()

      flash('Client deleted successfully!', 'success')
      return redirect(url_for('users'))

@app.route('/serch_shipment', methods=['POST'])
def serch_shipment():
      if not session.get('logged_in'):
            return redirect(url_for('admin_login'))
      data = request.get_json()
      search = data.get('search', '')
      user_id = session.get('user_id')
      user_role = session.get('role')
      if user_role == 'admin':
            shipments_query = Shipment.query
      else:
            shipments_query = Shipment.query.filter_by(user_id=user_id)

      # Add dynamic filtering
      filter_conditions = or_(
            shipment.shipment_code.like(f'%{search}%'),
            Shipment.sender.like(f'%{search}%'),
            Shipment.receiver.like(f'%{search}%'),
            Shipment.receiver_phone1.like(f'%{search}%'),
            Shipment.receiver_phone2.like(f'%{search}%'),
            Shipment.receiver_city.like(f'%{search}%'),
            Shipment.receiver_address.like(f'%{search}%'),
            Shipment.status.like(f'%{search}%'),
            Shipment.price.like(f'%{search}%'),
            Shipment.shipment_price.like(f'%{search}%'),
            Shipment.payment_status.like(f'%{search}%')
      )

      all_shipment_list = shipments_query.filter(filter_conditions).all()

      shipment_data = []
      for shipment in all_shipment_list:
            shipment_data.append({
                  'id': shipment.id,
                  'shipment_code': shipment.shipment_code,
                  'sender': shipment.sender,
                  'receiver': shipment.receiver,
                  'receiver_phone1': shipment.receiver_phone1,
                  'receiver_phone2': shipment.receiver_phone2,
                  'receiver_city': shipment.receiver_city,
                  'receiver_address': shipment.receiver_address,
                  'status': shipment.status,
                  'price': shipment.price,
                  'shipment_date': shipment.shipment_date,
                  'delivery_date': shipment.delivery_date,
                  'shipment_price': shipment.shipment_price,
                  'payment_status': shipment.payment_status,
                  'created_at': shipment.created_at
            })

      return jsonify({'all_shipment_list': shipment_data})
@app.route('/dowenloaddb')
def dowenloaddb():
      if not session.get('logged_in'):
            return redirect(url_for('admin_login'))
      # make he respons with a db file to download
      return send_file('./instance/speedlink.db', as_attachment=True)
@app.route('/logout')
def logout():
      session.pop('logged_in', None)
      session.pop('user_id', None)
      session.pop('email', None)
      session.pop('name', None)
      session.pop('role', None)
      return redirect('/login')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
            if request.method == 'POST':
                  # Get the uploaded file
                  file = request.files['file']
                  sender = request.form['sender']
                  if file and allowed_file(file.filename):
                        # Read the Excel file into a pandas DataFrame
                        df = pd.read_excel(file)
                        
                        # Iterate over rows in the DataFrame and add data to the database
                        for _, row in df.iterrows():
                              shipment = Shipment(
                                    user_id=sender,
                                    shipment_code=shipment_code_generator(),
                                    sender=sender,
                                    receiver=row['receiver'],
                                    receiver_phone1=row['receiver_phone1'],
                                    receiver_phone2=row['receiver_phone2'],
                                    receiver_city=row['receiver_city'],
                                    receiver_address=row['receiver_address'],
                                    status='Pending',
                                    price=row['price'],
                                    shipment_price=shipping_price_extractor(city=row['receiver_city'], user_id=sender),
                                    payment_status='unpaid'
                              )
                              db.session.add(shipment)
                        
                        # Commit changes to the database
                        db.session.commit()
                        
                        flash('Data uploaded successfully!', 'success')
                        return redirect(url_for('dashboard'))
                  else:
                        flash('Invalid file format. Please upload an Excel file.', 'error')
            return render_template('upload.html' , title='Upload Excel File', users=User.query.all())

# Function to check if the file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'xlsx'
# 404  Error Page
@app.errorhandler(404)
def page_not_found(e):
      return render_template('404.html'), 404
# 500  Error Page
@app.errorhandler(500)
def server_error(e):
      return render_template('500.html'), 500

if __name__ == '__main__':
      with app.app_context():
            db.create_all()
            print('Database Created and its path is: speedlink.db')
            # Check if the user table is empty and create a default admin user
            if not User.query.first():
                  new_user = User(
                        first_name='Admin',
                        last_name='Admin',
                        username='admin',
                        password='admin',
                        email='admin@admin.com',
                        phone='123456789',
                        address='Admin Address',
                        city='Admin City',
                        user_type='admin'
                  )
                  db.session.add(new_user)
                  db.session.commit()

      print(shipment_code_generator())
      app.run(debug=True, port=5000, host='0.0.0.0')
