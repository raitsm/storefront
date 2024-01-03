from app import create_app, db
from app.models import SalesItem
from werkzeug.security import generate_password_hash


def main():
    # Users to be added
    items_to_add = [
        {"code": "001-XXX", 
         "name": "Test Unit X",
         "picture": "N/A",
         "price_per_unit": 25, 
         "units_in_stock": 100, 
         "vendor_name": "Unknown",
        #  "sales_margin": 1.14,
         "units_purchased": 0},
        {"code": "001-000", 
         "name": "Various Machinery",
         "picture": "N/A",
         "price_per_unit": 2500, 
         "units_in_stock": 10, 
         "vendor_name": "Industrial Co.",
        #  "sales_margin": 0.98,
         "units_purchased": 0},
        {"code": "CCC-232", 
         "name": "Container M",
         "picture": "N/A",
         "price_per_unit": 3.25, 
         "units_in_stock": 1, 
         "vendor_name": "N/A",
        #  "sales_margin": 1.30,
         "units_purchased": 0},

        # Add more users as needed
    ]



    app = create_app()

    with app.app_context():
        # Check if users already exist
        for item_data in items_to_add:
            item = SalesItem.query.filter_by(code=item_data['code']).first()
            if not item:
                new_item = SalesItem(code=item_data['code'],
                                    name=item_data['name'],
                                    picture=item_data['picture'],
                                    price_per_unit=item_data['price_per_unit'],
                                    units_in_stock=item_data['units_in_stock'],
                                    vendor_name=item_data['vendor_name'],
                                    # sales_margin=item_data['sales_margin'],
                                    units_purchased=item_data['units_purchased']
                                    )
                db.session.add(new_item)

        db.session.commit()
        print('Items added successfully.')

if __name__ == "__main__":
    # with app.app_context():
        main()
