from app.models.project import Project
from app.models.page import CrawledPage, PageContent
from app.models.feature import FeatureNode
from app.models.analysis import AnalysisReport, AnalysisTemplate
from app.models.conversation import Conversation, ConversationMessage
from app.models.comparison import ComparisonAnalysis
from app.models.crawler import CrawlTask
from app.models.error_log import ErrorLog
from app.models.project_image import ProjectImage

all_models = [Project, CrawledPage, PageContent, FeatureNode, AnalysisReport, AnalysisTemplate, Conversation, ConversationMessage, ComparisonAnalysis, CrawlTask, ErrorLog, ProjectImage]
