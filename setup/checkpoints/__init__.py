from .base import BaseCheckpoint, CheckpointResult
from .o1_salesforce import SalesforceCheckpoint  # noqa: E402
from .o2_slack import SlackCheckpoint
from .o3_bedrock_gateway import BedrockGatewayCheckpoint
from .o4_orchestrator import OrchestratorCheckpoint
from .o5_system_apis import SystemApisCheckpoint
from .o6_deploy import DeployCheckpoint

CHECKPOINTS = [
    SalesforceCheckpoint(),
    SlackCheckpoint(),
    BedrockGatewayCheckpoint(),
    OrchestratorCheckpoint(),
    SystemApisCheckpoint(),
    DeployCheckpoint(),
]
