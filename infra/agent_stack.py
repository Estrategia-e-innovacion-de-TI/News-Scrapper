"""ECS Fargate for newsradar_aiagent."""

from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecr as ecr,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_logs as logs,
)
from constructs import Construct


class AgentStack(Stack):
    """ECS Fargate service for newsradar_aiagent.

    Least-privilege task role: Bedrock invoke-model only.

    Requisitos: 10.1, 10.9
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        vpc: ec2.IVpc,
        log_group: logs.ILogGroup,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ECR repository
        self.ecr_repo = ecr.Repository(
            self, "AgentEcrRepo", repository_name="newsradar-aiagent"
        )

        # Task role — least-privilege for aiagent component
        task_role = iam.Role(
            self,
            "AgentTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )
        task_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=["*"],
            )
        )

        # ECS cluster
        cluster = ecs.Cluster(
            self, "AgentCluster", vpc=vpc, cluster_name="news-radar-agent"
        )

        # Fargate task definition
        task_def = ecs.FargateTaskDefinition(
            self,
            "AgentTaskDef",
            cpu=512,
            memory_limit_mib=1024,
            task_role=task_role,
        )

        task_def.add_container(
            "AgentContainer",
            image=ecs.ContainerImage.from_ecr_repository(self.ecr_repo),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="aiagent", log_group=log_group
            ),
        )

        # Fargate service
        self.service = ecs.FargateService(
            self,
            "AgentService",
            cluster=cluster,
            task_definition=task_def,
            desired_count=1,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
        )
