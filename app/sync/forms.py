from flask import current_app
from flask_wtf import FlaskForm
from wtforms import SubmitField, HiddenField, DateField, StringField, BooleanField, ValidationError
from wtforms.validators import DataRequired, Length, InputRequired
from datetime import datetime, timedelta, timezone # UTC


def validate_date_range(form, field):
    """
    Date range validator.
    Checks if the value in the field occurs in the past or more than MAX_VALIDITY_PERIOD in the future
    """
    max_validity_days = current_app.config.get("TOKEN_MAX_VALIDITY_DAYS", 183)       # get the max validity days for tokens, 6 months by default

    today = datetime.now(timezone.utc).date()
    too_late = today + timedelta(days=max_validity_days) 
    if field.data < today:
        raise ValidationError("The date cannot be in the past.")
    elif field.data > too_late:
        raise ValidationError("The date cannot be more than six months in the future.")


class SyncForm(FlaskForm):
    submit = SubmitField('Sync Data')

class TokenForm(FlaskForm):
    id = HiddenField('Connection ID')
    connection_name = StringField('Connection Name', validators=[DataRequired(), Length(min=8, max=50)])
    expires_at = DateField('Expiration Date', validators=[DataRequired(),validate_date_range])
    revoked = BooleanField('Revoked', default=False)
 
class AddTokenForm(TokenForm):
    pass

class EditTokenForm(TokenForm):
    pass
