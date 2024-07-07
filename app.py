import os
import uuid
import logging
from flask import Flask, request, jsonify, redirect, url_for, render_template, flash, abort,session # type: ignore
from werkzeug.utils import secure_filename # type: ignore
from flask_login import LoginManager, login_user, logout_user, current_user, login_required # type: ignore
from werkzeug.security import generate_password_hash, check_password_hash # type: ignore
from functools import wraps
from models import db, User, Category, Product, Order, OrderItem, CartItem
from flask_wtf.csrf import CSRFProtect # type: ignore
from config import Config  
from forms import RegisterForm, LoginForm, CategoryForm,ProductForm,CartForm,CheckoutForm,CancelOrderForm
from googletrans import Translator


app = Flask(__name__, static_url_path='/static')
app.static_folder = 'static'
app.config.from_object(Config)
db.init_app(app)

translator = Translator()

csrf = CSRFProtect(app)
logging.basicConfig(level=logging.DEBUG)
@app.before_request
def create_admin():
   with app.app_context():
        hashed_password = generate_password_hash('admin1234')

        # Check if admin user already exists
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            new_user = User(username='admin', email='admin@gmail.com', password=hashed_password, role='admin')
            db.session.add(new_user)
            db.session.commit()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

UPLOAD_FOLDER = 'static/uploads/images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    selected_language = request.args.get('lang', 'en')
    categories = Category.query.all()
    products = Product.query.all()
    form = CartForm()

    for product in products:
        product.name = translate_product_name(product, selected_language)  # Implement your translation logic here

    return render_template('index.html', categories=categories, products=products, form=form)

def admin_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)  # Forbidden
        return func(*args, **kwargs)
    return decorated_view

@app.route('/admin/dashboard', methods=['GET'])
@admin_required
def admin_dashboard():
    categories = Category.query.all()
    products = Product.query.all()
    return render_template('admin_dashboard.html', categories=categories, products=products)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data

        hashed_password = generate_password_hash(password)
        try:
            new_user = User(username=username, email=email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('User registered successfully', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error: {e}', 'error')
            return render_template('register.html', form=form)

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash('Register to login', 'error')
            return redirect(url_for('register'))
        login_user(user)
        flash('Logged in successfully', 'success')
        return redirect(url_for('profile'))

    return render_template('login.html', form=form)

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', username=current_user.username, email=current_user.email, role=current_user.role)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully', 'success')
    return redirect(url_for('home'))

# Read categories
@app.route('/categories', methods=['GET'])
def get_categories():
    categories = Category.query.all()
    return render_template('categories.html', categories=categories)

@app.route('/admin/categories/new', methods=['GET', 'POST'])
@admin_required
def new_category():
    form = CategoryForm()

    if form.validate_on_submit():
        name = form.name.data
        file = form.file.data  # Uploaded file object
        

        if file and allowed_file(file.filename):
         filename =str(uuid.uuid4()) + '_' +  secure_filename(file.filename)
         file.save(os.path.join(app.config['UPLOADED_IMAGES_DEST'], filename))
        else:
         flash('Invalid file type', 'error')
         return redirect(url_for('new_category'))

        new_category = Category(name=name, image=filename)
        db.session.add(new_category)
        db.session.commit()
        flash('Category created successfully', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('new_category.html', form=form)

@app.route('/admin/categories/<int:category_id>/update', methods=['GET', 'POST'])
@admin_required
def update_category(category_id):
    category = Category.query.get_or_404(category_id)
    form = CategoryForm(obj=category)  # Populate form with existing category data

    if form.validate_on_submit():
        category.name = form.name.data  # Update category name
        form.populate_obj(category)  # Update category with form data
        
        if form.file.data:
            # Delete the old image file if it exists
            if category.image:
                old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], category.image)
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)

            # Save the new file
            filename = secure_filename(form.file.data.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            form.file.data.save(file_path)
            category.image = filename  # Save only the filename or relative path

        db.session.commit()
        flash('Category updated successfully', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('update_category.html', category=category, form=form)

@app.route('/admin/categories/<int:category_id>/delete', methods=['POST'])
@admin_required
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    products = Product.query.filter_by(category_id=category_id).all()
    for product in products:
        db.session.delete(product)
    db.session.delete(category)
    db.session.commit()
    flash('Category deleted successfully', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(request.url)
    
    if allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = str(uuid.uuid4()) + '_' + filename
        file.save(os.path.join(app.config['UPLOADED_IMAGES_DEST'], unique_filename))
        flash('File successfully uploaded', 'success')
        return jsonify({'message': 'File successfully uploaded', 'filename': unique_filename}), 201
    else:
        flash('Invalid file type', 'error')
        return redirect(request.url)
    
@app.route('/category/<int:category_id>')
def category(category_id):
    selected_language = session.get('lang', 'en')
    category = Category.query.get_or_404(category_id)
    products = Product.query.filter_by(category_id=category_id).all()
    for product in products:
        product.name = translate_product_name(product, selected_language)
    return render_template('category.html', category=category, products=products)

@app.route('/product/<int:product_id>')
def product(product_id):
    selected_language = session.get('lang', 'en')
    product = Product.query.get_or_404(product_id)
    product.name = translate_product_name(product, selected_language)
    form = CartForm()
    return render_template('product.html', product=product, form=form)
    
# Read products
@app.route('/category/<int:category_id>', methods=['GET'])
def get_products(category_id):
    category = Category.query.get_or_404(category_id)
    products = Product.query.filter_by(category_id=category_id).all()

    form=CartForm()
    return render_template('category.html', category=category,products=products,form=form)

# Read a specific product
@app.route('/product/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = Product.query.get_or_404(product_id)
    form=CartForm()
    return render_template('product.html', product=product,form=form)

@app.route('/admin/category/new', methods=['GET', 'POST'])
@admin_required
def new_product():
    form = ProductForm()

    if form.validate_on_submit():
        name = form.name.data
        description = form.description.data
        price = form.price.data
        category_id = form.category_id.data
        file = form.file.data

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = str(uuid.uuid4()) + '_' + filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
        else:
            flash('Invalid file type', 'error')
            return redirect(url_for('new_product'))

        new_product = Product(name=name, description=description, price=price,
                              category_id=category_id, image=unique_filename)
        db.session.add(new_product)
        db.session.commit()
        flash('Product created successfully', 'success')
        return redirect(url_for('admin_dashboard'))

    categories = Category.query.all()
    return render_template('new_product.html', form=form, categories=categories)

@app.route('/admin/category/<int:product_id>/update', methods=['GET', 'POST'])
@admin_required
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)

    if form.validate_on_submit():
        product.name = form.name.data
        product.description = form.description.data
        product.price = form.price.data
        product.category_id = form.category_id.data
        

        form.populate_obj(product)  # Update category with form data
        
        if form.file.data:
            # Delete the old image file if it exists
            if product.image:
                old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], product.image)
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)

            # Save the new file
            filename = secure_filename(form.file.data.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            form.file.data.save(file_path)
            product.image = filename  # Save only the filename or relative path

        db.session.commit()
        flash('Product updated successfully', 'success')
        return redirect(url_for('admin_dashboard'))

    categories = Category.query.all()
    return render_template('update_product.html', form=form, product=product, categories=categories)

@app.route('/admin/product/<int:product_id>/delete', methods=['POST'])
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    order_items = OrderItem.query.filter_by(product_id=product_id).all()
    for item in order_items:
        db.session.delete(item)
        
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/products_sold', methods=['GET'])
@admin_required
def products_sold():
    # Query all products with their total quantities sold
    products = db.session.query(Product, db.func.sum(OrderItem.quantity).label('total_quantity')) \
                        .join(OrderItem) \
                        .group_by(Product.id) \
                        .all()
    
    return render_template('products_sold.html', products=products)

@app.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    form = CartForm()
    if form.validate_on_submit():
        quantity = form.quantity.data
        # Update quantity logic goes here (update the cart item quantity for the product_id)
        cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
        if cart_item:
            cart_item.quantity += quantity
            logging.debug(f'Updated quantity for product_id={product_id}, user_id={current_user.id}, new_quantity={cart_item.quantity}')
        else:
            cart_item = CartItem(user_id=current_user.id, product_id=product_id, quantity=quantity)
            db.session.add(cart_item)
            logging.debug(f'Added new cart item for product_id={product_id}, user_id={current_user.id}, quantity={quantity}')
 
        db.session.commit()
        flash('Product added to cart', 'success')
    else:
        flash('Invalid quantity', 'error')

    return redirect(url_for('get_product', product_id=product_id))

@app.route('/cart/update/<int:product_id>', methods=['POST'])
@login_required
def update_cart(product_id):
    form = CartForm()
    if form.validate_on_submit():
        quantity = form.quantity.data
        cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()

        if cart_item:
            if quantity > 0:
                cart_item.quantity = quantity
            else:
                db.session.delete(cart_item)

            db.session.commit()
            flash('Cart updated successfully', 'success')
        else:
            flash('Item not found in cart', 'error')
    else:
        flash('Invalid quantity', 'error')
    return redirect(url_for('view_cart')) 

@app.route('/cart')
@login_required
def view_cart():
    form=CartForm()
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total_amount = sum(item.total_price for item in cart_items)
    logging.debug(f'User {current_user.id} cart items: {cart_items}')
    logging.debug(f'Total amount: {total_amount}')
    return render_template('cart.html', cart_items=cart_items, total_amount=total_amount,form=form)

@app.route('/orders', methods=['GET'])
@login_required
def view_orders():
    # Query orders associated with the current user
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.date.desc()).all()
    form = CancelOrderForm()
    # Render orders template with the retrieved orders
    return render_template('orders.html', orders=orders, form=form)

@app.route('/order/<int:order_id>/cancel', methods=['POST'])
@login_required
def cancel_order(order_id):
    form = CancelOrderForm()
    if form.validate_on_submit():
        order = Order.query.get_or_404(order_id)
        
        # Ensure the current user owns the order or is an admin
        if order.user_id != current_user.id and current_user.role != 'admin':
            flash('You are not authorized to cancel this order', 'danger')
            return redirect(url_for('view_orders'))
        
        # Update the order status to 'cancelled'
        order.status = 'cancelled'
        db.session.commit()
        flash('Order has been cancelled', 'success')
        return redirect(url_for('view_orders'))
    else:
        flash('Invalid request', 'danger')
        return redirect(url_for('view_orders'))
    
@app.route('/admin/orders', methods=['GET'])
@admin_required
def view_all_orders():
    orders = Order.query.order_by(Order.date.desc()).all()
    form = CancelOrderForm()
    return render_template('admin_orders.html', orders=orders, form=form)

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    form = CheckoutForm()
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total_amount =sum(item.product.price * item.quantity for item in cart_items)
    print("Cart Items:", cart_items)  # Debugging
    print("Total Amount:", total_amount)  # Debugging
    if form.validate_on_submit():
        shipping_address = form.shipping_address.data
        phone_number = form.phone_number.data
        payment_method = form.payment_method.data
        
        # Create the order
        order = Order(user_id=current_user.id, shipping_address=shipping_address, phone_number=phone_number, payment_method=payment_method, total_amount=total_amount)
        db.session.add(order)
        db.session.commit()
        
        # Add order items
        
        for item in cart_items:
            order_item = OrderItem(order_id=order.id, product_id=item.product.id, quantity=item.quantity, price=item.product.price)
            db.session.add(order_item)
            db.session.delete(item)  # Clear the item from the cart
        db.session.commit()

        flash('Order placed successfully!', 'success')
        return redirect(url_for('view_orders'))
    
    return render_template('checkout.html', form=form,cart_items=cart_items, total_amount=total_amount)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    selected_language = session.get('lang', 'en')  # Get the selected language from the session

    # Perform search logic here, e.g., querying your database
    results = Product.query.filter(Product.name.ilike(f'%{query}%')).all()
    for product in results:
        product.name = translate_product_name(product, selected_language)

    return render_template('search.html', results=results, query=query)

@app.before_request
def set_language():
    if 'lang' in request.args:
        session['lang'] = request.args.get('lang')
    elif 'lang' not in session:
        session['lang'] = 'en'

@app.context_processor
def inject_language():
    return dict(lang=session.get('lang', 'en'))

def translate_product_name(product, target_language):
    if target_language == 'te':  # Telugu translation
        translation = translator.translate(product.name, src='en', dest='te')
        return translation.text
    elif target_language == 'hi':  # Hindi translation
        translation = translator.translate(product.name, src='en', dest='hi')
        return translation.text
    else:
        return product.name  # Return original name if target language is not Telugu or Hindi

@app.route('/order/confirm/<int:order_id>', methods=['POST'])
@login_required
@admin_required  # Ensure only admins can confirm orders
def confirm_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.status == 'pending':
        order.status = 'confirmed'
        db.session.commit()
        flash('Order confirmed successfully', 'success')
    return redirect(url_for('view_all_orders'))

@app.route('/order/complete/<int:order_id>', methods=['POST'])
@login_required
@admin_required  # Ensure only admins can complete orders
def complete_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.status == 'confirmed':
        order.status = 'completed'
        db.session.commit()
        flash('Order marked as completed', 'success')
    return redirect(url_for('view_all_orders'))

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOADED_IMAGES_DEST']):
        os.makedirs(app.config['UPLOADED_IMAGES_DEST'])
    with app.app_context():
        db.create_all()
    app.run(debug=True)