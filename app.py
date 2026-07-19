from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'uzerp-secret-key-2024'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///uzerp.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==================== МОДЕЛИ ====================
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    customer_name = db.Column(db.String(100), default='Клиент')
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')
    total_price = db.Column(db.Float)
    
    product = db.relationship('Product', backref='orders')
    
    def calculate_total(self):
        if self.product:
            self.total_price = self.product.price * self.quantity
        return self.total_price

# ==================== СОЗДАНИЕ БАЗЫ ====================
with app.app_context():
    db.create_all()
    if Product.query.count() == 0:
        products = [
            Product(name='Ноутбук', description='Игровой ноутбук', price=1500.00, stock=10),
            Product(name='Мышь', description='Беспроводная мышь', price=25.50, stock=50),
            Product(name='Клавиатура', description='Механическая', price=80.00, stock=30),
            Product(name='Монитор', description='27 дюймов 4K', price=400.00, stock=15),
            Product(name='Наушники', description='Беспроводные', price=120.00, stock=25),
        ]
        db.session.add_all(products)
        db.session.commit()

# ==================== МАРШРУТЫ ====================
@app.route('/')
def index():
    products = Product.query.all()
    orders = Order.query.order_by(Order.order_date.desc()).limit(10).all()
    stats = {
        'total_products': Product.query.count(),
        'total_orders': Order.query.count(),
        'low_stock': Product.query.filter(Product.stock < 5).count(),
        'pending_orders': Order.query.filter_by(status='pending').count()
    }
    return render_template('index.html', products=products, orders=orders, stats=stats)

@app.route('/products')
def products():
    all_products = Product.query.order_by(Product.id).all()
    return render_template('products.html', products=all_products)

@app.route('/add_product', methods=['POST'])
def add_product():
    try:
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = float(request.form.get('price', 0))
        stock = int(request.form.get('stock', 0))
        
        if not name or price <= 0:
            flash('Название и цена обязательны!', 'error')
            return redirect(url_for('products'))
        
        product = Product(name=name, description=description, price=price, stock=stock)
        db.session.add(product)
        db.session.commit()
        flash(f'Товар "{name}" добавлен!', 'success')
    except Exception as e:
        flash(f'Ошибка: {str(e)}', 'error')
    return redirect(url_for('products'))

@app.route('/edit_product/<int:id>', methods=['POST'])
def edit_product(id):
    try:
        product = Product.query.get_or_404(id)
        product.name = request.form.get('name', '').strip()
        product.description = request.form.get('description', '').strip()
        product.price = float(request.form.get('price', 0))
        product.stock = int(request.form.get('stock', 0))
        db.session.commit()
        flash('Товар обновлён!', 'success')
    except Exception as e:
        flash(f'Ошибка: {str(e)}', 'error')
    return redirect(url_for('products'))

@app.route('/delete_product/<int:id>')
def delete_product(id):
    try:
        product = Product.query.get_or_404(id)
        db.session.delete(product)
        db.session.commit()
        flash('Товар удалён!', 'success')
    except Exception as e:
        flash(f'Ошибка: {str(e)}', 'error')
    return redirect(url_for('products'))

@app.route('/orders')
def orders():
    all_orders = Order.query.order_by(Order.order_date.desc()).all()
    products = Product.query.filter(Product.stock > 0).all()
    return render_template('orders.html', orders=all_orders, products=products)

@app.route('/create_order', methods=['POST'])
def create_order():
    try:
        product_id = int(request.form.get('product_id'))
        quantity = int(request.form.get('quantity', 1))
        customer_name = request.form.get('customer_name', 'Клиент').strip()
        
        product = Product.query.get(product_id)
        if not product:
            flash('Товар не найден!', 'error')
            return redirect(url_for('orders'))
        
        if product.stock < quantity:
            flash(f'Недостаточно товара! Остаток: {product.stock}', 'error')
            return redirect(url_for('orders'))
        
        order = Order(product_id=product_id, quantity=quantity, customer_name=customer_name)
        order.calculate_total()
        
        product.stock -= quantity
        
        db.session.add(order)
        db.session.commit()
        flash(f'Заказ #{order.id} создан на сумму {order.total_price} руб.!', 'success')
    except Exception as e:
        flash(f'Ошибка: {str(e)}', 'error')
    return redirect(url_for('orders'))

@app.route('/update_order/<int:id>', methods=['POST'])
def update_order(id):
    try:
        order = Order.query.get_or_404(id)
        new_status = request.form.get('status')
        if new_status in ['pending', 'processing', 'shipped', 'delivered', 'cancelled']:
            order.status = new_status
            db.session.commit()
            flash(f'Статус заказа #{id} обновлён!', 'success')
        else:
            flash('Неверный статус!', 'error')
    except Exception as e:
        flash(f'Ошибка: {str(e)}', 'error')
    return redirect(url_for('orders'))

@app.route('/delete_order/<int:id>')
def delete_order(id):
    try:
        order = Order.query.get_or_404(id)
        product = order.product
        if product:
            product.stock += order.quantity
        db.session.delete(order)
        db.session.commit()
        flash(f'Заказ #{id} удалён!', 'success')
    except Exception as e:
        flash(f'Ошибка: {str(e)}', 'error')
    return redirect(url_for('orders'))

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    products = []
    orders = []
    if query:
        products = Product.query.filter(
            Product.name.contains(query) | Product.description.contains(query)
        ).all()
        orders = Order.query.join(Product).filter(
            Product.name.contains(query) | Order.customer_name.contains(query)
        ).all()
    return render_template('search.html', query=query, products=products, orders=orders)

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 UzERP СИСТЕМА ЗАПУЩЕНА")
    print("📂 База данных:", os.path.abspath('uzerp.db'))
    print("🌐 Откройте: http://127.0.0.1:5000")
    print("="*50 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
