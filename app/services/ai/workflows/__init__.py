"""AI工作流"""

from .workflows import (
    AIWorkflow,
    FaultAnalysisWorkflow,
    HealthAnalysisWorkflow,
    PredictiveMaintenanceWorkflow,
    get_workflow,
    list_workflows
)

__all__ = [
    'AIWorkflow',
    'FaultAnalysisWorkflow',
    'HealthAnalysisWorkflow',
    'PredictiveMaintenanceWorkflow',
    'get_workflow',
    'list_workflows',
]