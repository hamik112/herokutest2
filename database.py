from flask_sqlalchemy import SQLAlchemy, Model
from flask import Flask

#from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

#from flask.ext.login import UserMixin
from multiprocessing.util import register_after_fork
from werkzeug.security import generate_password_hash, \
     check_password_hash
from datetime import datetime
app = Flask(__name__)
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///home/dn/Desktop/abay/tmp/test.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://root:De1414919@10.128.0.2/abay'
app.config['SQLALCHEMY_POOL_SIZE'] = 10
app.config['SQLALCHEMY_POOL_RECYCLE'] = 3600
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# engine = create_engine(
#      app.config['SQLALCHEMY_DATABASE_URI'])
db_session = scoped_session(sessionmaker(
    autocommit=False, autoflush=False, bind=db.engine))
# db.session.connection(execution_options={'isolation_level': 'READ COMMITTED'})
# db_session.connection(execution_options={'isolation_level': 'READ COMMITTED'})
#register_after_fork(db.engine, db.engine.dispose)

# connection = db.engine.connect()
# transaction = connection.begin()
# options = dict(bind=connection, binds={})
# db_session = db.create_scoped_session(options=options)

# class UnLockedAlchemy(SQLAlchemy):
#     def apply_driver_hacks(self, app, info, options):
#         if not "isolation_level" in options:
#             options["isolation_level"] = "READ UNCOMMITTED"  # For example
#         return super(UnLockedAlchemy, self).apply_driver_hacks(app, info, options)

# from sqlalchemy.types import TypeDecorator
# from sqlalchemy import DateTime as SdateTime
# import pytz
# tz = pytz.timezone('US/Pacific')
# class sDateTime(TypeDecorator):
#     impl = SdateTime
#     def process_bind_param(self, value, engine):
#         return value
#     def process_result_value(self, value, engine):
#         if value:
#             return value.replace(tzinfo=pytz.utc).astimezone(tz)
#         else:
#             return value

# Model of users
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer,primary_key=True,autoincrement=True)
    username = db.Column(db.String(20), nullable=False,unique=True)
    pw_hash = db.Column(db.String(200))
    email = db.Column(db.String(40),unique=True)
    authenticated = db.Column(db.Boolean,default=False)
    urole = db.Column(db.String(16)) #change to lower
    active = db.Column(db.Boolean,default=True)

    ##Shipping Email
    # notiemail = db.Column(db.String(40), unique=True)
    # notipass = db.Column(db.String(40))

    ##Setting
    # token = db.Column(db.Text)
    # tokenExpiration = db.Column(db.DateTime)

    ActiveItems = db.relationship("ActiveItem", backref='user',lazy='dynamic', cascade="all, delete-orphan")
    OrderItems = db.relationship("OrderItem", backref='user',lazy='dynamic', cascade="all, delete-orphan")
    SoldReceipts = db.relationship("SoldReceipt", backref='user',lazy='dynamic', cascade="all, delete-orphan")
    ScrapedItem = db.relationship("ScrapedItem", backref='user',lazy='dynamic', cascade="all, delete-orphan")

    DescriptionTemplate = db.relationship("DescriptionTemplate", backref='user',lazy='dynamic', cascade="all, delete-orphan")

    #dtemplate = db.relationship("DescriptionTemplate", uselist=False, back_populates="user")

    eBayAccounts = db.relationship("eBayAccount", backref='user',lazy='dynamic', cascade="all, delete-orphan")
    NotifyEmails = db.relationship("NotifyEmail", backref='user',lazy='dynamic', cascade="all, delete-orphan")
    AzonAccounts = db.relationship("AzonAccount", backref='user',lazy='dynamic', cascade="all, delete-orphan")
    Notifications = db.relationship("Notification", backref='user',lazy='dynamic', cascade="all, delete-orphan")

    # Settings
    PricerDefault = db.Column(db.Text)
    #Settings = db.relationship("Settings", uselist=False, back_populates="user")



    # created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    # updated_on = db.Column(db.DateTime(), default=datetime.utcnow,
    #                                       onupdate=datetime.utcnow)

    def __init__(self,username,pwd_hash,email,urole):
            self.username = username
            self.pw_hash = self.set_password(pwd_hash)
            self.email = email
            #self.authenticated = is_active
            self.urole = urole

    def get_id(self):
            return self.id
    def is_authenticated(self):
        """Return True if the user is authenticated."""
        return self.authenticated
    def is_active(self):
            return True
    def get_username(self):
            return self.username
    def get_urole(self):
            return self.urole
    def set_password(self,password):
        return generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.pw_hash, password)
    def is_anonymous(self):
        """False, as anonymous users aren't supported."""
        return False

# todo settings
# class Settings(db.Model):
#     __tablename__ = 'settings'
#     id = db.Column(db.Integer,primary_key=True,autoincrement=True)
#     PricerDefault = db.Column(db.Text)
#
#     user = db.relationship("User", back_populates="settings")
#

# Model for notification email
class NotifyEmail(db.Model):
    __tablename__ = 'notifyemail'
    id = db.Column(db.Integer,primary_key=True,autoincrement=True)
    uid = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    usern = db.Column(db.Text, nullable=False, unique=True)
    pw = db.Column(db.Text)

# Model for eBay accounts
class eBayAccount(db.Model):
    __tablename__ = 'ebayaccount'
    id = db.Column(db.Integer,primary_key=True,autoincrement=True)
    uid = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    usern = db.Column(db.Text, nullable=False, unique=True)

    # notiemail = db.Column(db.Text, nullable=False, unique=True)
    # notiepw = db.Column(db.Text)

    token = db.Column(db.Text, unique=True)
    tokenExpiration = db.Column(db.DateTime)

# Model for Amazon accounts
class AzonAccount(db.Model):
    __tablename__ = 'azonaccount'
    id = db.Column(db.Integer,primary_key=True,autoincrement=True)
    uid = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    usern = db.Column(db.Text, nullable=False, unique=True)
    pw = db.Column(db.Text)

    cc = db.relationship("CC", uselist=False, back_populates="azonaccount", cascade="all, delete-orphan")


# todo model for credit cards used to order on Amazon
class CC(db.Model):
    __tablename__ = 'cc'
    id = db.Column(db.Integer,primary_key=True,autoincrement=True)
    azonid = db.Column(db.Integer, db.ForeignKey('azonaccount.id'), nullable=False)

    cc = db.Column(db.Text, unique=True)
    cctype = db.Column(db.Text)
    mm = db.Column(db.Integer)
    yy = db.Column(db.Integer)

    AddressName = db.Column(db.Text)
    AddressStreet1 = db.Column(db.Text)
    AddressCity = db.Column(db.Text)
    AddressState = db.Column(db.Text)
    AddressCountry = db.Column(db.Text)
    AddressPhone = db.Column(db.Text)
    AddressZip = db.Column(db.Integer)

    azonaccount = db.relationship("AzonAccount", back_populates="cc")


# def SoldAmount(context):
#     if 'Quantity' in context.current_parameters:
#         return int(context.current_parameters['Quantity']) - int(context.current_parameters['QuantityAvailable'])
#     else:
#         return 0

# Current listed items on eBay
class ActiveItem(db.Model):

    __tablename__ = 'active_item'

    Title = db.Column(db.String(100))
    BuyItNowPrice = db.Column(db.Numeric(10,2))
    ItemID = db.Column(db.BIGINT, primary_key=True)
    Quantity = db.Column(db.Integer)
    QuantityAvailable = db.Column(db.Integer)
    #QuantitySold = db.Column(db.Integer)
    WatchCount = db.Column(db.Integer)
    TimeLeft = db.Column(db.DateTime)
    PictureDetailsURL = db.Column(db.Text)
    Asin = db.Column(db.String(15), default=None)

    AzonPrice = db.Column(db.Numeric(10,2))
    TargetProfit = db.Column(db.Numeric(10,2))
    PriceUpdated = db.Column(db.Boolean, default=True)
    CustomTargetPrice = db.Column(db.Boolean, default=False)
    CurrentOfferID = db.Column(db.String(200))

    PricerType = db.Column(db.String(15))
    PricerError = db.Column(db.Text)
    Notes = db.Column(db.Text)
    eBayAccount = db.Column(db.Text)

    Description = db.Column(db.Text)
    uid = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    #TheLineItems = db.relationship("LineItem", backref='active_item',lazy='dynamic')
    listing_stat = db.relationship("ListingStat", uselist=False, back_populates="active_item", cascade="all, delete-orphan")
    #Order = db.relationship("OrderItem", backref='active_item',lazy='dynamic')

    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow,
                                          onupdate=datetime.utcnow)

    SoldAmount = db.Column(db.Integer)

# Stats used for purging of old or unsold items
class ListingStat(db.Model):
    __tablename__ = 'listing_stat'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ItemID = db.Column(db.BIGINT, db.ForeignKey('active_item.ItemID'),nullable=False)
    LastPurgeDate = db.Column(db.DateTime)
    LastPurgeQuantity = db.Column(db.Integer) #item.SoldAmount
    LastPurgeQuantityAvailable = db.Column(db.Integer) # No use
    LastPurgeWatchCount = db.Column(db.Integer)

    PurgeZeroNextDate = db.Column(db.DateTime)

    active_item = db.relationship("ActiveItem", back_populates="listing_stat")
    uid = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    # updated_on = db.Column(db.DateTime(), default=datetime.utcnow,
    #                                       onupdate=datetime.utcnow)

# Model for orders/paid items
class OrderItem(db.Model):
    __tablename__ = 'order_item'
    CombinedOrder = db.Column(db.Boolean)
    Title = db.Column(db.String(300))
    OrderID = db.Column(db.String(40), primary_key=True)
    SellerPaidStatus = db.Column(db.String(35))
    CreatedTime = db.Column(db.DateTime)

    BuyerUserID = db.Column(db.String(40))
    TotalPrice = db.Column(db.Numeric(10,2))

    IsMultiLegShipping = db.Column(db.Boolean)

    ShippingService = db.Column(db.String(15))
    ShippingServiceCost = db.Column(db.Numeric(10,2))

    ##Get rid of this for LineItem Table
    ##ItemID = db.Column(db.Integer, db.ForeignKey('active_item.ItemID'))

    Asin = db.Column(db.String(12))

    Quantity = db.Column(db.Integer)

    PrivateNotes = db.Column(db.String(70))
    #TransactionID = db.Column(db.String(25))
    ShippedTime = db.Column(db.DateTime)
    #QuantityLeft = db.Column(db.Integer)
    #QuantitySold = db.Column(db.Integer)
    BuyerCheckoutMessage = db.Column(db.Text)
    Notes = db.Column(db.Text)

    #ShippingType = db.Column(db.String(20))
    # ShippingAddressName = db.Column(db.String(80))
    # ShippingAddressStreet1 = db.Column(db.String(80))
    # ShippingAddressStreet2 = db.Column(db.String(60))
    # ShippingAddressCity = db.Column(db.String(40))
    # ShippingAddressState = db.Column(db.String(20))
    # ShippingAddressCountry = (db.String(60))
    # ShippingAddressPhone = (db.String(20))
    # ShippingAddressZip = db.Column(db.Integer)

    #ActiveItemID =
    sold_receipt = db.relationship("SoldReceipt", uselist=False, back_populates="order_item", cascade="all, delete-orphan")
    line_item = db.relationship("LineItem", backref='sold_receipt',lazy='dynamic', cascade="all, delete-orphan")
    eBayAccount = db.Column(db.Text)
    AzonAccount = db.Column(db.Text)
    #return_refund = db.relationship("ReturnRefund", backref='order_item',lazy='dynamic')

    uid = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow,
                                          onupdate=datetime.utcnow)

# def updateReceipt(context):
#     from tasks import ReceiptOnUpdate
#     ReceiptOnUpdate.delay(context.current_parameters['OrderID'])
#     return datetime.utcnow

class SoldReceipt(db.Model):
    __tablename__ = 'sold_receipt'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    CombinedOrder = db.Column(db.Boolean)
    OrderID = db.Column(db.String(60), db.ForeignKey('order_item.OrderID'), unique=True)
    TotalPaid = db.Column(db.Numeric(10,2))
    TotalProfit = db.Column(db.Numeric(10,2))
    TotalPurchasePrice = db.Column(db.Numeric(10,2))
    SoldTime = db.Column(db.DateTime) #change to updated

    ItemCount = db.Column(db.Integer)

    FinalValueFee = db.Column(db.Numeric(10,2))
    PaypalFee = db.Column(db.Numeric(10,2))
    TotalTaxFee = db.Column(db.Numeric(10,2))

    uid = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    #Notes = db.Column(db.Text)

    order_item = db.relationship("OrderItem", back_populates="sold_receipt")
    #eBayAccount = db.Column(db.Text)


    updated_on = db.Column(db.DateTime(), default=datetime.utcnow,
                                          onupdate=datetime.utcnow)


# One line itme is one Amazon item
class LineItem(db.Model):
    __tablename__ = 'line_item'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    OrderID = db.Column(db.String(60), db.ForeignKey('order_item.OrderID'))
    OrderLineItemID = db.Column(db.String(30))
    #ItemID = db.Column(db.BIGINT, db.ForeignKey('active_item.ItemID'))
    Title = db.Column(db.String(80))
    Quantity = db.Column(db.Integer)
    Asin = db.Column(db.String(12))
    #AzOrderID = db.Column(db.String(70))
    PurchasePrice = db.Column(db.Numeric(10,2))
    Paid = db.Column(db.Numeric(10,2))
    Profit = db.Column(db.Numeric(10,2))
    Tax = db.Column(db.Numeric(10,2))
    SellerPaidStatus = db.Column(db.String(35))

    Notes = db.Column(db.Text)
    PrivateNotes = db.Column(db.String(70))

    PaymentHoldStatus = db.Column(db.String(12))

    order_item = db.relationship("OrderItem", back_populates="line_item")

# Model for items we scraped off Amazon
class ScrapedItem(db.Model):
    __tablename__ = 'scraped_item'
   # id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Asin = db.Column(db.String(12),nullable=False, primary_key=True)
    Title = db.Column(db.String(300))
    Price = db.Column(db.Numeric(10,2))
    Description = db.Column(db.Text)
    MPN = db.Column(db.String(60))
    Brand = db.Column(db.String(50))
    Category = db.Column(db.String(15))
    UPC = db.Column(db.String(20))
    Quantity = db.Column(db.Integer)
    PicURLs = db.Column(db.Text)
    Listed = db.Column(db.Boolean,default=False)

    uid = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Model for custom description template on eBay
class DescriptionTemplate(db.Model):
    __tablename__ = 'description_template'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    TemplateName = db.Column(db.String(20))
    Template = db.Column(db.Text)
    uid = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    #user = db.relationship("User", back_populates="description_template")

# Blacklist of names and brands for scraper
class BlackList(db.Model):
    __tablename__ = 'blacklist'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ListName = db.Column(db.String(10))
    List = db.Column(db.Text)
    #uid = db.Column(db.Integer, db.ForeignKey('user.id'))
    uid = db.Column(db.Integer)
    ##have to manually add and delete for new user
#
# class RemovedSoldItems(db.Model):
#     __tablename__ = 'removed_sold_items'
#     Asin = db.Column(db.String(12),nullable=False, primary_key=True)

# Model to show notifications on the top right of header
class Notification(db.Model):
    __tablename__ = 'notification'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uid = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    icon = db.Column(db.Text)
    type = db.Column(db.Integer,default=0)
    msg = db.Column(db.Text)
    link = db.Column(db.Text)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow,
                                          onupdate=datetime.utcnow)