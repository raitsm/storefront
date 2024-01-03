from flask import jsonify, request, Response, current_app
import json
import jwt
from datetime import datetime, timedelta, timezone # UTC

from app.models import SalesItem, APIToken, UserRole, User, Purchases, SyncHistory, ConnectionType
from app import db
from . import bp_api
from app.decorators import token_required
from app import CustomJSONEncoder
from app.utilities.sync_utilities import set_single_value, delete_items, update_items, OperationResult

# constants for dictionary keys used in warehouse sync.
# the dictionary keys identify sub-datasets, each of which needs to be treated differently
DELETED_KEY = 'deleted'
NOT_FOR_SALE_KEY = 'not_for_sale'
OUT_OF_STOCK_KEY = 'out_of_stock'
STOCK_UPDATES_KEY = 'stock_updates'


@bp_api.route('/purchases/', methods=['GET'])
@token_required
def get_available_items():
    """
    API endpoint that returns data on all purchases made since the previous sync or since store reset.

    """
    current_app.extensions['csrf'].exempt(get_available_items)      # CSRF exemption
    current_app.logger.info("Purchase data requested.")

    connection_start_time = datetime.now(timezone.utc)

    purchases = Purchases.query.filter_by(requires_sync=True).all()
    purchase_data = [{
        'purchase_code': purchase.purchase_code,
        'code': purchase.salesitem_code,
        'name': purchase.salesitem_name,
        'vendor_name': purchase.salesitem_vendor_name,
        'quantity': purchase.quantity,
        'price_per_unit': purchase.salesitem_item_base_price,
        # 'sales_margin': purchase.salesitem_sales_margin,
        'total_price': purchase.total_price,
        'purchase_time': purchase.purchase_time
    } for purchase in purchases]
    
    response_json = json.dumps(purchase_data, cls=CustomJSONEncoder)
    connection_end_time = datetime.now(timezone.utc)
    
    set_single_value(model=Purchases, field_to_update='requires_sync', new_value=False)

    sync_record = SyncHistory(remote_name="Warehouse",
                              timestamp_start=connection_start_time,
                              timestamp_end=connection_end_time,
                              connection_type=ConnectionType.SYNC,
                              updates_received=0,
                              updates_sent=len(purchase_data))
    db.session.add(sync_record)
    db.session.commit()

    return Response(response_json, mimetype='application/json')


@bp_api.route('/items/delete_all', methods=['POST'])
@token_required
def clear_stock():
    """
    API endpoint to delete all items (SalesItem) and all purchases (Purchases) in the store.
    Intended to be used in combination with bulk upload.
    Protect & use with caution.
    """
    current_app.extensions['csrf'].exempt(clear_stock)      # CSRF exemption

    message = f"Incoming request to DELETE store contents: {request.remote_addr}, {request.user_agent}"
    current_app.logger.info(message)

    try:
        connection_start_time=datetime.now(timezone.utc)
        db.session.query(SalesItem).delete()
        db.session.query(Purchases).delete()
        db.session.commit()
        connection_end_time=datetime.now(timezone.utc)
        current_app.logger.info("Sales items and purchase history removed from the store.")
        sync_record = SyncHistory(remote_name="Warehouse",
                            timestamp_start=connection_start_time,
                            timestamp_end=connection_end_time,
                            connection_type=ConnectionType.RESET)
        db.session.add(sync_record)
        db.session.commit()
               
        return jsonify({"success": True, "message": "All stock items and purchases cleared"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error("Sales items and purchase history could not be deleted from the store.")
        return jsonify({"success": False, "message": str(e)}), 500
    

@bp_api.route('/bulk_update', methods=['POST'])
@token_required
def bulk_update():
    """
    API endpoint to process bulk updates from warehouse.
    The data is received as a single dictionary where the actual datasets are wrapped inside.
    The outer dictionary includes keys that shall determine the action to be taken with the dataset inside:
    'deleted' - identifies items removed from the warehouse and thus to be removed from the store
    'not_for_sale' - identifies items flagged as not for sale and thus to be removed from the store
    'out_of_stock' - identifies items flagged as out of stock and thus to be removed from the store
    'stock_updates' - data that shall be applied to stock items in the store
    
    """
    current_app.extensions['csrf'].exempt(bulk_update)

    connection_start_time=datetime.now(timezone.utc)
    current_app.logger.info(f"Incoming request to UPDATE store contents: {request.remote_addr}, {request.user_agent}")
               
    data_in = request.get_json()
  
    connection_end_time=datetime.now(timezone.utc)

    # keys for the various sub-datasets in the data_in. 
    # the keys define what to do with each sub-dataset.  

    bulk_update_results = { DELETED_KEY: OperationResult(),
                         NOT_FOR_SALE_KEY: OperationResult(),
                         OUT_OF_STOCK_KEY: OperationResult(),
                         STOCK_UPDATES_KEY: OperationResult()
                         }
        
    # NB, there is a difference as to any of sub-datasets is empty, or entirely missing from the incoming batch.
    # In both cases, there could be legit reasons, so they are not treated as errors.
    if DELETED_KEY in data_in:
        items_delete = data_in[DELETED_KEY]
        print(items_delete)
        if items_delete:
            deletion_result = delete_items(target_model=SalesItem, 
                         key_col_target='code',
                         incoming_data=items_delete,
                         key_col_incoming='code'
                         )
            bulk_update_results[DELETED_KEY] = deletion_result
        else:
            current_app.logger.info("Deleted items dataset empty in the incoming batch.")
            print(">>> no deleted items from the warehouse")
    else:
        current_app.logger.warning("Deleted items dataset missing.")
 
    if NOT_FOR_SALE_KEY in data_in:
        items_not_for_sale = data_in[NOT_FOR_SALE_KEY]
        print(items_not_for_sale)
        if items_not_for_sale:
            not_for_sale_result = delete_items(target_model=SalesItem, 
                         key_col_target='code',
                         incoming_data=items_not_for_sale,
                         key_col_incoming='code'
                         )
            bulk_update_results[NOT_FOR_SALE_KEY] = not_for_sale_result

        else:
            current_app.logger.info("Not-for-sale dataset empty in the incoming batch.")
            print(">>> no Not For Sale items from the warehouse")
    else:
        current_app.logger.warning("Not-For-Sale items dataset missing.")
        print("!!!! Not For Sale item data missing from the delivery")

    if OUT_OF_STOCK_KEY in data_in:
        out_of_stock_items = data_in[OUT_OF_STOCK_KEY]
        print(items_not_for_sale)
        if out_of_stock_items:
            out_of_stock_result = delete_items(target_model=SalesItem, 
                         key_col_target='code',
                         incoming_data=out_of_stock_items,
                         key_col_incoming='code'
                         )
            bulk_update_results[OUT_OF_STOCK_KEY] = out_of_stock_result
        else:
            current_app.logger.info("Out-of-stock dataset empty in the incoming batch.")
            print(">>> no Out-of-stock items from the warehouse")
    else:
        current_app.logger.warning("Out-of-stock items dataset missing.")
        print("!!!! Not For Sale item data missing from the delivery")

    if STOCK_UPDATES_KEY in data_in:
        stock_updates = data_in[STOCK_UPDATES_KEY]
        print(stock_updates)
        if stock_updates:
            field_mapping = {'code':'code',
                    'name': 'name',
                    'description': 'description',
                    'vendor.name': 'vendor_name',
                    'price_per_unit': 'price_per_unit',
                    'units_in_stock': 'units_in_stock',
            }
                    # 'sales_margin': 'sales_margin'}

            stock_update_result = update_items(target_model=SalesItem,
                         key_col_target='code',
                         incoming_data=stock_updates,
                         key_col_incoming='code',
                         field_mapping=field_mapping,
                         timestamp_col='last_updated'
                         )
            bulk_update_results[STOCK_UPDATES_KEY] = stock_update_result
        else:
            current_app.logger.info("Stock item update dataset empty in the incoming batch.")
            print(">>> no item updates from the warehouse")
    else:
        current_app.logger.warning("Stock item update dataset missing.")
        print("!!!! Item updates missing from the delivery")

    records_received = 0
    
    for key, result in bulk_update_results.items():
        if isinstance(result, OperationResult):
            if result.result_code == OperationResult.SUCCESS:
                records_received += result.updated_count + result.added_count

    for key, result in bulk_update_results.items():
        if isinstance(result, OperationResult):
            bulk_update_results[key] = result.to_dict()

    sync_record = SyncHistory(remote_name="Warehouse",
                              timestamp_start=connection_start_time,
                              timestamp_end=connection_end_time,
                              connection_type=ConnectionType.SYNC,
                              updates_received=records_received)
    db.session.add(sync_record)
    db.session.commit()


    return jsonify(bulk_update_results)

