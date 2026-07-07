from fastapi import APIRouter
from .endpoints import auth, file, item, location, member, order, order_comment, order_confirm, user

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(member.router, prefix="/member", tags=["member"])
api_router.include_router(user.router, prefix="/user", tags=["user"])
api_router.include_router(location.router, prefix="/location", tags=["location"])
api_router.include_router(item.router, prefix="/item", tags=["item"])
api_router.include_router(order.router, prefix="/order", tags=["order"])
api_router.include_router(order_confirm.router, prefix="/order/confirm", tags=["order-confirm"])
api_router.include_router(order_comment.router, prefix="/order/comment", tags=["order-comment"])
api_router.include_router(file.router, prefix="/file", tags=["file"])
