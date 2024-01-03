from flask import Blueprint, redirect, url_for, render_template, request, current_app
from flask_login import current_user, login_required
from .forms import SyncForm, TokenForm, AddTokenForm, EditTokenForm
from datetime import datetime, timedelta, timezone, time #, UTC
from sqlalchemy.exc import SQLAlchemyError
from app import db
from app.decorators import role_required
from app.models import UserRole, APIToken, APIRole, SyncHistory
from app.sync import bp_sync
from app.utilities.token_utilities import generate_token, get_claim_from_token


# browse session history
@bp_sync.route('/sync_history')
@role_required(UserRole.ADMIN, UserRole.SALES_MANAGER)
def browse_session_history():
    """
    Browse session log.

    """
    items_per_page = current_app.config['ITEMS_PER_PAGE']
    page = request.args.get('page', 1, type=int)
    sync_history_pagination = SyncHistory.query.paginate(page=page, per_page=items_per_page, error_out=False)
    sync_history_items = sync_history_pagination.items
    
    return render_template("sync/sync_history.html", sync_history=sync_history_items, pagination=sync_history_pagination)


@bp_sync.route('/add_token', methods=['GET', 'POST'])
@role_required(UserRole.ADMIN)
def add_token_view():
    """
    Add a remote connection.
    """
    
    token_added = False
    validation_errors = []
    form = AddTokenForm()
    if form.validate_on_submit():
        try:
            expiration_date = datetime.combine(form.expires_at.data, time(0, 0, 0), tzinfo=timezone.utc)
            # expiration_date = datetime.combine(form.expires_at.data, time(0, 0, 0))
            my_token = generate_token(expiration_date=expiration_date, 
                                       connection_name=form.connection_name.data)
            if my_token:
                new_token = APIToken(
                    connection_name=form.connection_name.data,
                    token = my_token,
                    expires_at = form.expires_at.data,
                    revoked = form.revoked.data,
                )
                new_token.issued_at = get_claim_from_token(token=new_token.token, claim='iac')  # capture and store 'issued at' claim
                db.session.add(new_token)
                db.session.commit()
                token_added=True
            else:
                message = "Unknown error when creating token."
                validation_errors.append(message)
                print(message)
                # return redirect(url_for('sync.view_edit_tokens_view'))
                        
        except SQLAlchemyError as e:
            message = f"Error adding token: {e}"
            print(message)
            current_app.logger.error(message)
            validation_errors.append(message) 
    else:
        for field_name, error_messages in form.errors.items():
            for err in error_messages:
                message = f"Error in {field_name}: {err}"
                print(f"Error in {field_name}: {err}")
                validation_errors.append(message)
        

    return render_template('sync/add_token.html', form=form, action="Add", submit_button_text="Add", token_added=token_added, validation_errors=validation_errors)



@bp_sync.route('/browse_tokens')
@role_required(UserRole.ADMIN, UserRole.SALES_MANAGER)
def view_edit_tokens_view():
    """
    View, Edit and Delete remote connections (same as token management).
    """
    items_per_page = current_app.config['ITEMS_PER_PAGE']
    page = request.args.get('page', 1, type=int)
    # items = Item.query.paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)
    token_pagination = APIToken.query.paginate(page=page, per_page=items_per_page, error_out=False)
    token_items = token_pagination.items
    
    return render_template("sync/view_tokens.html", tokens=token_items, pagination=token_pagination)

@bp_sync.route('/token_status_togle/<int:token_id>')
@role_required(UserRole.ADMIN)
def toggle_token_status_view(token_id):
    """
    Flip token status from Active to Revoked and back.
    """
    status_changed = False
    token = APIToken.query.get_or_404(token_id)
    new_token_status = token.toggle_token_status()
    try:
        db.session.commit()
        status_changed = True
    except SQLAlchemyError as e:
        db.session.rollback()
        print("Error: could not toggle token status")
        status_changed = False

    return redirect(url_for('sync.view_edit_tokens_view'))


@bp_sync.route('/delete_token/<int:token_id>', methods=['POST'])
@role_required(UserRole.ADMIN)
def delete_token_view(token_id):
    """
    Delete a token.
    """
    token_deleted = False
    token = APIToken.query.get_or_404(token_id)
    
    try:
        db.session.delete(token)
        db.session.commit()
        token_deleted = True
    except:
        db.session.rollback()
        token_deleted = False
    finally:
        db.session.close()

    return redirect(url_for('sync.view_edit_tokens_view'))
    
    
        