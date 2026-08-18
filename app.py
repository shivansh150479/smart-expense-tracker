import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
# Secure secret key required to sign session cookies
app.secret_key = os.urandom(24)

# SQLite Database setup
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'budget.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Model for User Budgets
class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, index=True)
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), default='General')

# Automatically build database tables on startup safely inside application context
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form.get('username', '').strip()
        if name:
            session['username'] = name.title()
            session['show_welcome'] = True
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    username = session['username']
    
    # Strictly query ONLY budgets belonging to the logged-in user name
    user_budgets = Budget.query.filter_by(username=username).order_by(Budget.id.desc()).all()
    total_amount = sum(b.amount for b in user_budgets) if user_budgets else 0.0
    
    show_welcome = session.pop('show_welcome', False)
    
    return render_template('dashboard.html', 
                           username=username, 
                           budgets=user_budgets, 
                           total_amount=total_amount,
                           show_welcome=show_welcome)

@app.route('/add-budget', methods=['POST'])
def add_budget():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    title = request.form.get('title', '').strip()
    amount_raw = request.form.get('amount', '').strip()
    category = request.form.get('category', 'General').strip()
    
    # Defensive try-except block prevents invalid data from throwing 500 errors
    if title and amount_raw:
        try:
            amount = float(amount_raw)
            if amount > 0:
                new_budget = Budget(
                    username=session['username'],
                    title=title,
                    amount=amount,
                    category=category if category else 'General'
                )
                db.session.add(new_budget)
                db.session.commit()
        except ValueError:
            pass
            
    return redirect(url_for('dashboard'))

@app.route('/get-budget-detail/<int:budget_id>')
def get_budget_detail(budget_id):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    # Isolation Guard: Verify budget belongs to session user before returning details
    budget = Budget.query.filter_by(id=budget_id, username=session['username']).first()
    if budget:
        return jsonify({
            'id': budget.id,
            'title': budget.title,
            'amount': budget.amount,
            'category': budget.category
        })
    return jsonify({'error': 'Budget not found'}), 404

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
