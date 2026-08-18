import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = os.urandom(24)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'budget.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Main Budget Category (e.g., Goa Trip)
class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, index=True)
    title = db.Column(db.String(100), nullable=False)
    total_limit = db.Column(db.Float, nullable=False)
    expenses = db.relationship('Expense', backref='budget', cascade="all, delete-orphan", lazy=True)

# Sub-Expenses inside a Budget (e.g., Hotel, Fuel, Food)
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    budget_id = db.Column(db.Integer, db.ForeignKey('budget.id'), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)

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
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    username = session['username']
    user_budgets = Budget.query.filter_by(username=username).order_by(Budget.id.desc()).all()
    
    # Calculate totals
    overall_limit = sum(b.total_limit for b in user_budgets)
    overall_spent = sum(sum(e.amount for e in b.expenses) for b in user_budgets)
    overall_remaining = overall_limit - overall_spent
    
    return render_template('dashboard.html', 
                           username=username, 
                           budgets=user_budgets, 
                           overall_limit=overall_limit,
                           overall_spent=overall_spent,
                           overall_remaining=overall_remaining)

@app.route('/add-budget', methods=['POST'])
def add_budget():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    title = request.form.get('title', '').strip()
    limit_raw = request.form.get('total_limit', '').strip()
    
    if title and limit_raw:
        try:
            limit = float(limit_raw)
            if limit > 0:
                new_budget = Budget(username=session['username'], title=title, total_limit=limit)
                db.session.add(new_budget)
                db.session.commit()
        except ValueError:
            pass
            
    return redirect(url_for('dashboard'))

@app.route('/add-expense/<int:budget_id>', methods=['POST'])
def add_expense(budget_id):
    if 'username' not in session:
        return redirect(url_for('login'))
        
    budget = Budget.query.filter_by(id=budget_id, username=session['username']).first()
    if budget:
        item_name = request.form.get('item_name', '').strip()
        amount_raw = request.form.get('amount', '').strip()
        if item_name and amount_raw:
            try:
                amount = float(amount_raw)
                if amount > 0:
                    new_exp = Expense(budget_id=budget.id, item_name=item_name, amount=amount)
                    db.session.add(new_exp)
                    db.session.commit()
            except ValueError:
                pass
                
    return redirect(url_for('dashboard'))

@app.route('/get-budget-detail/<int:budget_id>')
def get_budget_detail(budget_id):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    budget = Budget.query.filter_by(id=budget_id, username=session['username']).first()
    if budget:
        spent = sum(e.amount for e in budget.expenses)
        remaining = budget.total_limit - spent
        expense_list = [{'id': e.id, 'item_name': e.item_name, 'amount': e.amount} for e in budget.expenses]
        
        return jsonify({
            'id': budget.id,
            'title': budget.title,
            'total_limit': budget.total_limit,
            'spent': spent,
            'remaining': remaining,
            'expenses': expense_list
        })
    return jsonify({'error': 'Not found'}), 404

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
