from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session

import datetime
import re

from models import db, User, Product, Category, Cart, Orders

from app import app

def auth_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if 'user_id' not in session:
            flash('You need to login first.')
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return inner

def admin_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if 'user_id' not in session:
            flash('You need to login first.')
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user.if_admin:
            flash('You are not authorized to view this page because you are not admin.')
            return redirect(url_for('index'))  
        return func(*args, **kwargs)
    return inner

@app.route('/')
@auth_required
def index():
    user = User.query.get(session['user_id'])
    if user.if_admin:
        return redirect(url_for('admin'))
    else:
        return render_template('index.html', user=user, categories=Category.query.all())

@app.route('/admin')
@admin_required
def admin():
    user = User.query.get(session['user_id'])
    if not user.if_admin:
        flash('You are not authorized to view this page.')
        return redirect(url_for('index'))
    return render_template('admin.html', user=user, categories=Category.query.all())

@app.route('/profile')
@auth_required
def profile():
    return render_template('profile.html', user=User.query.get(session['user_id']))

@app.route('/profile', methods=['POST'])
@auth_required
def profile_post():
    user = User.query.get(session['user_id'])
    username = request.form.get('username')
    name = request.form.get('name')
    password = request.form.get('password')
    cpassword = request.form.get('cpassword')
    if username == '' or password == '' or cpassword == '':
        flash("Username or password cannot be empty")
        return redirect(url_for('profile'))
    if not user.check_password(cpassword):
        flash("Incorrect current password")
        return redirect(url_for('profile'))
    if User.query.filter_by(username=username).first() and username != user.username:
        flash('User with this username already exists. Please choose some other username.')
        return redirect(url_for('profile'))
    user.username = username
    user.password = password
    user.name = name
    db.session.commit()
    flash('Profile updated successfully')
    return redirect(url_for('profile'))

@app.route('/login')
def login():
    return render_template('logon.html')

@app.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    if username=='' and password=='':
        flash('Please enter your username and password.')
        return redirect(url_for('login'))
    user = User.query.filter_by(username=username).first()
    if not user:
        flash('User does not exist.')
        return redirect(url_for('login'))
    if not user.check_password(password):
        flash('Password is incorrect')
        return redirect(url_for('login'))
    #login successful
    session['user_id'] = user.id
    return redirect(url_for('index'))


@app.route('/register')
def register():
    return render_template('logon.html')

@app.route('/register', methods=['POST'])
def register_post():
    username = request.form.get('username')
    password = request.form.get('password')
    name = request.form.get('name')
    if username == '' or password == '':
        flash('username or password is required')
        return redirect(url_for('register'))
    if password is None:
        flash('password cannot be empty')
        return redirect(url_for('register'))
    if User.query.filter_by(username=username).first():
        flash('user already registered')
        return redirect(url_for('register'))
    user = User(username=username,password=password, name=name)
    if password is None:
        flash('password cannot be empty')
        return redirect(url_for('register'))
    

    db.session.add(user)
    db.session.commit()
    flash('user registration successful')
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))


@app.route('/category/add')
@admin_required
def add_category():
    return render_template('category/add.html', user=User.query.get(session['user_id']))

@app.route('/category/add',methods=['POST'])
@admin_required
def add_category_post():
    name = request.form.get('name')
    if name is None or name == '':
        flash("category name cannot be empty")
        return redirect(url_for('add_category'))
    if len(name) > 64:
        flash('category name cannot be more than 64 characters')
        return redirect(url_for('add_category'))
    category = Category(name=name)
    db.session.add(category)
    db.session.commit()
    flash("Added category")
    return redirect(url_for('admin')) 


@app.route('/category/<int:id>/show')
@admin_required
def show_category(id):
    return render_template('category/show.html', user=User.query.get(session['user_id']), category=Category.query.get(id))

@app.route('/product/add')
@admin_required
def add_product():
    category_id = -1
    args = request.args
    if 'category_id' in args:        
        if Category.query.get(int(args.get('category_id'))):
            category_id = int(args.get('category_id'))

    return render_template('product/add.html',
                            user=User.query.get(session['user_id']),
                            category_id=category_id,
                            categories=Category.query.all(),
                            nowstring = datetime.datetime.now().strftime('%Y-%m-%d')
                            )

@app.route('/product/add' , methods=['POST'])
@admin_required
def add_product_post():
    name = request.form.get('name')
    quantity = request.form.get('quantity')
    price = request.form.get('price')
    category = request.form.get('category')
    man_date = request.form.get('manufacture_date')
    if name == '':
        flash('Product name cannot be empty')
        return redirect(url_for('add_product'))
    if len(name) > 64:
        flash('Product name too long')
        return redirect(url_for('add_product'))
    if quantity=='':
        flash('Quantity cannot be empty')
        return redirect(url_for('add_product'))
    if quantity.isdigit() == False: 
        flash('Quantity must be a Number.')
        return redirect(url_for('add_product'))
    quantity = int(quantity)

    if price == '':
        flash('Price cannot be Empty.')
        return redirect(url_for('add_product'))
    if not re.match(r'^\d+(\.\d+)?$', price):
        flash('Price must be a Number')
        return redirect(url_for('add_product'))
    price = float(price)

    if category == '':
        flash("Category cannot be Empty")
        return redirect(url_for('add_product'))
    category = Category.query.get(category)
    if not category:
        flash('Category does not exist')
        return redirect(url_for('add_product'))
    if man_date == '':
        flash('Manufacture date cannot be empty')
        return redirect(url_for('add_product'))
    try:
        man_date = datetime.datetime.strptime(man_date, '%Y-%m-%d')
    except ValueError:
        flash('Invalid date')
        return redirect(url_for('add_product'))

    product = Product(name=name, quantity=quantity,price=price,category=category, man_date=man_date)
    db.session.add(product)
    db.session.commit()
    flash('Product added successfully')
    return redirect(url_for('show_category', id=category.id))  
    
@app.route('/product/<int:id>/edit')
@admin_required
def edit_product(id):
    product = Product.query.get(id)
    return render_template('product/edit.html', user=User.query.get(session['user_id']),
                            product=product,
                            categories=Category.query.all(),
                            nowstring=datetime.datetime.now().strftime('%Y-%m-%d'),
                            manufacture_date= product.man_date.strftime('%Y-%m-%d')
                            )

@app.route('/product/<int:id>/edit', methods=['POST'])
@admin_required
def edit_product_post(id):
    name = request.form.get('name')
    quantity = request.form.get('quantity')
    price = request.form.get('price')
    category = request.form.get('category')
    man_date = request.form.get('manufacture_date')
    if name == '':
        flash('Product name cannot be empty')
        return redirect(url_for('add_product'))
    if len(name) > 64:
        flash('Product name too long')
        return redirect(url_for('add_product'))
    if quantity=='':
        flash('Quantity cannot be empty')
        return redirect(url_for('add_product'))
    if quantity.isdigit() == False: 
        flash('Quantity must be a Number.')
        return redirect(url_for('add_product'))
    quantity = int(quantity)

    if price == '':
        flash('Price cannot be Empty.')
        return redirect(url_for('add_product'))
    if not re.match(r'^\d+(\.\d+)?$', price):
        flash('Price must be a Number')
        return redirect(url_for('add_product'))
    price = float(price)

    if category == '':
        flash("Category cannot be Empty")
        return redirect(url_for('add_product'))
    category = Category.query.get(category)
    if not category:
        flash('Category does not exist')
        return redirect(url_for('add_product'))
    if man_date == '':
        flash('Manufacture date cannot be empty')
        return redirect(url_for('add_product'))
    try:
        man_date = datetime.datetime.strptime(man_date, '%Y-%m-%d')
    except ValueError:
        flash('Invalid date')
        return redirect(url_for('add_product'))

    product = Product.query.get(id)
    product.name = name
    product.quantity = quantity
    product.price = price
    product.category = category
    product.man_date = man_date
    db.session.commit()
    flash('Product Edited successfully')
    return redirect(url_for('show_category', id=category.id))

@app.route('/product/<int:id>/delete')
@admin_required
def delete_product(id):
    product = Product.query.get(id)
    if not product:
        flash('Product does not exist')
        return redirect(url_for('admin'))
    return render_template('product/delete.html', user=User.query.get(session['user_id']), product=product)

@app.route('/product/<int:id>/delete', methods=['POST'])
@admin_required
def delete_product_post(id):
    product = Product.query.get(id)
    if not product:
        flash('Product does not exist')
        return redirect(url_for('admin'))
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully')
    return redirect(url_for('admin'))

@app.route('/category/<int:id>/edit')
@admin_required
def edit_category(id):
    return render_template('category/edit.html', user = User.query.get(session['user_id']), category = Category.query.get(id))

@app.route('/category/<int:id>/edit', methods = ['POST'])
@admin_required
def edit_category_post(id):
    category = Category.query.get(id)
    name = request.form.get('name')
    if name is None or name == "":
        flash('Category name is required')
        return redirect(url_for('edit_category', id=id))
    if len(name)>64:
        flash('Category name is too long')
        return redirect(url_for('edit_category', id=id))
    category.name = name
    db.session.commit()
    flash('Category Updated Successfully.')
    return redirect(url_for('admin'))

@app.route('/category/<int:id>/delete')
@admin_required
def delete_category(id):
    category = Category.query.get(id)
    if not category:
        flash('Category does not exist')
        return redirect(url_for('admin'))
    return render_template('category/delete.html', user=User.query.get(session['user_id']), category=category)

@app.route('/category/<int:id>/delete', methods=['POST'])
@admin_required
def delete_category_post(id):
    category = Category.query.get(id)
    if not category:
        flash('Category does not exist')
        return redirect(url_for('admin'))
    db.session.delete(category)
    db.session.commit()
    flash('Category successfully deleted.')
    return redirect(url_for('admin'))



#---- user carting and orders ----#


@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
@auth_required
def add_to_cart(product_id):
    quantity = request.form.get('quantity')
    return "add to cart for product id: " + str(product_id) + "quantity: " + str(quantity) 


@app.route('/cart')
@auth_required
def cart():
    return ""

@app.route('/orders')
@auth_required
def orders():
    return ""
