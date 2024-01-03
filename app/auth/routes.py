from flask import render_template, redirect, url_for, flash, request
from urllib.parse import urlsplit
from flask_login import login_user, logout_user, current_user
import sqlalchemy as sa
from datetime import datetime
from app import db
from app.auth import bp_auth
from app.auth.forms import LoginForm
from app.models import User


@bp_auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
   
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            error_message = "Incorrect username or password"
            return render_template('auth/login.html', form=form, error=error_message)

        login_user(user, remember=form.remember_me.data)
        user.last_logon = datetime.utcnow()
       
        # Commit the update to the database
        db.session.commit()

        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('main.index')
        return redirect(next_page)
    return render_template('auth/login.html', title=('Sign In'), form=form)


@bp_auth.route('/logout')
def logout():
    logout_user()
    return render_template('auth/logout_success.html')


