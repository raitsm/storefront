# utility functions used by data sync
# data preparation, filtering, upload, download

from flask import current_app
from datetime import datetime, timezone # UTC
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import update, inspect
# import requests
from app.models import SalesItem, Purchases
from app import db
from flask import current_app

class OperationResult:
    """
    Class to store the update/deletion statistics and error codes
    """
    # operation status definitions
    SUCCESS = 0
    FAILURE = 1
    NOT_PERFORMED = 2
    
    def __init__(self):
        self.http_response = 500  # HTTP response code
        self.result_code = OperationResult.NOT_PERFORMED       # 0 - success, 1 - unsuccessful, 2 - not performed
        self.result_message = "Operation not performed"
        self.deleted_count = 0
        self.updated_count = 0
        self.added_count = 0
        self.erroneous_count = 0
        self.not_found_count = 0

    def update(self, result_code, result_message="", http_response=500, **kwargs):

        self.result_code = result_code
        self.result_message = result_message or self.result_message
        self.http_response = http_response

        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_dict(self):
        return vars(self)

    # load values from a dictionary    
    def load_from_dict(self, data_dict):
        for key, value in data_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)
                
    # methods to check various states of the operation.
    def operation_success(self):
        return self.result_code == OperationResult.SUCCESS

    def operation_failure(self):
        return self.result_code == OperationResult.FAILURE
    
    def operation_not_performed(self):
        return self.result_code == OperationResult.NOT_PERFORMED


def delete_items(target_model, key_col_target, incoming_data, key_col_incoming):
    """
    Args:
        target_model: Model where to remove items from
        key_col_target: The field name in the model used to identify items for deletion.
        incoming_data: List of dictionaries, each containing the search key and value. 
                       The value will be used to identify the records to be removed from the target
        key_col_incoming: The field name in the incoming data used to identify items for deletion. 

    Returns:
        OperationResult object including result status, result message, http response, as well as counts of
        deleted items, not found items, and of erroneous items.
        
        An erroneous item is one that does not include field label specified in key_col_incoming
        
    Usage: result = delete_items(SalesItems, 'code', data, 'code')        
    """

    num_deleted_items = 0
    num_not_found_items = 0
    num_error_items = 0
    
    operation_result = OperationResult()
    
    if key_col_target not in inspect(target_model).attrs:
        # raise ValueError(f"'{search_key_col}' is not a valid column in {target_model.__name__}")
        error_message =f"'{key_col_target}' is not a valid column in {target_model.__name__}"
        current_app.logger.error(error_message)
        operation_result.update(result_code=OperationResult.FAILURE,
                                result_message=error_message,
                                http_response=500,
                                deleted_count=num_deleted_items,
                                not_found_count=num_not_found_items,
                                erroneous_count=num_error_items
                                )
        return operation_result

    # Dynamically get the column to be used for filtering
    search_col = getattr(target_model, key_col_target)
    
    for item_data in incoming_data:
        # check if the items in incoming data lack the required field (key_col_incoming).
        # if there is no such field, log an error, increase erroneous item count, and continue.
        # No need to terminate, there may be good items in the incoming data.
        if key_col_incoming not in item_data:
            current_app.logger.error(f"'{key_col_incoming}' is not found in {item_data}")
            num_error_items += 1
            # num_error_items.append(item_data)
            continue
        search_value = item_data[key_col_incoming]
        item = target_model.query.filter(search_col == search_value).first()

        if item:
            try:
                db.session.delete(item)
                num_deleted_items += 1
            except SQLAlchemyError as e:
                db.session.rollback()
                error_message = f"!!! Error {e} while deleting item {search_value}"
                current_app.logger.error(error_message)
                operation_result.update(result_code=OperationResult.FAILURE,
                                        result_message=error_message,
                                        http_response=500,
                                        deleted_count=0,                    # since no items were deleted due to roll-back
                                        not_found_count=num_not_found_items,
                                        erroneous_count=num_error_items
                                        )
                return operation_result
        else:
            num_not_found_items += 1

    db.session.commit()

    operation_result.update(result_code=OperationResult.SUCCESS,
                            result_message="Operation successful.",
                            http_response=200,
                            deleted_count=num_deleted_items,
                            not_found_count=num_not_found_items,
                            erroneous_count=num_error_items
                            )
    current_app.logger.info(f"Deletion complete: {operation_result.deleted_count} items deleted from {target_model.__name__}, {operation_result.not_found_count} items not located, {operation_result.erroneous_count} erroneous items in the input.")
    return operation_result


def update_items(target_model, key_col_target, incoming_data, key_col_incoming, field_mapping,timestamp_col=None):
    """
    Updates or adds items to an SQLAlchemy model based on incoming data.
    Args:
        target_model: SQLAlchemy model class to update or add items to.
        key_col_target: The field name in the model used to identify items for update.
        incoming_data: List of dictionaries, each dictionary represents a record. 
        key_col_incoming: The field in the incoming data with a unique item identifier.
                            If the identifier is found in key_col_target of target model, the item shall be updated,
                            otherwise it shall be added to the model.
        field_mapping: Dictionary mapping fields in the incoming data to the target model's fields.
        timestamp_col: The field name (optional) in the model where timestamp of the update/creation shall be recorded.
                        Default is None, meaning no timestamp will be added by default.

    Returns:
        OperationResult object including result status, result message, http response, as well as counts of
        added items, updated items, and of erroneous items.
                
        An erroneous item is one that does not include field label specified in key_col_incoming
        
    Usage example: update_items(SalesItems, 'code', data, 'code', salesitem_field_map)        
    """

    # items_for_removal = []
    operation_result = OperationResult()
    number_updated = 0
    number_added = 0
    number_error_items = 0
    
    model_columns = inspect(target_model).attrs
    
    # Check if Validate all expected model field names in field_mapping are actually present in target_model
    
    if not all(field in model_columns for field in field_mapping.values()):
        
        error_message = f"Field mapping values do not match fields in {target_model.__name__}."
        current_app.logger.error(error_message)
        
        operation_result.update(result_code=OperationResult.FAILURE,
                            result_message=error_message,
                            http_response=500,
                            updated_count=number_updated,
                            added_count=number_added,
                            erroneous_count=number_error_items
                            )
        
        return operation_result

    if key_col_target not in inspect(target_model).attrs:
        error_message = f"'{key_col_target}' is not a valid column in {target_model.__name__}"
        current_app.logger.error(error_message)
        operation_result.update(result_code=OperationResult.FAILURE,
                            result_message=error_message,
                            http_response=500,
                            updated_count=number_updated,
                            added_count=number_added,
                            erroneous_count=number_error_items
                            )
        
        return operation_result

    try:
        for item_data in incoming_data:
            # Ensure all field_mapping keys are in the item_data
            if not all(key in item_data for key in field_mapping.keys()):
                current_app.logger.error(f"Missing field(s) in item data: {item_data}")
                number_error_items += 1
                continue

            # Lookup or initialize the item
            search_value = item_data[key_col_incoming]
            item = target_model.query.filter_by(**{key_col_target: search_value}).first()
            if item:
                operation = 'update'
            else:
                item = target_model()
                operation = 'add'

            # Apply field mapping and update/create item
            for incoming_field, model_field in field_mapping.items():
                setattr(item, model_field, item_data[incoming_field])

            # Set timestamp if applicable
            if timestamp_col and timestamp_col in model_columns:
                setattr(item, timestamp_col, datetime.now(timezone.utc))

            db.session.add(item)

            if operation == 'update':
                number_updated += 1
            else:
                number_added += 1

        # Commit all changes after processing all items
        db.session.commit()
        
    except SQLAlchemyError as e:
        db.session.rollback()
        error_message = f"Error processing batch update/add: {e}"
        current_app.logger.error(error_message)
        operation_result.update(result_code=OperationResult.FAILURE,
                            result_message=error_message,
                            http_response=500,
                            updated_count=0,        # 0 due to rollback
                            added_count=0,          # 0 due to rollback
                            erroneous_count=number_error_items
                            )
        return operation_result


    # return successful result
    operation_result.update(result_code=OperationResult.SUCCESS,
                            result_message="Operation successful.",
                            http_response=200,
                            updated_count=number_updated,
                            added_count=number_added,
                            erroneous_count=number_error_items
                            )
    current_app.logger.info(f"Update complete: {operation_result.updated_count} items updated, {operation_result.added_count} items added in {target_model.__name__}, there were {operation_result.erroneous_count} erroneous items in the input.")

    return operation_result


# def add_item(target_model, data_item, field_mapping):
#     pass

def set_single_value(model, field_to_update, new_value, **conditions):
    """
    Safely updates a single field in a given model based on provided conditions.

    Args:
        model (db.Model): The model to update.
        field_to_update (str): The name of the field to be updated.
        new_value: The new value to set for the field.
        **conditions: Field-value pairs as conditions to filter records.

    Returns:
        str: A message indicating the outcome of the operation.
    """

    # Check if the field to update exists in the model
    if not hasattr(model, field_to_update):
        return f"Error: Field '{field_to_update}' not found in model."

    # Build initial query
    query = update(model)

    # Add conditions to the query
    for field, value in conditions.items():
        if not hasattr(model, field):
            return f"Error: Condition field '{field}' not found in model."
        query = query.where(getattr(model, field) == value)

    try:
        # Apply the update
        query = query.values({field_to_update: new_value})

        # Execute the query
        result = db.session.execute(query)
        db.session.commit()

        # Return the number of rows matched
        return f"Updated {result.rowcount} records."
    except SQLAlchemyError as e:
        # Rollback in case of error
        db.session.rollback()
        return f"Error: {e}"
