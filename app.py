from flask import Flask,request,jsonify,render_template,redirect,url_for,session,flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import timedelta

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///speedlink.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'SpeedLink'
app.config['API_URL'] = 'http://speedlink-delivery.com'
app.config['API_VERSION'] = 'v1'
app.config['API_NAME'] = 'speedlink'
app.permanent_session_lifetime = timedelta(days=30)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
# Users DataBase
class User(db.Model):
      id         = db.Column(db.Integer, primary_key=True)
      first_name = db.Column(db.String(80), nullable=False)
      last_name  = db.Column(db.String(80), nullable=False)
      username   = db.Column(db.String(80), nullable=False, unique=True)
      password   = db.Column(db.String(80), nullable=False)
      email      = db.Column(db.String(120), nullable=False, unique=True)
      phone      = db.Column(db.String(80), nullable=False)                
      address    = db.Column(db.String(80), nullable=False)
      city       = db.Column(db.String(80), nullable=False)
      user_type  = db.Column(db.String(80), nullable=False) # Admin, shipper, delivery
      created_at = db.Column(db.DateTime, server_default=db.func.now())
      # Shipment Database
class Shipment(db.Model):
      id = db.Column(db.Integer, primary_key=True)
      user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
      Shipment_code = db.Column(db.String(80), nullable=False)
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

class ShippingPrice(db.Model):
      id              = db.Column(db.Integer, primary_key=True)
      user_id         = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
      city            = db.Column(db.String(80), nullable=False)
      price           = db.Column(db.String(80), nullable=False)
      created_at      = db.Column(db.DateTime, server_default=db.func.now())
class SystemSetting(db.Model):
      id              = db.Column(db.Integer, primary_key=True)
      key             = db.Column(db.String(80), nullable=False)
      value           = db.Column(db.String(80), nullable=False)
      created_at      = db.Column(db.DateTime, server_default=db.func.now())
class SystemCity(db.Model):
      id              = db.Column(db.Integer, primary_key=True)
      city            = db.Column(db.String(80), nullable=False, unique=True)
      default_price   = db.Column(db.String(80), nullable=False)
      created_at      = db.Column(db.DateTime, server_default=db.func.now())

def ShipmentCodeGenerator():
    import random
    prefix = 'SL-'
    suffix = ''.join(random.choices('0123456789', k=6))
    return prefix + suffix
def ShippingPriceExtractor(city, user_id):
      shipping_price = ShippingPrice.query.filter_by(city=city, user_id=user_id).first()
      if shipping_price:
            return shipping_price.price
      else:
            system_city = SystemCity.query.filter_by(city=city).first()
            if system_city:
                  return system_city.default_price
            else:
                  return 60
# App Routes
# -main Pages
@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))

    user_id = session.get('user_id')
    user_role = session.get('roule')

    if user_role == 'admin':
        shipments_query = Shipment.query
    else:
        shipments_query = Shipment.query.filter_by(sender=user_id)
    AllShipmentList = shipments_query.order_by(Shipment.created_at.desc()).limit(100).all()
    AllShipmentCount = shipments_query.count()
    PendingShipmentcount = shipments_query.filter_by(status='Pending').count()
    DeliveredShipmentcount = shipments_query.filter_by(status='Delivered').count()
    CancelledShipmentcount = shipments_query.filter_by(status='Cancelled').count()

    context = {
        'title': "Dashboard",
        'AllShipmentList': AllShipmentList,
        'AllShipmentCount': AllShipmentCount,
        'PendingShipmentcount': PendingShipmentcount,
        'DeliveredShipmentcount': DeliveredShipmentcount,
        'CancelledShipmentcount': CancelledShipmentcount
    }
    
    return render_template('index.html', **context)

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
# - Functional Pages
@app.route('/add_shipment')
def add_shipment():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    users = User.query.all()
    syscity = SystemCity.query.all()
    context = {
        'title': "Add Shipment",
        'shipment_code': ShipmentCodeGenerator(),
        'syscity': syscity,
        'users': users
    }

    return render_template('add_shipment.html', **context)

@app.route('/add_shipment', methods=['POST'])
def add_shipmentpost():
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
    shipment_price = ShippingPriceExtractor(city=receiver_city, user_id=user_id)
    payment_status = request.form['payment_status']

    # Create a new Shipment object
    new_shipment = Shipment(
        user_id=user_id,
        Shipment_code=shipment_code,
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
    
    return render_template('add_shipment.html', message='Shipment added successfully', message_type='success')

@app.route('/login')
def admin_login():
    return render_template('login.html')
@app.route('/login', methods=['POST'])
def admin_login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    user = User.query.filter_by(email=username, password=password).first()
    if not user:
        user = User.query.filter_by(username=username, password=password).first()
        if not user:
            user = User.query.filter_by(phone=username, password=password).first()
            if not user:
                  return render_template('login.html', message='Invalid Credentials')
    print(f"username and password are: {username} and {password}")

    # Setting session data
    session['logged_in'] = True
    session['user_id']   = user.id
    session['email']     = user.email
    session['roule']     = user.user_type
    session['name']      = user.first_name + ' ' + user.last_name
    session.permanent    = True  
    return redirect('/dashboard')

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
    db.session.commit()
    
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
@app.route('/edit_client/<int:id>', methods=['POST'])
def edit_client(id):
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))

    user = User.query.get_or_404(id)
    user.first_name = request.form['first_name']
    user.last_name = request.form['last_name']
    user.username = request.form['username']
    if request.form['password']:
        user.password = generate_password_hash(request.form['password'])
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

@app.route('/logout')
def logout():
        session.pop('logged_in', None)
        session.pop('user_id', None)
        session.pop('email', None)
        session.pop('name', None)
        session.pop('roule', None)
        return redirect('/login')

if '__main__' == __name__ :
      with app.app_context():
            db.create_all()
            print('Database Created and her path is : speedlink.db')
            # check if the user table is empty and create a default admin user
            if not User.query.first():
                  new_user = User(
                        first_name   ='Admin',
                        last_name    ='Admin',
                        username     ='admin',
                        password     ='admin',
                        email        = 'admin@admin.com',
                        phone        = '123456789',
                        address      = 'Admin Address',
                        city         = 'Admin City',
                        user_type    = 'admin'
                  )
                  db.session.add(new_user)
                  db.session.commit()

      print(ShipmentCodeGenerator())
      app.run(debug=True, port=5000, host='0.0.0.0')