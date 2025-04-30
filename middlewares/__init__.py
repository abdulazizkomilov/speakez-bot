from loader import dp
from .user import UserMiddleware, StreamingGuardMiddleware
from .channels import SubscriptionMiddleware
from .throttling import ThrottlingMiddleware

if __name__ == "middlewares":
    dp.message.middleware(UserMiddleware())
    dp.message.middleware(StreamingGuardMiddleware())
    dp.message.middleware(SubscriptionMiddleware())
    dp.message.middleware(ThrottlingMiddleware())
