from tortoise import Model, fields
from pydantic import BaseModel
from datetime import datetime
from tortoise.contrib.pydantic import pydantic_model_creator


class User(Model):
    id = fields.IntField(pk=True, index=True)
    username = fields.CharField(max_length=30, null=False, unique=True)
    email = fields.CharField(max_length=100, null=False, unique=True)
    password = fields.CharField(max_length=100, null=False)
    is_verified = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(default=datetime.utcnow)


class Business(Model):
    id = fields.IntField(pk=True, index=True)
    name = fields.CharField(max_length=120, unique=True)
    city = fields.CharField(max_length=120, default="Unspecified")
    region = fields.CharField(max_length=120, default="Unspecified")
    description = fields.TextField(null=True)
    logo = fields.CharField(max_length=120, null=False, default="default.png")
    owner = fields.ForeignKeyField("models.User", related_name="businesses")


# class Category(Model):
#     id = fields.IntField(pk=True, index=True)
#     name = fields.CharField(max_length=120, null=False)


class Product(Model):
    id = fields.IntField(pk=True, index=True)
    name = fields.CharField(max_length=120, null=True, index=True)
    # category = fields.ForeignKeyField("models.Category", related_name="products")
    original_price = fields.DecimalField(max_digits=12, decimal_places=2)
    new_price = fields.DecimalField(max_digits=12, decimal_places=2)
    percentage_discount = fields.IntField()
    expires_in = fields.DatetimeField(default=datetime.utcnow)
    image = fields.CharField(max_length=120, null=False, default="default_product_img.jpg")
    business = fields.ForeignKeyField("models.Business", related_name="products")


user_pydantic = pydantic_model_creator(User, name="User", exclude=("is_verified",))
user_pydanticIn = pydantic_model_creator(User, name="UserIn", exclude_readonly=True,
                                         exclude=("created_at", "is_verified"))
user_pydanticOut = pydantic_model_creator(User, name="UserOut", exclude=("password",))

business_pydantic = pydantic_model_creator(Business, name="Business")
business_pydanticIn = pydantic_model_creator(Business, name="BusinessIn", exclude_readonly=True, exclude=("logo", "id"))

product_pydantic = pydantic_model_creator(Product, name="Product")
product_pydantiIn = pydantic_model_creator(Product, name="ProductIn", exclude=("percentage_discount", "id", "image"))
