from flask import Flask, request, redirect, render_template, flash, session
from flask_mail import Mail, Message
import hashlib
import urllib.parse
import sqlite3

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Needed for session management

# Email Configuration
app.config['MAIL_SERVER'] = 'smtp-relay.brevo.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'mathebulanhlobo69@gmail.com'
app.config['MAIL_PASSWORD'] = 'b5wNDIOJFtKQXHB4'
app.config['MAIL_DEFAULT_SENDER'] = 'mathebulanhlobo69@gmail.com'

mail = Mail(app)

# PayFast credentials
MERCHANT_ID = '10000100'
MERCHANT_KEY = '46f0cd694581a'
PAYFAST_URL = 'https://sandbox.payfast.co.za/eng/process'
DB = 'transactions.db'

@app.route('/')
def index():
    return render_template('checkout.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        # Save the email to your database and handle user registration
        flash('Registration successful! Please check your email for confirmation.', 'success')
        send_email(email)
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Handle user login
        session['logged_in'] = True
        return redirect('/')
    return render_template('login.html')

@app.route('/pay', methods=['POST'])
def pay():
    if not session.get('logged_in'):
        return redirect('/login')

    item = request.form['item']
    amount = request.form['amount']
    email = request.form['email']

    with sqlite3.connect(DB) as conn:
        conn.execute("INSERT INTO transactions (item_name, amount, status) VALUES (?, ?, ?)",
                     (item, amount, 'pending'))

    data = {
        'merchant_id': MERCHANT_ID,
        'merchant_key': MERCHANT_KEY,
        'amount': amount,
        'item_name': item,
        'return_url': request.url_root + 'success?email=' + email,
        'cancel_url': request.url_root + 'cancel',
        'notify_url': request.url_root + 'notify',
    }

    signature = '&'.join(f"{k}={v}" for k, v in data.items())
    data['signature'] = hashlib.md5(signature.encode()).hexdigest()

    return redirect(PAYFAST_URL + '?' + urllib.parse.urlencode(data))

@app.route('/success')
def success():
    email = request.args.get('email', '')
    if email:
        try:
            msg = Message("Payment Confirmed", recipients=[email])
            msg.body = "Thank you! Your payment was successful."
            mail.send(msg)
            return render_template('success.html', email=email)
        except Exception as e:
            return f"Payment successful, but email failed: {str(e)}"
    return "Payment successful!"

@app.route('/cancel')
def cancel():
    return "Payment canceled."

@app.route('/notify', methods=['POST'])
def notify():
    data = request.form.to_dict()
    sig = data.pop('signature', '')

    signature = '&'.join(f"{k}={v}" for k, v in sorted(data.items()))
    local_sig = hashlib.md5(signature.encode()).hexdigest()

    if sig == local_sig:
        with sqlite3.connect(DB) as conn:
            conn.execute("UPDATE transactions SET status = ? WHERE item_name = ?",
                         (data.get('payment_status', 'unknown'), data.get('item_name')))
        return "OK", 200
    return "Invalid", 400

@app.route('/send-confirmation-email/<email>')
def send_email(email):
    msg = Message("Confirmation Email", recipients=[email])
    msg.body = "Thank you for registering! Your account has been successfully created."
    mail.send(msg)
    return "Confirmation email sent!"

def init_db():
    with sqlite3.connect(DB) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY,
        item_name TEXT,
        amount TEXT,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
