"""ECS Fargate for newsradar_smcp + ECR + EventBridge schedules."""

from aws_cdk import (
    Stack,
    Duration,
    aws_ec2 as ec2,
    aws_ecr as ecr,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_logs as logs,
    aws_events as events,
    aws_events_targets as events_targets,
    aws_s3 as s3,
    aws_sns as sns,
)
from constructs import Construct


class PipelineStack(Stack):
    """ECS Fargate task for newsradar_smcp pipeline + EventBridge schedules.

    - 0.5 vCPU, 1 GB memory
    - EventBridge: vigilancia weekly (Mon 6:00 UTC), search papers/repos
      (monthly day 1), search patents (quarterly)
    - Least-privilege task role: S3 r/w, Secrets Manager read, SNS publish,
      CloudWatch Logs, Bedrock invoke-model

    Requisitos: 10.1, 10.2, 10.3, 10.9
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        vpc: ec2.IVpc,
        artifacts_bucket: s3.IBucket,
        log_group: logs.ILogGroup,
        alerts_topic: sns.ITopic,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ECR repository
        self.ecr_repo = ecr.Repository(
            self,
            "SmcpEcrRepo",
            repository_name="newsradar-smcp",
        )

        # ECS cluster
        self.cluster = ecs.Cluster(
            self, "PipelineCluster", vpc=vpc, cluster_name="news-radar-pipeline"
        )

        # Task role — least-privilege for smcp component
        task_role = iam.Role(
            self,
            "SmcpTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )
        artifacts_bucket.grant_read_write(task_role)
        log_group.grant_write(task_role)
        alerts_topic.grant_publish(task_role)
        task_role.add_to_policy(
            iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=["arn:aws:secretsmanager:*:*:secret:news-radar/*"],
            )
        )
        task_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=["*"],  # Bedrock model ARNs are region-specific
            )
        )

        # Fargate task definition — 0.5 vCPU, 1 GB
        task_def = ecs.FargateTaskDefinition(
            self,
            "SmcpTaskDef",
            cpu=512,
            memory_limit_mib=1024,
            task_role=task_role,
        )

        task_def.add_container(
            "SmcpContainer",
            image=ecs.ContainerImage.from_ecr_repository(self.ecr_repo),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="smcp", log_group=log_group
            ),
            environment={
                "ARTIFACTS_BUCKET": artifacts_bucket.bucket_name,
                "SNS_TOPIC_ARN": alerts_topic.topic_arn,
            },
        )

        # --- EventBridge schedules ---

        # Vigilancia weekly: Monday 6:00 UTC
        events.Rule(
            self,
            "VigilanciaWeeklySchedule",
            schedule=events.Schedule.cron(
                minute="0", hour="6", week_day="MON"
            ),
            targets=[
                events_targets.EcsTask(
                    cluster=self.cluster,
                    task_definition=task_def,
                    subnet_selection=ec2.SubnetSelection(
                        subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                    ),
                )
            ],
        )

        # Search papers & repos: monthly day 1
        events.Rule(
            self,
            "SearchPapersReposSchedule",
            schedule=events.Schedule.cron(
                minute="0", hour="7", day="1", month="*"
            ),
            targets=[
                events_targets.EcsTask(
                    cluster=self.cluster,
                    task_definition=task_def,
                    subnet_selection=ec2.SubnetSelection(
                        subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                    ),
                )
            ],
        )

        # Search patents: quarterly (Jan, Apr, Jul, Oct day 1)
        events.Rule(
            self,
            "SearchPatentsSchedule",
            schedule=events.Schedule.cron(
                minute="0", hour="8", day="1", month="1,4,7,10"
            ),
            targets=[
                events_targets.EcsTask(
                    cluster=self.cluster,
                    task_definition=task_def,
                    subnet_selection=ec2.SubnetSelection(
                        subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                    ),
                )
            ],
        )
