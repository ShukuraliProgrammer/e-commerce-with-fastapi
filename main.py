from fastapi import FastAPI, Request, Depends
from tortoise import models
from tortoise.contrib.fastapi import register_tortoise
from models import *
from authentication import get_hash_password, token_generator
from tortoise.signals import post_save
from tortoise import BaseDBAsyncClient
from typing import List, Optional, Type
from fastapi.responses import HTMLResponse
from authentication import verify_token
from fastapi.templating import Jinja2Templates
from emails import *
from fastapi.exceptions import HTTPException
from fastapi import status
from fastapi.security import (OAuth2PasswordBearer, OAuth2PasswordRequestFormStrict)

# image upload
from fastapi import File, UploadFile
import secrets
from fastapi.staticfiles import StaticFiles
from PIL import Image

# static file setup

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return {"Message": "HI"}


oath2_schema = OAuth2PasswordBearer(tokenUrl='token')


@app.post("/token")
async def generate_token(request_form: OAuth2PasswordRequestFormStrict = Depends()):
    token = await token_generator(request_form.username, request_form.password)
    return {
        "access_token": token,
        "Type": "Bearer",
    }


async def get_current_user(token: str = Depends(oath2_schema)):
    try:
        payload = jwt.decode(token, config["SECRET"], algorithms=['HS256'])
        user = await User.get(id=payload.get("id"))
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid User data",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user


@app.post("/user/me")
async def user_login(user: user_pydanticIn = Depends(get_current_user)):
    business = await Business.get(owner=user)
    logo = business.logo
    logo_path = "localhost:8000/static/images/" + logo

    return {
        "status": "Ok",
        "data": {
            "username": user.username,
            "email": user.email,
            "is_verify": user.is_verified,
            "created_at": user.created_at.strftime("%b %d %Y"),
            "logo": logo_path
        }
    }


templates = Jinja2Templates(directory="templates")


@app.get("/verification", response_class=HTMLResponse)
async def email_verification(request: Request, token: str):
    user = await verify_token(token)
    print("token --> ", token)
    if user and not user.is_verified:
        user.is_verified = True
        await user.save()
        return templates.TemplateResponse("verification.html", {"request": request, "user": user.username})

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid Token or Expired Token",
        headers={"WWW-Authenticate": "Bearer"}
    )


@post_save(User)
async def create_business(
        sender: "Type[User]",
        instance: User,
        created: bool,
        using_db: "Optional[BaseDBAsyncClient]",
        update_fields: List[str]
) -> None:
    if created:
        business_obj = await Business.create(
            name=instance.username, owner=instance
        )

        await business_pydantic.from_tortoise_orm(business_obj)
        # send email
        await send_email([instance.email], instance)


@app.post("/registration")
async def user_registrations(user: user_pydanticIn):
    user_info = user.dict(exclude_unset=True)
    user_info['password'] = get_hash_password(user_info['password'])
    user_obj = await User.create(**user_info)
    new_user = await user_pydantic.from_tortoise_orm(user_obj)
    return {
        "status": "Ok",
        "data": f"Hello {new_user.username}, thanks for registrations.\n"
                f"Please check your email and click on the link to confirm you registrations"
    }


@app.post("/products/create")
async def create_product(product: product_pydantic,
                         user: user_pydantic = Depends(get_current_user)):
    product = product.dict(exclude_unset=True)
    if product['original_price'] > 0:
        product['original_price'] = ((product["original_price"] - product['new_price']) / product[
            'original_price']) * 100

    product_obj = await Product.create(**product, business=user)
    product_obj = await product_pydantic.from_tortoise_orm(product_obj)
    return {
        "status": "ok",
        "data": product_obj
    }


@app.get("/products")
async def get_products():
    response = await product_pydantic.from_queryset(Product.all())
    return {
        "status": "Ok",
        "data": response
    }


@app.get("/products/{id}")
async def get_product_detail(id: int):
    product = await Product.get(id=id)
    business = await product.business
    owner = await business.owner
    response = await product_pydantic.from_queryset_single(Product.get(id=id))
    return {
        "status": "Ok",
        "data": {
            "product_information": response,
            "business_information": {
                "name": business.name,
                "city": business.city,
                "region": business.region,
                "description": business.description,
                "logo": business.logo,
                "business_id": business.id,
                "owner": owner.id
            }
        }
    }


@app.delete("/product/{id}")
async def delete_product(id: int, user: user_pydantic = Depends(get_current_user)):
    product = await Product.get(id=id)
    business = await product.business
    owner = await business.owner
    if owner == user:
        await product.delete()
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated to perform this action",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.put("/product/update")
async def product_update(id: int,
                         update_info: product_pydantiIn,
                         user: user_pydantic = Depends(get_current_user)):
    product = await Product.get(id=id)
    business = await product.business
    owner = await business.owner

    update_info = update_info.dict(exclude_unset=True)
    if owner == user and update_info['original_price'] != 0:
        await product.update_from_dict(update_info)
        await product.save()
        response = await product_pydantic.from_tortoise_orm(product)
        return {
            "status": "Ok",
            "data": response
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated to perform this action",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.put("/business/update")
async def update_business(id: int,
                          update_info: business_pydanticIn,
                          user: user_pydantic = Depends(get_current_user)):
    business = await Business.get(id=id)
    owner = await business.owner
    update_info = update_info.dict()
    if owner == user:
        await business.update_from_dict(update_info)
        await business.save()
        response = await business_pydantic.from_tortoise_orm(business)
        return {
            "status": "Ok",
            "data": response
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated to perform this action",
            headers={"WWW-Authenticate": "Bearer"},
        )


# image upload
@app.post("/uploadfile/profile")
async def create_upload_file(file: UploadFile = File(...),
                             user: user_pydantic = Depends(get_current_user)):
    FILEPATH = "./static/images/"
    filename = file.filename
    extension = filename.split(".")[1]

    if extension not in ["jpg", "png"]:
        return {"status": "error", "detail": "file extension not allowed"}

    token_name = secrets.token_hex(10) + "." + extension
    generated_name = FILEPATH + token_name
    file_content = await file.read()
    with open(generated_name, "wb") as file:
        file.write(file_content)

    # pillow
    img = Image.open(generated_name)
    img = img.resize(size=(200, 200))
    img.save(generated_name)

    file.close()

    business = await Business.get(owner=user)
    owner = await business.owner

    # check if the user making the request is authenticated
    print(user.id)
    print(owner.id)
    if owner == user:
        business.logo = token_name
        await business.save()

    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated to perform this action",
            headers={"WWW-Authenticate": "Bearer"},
        )
    file_url = "localhost:8000" + generated_name[1:]
    return {"status": "ok", "filename": file_url}


@app.post("/uploadfile/product/{id}")
async def uploadfile_product(id: int, file: UploadFile = File(...),
                             user: user_pydantic = Depends(get_current_user)):
    FILEPATH = "./static/images/"
    filename = file.filename
    extension = filename.split(".")[1]

    if extension not in ["jpg", "png"]:
        return {"status": "error", "detail": "file extension not allowed"}

    token_name = secrets.token_hex(10) + "." + extension
    generated_name = FILEPATH + token_name
    file_content = await file.read()
    with open(generated_name, "wb") as file:
        file.write(file_content)

    # pillow
    img = Image.open(generated_name)
    img = img.resize(size=(200, 200))
    img.save(generated_name)

    file.close()

    product = await Product.get(id=id)
    business = await product.business
    owner = await business.owner
    if owner == user:
        product.image = token_name
        await product.save()

    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated to perform this action",
            headers={"WWW-Authenticate": "Bearer"},
        )

    file_url = "http://localhost:8000" + generated_name[1:]
    return {
        "status": "ok",
        "filename": file_url
    }


register_tortoise(
    app,
    db_url="sqlite://database.sqlite3",
    modules={"models": ["models"]},
    generate_schemas=True,
    add_exception_handlers=True
)
