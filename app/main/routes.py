from flask import Blueprint, redirect, url_for, render_template, request, flash
from flask import current_app
from flask_login import current_user, login_required
from datetime import datetime, timezone # UTC
from app import db
from .forms import SupportForm, PurchaseForm, PurchaseVerificationForm
from app.models import SalesItem, Purchases, UserRole
from app.decorators import role_required
from app.main import bp_main

@bp_main.route('/')
def index():
    """
    Main view, showing list of items available for sale. Login is not required.
    """
    items_per_page = current_app.config['ITEMS_PER_PAGE']
    page = request.args.get('page', 1, type=int)

    sales_items_pagination = SalesItem.query.paginate(page=page, per_page=items_per_page, error_out=False)
    sales_items = sales_items_pagination.items
    return render_template("main/items_list.html", items=sales_items, pagination=sales_items_pagination)

@bp_main.route('/view_item/<int:item_id>')
@login_required
def view_item(item_id):
    """
    Show item details. Authenticated users only.
    """
    # Fetch item details based on item_id
    item = SalesItem.query.get_or_404(item_id)
    return render_template('main/view_item_details.html', item=item)

# see item details and decide whether to buy or to return to store catalog
@bp_main.route('/item/<int:item_id>')
@login_required
def item_details(item_id):
    
    item = SalesItem.query.get_or_404(item_id)
    form = PurchaseForm()

    # Limit the max quantity to purchase
    max_units = min(item.units_in_stock, current_app.config['MAX_UNITS_PER_PURCHASE'])
    form.quantity.validators[1].max = max_units

    return render_template('main/item_details_purchase.html', item=item, form=form)

# purchase form, specify the amount of units
@bp_main.route('/purchase/<int:item_id>', methods=['GET', 'POST'])
@login_required
def purchase_item(item_id):
    """
    View item details for non-customers
    Purchase item for customers
    """

    if not current_user.is_customer():
        return redirect(url_for('main.index'))

    item = SalesItem.query.get_or_404(item_id)
    form = PurchaseForm()

    if form.validate_on_submit():
        quantity_to_purchase = form.quantity.data

        if quantity_to_purchase > item.units_in_stock:
            flash('Insufficient stock available.', 'danger')
            return redirect(url_for('main.purchase_item', form=form, item_id=item_id))

        return redirect(url_for('main.purchase_verification', item_id=item_id, quantity=quantity_to_purchase))

    return render_template('main/item_details_purchase.html', form=form, item=item)


@bp_main.route('/purchase_verification/<int:item_id>', methods=['GET'])
@login_required
def purchase_verification(item_id):
    item = SalesItem.query.get_or_404(item_id)
    
    quantity = request.args.get('quantity', type=int)

    verification_form = PurchaseVerificationForm()
    verification_form.item_code.data = item.code
    verification_form.item_name.data = item.name
    verification_form.price_per_unit.data = item.price_per_unit
    verification_form.purchase_quantity.data = quantity
    verification_form.total_price.data = item.price_per_unit *quantity      # * item.sales_margin 

    total_price = item.price_per_unit * quantity                            # * item.sales_margin 
    
    return render_template('main/purchase_verification.html', 
                           item=item, 
                           quantity=quantity, 
                           total_price=total_price)


# def purchase_verification(item_id):
#     item = SalesItem.query.get_or_404(item_id)
#     quantity = request.args.get('quantity', type=int)

#     verification_form = PurchaseVerificationForm()
#     verification_form.item_code.data = item.code
#     verification_form.item_name.data = item.name
#     verification_form.price_per_unit.data = item.price_per_unit
#     verification_form.purchase_quantity.data = quantity
#     verification_form.total_price.data = item.price_per_unit * quantity

#     return render_template('main/purchase_verification.html', form=verification_form, item_id=item_id, quantity=quantity)


# finalize purchase purchase details

@bp_main.route('/finalize_purchase/<int:item_id>', methods=['POST'])
@login_required
@role_required(UserRole.CUSTOMER)
def finalize_purchase(item_id):
    if not current_user.is_customer():
        return redirect(url_for('main.index'))

    item = SalesItem.query.get_or_404(item_id)
    
    quantity_str = request.form.get('quantity')
    if quantity_str is None:
        flash('No quantity provided.', 'danger')
        return redirect(url_for('main.item_details', item_id=item_id))

    quantity_to_purchase = int(quantity_str)

    item.units_in_stock -= quantity_to_purchase
    item.units_purchased += quantity_to_purchase
    item_purchase_price = item.price_per_unit       #
    purchase_total_price = item_purchase_price * quantity_to_purchase

    purchase = Purchases(salesitem_id=item.id,
                         purchase_code=datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")+"_"+item.code, 
                         salesitem_code=item.code,
                         salesitem_name=item.name,
                         salesitem_vendor_name=item.vendor_name,
                         user_id=current_user.id,
                         quantity=quantity_to_purchase,
                         salesitem_item_base_price=item.price_per_unit,
                        #  salesitem_sales_margin=item.sales_margin,
                         salesitem_purchase_price=item_purchase_price,
                         total_price=purchase_total_price)

    db.session.add(purchase)
    db.session.commit()

    flash('Purchase successful!', 'success')
    return redirect(url_for('main.index'))


@bp_main.route('/support', methods=['GET', 'POST'])
def support():
    form = SupportForm()
    if form.validate_on_submit():
        # Redirect to previous page or a default page
        return redirect(request.args.get('next') or url_for('main.index'))
    return render_template("main/support.html", form=form)


# browse data on all purchases in the store, available only to sales mgrs and auditors.
@bp_main.route('/purchase_view')
@login_required
@role_required(UserRole.SALES_MANAGER, UserRole.READ_ONLY)
def purchase_view():
    items_per_page = current_app.config['ITEMS_PER_PAGE']
    page = request.args.get('page', 1, type=int)

    purchases_pagination = Purchases.query.paginate(page=page, per_page=items_per_page, error_out=False)
    purchases_items = purchases_pagination.items
    return render_template("main/purchases_list.html", purchases=purchases_items, pagination=purchases_pagination)


@bp_main.route('/dashboard')
@login_required
def dashboard():
    return render_template("main/dashboard.html")
