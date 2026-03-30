#!/usr/bin/env python3
"""CDK app entry point — instantiates all News Radar stacks."""

import aws_cdk as cdk
from aws_cdk import aws_ec2 as ec2

from storage_stack import StorageStack
from monitoring_stack import MonitoringStack
from pipeline_stack import PipelineStack
from api_stack import ApiStack
from agent_stack import AgentStack
from frontend_stack import FrontendStack

app = cdk.App()

env = cdk.Environment(
    account=app.node.try_get_context("account") or "123456789012",
    region=app.node.try_get_context("region") or "us-east-1",
)

# Shared VPC — TODO: import existing VPC or create new one for SBX
vpc_stack = cdk.Stack(app, "NewsRadarVpc", env=env)
vpc = ec2.Vpc(
    vpc_stack,
    "Vpc",
    vpc_name="news-radar-sbx",
    max_azs=2,
    nat_gateways=1,
)

# Foundation stacks
storage = StorageStack(app, "NewsRadarStorage", env=env)
monitoring = MonitoringStack(app, "NewsRadarMonitoring", env=env)

# Compute stacks
pipeline = PipelineStack(
    app,
    "NewsRadarPipeline",
    vpc=vpc,
    artifacts_bucket=storage.artifacts_bucket,
    log_group=monitoring.log_group,
    alerts_topic=monitoring.alerts_topic,
    env=env,
)

api = ApiStack(
    app,
    "NewsRadarApi",
    vpc=vpc,
    artifacts_bucket=storage.artifacts_bucket,
    log_group=monitoring.log_group,
    env=env,
)

agent = AgentStack(
    app,
    "NewsRadarAgent",
    vpc=vpc,
    log_group=monitoring.log_group,
    env=env,
)

frontend = FrontendStack(app, "NewsRadarFrontend", env=env)

app.synth()
