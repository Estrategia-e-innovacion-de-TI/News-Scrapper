"""CloudWatch log group (30d retention) + SNS topic news-radar-alerts."""

from aws_cdk import (
    Stack,
    aws_logs as logs,
    aws_sns as sns,
)
from constructs import Construct


class MonitoringStack(Stack):
    """CloudWatch logs + SNS alerting.

    Requisitos: 10.6
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # CloudWatch log group — 30 day retention
        self.log_group = logs.LogGroup(
            self,
            "NewsRadarLogGroup",
            log_group_name="/news-radar/pipeline",
            retention=logs.RetentionDays.ONE_MONTH,
        )

        # SNS topic for run failure notifications
        self.alerts_topic = sns.Topic(
            self,
            "AlertsTopic",
            topic_name="news-radar-alerts",
            display_name="News Radar Pipeline Alerts",
        )
