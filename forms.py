# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField,FileField, SubmitField, TextAreaField, DecimalField,IntegerField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, NumberRange,Length, Regexp
from flask_wtf.file import FileAllowed

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class CategoryForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    file = FileField('Image', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])  # FileField for uploading image files
    submit = SubmitField('Update_Category')

# forms.py
class ProductForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    price = DecimalField('Price', validators=[DataRequired()])
    category_id = IntegerField('Category ID', validators=[DataRequired()])
    file = FileField('Image')
    submit = SubmitField('Create')

class CartForm(FlaskForm):
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Add to cart')

class CheckoutForm(FlaskForm):
    shipping_address = StringField('Shipping Address', validators=[DataRequired(), Length(min=5, max=100)])
    phone_number = StringField('Phone Number', validators=[DataRequired(), Regexp(r'^\d{10}$', message="Enter a valid 10-digit phone number.")])
    payment_method = SelectField('Payment Method', choices=[('cash_on_delivery', 'Cash On Delivery')], validators=[DataRequired()])
    submit = SubmitField('Place Order')

class CancelOrderForm(FlaskForm):
    submit = SubmitField('Cancel')
