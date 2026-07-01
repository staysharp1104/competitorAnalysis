from app.routes.projects import router as projects_router
from app.routes.pages import router as pages_router
from app.routes.features import router as features_router
from app.routes.analysis import router as analysis_router
from app.routes.export import router as export_router
from app.routes.comparison import router as comparison_router
from app.routes.crawler import router as crawler_router
from app.routes.monitor import router as monitor_router
from app.routes.images import router as images_router

routers = [projects_router, pages_router, features_router, analysis_router, export_router, comparison_router, crawler_router, monitor_router, images_router]
