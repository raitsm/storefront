# forms used to handle purchases

from flask_wtf import FlaskForm
from wtforms import SubmitField, IntegerField, StringField
from wtforms.validators import DataRequired, NumberRange

class SupportForm(FlaskForm):
    submit = SubmitField('OK')


class PurchaseForm(FlaskForm):
    """
    Purchase form.
    """
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)], default=1)
    submit = SubmitField('Purchase')

class PurchaseVerificationForm(FlaskForm):
    """
    Purchase verification form.
    """
    item_code = StringField('Item Code', render_kw={'readonly': True})
    item_name = StringField('Item Name', render_kw={'readonly': True})
    price_per_unit = StringField('Price per Unit', render_kw={'readonly': True})
    purchase_quantity = StringField('Purchase Quantity', render_kw={'readonly': True})
    total_price = StringField('Total Price', render_kw={'readonly': True})
    proceed = SubmitField('Proceed')
    cancel = SubmitField('Cancel')
    