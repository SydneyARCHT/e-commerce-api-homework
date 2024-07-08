
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from sqlalchemy import select, delete
from flask_marshmallow import Marshmallow
from flask_cors import CORS
import datetime
from typing import List
from marshmallow import ValidationError, fields, validate

app = Flask(__name__) # instantiate our app 
CORS(app) 
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+mysqlconnector://root:SydneyARCHTsql1!@localhost/e_comm_api_db"

class Base(DeclarativeBase): 
    pass

db = SQLAlchemy(app, model_class=Base) 
ma = Marshmallow(app) 


class Customer(Base): 
    __tablename__ = "Customers" 
    customer_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(255), nullable=False)
    email: Mapped[str] = mapped_column(db.String(320), nullable=False)
    phone: Mapped[str] = mapped_column(db.String(15))
    customer_account: Mapped["CustomerAccount"] = db.relationship(back_populates="customer")
    orders: Mapped[List["Order"]] = db.relationship(back_populates="customer")


class CustomerAccount(Base):
    __tablename__ = "Customer_Accounts"
    account_id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(db.String(255), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(db.String(255), nullable = False)
    customer_id: Mapped[int] = mapped_column(db.ForeignKey('Customers.customer_id'))
    customer: Mapped["Customer"] = db.relationship(back_populates="customer_account")

order_product = db.Table( 
    "Order_Product", 
    Base.metadata, 
    db.Column("order_id", db.ForeignKey("Orders.order_id"), primary_key=True), 
    db.Column("product_id", db.ForeignKey("Products.product_id"), primary_key=True)  
)

class Order(Base):
    __tablename__ = "Orders"
    order_id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[datetime.date] = mapped_column(db.Date, nullable = False)
    customer_id: Mapped[int] = mapped_column(db.ForeignKey("Customers.customer_id"))
    customer: Mapped["Customer"] = db.relationship(back_populates="orders") 
    products: Mapped[List["Product"]] = db.relationship(secondary=order_product) 

class Product(Base):
    __tablename__ = "Products"
    product_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(255), nullable=False)
    price: Mapped[float] = mapped_column(db.Float, nullable=False)


with app.app_context(): 
    db.create_all()

# Customer Schema
class CustomerSchema(ma.Schema):
    customer_id = fields.Integer()
    name = fields.String(required=True)
    email = fields.String(required=True)
    phone = fields.String(required=True)

    class Meta:
        fields = ("customer_id", "email", "name", "phone")


customer_schema = CustomerSchema()
customers_schema = CustomerSchema(many=True)


# Get a Customer
@app.route("/customers", methods = ["GET"])
def get_customers():
    query = select(Customer) 
    # SELECT * FROM Customers
    result = db.session.execute(query).scalars() 
    customers = result.all() 
    return customers_schema.jsonify(customers)

# Adding a Customer
@app.route("/customers", methods = ["POST"])
def add_customer():
    try:
        customer_data = customer_schema.load(request.json) 
    except ValidationError as err:
        return jsonify(err.messages), 400 
    with Session(db.engine) as session:  
        with session.begin(): 
            name = customer_data['name'] 
            email = customer_data['email'] 
            phone = customer_data['phone'] 
            new_customer = Customer(name=name, email=email, phone=phone) 
            session.add(new_customer) 
            session.commit()
    return jsonify({"message": "New Customer successfully added."}), 201 

# Updating a Customer
@app.route("/customers/<int:id>", methods=["PUT"])
def update_customer(id):
    with Session(db.engine) as session:
        with session.begin():
            query = select(Customer).filter(Customer.customer_id == id) 
            result = session.execute(query).scalars().first() 
            if result is None:  
                return jsonify({"message": "Customer not found"}), 404     
            customer = result 
            try: 
                customer_data = customer_schema.load(request.json) 
            except ValidationError as e: 
                return jsonify(e.messages), 400 
            for field, value in customer_data.items():
                setattr(customer, field, value) 
            session.commit() 
    return jsonify({"message": "Customer details updated successfully"}), 200 


@app.route("/customers/<int:id>", methods=["DELETE"])
def delete_customer(id):
    with Session(db.engine) as session:
        with session.begin():
            query = select(Customer).filter(Customer.customer_id == id)
            result = session.execute(query).scalars().first()
            if result is None:
                return jsonify({"error": "Customer not found..."}), 404 
            session.delete(result)
        return jsonify({"message": "Customer removed successfully!"})


# For Accounts
class AccountSchema(ma.Schema):
    account_id = fields.Integer()
    username = fields.String(required=True)
    password = fields.String(required=True)
    customer_id = fields.Integer(required=True)
    class Meta:
        fields = ("account_id", "username", "password", "customer_id")
accounts_schema = AccountSchema(many=True)


# # Get all customer accounts
@app.route("/customeraccounts", methods=["GET"])
def get_customer_account():
    query = select(CustomerAccount)
    result = db.session.execute(query).scalars() 
    customers = result.all() 
    return accounts_schema.jsonify(customers)


@app.route("/customeraccount", methods=["POST"])

def add_customer_account():
    try:
        customer_account_data = accounts_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    with Session(db.engine) as session:
        with session.begin():
            username = customer_account_data['username']
            password = customer_account_data['password']
            customer_id = customer_account_data['customer_id']
            new_account = CustomerAccount(username=username, password=password, customer_id=customer_id)
            session.add(new_account)
            session.commit()
        return jsonify({"message": "New Customer successfully added!"}), 201 
    

@app.route("/customeraccount/<int:account_id>", methods=["PUT"])
def update_customer_account(account_id):
    with Session(db.engine) as session:
        with session.begin():
            query = select(CustomerAccount).filter_by(account_id=account_id)
            result = session.execute(query).scalars().first()           
            if result is None:
                return jsonify({"message": "Customer not found"}), 404            
            customer = result
            try: 
                customer_account_data = accounts_schema.load(request.json)
            except ValidationError as e:
                return jsonify(e.messages), 400           
            for field, value in customer_account_data.items():
                setattr(customer, field, value)
            session.commit() 
    return jsonify({"message": "Customer details updated successfully."}), 200      


@app.route("/customeraccount/<int:account_id>", methods=["DELETE"])
def delete_customer_account(account_id):
    with Session(db.engine) as session:
        with session.begin():
            query = select(CustomerAccount).filter(CustomerAccount.account_id == account_id)
            result = session.execute(query).scalars().first()         
            if result is None:
                return jsonify({"message": "Customer not found"}), 404    
            session.delete(result)
            return jsonify({"message": "Customer has been deleted."}), 200 


# For Products
class ProductSchema(ma.Schema):
    product_id = fields.Integer(required=False)
    name = fields.String(required=True, validate=validate.Length(min=1)) 
    price = fields.Float(required=True, validate=validate.Range(min=0)) 
    class Meta:
        fields = ("product_id", "name", "price") 

# Instance of Schema
product_schema = ProductSchema()
products_schema = ProductSchema(many=True)


# Getting Products
@app.route("/products", methods=["GET"])
def get_products():
    query = select(Product) #SELECT * FROM product
    result = db.session.execute(query).scalars()
    products = result.all()
    return products_schema.jsonify(products) 


# Creating a Product
@app.route("/products", methods=["POST"])
def add_product():
    try:   
        product_data = product_schema.load(request.json)
    except ValidationError as err:   
        return jsonify(err.messages) , 400 
    with Session(db.engine) as session:
        with session.begin():
            new_product = Product(name=product_data['name'],price= product_data['price'])
            session.add(new_product)
            session.commit()
    return jsonify({"Message": "new product added successfully"}) , 201 


# Updating a Product by ID
@app.route("/products/<int:product_id>", methods =["PUT"])
def update_product(product_id):
    with Session(db.engine) as session:
        with session.begin():
            query = select(Product).filter(Product.product_id == product_id)
            result = session.execute(query).scalar() 
            print(result)
            if result is None:
                return jsonify({"error": "Product not found"}), 404 
            product = result
            try:
                product_data = product_schema.load(request.json)
            except ValidationError as err:
                return jsonify(err.messages), 400 
            for field, value in product_data.items():
                setattr(product,field, value)
            session.commit()
            return jsonify({"Message":f"Product with id of {product_id} updated successfully"}), 200 


# Deleting a Product
@app.delete("/products/<int:product_id>")
def delete_product(product_id):
    delete_statment = delete(Product).where(Product.product_id == product_id)
    with db.session.begin():
        result = db.session.execute(delete_statment)
        if result.rowcount == 0:
            return jsonify({"error":f"Product with id of {product_id} doesn't exist!"}), 404
        return jsonify({"message":"Product has been deleted successfully"}), 200


# For Orders
class OrderSchema(ma.Schema):
    order_id = fields.Integer(required= False)
    customer_id = fields.Integer(required = True)
    date = fields.Date(required=True) #"2024-07-05"
    product_id = fields.List(fields.Integer(), required= False)
    class Meta:
        fields = ("order_id","customer_id","date","product_id")
# Instance of Schemas
order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)


# Getting All Orders
@app.get("/orders") 
def get_orders():
    query = select(Order) 
    result = db.session.execute(query).scalars().all()
    orders_with_products = []
    orders = result
    for order in orders:
        order_dict = {
            "order_id": order.order_id,
            "customer_id": order.customer_id,
            "date": order.date,
            "products": [product.product_id for product in order.products]
        }
        orders_with_products.append(order_dict)
    return jsonify(orders_with_products)


# Creating an Order
@app.post("/orders")
def add_order():
    try:
        order_data = order_schema.load(request.json)
    except ValidationError as err:    
        return jsonify(err.messages), 400
    product_ids = order_data.get('product_id', [])
    new_order = Order(
        customer_id=order_data['customer_id'],
        date=order_data['date']
    )
    with Session(db.engine) as session:
        with session.begin():
            for product_id in product_ids:
                product = session.query(Product).get(product_id)
                if product:
                    new_order.products.append(product)
            session.add(new_order)
            session.commit()
    return jsonify({"message": "Order added successfully"}), 201


# Update Orders by ID
@app.put("/orders/<int:order_id>")
def update_orders(order_id):
    with Session(db.engine) as session:
        with session.begin():
            query = select(Order).filter(Order.order_id == order_id)
            result = session.execute(query).scalar() 
            if result is None:
                return jsonify({"message":"Order not found!"})
            order = result
            try:
                order_data = order_schema.load(request.json)
            except ValidationError as err:
                return jsonify(err.messages), 400
            order.customer_id = order_data.get('customer_id', order.customer_id)
            order.date = order_data.get('date', order.date)
            product_ids = order_data.get('product_id', [])
            order.products.clear() 
            for product_id in product_ids:
                product = session.query(Product).get(product_id)
                if product:
                    order.products.append(product)
            session.commit()
            return jsonify({"message":f"Order: {order_id} has been updated."}), 200
    
# Deleting Orders
@app.delete("/orders/<int:order_id>")
def delete_order(order_id):
    delete_statement = delete(Order).where(Order.order_id == order_id)
    with db.session.begin():
        result = db.session.execute(delete_statement)
        if result.rowcount == 0:
            return jsonify({"Error":f"Order with ID: {order_id} doesnt exist."})
        return jsonify({"message":"Order has been deleted successfully"})


@app.route("/") 
def home(): 
    return "Welcome to my first Testing API, fingers crossed. " 

if __name__ == "__main__": 
    app.run(debug=True, port=5000)